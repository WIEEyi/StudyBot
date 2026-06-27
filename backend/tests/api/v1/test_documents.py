"""
Documents API 单元测试

覆盖:
- 上传文档（PDF/TXT/MD/HTML）
- 文档列表（分页 + 类型过滤）
- 文档详情
- 删除文档
- 异常: 401/403/404
"""

import io
import pytest
from httpx import AsyncClient


@pytest.mark.anyio
class TestUploadDocument:
    """POST /documents — 上传文档"""

    async def test_upload_txt(self, async_client: AsyncClient):
        """上传 TXT 文件"""
        content = b"This is a test document about Python programming."
        files = {"file": ("test.txt", content, "text/plain")}
        resp = await async_client.post("/api/v1/documents", files=files)
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "test"
        assert data["file_type"] == "txt"
        assert "Python" in data["content"]

    async def test_upload_md(self, async_client: AsyncClient):
        """上传 Markdown 文件"""
        content = b"# Hello\n\nThis is **markdown** content."
        files = {"file": ("notes.md", content, "text/markdown")}
        resp = await async_client.post("/api/v1/documents", files=files)
        assert resp.status_code == 201
        data = resp.json()
        assert data["file_type"] == "md"
        assert "markdown" in data["content"].lower()

    async def test_upload_html(self, async_client: AsyncClient):
        """上传 HTML 文件"""
        content = b"<html><body><h1>Title</h1><p>Paragraph text</p></body></html>"
        files = {"file": ("page.html", content, "text/html")}
        resp = await async_client.post("/api/v1/documents", files=files)
        assert resp.status_code == 201
        data = resp.json()
        assert data["file_type"] == "html"
        assert "Paragraph text" in data["content"]

    async def test_upload_pdf(self, async_client: AsyncClient):
        """上传 PDF 文件（最小有效 PDF）"""
        # 最小的有效 PDF 文件
        pdf_content = (
            b"%PDF-1.0\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
            b"3 0 obj<</Type/Page/MediaBox[0 0 3 3]>>endobj\n"
            b"xref\n0 4\n0000000000 65535 f \n"
            b"0000000009 00000 n \n0000000058 00000 n \n"
            b"0000000115 00000 n \n"
            b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF"
        )
        files = {"file": ("doc.pdf", pdf_content, "application/pdf")}
        resp = await async_client.post("/api/v1/documents", files=files)
        assert resp.status_code == 201
        data = resp.json()
        assert data["file_type"] == "pdf"


@pytest.mark.anyio
class TestListDocuments:
    """GET /documents — 文档列表"""

    async def test_list_documents(self, async_client: AsyncClient):
        """获取文档列表"""
        # 先上传一个文档
        files = {"file": ("list_test.txt", b"content here", "text/plain")}
        await async_client.post("/api/v1/documents", files=files)

        resp = await async_client.get("/api/v1/documents")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1

    async def test_filter_by_type(self, async_client: AsyncClient):
        """按类型过滤文档"""
        resp = await async_client.get("/api/v1/documents?file_type=txt")
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            assert item["file_type"] == "txt"

    async def test_list_without_auth(self):
        """未认证访问列表 → 401"""
        from httpx import AsyncClient, ASGITransport
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/documents")
            assert resp.status_code in (401, 403)


@pytest.mark.anyio
class TestGetDocument:
    """GET /documents/{id} — 文档详情"""

    async def test_get_existing(self, async_client: AsyncClient):
        """获取已存在的文档"""
        # 先上传
        files = {"file": ("detail_test.txt", b"detail content", "text/plain")}
        create_resp = await async_client.post("/api/v1/documents", files=files)
        doc_id = create_resp.json()["id"]

        resp = await async_client.get(f"/api/v1/documents/{doc_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == doc_id

    async def test_get_nonexistent(self, async_client: AsyncClient):
        """获取不存在的文档 → 404"""
        resp = await async_client.get("/api/v1/documents/99999")
        assert resp.status_code == 404


@pytest.mark.anyio
class TestDeleteDocument:
    """DELETE /documents/{id} — 删除文档"""

    async def test_delete_existing(self, async_client: AsyncClient):
        """删除已存在的文档"""
        # 先上传
        files = {"file": ("delete_me.txt", b"to be deleted", "text/plain")}
        create_resp = await async_client.post("/api/v1/documents", files=files)
        doc_id = create_resp.json()["id"]

        resp = await async_client.delete(f"/api/v1/documents/{doc_id}")
        assert resp.status_code == 204

        # 确认已删除
        resp = await async_client.get(f"/api/v1/documents/{doc_id}")
        assert resp.status_code == 404

    async def test_delete_nonexistent(self, async_client: AsyncClient):
        """删除不存在的文档 → 404"""
        resp = await async_client.delete("/api/v1/documents/99999")
        assert resp.status_code == 404
