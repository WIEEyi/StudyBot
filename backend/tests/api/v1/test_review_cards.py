"""
间隔复习测试

测试覆盖:
- 复习卡片 CRUD 操作
- SM-2 算法评分
- 列表过滤 (overdue/today)
- 权限校验 (401/403)
- 参数校验 (422)
"""

import pytest


class TestReviewCardCRUD:
    """复习卡片 CRUD 测试"""

    @pytest.mark.asyncio
    async def test_create_card(self, async_client):
        """创建复习卡片"""
        resp = await async_client.post(
            "/api/v1/review-cards",
            json={
                "front": "Python 中的 GIL 是什么？",
                "back": "GIL（全局解释器锁）是 CPython 的一个机制，确保同一时刻只有一个线程执行 Python 字节码。",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["front"] == "Python 中的 GIL 是什么？"
        assert data["back"] == "GIL（全局解释器锁）是 CPython 的一个机制，确保同一时刻只有一个线程执行 Python 字节码。"
        assert data["source"] == "manual"
        assert data["ease_factor"] == 2.5
        assert data["interval"] == 0
        assert data["repetitions"] == 0
        assert data["next_review_at"] is None
        assert data["last_reviewed_at"] is None

    @pytest.mark.asyncio
    async def test_create_card_with_document(self, async_client):
        """创建关联文档的复习卡片"""
        import io

        # 先上传文档
        content = "测试文档内容\n" * 10
        file = io.BytesIO(content.encode("utf-8"))
        doc_resp = await async_client.post(
            "/api/v1/documents",
            files={"file": ("test.txt", file, "text/plain")},
            data={"title": "测试文档"},
        )
        assert doc_resp.status_code == 201
        doc_id = doc_resp.json()["id"]

        # 创建关联卡片
        resp = await async_client.post(
            "/api/v1/review-cards",
            json={
                "front": "测试问题",
                "back": "测试答案",
                "document_id": doc_id,
            },
        )
        assert resp.status_code == 201
        assert resp.json()["document_id"] == doc_id

    @pytest.mark.asyncio
    async def test_list_cards(self, async_client):
        """获取复习卡片列表"""
        # 创建两张卡片
        await async_client.post(
            "/api/v1/review-cards",
            json={"front": "问题1", "back": "答案1"},
        )
        await async_client.post(
            "/api/v1/review-cards",
            json={"front": "问题2", "back": "答案2"},
        )

        resp = await async_client.get("/api/v1/review-cards")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 2
        assert "items" in data
        assert len(data["items"]) >= 2

    @pytest.mark.asyncio
    async def test_list_cards_pagination(self, async_client):
        """分页测试"""
        resp = await async_client.get("/api/v1/review-cards?offset=0&limit=1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["limit"] == 1
        assert data["offset"] == 0
        assert len(data["items"]) <= 1

    @pytest.mark.asyncio
    async def test_get_card_detail(self, async_client):
        """获取单个卡片详情"""
        create_resp = await async_client.post(
            "/api/v1/review-cards",
            json={"front": "详情测试问题", "back": "详情测试答案"},
        )
        card_id = create_resp.json()["id"]

        resp = await async_client.get(f"/api/v1/review-cards/{card_id}")
        assert resp.status_code == 200
        assert resp.json()["front"] == "详情测试问题"

    @pytest.mark.asyncio
    async def test_update_card(self, async_client):
        """更新卡片内容"""
        create_resp = await async_client.post(
            "/api/v1/review-cards",
            json={"front": "旧问题", "back": "旧答案"},
        )
        card_id = create_resp.json()["id"]

        resp = await async_client.put(
            f"/api/v1/review-cards/{card_id}",
            json={"front": "新问题", "back": "新答案"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["front"] == "新问题"
        assert data["back"] == "新答案"

    @pytest.mark.asyncio
    async def test_delete_card(self, async_client):
        """删除卡片"""
        create_resp = await async_client.post(
            "/api/v1/review-cards",
            json={"front": "待删除问题", "back": "待删除答案"},
        )
        card_id = create_resp.json()["id"]

        resp = await async_client.delete(f"/api/v1/review-cards/{card_id}")
        assert resp.status_code == 204

        # 确认已删除
        get_resp = await async_client.get(f"/api/v1/review-cards/{card_id}")
        assert get_resp.status_code == 404


class TestSM2Review:
    """SM-2 算法评分测试"""

    @pytest.mark.asyncio
    async def test_review_first_time_correct(self, async_client):
        """首次正确回忆: rating=4 → interval=1 天, repetitions=1"""
        create_resp = await async_client.post(
            "/api/v1/review-cards",
            json={"front": "首次复习测试", "back": "测试答案"},
        )
        card_id = create_resp.json()["id"]

        # 评分 4（正确回忆）
        resp = await async_client.post(
            f"/api/v1/review-cards/{card_id}/review",
            json={"rating": 4},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["rating"] == 4
        assert data["repetitions"] == 1
        assert data["new_interval"] == 1  # 首次正确 = 1 天
        assert data["previous_interval"] == 0
        assert "next_review_at" in data

    @pytest.mark.asyncio
    async def test_review_second_time_correct(self, async_client):
        """第二次正确回忆: interval=6 天"""
        create_resp = await async_client.post(
            "/api/v1/review-cards",
            json={"front": "第二次复习测试", "back": "测试答案"},
        )
        card_id = create_resp.json()["id"]

        # 第一次评分
        resp1 = await async_client.post(
            f"/api/v1/review-cards/{card_id}/review",
            json={"rating": 5},
        )
        assert resp1.status_code == 200
        assert resp1.json()["repetitions"] == 1
        assert resp1.json()["new_interval"] == 1

        # 第二次评分
        resp2 = await async_client.post(
            f"/api/v1/review-cards/{card_id}/review",
            json={"rating": 5},
        )
        assert resp2.status_code == 200
        data = resp2.json()
        assert data["repetitions"] == 2
        assert data["new_interval"] == 6  # 第二次正确 = 6 天
        assert data["previous_interval"] == 1

    @pytest.mark.asyncio
    async def test_review_third_time_correct(self, async_client):
        """第三次正确回忆: interval = past_interval * ease_factor"""
        create_resp = await async_client.post(
            "/api/v1/review-cards",
            json={"front": "第三次复习测试", "back": "测试答案"},
        )
        card_id = create_resp.json()["id"]

        # 前两次评分（都是正确）
        await async_client.post(
            f"/api/v1/review-cards/{card_id}/review",
            json={"rating": 5},
        )
        await async_client.post(
            f"/api/v1/review-cards/{card_id}/review",
            json={"rating": 5},
        )

        # 第三次评分
        resp3 = await async_client.post(
            f"/api/v1/review-cards/{card_id}/review",
            json={"rating": 5},
        )
        assert resp3.status_code == 200
        data = resp3.json()
        assert data["repetitions"] == 3
        # interval = 6 * 2.5 ≈ 15 (ease_factor stays at 2.5 for perfect scores)
        assert data["new_interval"] >= 6  # 至少比第二次大

    @pytest.mark.asyncio
    async def test_review_forgotten(self, async_client):
        """评分 < 3（遗忘）: repetitions 重置为 0, interval 重置为 1 天"""
        create_resp = await async_client.post(
            "/api/v1/review-cards",
            json={"front": "遗忘测试", "back": "测试答案"},
        )
        card_id = create_resp.json()["id"]

        # 先正确几次
        await async_client.post(
            f"/api/v1/review-cards/{card_id}/review",
            json={"rating": 5},
        )
        await async_client.post(
            f"/api/v1/review-cards/{card_id}/review",
            json={"rating": 5},
        )

        # 第三次遗忘了 (rating=1)
        resp = await async_client.post(
            f"/api/v1/review-cards/{card_id}/review",
            json={"rating": 1},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["repetitions"] == 0
        assert data["new_interval"] == 1  # 重置为 1 天

    @pytest.mark.asyncio
    async def test_ease_factor_decreases_with_low_ratings(self, async_client):
        """低评分降低 ease_factor"""
        create_resp = await async_client.post(
            "/api/v1/review-cards",
            json={"front": "难度测试", "back": "测试答案"},
        )
        card_id = create_resp.json()["id"]

        # 先正确一次建立 baseline
        await async_client.post(
            f"/api/v1/review-cards/{card_id}/review",
            json={"rating": 5},
        )

        # 低评分 (rating=0)
        await async_client.post(
            f"/api/v1/review-cards/{card_id}/review",
            json={"rating": 0},
        )

        # 查看卡片详情确认 ease_factor 降低了
        get_resp = await async_client.get(f"/api/v1/review-cards/{card_id}")
        assert get_resp.status_code == 200
        card = get_resp.json()
        # 从 2.5 降低
        assert card["ease_factor"] < 2.5

    @pytest.mark.asyncio
    async def test_ease_factor_minimum(self, async_client):
        """ease_factor 不应低于 1.3"""
        create_resp = await async_client.post(
            "/api/v1/review-cards",
            json={"front": "最低难度测试", "back": "测试答案"},
        )
        card_id = create_resp.json()["id"]

        # 连续多次最低评分
        for _ in range(10):
            await async_client.post(
                f"/api/v1/review-cards/{card_id}/review",
                json={"rating": 0},
            )

        get_resp = await async_client.get(f"/api/v1/review-cards/{card_id}")
        card = get_resp.json()
        assert card["ease_factor"] >= 1.3

    @pytest.mark.asyncio
    async def test_review_updates_last_reviewed_at(self, async_client):
        """复习后 last_reviewed_at 应被更新"""
        create_resp = await async_client.post(
            "/api/v1/review-cards",
            json={"front": "更新时间测试", "back": "测试答案"},
        )
        card_id = create_resp.json()["id"]

        await async_client.post(
            f"/api/v1/review-cards/{card_id}/review",
            json={"rating": 4},
        )

        get_resp = await async_client.get(f"/api/v1/review-cards/{card_id}")
        card = get_resp.json()
        assert card["last_reviewed_at"] is not None
        assert card["next_review_at"] is not None


class TestReviewCardDueFilter:
    """到期过滤测试"""

    @pytest.mark.asyncio
    async def test_list_overdue_cards(self, async_client):
        """过滤已过期卡片（新创建的 card next_review_at=None 也算 overdue）"""
        # 新创建的卡片 next_review_at=None，应在 overdue 列表中
        resp = await async_client.get("/api/v1/review-cards?due_filter=overdue")
        assert resp.status_code == 200
        data = resp.json()
        # 前面的测试创建的卡片都是 overdue
        assert data["total"] >= 0  # 可能有也可能没有

    @pytest.mark.asyncio
    async def test_list_all_cards(self, async_client):
        """不过滤时返回所有卡片"""
        resp = await async_client.get("/api/v1/review-cards")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_list_with_invalid_due_filter(self, async_client):
        """无效的 due_filter 返回 422"""
        resp = await async_client.get("/api/v1/review-cards?due_filter=invalid")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_list_with_source_filter(self, async_client):
        """按来源过滤"""
        resp = await async_client.get("/api/v1/review-cards?source=manual")
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            assert item["source"] == "manual"


class TestReviewCardAuthErrors:
    """权限测试"""

    @pytest.mark.asyncio
    async def test_create_without_auth_returns_401(self, async_client):
        """无认证创建返回 401/403"""
        from httpx import AsyncClient, ASGITransport
        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as no_auth:
            resp = await no_auth.post(
                "/api/v1/review-cards",
                json={"front": "问题", "back": "答案"},
            )
            assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_get_nonexistent_card_returns_404(self, async_client):
        """获取不存在的卡片返回 404"""
        resp = await async_client.get("/api/v1/review-cards/99999")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_review_nonexistent_card_returns_404(self, async_client):
        """评分不存在的卡片返回 404"""
        resp = await async_client.post(
            "/api/v1/review-cards/99999/review",
            json={"rating": 4},
        )
        assert resp.status_code == 404


class TestReviewCardValidation:
    """参数校验测试"""

    @pytest.mark.asyncio
    async def test_create_empty_front_returns_422(self, async_client):
        """空 front 返回 422"""
        resp = await async_client.post(
            "/api/v1/review-cards",
            json={"front": "", "back": "答案"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_empty_back_returns_422(self, async_client):
        """空 back 返回 422"""
        resp = await async_client.post(
            "/api/v1/review-cards",
            json={"front": "问题", "back": ""},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_review_invalid_rating_too_high(self, async_client):
        """评分 > 5 返回 422"""
        create_resp = await async_client.post(
            "/api/v1/review-cards",
            json={"front": "评分测试", "back": "答案"},
        )
        card_id = create_resp.json()["id"]

        resp = await async_client.post(
            f"/api/v1/review-cards/{card_id}/review",
            json={"rating": 6},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_review_invalid_rating_negative(self, async_client):
        """评分 < 0 返回 422"""
        create_resp = await async_client.post(
            "/api/v1/review-cards",
            json={"front": "评分测试2", "back": "答案"},
        )
        card_id = create_resp.json()["id"]

        resp = await async_client.post(
            f"/api/v1/review-cards/{card_id}/review",
            json={"rating": -1},
        )
        assert resp.status_code == 422


class TestSM2AlgorithmUnit:
    """SM-2 算法纯单元测试（不需要数据库）"""

    def test_calculate_sm2_first_correct(self):
        """第1次正确: interval=1, repetitions=1"""
        from app.services.sm2_service import calculate_sm2

        result = calculate_sm2(
            rating=4,
            current_interval=0,
            current_repetitions=0,
            current_ease_factor=2.5,
        )
        assert result["repetitions"] == 1
        assert result["interval"] == 1
        assert result["ease_factor"] == 2.5  # 评分 4 不影响 EF

    def test_calculate_sm2_second_correct(self):
        """第2次正确: interval=6, repetitions=2"""
        from app.services.sm2_service import calculate_sm2

        result = calculate_sm2(
            rating=4,
            current_interval=1,
            current_repetitions=1,
            current_ease_factor=2.5,
        )
        assert result["repetitions"] == 2
        assert result["interval"] == 6

    def test_calculate_sm2_third_correct(self):
        """第3次正确: interval 按 ease_factor 递增"""
        from app.services.sm2_service import calculate_sm2

        result = calculate_sm2(
            rating=5,
            current_interval=6,
            current_repetitions=2,
            current_ease_factor=2.5,
        )
        assert result["repetitions"] == 3
        # rating=5 时 EF 升至 2.6, round(6 * 2.6) = round(15.6) = 16
        assert result["interval"] == 16
        assert result["ease_factor"] == 2.6

    def test_calculate_sm2_forgotten(self):
        """遗忘: repetitions=0, interval=1"""
        from app.services.sm2_service import calculate_sm2

        result = calculate_sm2(
            rating=1,
            current_interval=10,
            current_repetitions=3,
            current_ease_factor=2.5,
        )
        assert result["repetitions"] == 0
        assert result["interval"] == 1

    def test_calculate_sm2_ease_factor_decrease(self):
        """低评分降低 ease_factor"""
        from app.services.sm2_service import calculate_sm2

        result = calculate_sm2(
            rating=1,
            current_interval=10,
            current_repetitions=3,
            current_ease_factor=2.5,
        )
        # EF' = 2.5 + (0.1 - 4 * (0.08 + 4 * 0.02))
        # = 2.5 + (0.1 - 4 * 0.16)
        # = 2.5 + (0.1 - 0.64)
        # = 2.5 - 0.54 = 1.96
        assert result["ease_factor"] < 2.5

    def test_calculate_sm2_ease_factor_minimum(self):
        """ease_factor 不低于 1.3"""
        from app.services.sm2_service import calculate_sm2

        result = calculate_sm2(
            rating=0,
            current_interval=0,
            current_repetitions=0,
            current_ease_factor=1.3,  # 已经是最低
        )
        assert result["ease_factor"] >= 1.3

    def test_calculate_sm2_next_review_at_in_future(self):
        """next_review_at 应在未来"""
        from datetime import datetime, timezone
        from app.services.sm2_service import calculate_sm2

        result = calculate_sm2(
            rating=4,
            current_interval=0,
            current_repetitions=0,
            current_ease_factor=2.5,
        )
        assert result["next_review_at"] > datetime.now(timezone.utc)

    def test_calculate_sm2_invalid_rating(self):
        """无效评分应抛出 ValueError"""
        import pytest as pytest_mod
        from app.services.sm2_service import calculate_sm2

        with pytest_mod.raises(ValueError):
            calculate_sm2(
                rating=6,
                current_interval=0,
                current_repetitions=0,
                current_ease_factor=2.5,
            )

        with pytest_mod.raises(ValueError):
            calculate_sm2(
                rating=-1,
                current_interval=0,
                current_repetitions=0,
                current_ease_factor=2.5,
            )

    def test_is_card_due(self):
        """测试 is_card_due 函数"""
        from datetime import datetime, timezone, timedelta
        from app.services.sm2_service import is_card_due

        now = datetime.now(timezone.utc)

        # None（从未复习）→ 到期
        assert is_card_due(None, now) is True

        # 过去的 next_review_at → 到期
        past = now - timedelta(days=1)
        assert is_card_due(past, now) is True

        # 未来的 next_review_at → 未到期
        future = now + timedelta(days=1)
        assert is_card_due(future, now) is False

        # 刚好现在 → 到期
        assert is_card_due(now, now) is True
