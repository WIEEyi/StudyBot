"""
Celery Worker 同步数据库工具

Celery Worker 运行在独立进程，需要自己的同步数据库连接。
"""

import logging
from sqlalchemy import create_engine, update, text
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# 将 asyncpg URL 转为同步 psycopg2
_sync_url = settings.DATABASE_URL.replace("+asyncpg", "+psycopg2")
_sync_engine = create_engine(_sync_url, pool_size=5, max_overflow=10)


def update_document_content(document_id: int, content: str):
    """同步更新文档的 content 字段"""
    with _sync_engine.begin() as conn:
        conn.execute(
            text("UPDATE documents SET content = :content WHERE id = :id"),
            {"content": content, "id": document_id},
        )
    logger.info("文档内容已更新: id=%s", document_id)
