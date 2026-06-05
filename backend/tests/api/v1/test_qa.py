"""
RAG 问答测试

测试覆盖:
- 基本 RAG 问答正常流程
- 未认证请求返回 401
- 参数校验（空问题、过长问题、top_k 范围）
- document_id 不存在/无权限
- 无文档时仍可正常返回（优雅降级）
"""

import io
import pytest
from unittest.mock import MagicMock, AsyncMock


# ===================== Mock LLM =====================

class MockAnswerOutput:
    """模拟 LLM 结构化输出 AnswerOutput"""
    def __init__(self, answer="", citations=None):
        self.answer = answer
        self.citations = citations or []


class MockCitationOutput:
    """模拟 LLM 结构化输出 CitationOutput"""
    def __init__(self, chunk_id=0, excerpt=""):
        self.chunk_id = chunk_id
        self.excerpt = excerpt


class MockStructuredLLM:
    """模拟 ChatOpenAI.with_structured_output() 返回的对象"""
    def __init__(self, answer="", citations=None):
        self.answer = answer
        self.citations = citations or []

    async def ainvoke(self, messages, **kwargs):
        """模拟异步调用，返回 MockAnswerOutput"""
        return MockAnswerOutput(answer=self.answer, citations=self.citations)


class MockChatOpenAI:
    """模拟 langchain_openai.ChatOpenAI"""
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def with_structured_output(self, schema, **kwargs):
        """返回一个 mock structured LLM"""
        return MockStructuredLLM(
            answer="这是基于文档内容的模拟答案。",
            citations=[
                MockCitationOutput(chunk_id=1, excerpt="模拟引用原文片段"),
            ],
        )


@pytest.fixture(autouse=True)
def mock_llm(monkeypatch):
    """Mock ChatOpenAI，避免测试中调用真实 OpenAI LLM API"""
    # 创建一个 mock ChatOpenAI 类，每次实例化返回 MockChatOpenAI
    def mock_chat_openai_factory(**kwargs):
        return MockChatOpenAI(**kwargs)

    monkeypatch.setattr(
        "app.agents.digest_agent.ChatOpenAI",
        mock_chat_openai_factory,
    )
    # 同时 mock qa.py 中通过 run_digest 间接使用的 ChatOpenAI
    # （在 digest_agent 模块内部创建，已通过上面的 patch 覆盖）


# ===================== 正常流程测试 =====================

class TestQAAsk:
    """RAG 问答正常流程测试"""

    @pytest.mark.asyncio
    async def test_ask_returns_answer_with_citations(self, async_client):
        """基本 RAG 问答应返回答案和引用"""
        # 上传包含特定内容的文档
        content = "Python 的异步编程主要通过 asyncio 库来实现。核心概念包括协程 (coroutine) 和事件循环 (event loop)。\n" * 20
        file = io.BytesIO(content.encode("utf-8"))
        resp = await async_client.post(
            "/api/v1/documents",
            files={"file": ("python_async.txt", file, "text/plain")},
            data={"title": "Python 异步编程笔记"},
        )
        assert resp.status_code == 201

        # 提问
        qa_resp = await async_client.post(
            "/api/v1/qa/ask",
            json={
                "question": "Python 中如何实现异步编程",
                "top_k": 3,
            },
        )
        assert qa_resp.status_code == 200
        data = qa_resp.json()

        # 验证响应结构
        assert data["question"] == "Python 中如何实现异步编程"
        assert "answer" in data
        assert isinstance(data["answer"], str)
        assert len(data["answer"]) > 0
        assert "citations" in data
        assert isinstance(data["citations"], list)

        # 验证引用格式
        for citation in data["citations"]:
            assert "chunk_id" in citation
            assert "document_id" in citation
            assert "document_title" in citation
            assert "chunk_index" in citation
            assert "content" in citation
            assert "similarity" in citation

    @pytest.mark.asyncio
    async def test_ask_with_document_id_filter(self, async_client):
        """限定 document_id 的问答应在指定文档内搜索"""
        # 上传两个文档
        content1 = "机器学习是人工智能的一个分支，包括监督学习和无监督学习。\n" * 15
        file1 = io.BytesIO(content1.encode("utf-8"))
        resp1 = await async_client.post(
            "/api/v1/documents",
            files={"file": ("ml.txt", file1, "text/plain")},
            data={"title": "机器学习笔记"},
        )
        assert resp1.status_code == 201
        doc1_id = resp1.json()["id"]

        content2 = "Web 开发涉及前端 HTML/CSS/JS 和后端数据库技术。\n" * 15
        file2 = io.BytesIO(content2.encode("utf-8"))
        resp2 = await async_client.post(
            "/api/v1/documents",
            files={"file": ("web.txt", file2, "text/plain")},
            data={"title": "Web 开发笔记"},
        )
        assert resp2.status_code == 201

        # 限定搜索第一个文档
        qa_resp = await async_client.post(
            "/api/v1/qa/ask",
            json={
                "question": "什么是机器学习",
                "document_id": doc1_id,
                "top_k": 3,
            },
        )
        assert qa_resp.status_code == 200
        data = qa_resp.json()
        assert "answer" in data
        assert isinstance(data["citations"], list)

    @pytest.mark.asyncio
    async def test_ask_with_default_top_k(self, async_client):
        """不传 top_k 时应使用默认值 5"""
        content = "测试内容。\n" * 20
        file = io.BytesIO(content.encode("utf-8"))
        resp = await async_client.post(
            "/api/v1/documents",
            files={"file": ("test.txt", file, "text/plain")},
            data={"title": "测试"},
        )
        assert resp.status_code == 201

        qa_resp = await async_client.post(
            "/api/v1/qa/ask",
            json={"question": "测试问题"},
        )
        assert qa_resp.status_code == 200


