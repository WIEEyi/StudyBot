"""
Embedding Service — 文档向量化 + 语义搜索

功能:
1. 文本分块 (chunking)
2. 调用 OpenAI Embedding API 生成向量
3. pgvector 语义搜索
"""

import logging
from typing import Optional

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# 分块参数
CHUNK_SIZE = 500      # 每块最大字符数
CHUNK_OVERLAP = 50    # 块间重叠字符数


def chunk_text(content: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """将文本分块

    按固定大小切分，块之间保留重叠以维持上下文连续性。

    Args:
        content: 原始文本
        chunk_size: 每块最大字符数
        overlap: 块间重叠字符数

    Returns:
        分块后的文本列表
    """
    if not content or not content.strip():
        return []

    chunks = []
    start = 0
    while start < len(content):
        end = start + chunk_size
        chunk = content[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start += chunk_size - overlap

    return chunks


async def generate_embedding(text_content: str) -> list[float]:
    """调用 OpenAI Embedding API 生成向量

    Args:
        text_content: 文本内容

    Returns:
        1536 维向量 (list[float])
    """
    import httpx

    async with httpx.AsyncClient() as client:
        api_key = settings.EMBEDDING_API_KEY or settings.LLM_API_KEY
        api_base = settings.EMBEDDING_API_BASE

        resp = await client.post(
            f"{api_base}/embeddings",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.EMBEDDING_MODEL,
                "input": text_content[:8000],  # API 限制
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["data"][0]["embedding"]


async def embed_and_store(document_id: int, content: str, db: AsyncSession) -> int:
    """将文档内容分块、生成向量并存入数据库

    Args:
        document_id: 文档 ID
        content: 文档文本内容
        db: 数据库会话

    Returns:
        创建的 chunk 数量
    """
    from app.models.document_chunk import DocumentChunk

    # 先删除该文档的旧 chunks
    await db.execute(
        text("DELETE FROM document_chunks WHERE document_id = :doc_id"),
        {"doc_id": document_id},
    )

    # 分块
    chunks = chunk_text(content)
    if not chunks:
        return 0

    # 逐块生成向量并存储
    count = 0
    for i, chunk_content in enumerate(chunks):
        try:
            embedding = await generate_embedding(chunk_content)
            chunk = DocumentChunk(
                document_id=document_id,
                chunk_index=i,
                content=chunk_content,
                embedding=embedding,
            )
            db.add(chunk)
            count += 1
        except Exception as e:
            logger.warning("Embedding 生成失败 (chunk %d): %s", i, e)

    await db.commit()
    logger.info("文档分块完成: doc_id=%s, chunks=%d", document_id, count)
    return count


async def semantic_search(
    query: str,
    user_id: int,
    db: AsyncSession,
    document_id: Optional[int] = None,
    top_k: int = 5,
    threshold: float = 0.3,
) -> list[dict]:
    """语义搜索 — 找到与查询最相关的文档块

    使用 pgvector 的余弦相似度搜索。

    Args:
        query: 用户查询文本
        user_id: 当前用户 ID（权限隔离）
        db: 数据库会话
        document_id: 可选，限定搜索范围
        top_k: 返回最多结果数
        threshold: 最低相似度阈值

    Returns:
        [{"chunk_id", "document_id", "document_title", "content", "similarity"}]
    """
    from app.models.document_chunk import DocumentChunk
    from app.models.document import Document

    try:
        query_embedding = await generate_embedding(query)
    except Exception as e:
        logger.error("查询 Embedding 生成失败: %s", e)
        return []

    # 构建向量搜索 SQL（余弦相似度）
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

    conditions = ["d.user_id = :user_id"]
    params = {"user_id": user_id, "top_k": top_k, "embedding": embedding_str}

    if document_id is not None:
        conditions.append("dc.document_id = :doc_id")
        params["doc_id"] = document_id

    where_clause = " AND ".join(conditions)

    sql = text(f"""
        SELECT
            dc.id AS chunk_id,
            dc.document_id,
            d.title AS document_title,
            dc.chunk_index,
            dc.content,
            1 - (dc.embedding <=> CAST(:embedding AS vector)) AS similarity
        FROM document_chunks dc
        JOIN documents d ON dc.document_id = d.id
        WHERE {where_clause}
          AND dc.embedding IS NOT NULL
          AND 1 - (dc.embedding <=> CAST(:embedding AS vector)) > :threshold
        ORDER BY dc.embedding <=> CAST(:embedding AS vector)
        LIMIT :top_k
    """)
    params["threshold"] = threshold

    result = await db.execute(sql, params)
    rows = result.fetchall()

    return [
        {
            "chunk_id": row.chunk_id,
            "document_id": row.document_id,
            "document_title": row.document_title,
            "chunk_index": row.chunk_index,
            "content": row.content,
            "similarity": round(float(row.similarity), 3),
        }
        for row in rows
    ]
