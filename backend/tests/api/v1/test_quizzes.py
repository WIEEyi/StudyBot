"""
测验题测试

测试覆盖:
- AI 生成题目正常流程
- 题目列表/详情/删除
- 权限和参数校验
"""

import io
import pytest
from unittest.mock import MagicMock, AsyncMock


# ===================== Mock LLM =====================

class MockQuizItem:
    def __init__(self, type="multiple_choice", question="", options=None, correct_answer="", explanation=""):
        self.type = type
        self.question = question
        self.options = options or []
        self.correct_answer = correct_answer
        self.explanation = explanation

    def model_dump(self):
        return {
            "type": self.type,
            "question": self.question,
            "options": self.options,
            "correct_answer": self.correct_answer,
            "explanation": self.explanation,
        }


class MockQuizOutput:
    def __init__(self, quizzes=None):
        self.quizzes = quizzes or [
            MockQuizItem(
                type="multiple_choice",
                question="Python 中的列表(list)和元组(tuple)有什么区别？",
                options=["列表可变，元组不可变", "列表不可变，元组可变", "两者完全相同", "两者都不可变"],
                correct_answer="列表可变，元组不可变",
                explanation="列表使用 [] 创建，支持增删改；元组使用 () 创建，一旦创建不能修改。",
            ),
            MockQuizItem(
                type="true_false",
                question="Python 中字典的键必须是不可变类型。",
                options=["对", "错"],
                correct_answer="对",
                explanation="字典的键必须是可哈希的，而可哈希的类型都是不可变类型（如字符串、数字、元组）。",
            ),
            MockQuizItem(
                type="short_answer",
                question="什么是 Python 装饰器？",
                options=[],
                correct_answer="装饰器是一个接受函数作为参数并返回新函数的可调用对象，用于在不修改原函数的情况下扩展其功能。",
                explanation="装饰器是 Python 中实现 AOP（面向切面编程）的方式。",
            ),
        ]


class MockStructuredLLM:
    async def ainvoke(self, messages, **kwargs):
        return MockQuizOutput()


class MockChatOpenAI:
    def __init__(self, **kwargs):
        pass

    def with_structured_output(self, schema, **kwargs):
        return MockStructuredLLM()


@pytest.fixture(autouse=True)
def mock_llm_quiz(monkeypatch):
    """Mock ChatOpenAI，避免测试中调用真实 OpenAI API"""
    monkeypatch.setattr(
        "app.agents.quiz_agent.ChatOpenAI",
        lambda **kwargs: MockChatOpenAI(**kwargs),
    )


# ===================== 正常流程 =====================

