"""
语义搜索路由

POST /api/v1/search — 在用户所有文档中执行语义搜索

Step 10: 返回匹配的分块 + 相似度分数（基础语义搜索）
Step 11: 将在此之上增加 LLM 问答生成（RAG）

技术实现:
- 查询文本通过 OpenAI text-embedding-3-small 向量化
- 使用 pgvector <=> 操作符（余弦距离）计算相似度
- HNSW 索引提供亚毫秒级近似搜索
- 仅搜索登录用户自己的文档（user_id 过滤）
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status as http_status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.search import SearchRequest, SearchResultItem, SearchResponse
from app.services.embedding_service import embed_query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["语义搜索"])


@router.post("", response_model=SearchResponse)
async def semantic_search(
    request: SearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """语义搜索

    流程:
    1. 将查询文本向量化（OpenAI text-embedding-3-small）
    2. 在用户所有文档分块中执行余弦相似度搜索（pgvector <=> 操作符）
    3. 返回 top_k 个最相关分块（含文档标题和相似度分数）

    相似度 = 1 - 余弦距离，范围 [0, 1]，1 表示完全匹配。
    """
    # 1. 向量化查询
    try:
        query_embedding = await embed_query(request.query)
    except Exception as e:
        logger.error("查询向量化失败: %s", str(e))
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="搜索服务暂不可用，请稍后重试",
        )

    # 2. 余弦相似度搜索
    # pgvector <=> 操作符返回余弦距离 (0-2)，1-distance = 余弦相似度 (0-1)
    # CAST(:query_vec AS vector) 将 Python float 列表转为 pgvector 类型
    sql = text("""
        SELECT
            dc.id AS chunk_id,
            dc.document_id,
            d.title AS document_title,
            dc.chunk_index,
            dc.content,
            dc.token_count,
            1 - (dc.embedding <=> CAST(:query_vec AS vector)) AS similarity
        FROM document_chunks dc
        JOIN documents d ON dc.document_id = d.id
        WHERE dc.user_id = :user_id
          AND dc.embedding IS NOT NULL
          AND 1 - (dc.embedding <=> CAST(:query_vec AS vector)) >= :threshold
        ORDER BY dc.embedding <=> CAST(:query_vec AS vector)
        LIMIT :top_k
    """)

    # 将 Python float 列表转为 pgvector 字符串格式 "[1.0,2.0,3.0]"
    # asyncpg 通过 raw SQL text() 传参时需要字符串，ORM 的 Vector 类型会自动处理转换
    vec_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

    result = await db.execute(
        sql,
        {
            "query_vec": vec_str,
            "user_id": current_user.id,
            "threshold": request.threshold,
            "top_k": request.top_k,
        },
    )
    rows = result.fetchall()

    # 3. 构建响应
    items = [
        SearchResultItem(
            chunk_id=row.chunk_id,
            document_id=row.document_id,
            document_title=row.document_title,
            chunk_index=row.chunk_index,
            content=row.content,
            similarity=round(row.similarity, 4),
            token_count=row.token_count,
        )
        for row in rows
    ]

    logger.info(
        "语义搜索完成: query='%s', top_k=%d, 结果数=%d",
        request.query[:50], request.top_k, len(items),
    )
    return SearchResponse(
        query=request.query,
        results=items,
        total=len(items),
    )
