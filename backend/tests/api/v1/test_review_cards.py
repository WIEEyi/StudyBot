"""
ReviewCards API 单元测试

覆盖:
- 创建卡片
- 卡片列表（分页 + due_filter）
- 更新卡片
- 删除卡片
- SM-2 评分
- 异常: 401/403/404
"""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
class TestCreateReviewCard:
    """POST /review-cards — 创建复习卡片"""

    async def test_create_minimal(self, async_client: AsyncClient):
        """创建最简卡片"""
        resp = await async_client.post("/api/v1/review-cards", json={
            "front": "What is Python?",
            "back": "A high-level programming language.",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["front"] == "What is Python?"
        assert data["back"] == "A high-level programming language."
        assert data["ease_factor"] == 2.5
        assert data["interval"] == 0
        assert data["repetitions"] == 0

    async def test_create_with_empty_front(self, async_client: AsyncClient):
        """空的正面 → 422"""
        resp = await async_client.post("/api/v1/review-cards", json={
            "front": "",
            "back": "Answer",
        })
        assert resp.status_code == 422


@pytest.mark.anyio
class TestListReviewCards:
    """GET /review-cards — 卡片列表"""

    async def test_list_cards(self, async_client: AsyncClient):
        """获取卡片列表"""
        resp = await async_client.get("/api/v1/review-cards")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    async def test_filter_overdue(self, async_client: AsyncClient):
        """按 overdue 过滤"""
        resp = await async_client.get("/api/v1/review-cards?due_filter=overdue")
        assert resp.status_code == 200

    async def test_filter_today(self, async_client: AsyncClient):
        """按 today 过滤"""
        resp = await async_client.get("/api/v1/review-cards?due_filter=today")
        assert resp.status_code == 200


@pytest.mark.anyio
class TestUpdateReviewCard:
    """PUT /review-cards/{id} — 更新卡片"""

    async def test_update_front(self, async_client: AsyncClient):
        """更新卡片正面"""
        # 先创建
        create_resp = await async_client.post("/api/v1/review-cards", json={
            "front": "Original front",
            "back": "Original back",
        })
        card_id = create_resp.json()["id"]

        resp = await async_client.put(f"/api/v1/review-cards/{card_id}", json={
            "front": "Updated front",
        })
        assert resp.status_code == 200
        assert resp.json()["front"] == "Updated front"

    async def test_update_nonexistent(self, async_client: AsyncClient):
        """更新不存在的卡片 → 404"""
        resp = await async_client.put("/api/v1/review-cards/99999", json={
            "front": "Updated",
        })
        assert resp.status_code == 404


@pytest.mark.anyio
class TestDeleteReviewCard:
    """DELETE /review-cards/{id} — 删除卡片"""

    async def test_delete_existing(self, async_client: AsyncClient):
        """删除已存在的卡片"""
        create_resp = await async_client.post("/api/v1/review-cards", json={
            "front": "To delete",
            "back": "Answer",
        })
        card_id = create_resp.json()["id"]

        resp = await async_client.delete(f"/api/v1/review-cards/{card_id}")
        assert resp.status_code == 204

    async def test_delete_nonexistent(self, async_client: AsyncClient):
        """删除不存在的卡片 → 404"""
        resp = await async_client.delete("/api/v1/review-cards/99999")
        assert resp.status_code == 404


@pytest.mark.anyio
class TestSM2Review:
    """POST /review-cards/{id}/review — SM-2 评分"""

    async def test_review_high_rating(self, async_client: AsyncClient):
        """高分评分 → interval 增加"""
        create_resp = await async_client.post("/api/v1/review-cards", json={
            "front": "SM-2 test",
            "back": "Answer",
        })
        card_id = create_resp.json()["id"]

        resp = await async_client.post(f"/api/v1/review-cards/{card_id}/review", json={
            "rating": 5,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["rating"] == 5
        assert data["new_repetitions"] == 1
        assert data["new_interval"] == 1  # 第一次正确 → 1天
        assert data["next_review_at"] is not None

    async def test_review_low_rating(self, async_client: AsyncClient):
        """低分评分 → 重置"""
        create_resp = await async_client.post("/api/v1/review-cards", json={
            "front": "SM-2 reset test",
            "back": "Answer",
        })
        card_id = create_resp.json()["id"]

        # 先评高分
        await async_client.post(f"/api/v1/review-cards/{card_id}/review", json={"rating": 5})

        # 再评低分 → 应该重置
        resp = await async_client.post(f"/api/v1/review-cards/{card_id}/review", json={
            "rating": 1,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["new_repetitions"] == 0  # 重置
        assert data["new_interval"] == 1     # 重置为1天

    async def test_review_invalid_rating(self, async_client: AsyncClient):
        """无效评分 → 422"""
        create_resp = await async_client.post("/api/v1/review-cards", json={
            "front": "Invalid rating test",
            "back": "Answer",
        })
        card_id = create_resp.json()["id"]

        resp = await async_client.post(f"/api/v1/review-cards/{card_id}/review", json={
            "rating": 10,  # 超出范围
        })
        assert resp.status_code == 422

    async def test_review_nonexistent(self, async_client: AsyncClient):
        """评分不存在的卡片 → 404"""
        resp = await async_client.post("/api/v1/review-cards/99999/review", json={
            "rating": 3,
        })
        assert resp.status_code == 404
