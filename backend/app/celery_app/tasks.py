"""
Celery 异步任务

定义需要在后台执行的任务：
- 文档文本提取（大文件处理不阻塞 API）
- 文档向量化（Embedding 生成）
"""

import logging
from app.celery_app.celery import celery

logger = logging.getLogger(__name__)


@celery.task(bind=True, max_retries=3)
def extract_document_text(self, document_id: int, file_path: str, file_type: str) -> dict:
    """异步提取文档文本内容

    在后台 Worker 中执行，避免大文件处理阻塞 API 请求。
    提取完成后更新 Document.content 字段。

    Args:
        document_id: 文档 ID
        file_path: 文件在磁盘上的路径
        file_type: 文件类型 (pdf/md/txt/html)

    Returns:
        {"document_id": int, "content_length": int, "status": "success"|"error"}
    """
    try:
        # 读取文件
        with open(file_path, "rb") as f:
            file_bytes = f.read()

        # 根据类型提取文本
        if file_type == "pdf":
            from PyPDF2 import PdfReader
            import io
            reader = PdfReader(io.BytesIO(file_bytes))
            pages = [p.extract_text() or "" for p in reader.pages]
            content = "\n\n".join(pages)
        elif file_type == "md":
            from markdown_it import MarkdownIt
            import re
            raw = file_bytes.decode("utf-8", errors="replace")
            html = MarkdownIt().render(raw)
            content = re.sub(r"<[^>]+>", "", html).strip()
        elif file_type == "html":
            import re
            raw = file_bytes.decode("utf-8", errors="replace")
            content = re.sub(r"<[^>]+>", "", raw).strip()
        else:
            content = file_bytes.decode("utf-8", errors="replace")

        # 更新数据库（使用同步引擎）
        from app.celery_app.db_sync import update_document_content
        update_document_content(document_id, content)

        logger.info(
            "文档提取完成: id=%s, type=%s, length=%d",
            document_id, file_type, len(content),
        )

        return {
            "document_id": document_id,
            "content_length": len(content),
            "status": "success",
        }

    except Exception as exc:
        logger.error("文档提取失败: id=%s, error=%s", document_id, exc)
        # 自动重试（最多 3 次）
        raise self.retry(exc=exc, countdown=60)


@celery.task(bind=True, max_retries=2)
def generate_document_embeddings(self, document_id: int, content: str) -> dict:
    """异步生成文档向量嵌入（预留，RAG 升级后启用）

    Args:
        document_id: 文档 ID
        content: 文档文本内容

    Returns:
        {"document_id": int, "chunks": int, "status": "success"}
    """
    # 预留：RAG 升级时实现
    logger.info("Embedding 任务（预留）: document_id=%s", document_id)
    return {
        "document_id": document_id,
        "chunks": 0,
        "status": "placeholder",
    }