# ===================== 参数校验测试 =====================

class TestQAValidation:
    """RAG 问答参数校验测试"""

    @pytest.mark.asyncio
    async def test_ask_empty_question_returns_422(self, async_client):
        """空问题应返回 422"""
        resp = await async_client.post(
            "/api/v1/qa/ask",
            json={"question": "", "top_k": 5},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_ask_question_too_long_returns_422(self, async_client):
        """超过 1000 字符的问题应返回 422"""
        resp = await async_client.post(
            "/api/v1/qa/ask",
            json={"question": "x" * 1001, "top_k": 5},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_ask_top_k_exceeds_max(self, async_client):
        """top_k > 20 应返回 422"""
        resp = await async_client.post(
            "/api/v1/qa/ask",
            json={"question": "测试", "top_k": 21},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_ask_top_k_below_min(self, async_client):
        """top_k < 1 应返回 422"""
        resp = await async_client.post(
            "/api/v1/qa/ask",
            json={"question": "测试", "top_k": 0},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_ask_missing_question_returns_422(self, async_client):
        """缺少必填字段 question 应返回 422"""
        resp = await async_client.post(
            "/api/v1/qa/ask",
            json={"top_k": 5},
        )
        assert resp.status_code == 422


# ===================== 权限测试 =====================

class TestQAAuthErrors:
    """RAG 问答权限测试"""

    @pytest.mark.asyncio
    async def test_ask_without_auth_returns_401(self, async_client):
        """无认证请求应返回 401/403"""
        from httpx import AsyncClient, ASGITransport
        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as no_auth:
            resp = await no_auth.post(
                "/api/v1/qa/ask",
                json={"question": "测试", "top_k": 5},
            )
            assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_ask_with_nonexistent_document_returns_404(self, async_client):
        """指定不存在的 document_id 应返回 404"""
        resp = await async_client.post(
            "/api/v1/qa/ask",
            json={
                "question": "测试问题",
                "document_id": 99999,  # 不存在的文档 ID
                "top_k": 5,
            },
        )
        assert resp.status_code == 404


# ===================== 边界条件测试 =====================

class TestQAEdgeCases:
    """RAG 问答边界条件测试"""

    @pytest.mark.asyncio
    async def test_ask_no_documents_no_crash(self, async_client):
        """没有上传任何文档时，问答不应崩溃（优雅降级）"""
        # 不传 document_id 的情况下，如果用户没有文档，搜索返回空
        # 但 conftest 中已有其他测试上传的文档...
        # 使用一个不太可能匹配的查询
        resp = await async_client.post(
            "/api/v1/qa/ask",
            json={
                "question": "这是一个几乎不可能匹配的特定问题 xyzabc123",
                "top_k": 3,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        # 即使没有找到相关内容，也应该返回一个友好的提示
        assert "answer" in data
        assert isinstance(data["answer"], str)
        assert len(data["answer"]) > 0  # 应该有一个错误提示消息

    @pytest.mark.asyncio
    async def test_ask_large_top_k_works(self, async_client):
        """使用最大 top_k (20) 应正常工作"""
        content = "深度学习是机器学习的一个子领域。\n" * 30
        file = io.BytesIO(content.encode("utf-8"))
        resp = await async_client.post(
            "/api/v1/documents",
            files={"file": ("dl.txt", file, "text/plain")},
            data={"title": "深度学习"},
        )
        assert resp.status_code == 201

        qa_resp = await async_client.post(
            "/api/v1/qa/ask",
            json={
                "question": "什么是深度学习",
                "top_k": 20,  # 最大允许值
            },
        )
        assert qa_resp.status_code == 200
        data = qa_resp.json()
        assert "answer" in data
