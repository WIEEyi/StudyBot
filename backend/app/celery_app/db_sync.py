"""
Celery Worker 同步数据库工具

Celery Worker 运行在独立进程，需要自己的同步数据库连接。
"""

import logging
import json
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


def delete_document_chunks(document_id: int):
    """删除文档的旧向量块（在重新嵌入前调用）"""
    with _sync_engine.begin() as conn:
        result = conn.execute(
            text("DELETE FROM document_chunks WHERE document_id = :id"),
            {"id": document_id},
        )
        deleted = result.rowcount
    logger.info("已删除 %d 个旧块: document_id=%s", deleted, document_id)
    return deleted


def insert_document_chunk(
    document_id: int,
    chunk_index: int,
    content: str,
    embedding: list[float],
):
    """插入一个文档块及其向量嵌入"""
    with _sync_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO document_chunks (document_id, chunk_index, content, embedding) "
                "VALUES (:document_id, :chunk_index, :content, :embedding)"
            ),
            {
                "document_id": document_id,
                "chunk_index": chunk_index,
                "content": content,
                "embedding": json.dumps(embedding),  # pgvector 接受 JSON 数组
            },
        )
