"""
QA API 单元测试

覆盖:
- POST /qa/ask — RAG 问答
- 有文档和无文档的场景
- 异常: 401
"""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
class TestQAAsk:
    """POST /qa/ask — RAG 问答"""

    async def test_ask_without_documents(self, async_client: AsyncClient):
        """无文档时问答"""
        resp = await async_client.post("/api/v1/qa/ask", json={
            "question": "What is Python?",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["question"] == "What is Python?"
        assert "answer" in data
        assert "citations" in data

    async def test_ask_with_document(self, async_client: AsyncClient):
        """上传文档后问答"""
        # 先上传文档
        files = {"file": ("python_guide.txt", b"Python is a high-level programming language known for its simplicity and readability.", "text/plain")}
        await async_client.post("/api/v1/documents", files=files)

        resp = await async_client.post("/api/v1/qa/ask", json={
            "question": "What is Python?",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["question"] == "What is Python?"
        assert len(data["citations"]) > 0  # 应该找到相关文档

    async def test_ask_with_specific_document(self, async_client: AsyncClient):
        """指定文档 ID 问答"""
        # 先上传文档
        files = {"file": ("specific_doc.txt", b"Machine learning is a subset of AI.", "text/plain")}
        create_resp = await async_client.post("/api/v1/documents", files=files)
        doc_id = create_resp.json()["id"]

        resp = await async_client.post("/api/v1/qa/ask", json={
            "question": "What is machine learning?",
            "document_id": doc_id,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["question"] == "What is machine learning?"

    async def test_ask_without_auth(self):
        """未认证 → 401"""
        from httpx import AsyncClient, ASGITransport
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/v1/qa/ask", json={
                "question": "test",
            })
            assert resp.status_code in (401, 403)

    async def test_ask_empty_question(self, async_client: AsyncClient):
        """空问题 → 422"""
        resp = await async_client.post("/api/v1/qa/ask", json={
            "question": "",
        })
        assert resp.status_code == 422
