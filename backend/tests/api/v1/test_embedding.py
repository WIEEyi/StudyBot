"""
文档嵌入向量化测试

测试覆盖:
- 上传文档后自动创建分块
- 显式 embed 端点调用
- 空内容 / 不存在文档 / 未认证等异常路径
- 分块列表分页和排序
"""

import io
import pytest


class TestAutoEmbedOnUpload:
    """上传后自动嵌入测试"""

    @pytest.mark.asyncio
    async def test_upload_txt_auto_creates_chunks(self, async_client):
        """上传 TXT 文档后应自动创建分块"""
        content = "这是Python编程语言的学习笔记。\n" * 30
        file = io.BytesIO(content.encode("utf-8"))
        response = await async_client.post(
            "/api/v1/documents",
            files={"file": ("test.txt", file, "text/plain")},
            data={"title": "Python学习笔记"},
        )
        assert response.status_code == 201
        doc = response.json()

        # 检查自动创建的分块
        chunks_resp = await async_client.get(
            f"/api/v1/documents/{doc['id']}/chunks"
        )
        assert chunks_resp.status_code == 200
        chunks_data = chunks_resp.json()
        assert chunks_data["total"] >= 1
        assert len(chunks_data["items"]) >= 1

    @pytest.mark.asyncio
    async def test_upload_pdf_auto_creates_chunks(self, async_client):
        """上传 PDF 后应自动创建分块"""
        # 用最简 PDF 测试（仅含文本的 PDF）
        pdf_content = (
            b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
            b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\n"
            b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n"
            b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF"
        )
        file = io.BytesIO(pdf_content)
        response = await async_client.post(
            "/api/v1/documents",
            files={"file": ("sample.pdf", file, "application/pdf")},
            data={"title": "PDF文档"},
        )
        assert response.status_code == 201
        doc = response.json()

        # PDF 可能提取为空文本（因为是最简 PDF），所以不强制检查分块数
        chunks_resp = await async_client.get(
            f"/api/v1/documents/{doc['id']}/chunks"
        )
        assert chunks_resp.status_code == 200


class TestExplicitEmbed:
    """显式 embed 端点测试"""

    @pytest.mark.asyncio
    async def test_embed_endpoint_returns_chunks_created(self, async_client):
        """显式调用 embed 端点返回正确的 chunks_created"""
        content = "这是机器学习入门课程的学习资料。\n" * 40
        file = io.BytesIO(content.encode("utf-8"))
        resp = await async_client.post(
            "/api/v1/documents",
            files={"file": ("ml.txt", file, "text/plain")},
            data={"title": "机器学习"},
        )
        doc_id = resp.json()["id"]

        # 显式调用 embed（会先删旧块再重新创建）
        embed_resp = await async_client.post(
            f"/api/v1/documents/{doc_id}/embed"
        )
        assert embed_resp.status_code == 200
        data = embed_resp.json()
        assert data["document_id"] == doc_id
        assert data["chunks_created"] >= 1

    @pytest.mark.asyncio
    async def test_embed_empty_content_returns_422(self, async_client):
        """空内容文档调用 embed 返回 422"""
        # 先上传一个空文件
        file = io.BytesIO(b"")
        resp = await async_client.post(
            "/api/v1/documents",
            files={"file": ("empty.txt", file, "text/plain")},
            data={"title": "空文件"},
        )
        # 空文件上传本身应该被拒绝（Step 9 的逻辑）
        if resp.status_code == 201:
            doc_id = resp.json()["id"]
            embed_resp = await async_client.post(
                f"/api/v1/documents/{doc_id}/embed"
            )
            # 内容为空时应返回 422
            assert embed_resp.status_code == 422

    @pytest.mark.asyncio
    async def test_embed_nonexistent_document_returns_404(self, async_client):
        """embed 不存在的文档返回 404"""
        resp = await async_client.post("/api/v1/documents/99999/embed")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_reembedding_replaces_chunks(self, async_client):
        """重复 embed 会替换旧分块，不会翻倍"""
        content = "深度学习基础知识。\n" * 30
        file = io.BytesIO(content.encode("utf-8"))
        resp = await async_client.post(
            "/api/v1/documents",
            files={"file": ("dl.txt", file, "text/plain")},
            data={"title": "深度学习"},
        )
        doc_id = resp.json()["id"]

        # 第一次获取分块数
        chunks1 = await async_client.get(f"/api/v1/documents/{doc_id}/chunks")
        count1 = chunks1.json()["total"]

        # 显式重新嵌入
        embed_resp = await async_client.post(f"/api/v1/documents/{doc_id}/embed")
        assert embed_resp.status_code == 200

        # 第二次获取分块数（应该与第一次相同，不会翻倍）
        chunks2 = await async_client.get(f"/api/v1/documents/{doc_id}/chunks")
        count2 = chunks2.json()["total"]

        assert count2 == count1