class TestQuizGenerate:
    @pytest.mark.asyncio
    async def test_generate_from_document(self, async_client):
        """AI 从文档生成题目"""
        content = ("Python 是一种高级编程语言。列表(list)是可变序列，使用 [] 创建。"
                   "元组(tuple)是不可变序列，使用 () 创建。"
                   "字典(dict)是键值对集合，键必须是不可变类型。"
                   "装饰器(decorator)是对函数的包装，用 @ 语法使用。\n") * 10
        file = io.BytesIO(content.encode("utf-8"))
        doc_resp = await async_client.post(
            "/api/v1/documents",
            files={"file": ("python_basics.txt", file, "text/plain")},
            data={"title": "Python 基础"},
        )
        assert doc_resp.status_code == 201
        doc_id = doc_resp.json()["id"]

        resp = await async_client.post(
            "/api/v1/quizzes/generate",
            json={"document_id": doc_id, "num_questions": 3},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["document_id"] == doc_id
        assert data["total"] == 3
        assert len(data["quizzes"]) == 3

        for q in data["quizzes"]:
            assert "id" in q
            assert "question" in q
            assert "correct_answer" in q
            assert q["source"] == "ai_generated"
            assert q["document_id"] == doc_id

    @pytest.mark.asyncio
    async def test_generate_default_num_questions(self, async_client):
        """不传 num_questions 时默认生成 5 道题目"""
        content = "测试内容。\n" * 15
        file = io.BytesIO(content.encode("utf-8"))
        doc_resp = await async_client.post(
            "/api/v1/documents",
            files={"file": ("test.txt", file, "text/plain")},
            data={"title": "测试"},
        )
        assert doc_resp.status_code == 201
        doc_id = doc_resp.json()["id"]

        resp = await async_client.post(
            "/api/v1/quizzes/generate",
            json={"document_id": doc_id},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["total"] == 3  # mock 返回 3 道题


class TestQuizList:
    @pytest.mark.asyncio
    async def test_list_quizzes(self, async_client):
        """列出测验题"""
        resp = await async_client.get("/api/v1/quizzes")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_list_filter_by_document(self, async_client):
        """按文档 ID 过滤"""
        # 先上传文档并生成题目
        content = "过滤测试文档内容。\n" * 10
        file = io.BytesIO(content.encode("utf-8"))
        doc_resp = await async_client.post(
            "/api/v1/documents",
            files={"file": ("filter_test.txt", file, "text/plain")},
            data={"title": "过滤测试"},
        )
        assert doc_resp.status_code == 201
        doc_id = doc_resp.json()["id"]

        await async_client.post(
            "/api/v1/quizzes/generate",
            json={"document_id": doc_id, "num_questions": 3},
        )

        resp = await async_client.get(f"/api/v1/quizzes?document_id={doc_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 3


class TestQuizDetail:
    @pytest.mark.asyncio
    async def test_get_quiz(self, async_client):
        """获取题目详情"""
        # 先生成一道题目
        content = "详情测试内容。\n" * 10
        file = io.BytesIO(content.encode("utf-8"))
        doc_resp = await async_client.post(
            "/api/v1/documents",
            files={"file": ("detail.txt", file, "text/plain")},
            data={"title": "详情测试"},
        )
        doc_id = doc_resp.json()["id"]

        gen_resp = await async_client.post(
            "/api/v1/quizzes/generate",
            json={"document_id": doc_id, "num_questions": 3},
        )
        quiz_id = gen_resp.json()["quizzes"][0]["id"]

        resp = await async_client.get(f"/api/v1/quizzes/{quiz_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == quiz_id


class TestQuizDelete:
    @pytest.mark.asyncio
    async def test_delete_quiz(self, async_client):
        """删除题目"""
        content = "删除测试内容。\n" * 10
        file = io.BytesIO(content.encode("utf-8"))
        doc_resp = await async_client.post(
            "/api/v1/documents",
            files={"file": ("delete_test.txt", file, "text/plain")},
            data={"title": "删除测试"},
        )
        doc_id = doc_resp.json()["id"]

        gen_resp = await async_client.post(
            "/api/v1/quizzes/generate",
            json={"document_id": doc_id, "num_questions": 3},
        )
        quiz_id = gen_resp.json()["quizzes"][0]["id"]

        del_resp = await async_client.delete(f"/api/v1/quizzes/{quiz_id}")
        assert del_resp.status_code == 204

        # 确认已删除
        get_resp = await async_client.get(f"/api/v1/quizzes/{quiz_id}")
        assert get_resp.status_code == 404


# ===================== 权限测试 =====================

class TestQuizAuthErrors:
    @pytest.mark.asyncio
    async def test_generate_without_auth(self, async_client):
        """无认证生成返回 401/403"""
        from httpx import AsyncClient, ASGITransport
        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as no_auth:
            resp = await no_auth.post(
                "/api/v1/quizzes/generate",
                json={"document_id": 1, "num_questions": 3},
            )
            assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_generate_nonexistent_document(self, async_client):
        """生成题目前文档不存在返回 404"""
        resp = await async_client.post(
            "/api/v1/quizzes/generate",
            json={"document_id": 99999, "num_questions": 3},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_nonexistent_quiz(self, async_client):
        """获取不存在的题目返回 404"""
        resp = await async_client.get("/api/v1/quizzes/99999")
        assert resp.status_code == 404


# ===================== 参数校验 =====================

class TestQuizValidation:
    @pytest.mark.asyncio
    async def test_generate_invalid_num_questions_too_high(self, async_client):
        """num_questions > 10 返回 422"""
        resp = await async_client.post(
            "/api/v1/quizzes/generate",
            json={"document_id": 1, "num_questions": 11},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_generate_invalid_num_questions_too_low(self, async_client):
        """num_questions < 1 返回 422"""
        resp = await async_client.post(
            "/api/v1/quizzes/generate",
            json={"document_id": 1, "num_questions": 0},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_list_invalid_source(self, async_client):
        """无效 source 过滤返回 422"""
        resp = await async_client.get("/api/v1/quizzes?source=invalid")
        assert resp.status_code == 422
