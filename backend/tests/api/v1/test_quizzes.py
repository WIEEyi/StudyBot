"""
测验题 CRUD 单元测试

覆盖:
- 正常路径: 创建/列表/详情/更新/删除/生成/批改
- 异常路径: 401 未认证 / 404 不存在 / 422 参数校验
"""

import pytest


# ===================== 正常路径测试 =====================

class TestCreateQuiz:
    """POST /quizzes — 创建测验题"""

    @pytest.mark.asyncio
    async def test_create_with_all_fields(self, async_client):
        """创建带所有字段的测验题"""
        response = await async_client.post("/api/v1/quizzes", json={
            "question": "Python 中的列表和元组有什么区别？",
            "options": ["列表可变", "元组可变", "两者都不可变", "两者都可变"],
            "correct_answer": 0,
            "explanation": "列表是可变的，元组是不可变的",
            "source": "manual",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["question"] == "Python 中的列表和元组有什么区别？"
        assert len(data["options"]) == 4
        assert data["correct_answer"] == 0
        assert data["explanation"] == "列表是可变的，元组是不可变的"
        assert data["source"] == "manual"
        assert data["document_id"] is None
        assert "id" in data
        assert "created_at" in data

        # 清理
        await async_client.delete(f"/api/v1/quizzes/{data['id']}")

    @pytest.mark.asyncio
    async def test_create_minimal(self, async_client):
        """只传必填字段（question + options + correct_answer）"""
        response = await async_client.post("/api/v1/quizzes", json={
            "question": "最小题目",
            "options": ["对", "错"],
            "correct_answer": 0,
        })
        assert response.status_code == 201
        data = response.json()
        assert data["question"] == "最小题目"
        assert len(data["options"]) == 2
        assert data["correct_answer"] == 0
        assert data["source"] == "manual"  # 默认值

        await async_client.delete(f"/api/v1/quizzes/{data['id']}")

    @pytest.mark.asyncio
    async def test_create_invalid_answer_index(self, async_client):
        """correct_answer 超出 options 范围 → 422"""
        response = await async_client.post("/api/v1/quizzes", json={
            "question": "测试",
            "options": ["A", "B", "C"],
            "correct_answer": 5,  # 超出范围
        })
        assert response.status_code == 422


class TestListQuizzes:
    """GET /quizzes — 分页列表"""

    @pytest.mark.asyncio
    async def test_list_empty(self, async_client):
        """空列表"""
        response = await async_client.get("/api/v1/quizzes")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "offset" in data
        assert "limit" in data
        assert isinstance(data["items"], list)

    @pytest.mark.asyncio
    async def test_list_with_pagination(self, async_client):
        """分页参数"""
        response = await async_client.get("/api/v1/quizzes?offset=0&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert data["offset"] == 0
        assert data["limit"] == 5

    @pytest.mark.asyncio
    async def test_list_filter_by_document(self, async_client):
        """按 document_id 过滤 — 无文档的测验不出现"""
        # 先创建测验（不带 document_id）
        r = await async_client.post("/api/v1/quizzes", json={
            "question": "过滤测试题目",
            "options": ["是", "否"],
            "correct_answer": 0,
        })
        assert r.status_code == 201
        quiz_id = r.json()["id"]

        # 用不存在的 document_id 过滤，不应返回该测验
        response = await async_client.get("/api/v1/quizzes?document_id=99999")
        assert response.status_code == 200
        data = response.json()
        quiz_ids = [q["id"] for q in data["items"]]
        assert quiz_id not in quiz_ids

        await async_client.delete(f"/api/v1/quizzes/{quiz_id}")

    @pytest.mark.asyncio
    async def test_list_with_data(self, async_client):
        """列表中有数据时的基本断言"""
        r = await async_client.post("/api/v1/quizzes", json={
            "question": "列表测试题目",
            "options": ["对", "错"],
            "correct_answer": 1,
        })
        assert r.status_code == 201
        quiz_id = r.json()["id"]

        response = await async_client.get("/api/v1/quizzes")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert isinstance(data["items"], list)

        await async_client.delete(f"/api/v1/quizzes/{quiz_id}")


class TestGetQuiz:
    """GET /quizzes/{id} — 详情"""

    @pytest.mark.asyncio
    async def test_get_existing(self, async_client):
        """获取存在的测验题"""
        r = await async_client.post("/api/v1/quizzes", json={
            "question": "详情测试题目",
            "options": ["选项A", "选项B", "选项C", "选项D"],
            "correct_answer": 2,
            "explanation": "这是解析",
        })
        assert r.status_code == 201
        quiz_id = r.json()["id"]

        response = await async_client.get(f"/api/v1/quizzes/{quiz_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == quiz_id
        assert data["question"] == "详情测试题目"
        assert data["correct_answer"] == 2
        assert data["explanation"] == "这是解析"

        await async_client.delete(f"/api/v1/quizzes/{quiz_id}")

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, async_client):
        """获取不存在的测验题 → 404"""
        response = await async_client.get("/api/v1/quizzes/99999")
        assert response.status_code == 404


class TestUpdateQuiz:
    """PUT /quizzes/{id} — 更新"""

    @pytest.mark.asyncio
    async def test_update_all_fields(self, async_client):
        """更新所有字段"""
        r = await async_client.post("/api/v1/quizzes", json={
            "question": "原标题",
            "options": ["旧A", "旧B"],
            "correct_answer": 0,
        })
        assert r.status_code == 201
        quiz_id = r.json()["id"]

        response = await async_client.put(f"/api/v1/quizzes/{quiz_id}", json={
            "question": "新标题",
            "options": ["新A", "新B", "新C"],
            "correct_answer": 2,
            "explanation": "新解析",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["question"] == "新标题"
        assert len(data["options"]) == 3
        assert data["correct_answer"] == 2
        assert data["explanation"] == "新解析"

        await async_client.delete(f"/api/v1/quizzes/{quiz_id}")

    @pytest.mark.asyncio
    async def test_update_nonexistent(self, async_client):
        """更新不存在的测验题 → 404"""
        response = await async_client.put("/api/v1/quizzes/99999", json={
            "question": "新标题",
        })
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_empty_body(self, async_client):
        """更新空请求体 → 400"""
        r = await async_client.post("/api/v1/quizzes", json={
            "question": "测试",
            "options": ["A", "B"],
            "correct_answer": 0,
        })
        assert r.status_code == 201
        quiz_id = r.json()["id"]

        response = await async_client.put(f"/api/v1/quizzes/{quiz_id}", json={})
        assert response.status_code == 400

        await async_client.delete(f"/api/v1/quizzes/{quiz_id}")


class TestDeleteQuiz:
    """DELETE /quizzes/{id} — 删除"""

    @pytest.mark.asyncio
    async def test_delete_existing(self, async_client):
        """删除存在的测验题 → 204"""
        r = await async_client.post("/api/v1/quizzes", json={
            "question": "待删除",
            "options": ["是", "否"],
            "correct_answer": 0,
        })
        assert r.status_code == 201
        quiz_id = r.json()["id"]

        response = await async_client.delete(f"/api/v1/quizzes/{quiz_id}")
        assert response.status_code == 204

        # 确认已删除
        get_r = await async_client.get(f"/api/v1/quizzes/{quiz_id}")
        assert get_r.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, async_client):
        """删除不存在的测验题 → 404"""
        response = await async_client.delete("/api/v1/quizzes/99999")
        assert response.status_code == 404


class TestGenerateQuiz:
    """POST /quizzes/generate — AI 生成"""

    @pytest.mark.asyncio
    async def test_generate_nonexistent_document(self, async_client):
        """不存在的文档 → 404"""
        response = await async_client.post("/api/v1/quizzes/generate", json={
            "document_id": 99999,
            "count": 3,
        })
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_generate_empty_content_document(self, async_client):
        """文档内容为空 → 400"""
        # 上传一个空内容文档
        files = {"file": ("empty.txt", b"", "text/plain")}
        create_resp = await async_client.post("/api/v1/documents", files=files)
        if create_resp.status_code == 201:
            doc_id = create_resp.json()["id"]
            response = await async_client.post("/api/v1/quizzes/generate", json={
                "document_id": doc_id,
                "count": 3,
            })
            assert response.status_code == 400
            # 清理
            await async_client.delete(f"/api/v1/documents/{doc_id}")


class TestGradeQuiz:
    """POST /quizzes/grade — 批改"""

    @pytest.mark.asyncio
    async def test_grade_all_correct(self, async_client):
        """全部答对"""
        # 创建 2 道题
        quizzes = []
        for i in range(2):
            r = await async_client.post("/api/v1/quizzes", json={
                "question": f"题目{i+1}",
                "options": ["A", "B", "C"],
                "correct_answer": 1,
            })
            assert r.status_code == 201
            quizzes.append(r.json())

        response = await async_client.post("/api/v1/quizzes/grade", json=[
            {"quiz_id": quizzes[0]["id"], "selected_index": 1},
            {"quiz_id": quizzes[1]["id"], "selected_index": 1},
        ])
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["correct_count"] == 2
        assert data["score_percent"] == 100.0
        assert len(data["results"]) == 2

        for q in quizzes:
            await async_client.delete(f"/api/v1/quizzes/{q['id']}")

    @pytest.mark.asyncio
    async def test_grade_partial(self, async_client):
        """部分答对"""
        r1 = await async_client.post("/api/v1/quizzes", json={
            "question": "题目1",
            "options": ["A", "B"],
            "correct_answer": 0,
        })
        r2 = await async_client.post("/api/v1/quizzes", json={
            "question": "题目2",
            "options": ["A", "B"],
            "correct_answer": 1,
        })
        assert r1.status_code == 201
        assert r2.status_code == 201
        q1_id = r1.json()["id"]
        q2_id = r2.json()["id"]

        response = await async_client.post("/api/v1/quizzes/grade", json=[
            {"quiz_id": q1_id, "selected_index": 0},  # 对
            {"quiz_id": q2_id, "selected_index": 0},  # 错
        ])
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["correct_count"] == 1
        assert data["score_percent"] == 50.0

        await async_client.delete(f"/api/v1/quizzes/{q1_id}")
        await async_client.delete(f"/api/v1/quizzes/{q2_id}")

    @pytest.mark.asyncio
    async def test_grade_empty_submission(self, async_client):
        """空提交 → 400"""
        response = await async_client.post("/api/v1/quizzes/grade", json=[])
        assert response.status_code == 400


# ===================== 异常路径测试 =====================

class TestUnauthorized:
    """401 未认证"""

    @pytest.mark.asyncio
    async def test_list_without_auth(self, async_client):
        """无认证获取列表"""
        headers = dict(async_client.headers)
        del async_client.headers["Authorization"]
        try:
            response = await async_client.get("/api/v1/quizzes")
            assert response.status_code in (401, 403)
        finally:
            async_client.headers.update(headers)

    @pytest.mark.asyncio
    async def test_create_without_auth(self, async_client):
        """无认证创建"""
        headers = dict(async_client.headers)
        del async_client.headers["Authorization"]
        try:
            response = await async_client.post("/api/v1/quizzes", json={
                "question": "test",
                "options": ["A", "B"],
                "correct_answer": 0,
            })
            assert response.status_code in (401, 403)
        finally:
            async_client.headers.update(headers)


class TestValidation:
    """422 参数校验"""

    @pytest.mark.asyncio
    async def test_create_empty_question(self, async_client):
        """空题目 → 422"""
        response = await async_client.post("/api/v1/quizzes", json={
            "question": "",
            "options": ["A", "B"],
            "correct_answer": 0,
        })
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_missing_options(self, async_client):
        """缺少 options → 422"""
        response = await async_client.post("/api/v1/quizzes", json={
            "question": "test",
            "correct_answer": 0,
        })
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_single_option(self, async_client):
        """只有 1 个选项 → 422（最少 2 个）"""
        response = await async_client.post("/api/v1/quizzes", json={
            "question": "test",
            "options": ["唯一选项"],
            "correct_answer": 0,
        })
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_negative_answer_index(self, async_client):
        """负数答案索引 → 422"""
        response = await async_client.post("/api/v1/quizzes", json={
            "question": "test",
            "options": ["A", "B"],
            "correct_answer": -1,
        })
        assert response.status_code == 422