class TestDocumentChunkList:
    """分块列表测试"""

    @pytest.mark.asyncio
    async def test_chunks_ordered_by_index(self, async_client):
        """分块按 chunk_index 升序排列"""
        content = "第一章\n" + ("Python基础 " * 100) + "\n第二章\n" + ("数据结构 " * 100)
        file = io.BytesIO(content.encode("utf-8"))
        resp = await async_client.post(
            "/api/v1/documents",
            files={"file": ("chapters.txt", file, "text/plain")},
            data={"title": "有序章节"},
        )
        assert resp.status_code == 201
        doc_id = resp.json()["id"]

        chunks_resp = await async_client.get(
            f"/api/v1/documents/{doc_id}/chunks"
        )
        items = chunks_resp.json()["items"]
        assert len(items) >= 1

        # 验证 chunk_index 递增
        indices = [c["chunk_index"] for c in items]
        assert indices == sorted(indices)

    @pytest.mark.asyncio
    async def test_chunks_pagination(self, async_client):
        """分块列表支持分页"""
        content = ("长篇学习资料内容。\n" * 100)
        file = io.BytesIO(content.encode("utf-8"))
        resp = await async_client.post(
            "/api/v1/documents",
            files={"file": ("long.txt", file, "text/plain")},
            data={"title": "长文档"},
        )
        doc_id = resp.json()["id"]

        # 分页：每页 2 条
        page1 = await async_client.get(
            f"/api/v1/documents/{doc_id}/chunks?offset=0&limit=2"
        )
        assert page1.status_code == 200
        data1 = page1.json()
        assert len(data1["items"]) <= 2

        # 验证 total > limit 表示有更多数据
        if data1["total"] > 2:
            page2 = await async_client.get(
                f"/api/v1/documents/{doc_id}/chunks?offset=2&limit=2"
            )
            assert page2.status_code == 200
            data2 = page2.json()
            assert len(data2["items"]) >= 1
            # 两页的 chunk_index 不重复
            idx_page1 = {c["chunk_index"] for c in data1["items"]}
            idx_page2 = {c["chunk_index"] for c in data2["items"]}
            assert idx_page1.isdisjoint(idx_page2)

    @pytest.mark.asyncio
    async def test_chunks_no_embedding_in_response(self, async_client):
        """分块响应中不应包含 embedding 向量字段"""
        content = "测试文档内容。" * 20
        file = io.BytesIO(content.encode("utf-8"))
        resp = await async_client.post(
            "/api/v1/documents",
            files={"file": ("no_emb.txt", file, "text/plain")},
            data={"title": "无向量测试"},
        )
        doc_id = resp.json()["id"]

        chunks_resp = await async_client.get(
            f"/api/v1/documents/{doc_id}/chunks"
        )
        items = chunks_resp.json()["items"]
        assert len(items) >= 1
        # 不应该包含 embedding 字段
        assert "embedding" not in items[0]

    @pytest.mark.asyncio
    async def test_chunks_nonexistent_document_returns_404(self, async_client):
        """不存在的文档的分块列表返回 404"""
        resp = await async_client.get("/api/v1/documents/99999/chunks")
        assert resp.status_code == 404


class TestEmbedAuthErrors:
    """嵌入权限测试"""

    @pytest.mark.asyncio
    async def test_embed_without_auth_returns_401(self, async_client):
        """无认证调用 embed 返回 401/403"""
        # 创建临时客户端（无 token）
        from httpx import AsyncClient, ASGITransport
        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as no_auth:
            resp = await no_auth.post("/api/v1/documents/1/embed")
            assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_chunks_without_auth_returns_401(self, async_client):
        """无认证调用 chunks 返回 401/403"""
        from httpx import AsyncClient, ASGITransport
        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as no_auth:
            resp = await no_auth.get("/api/v1/documents/1/chunks")
            assert resp.status_code in (401, 403)
