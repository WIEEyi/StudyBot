"""
RAG 问答路由

提供的接口:
- POST /qa/ask — 基于文档的语义问答（RAG）

搜索策略:
1. 优先使用 pgvector 语义搜索（需要文档已嵌入向量）
2. 回退到关键词匹配（兼容无 Embedding API Key 的场景）
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.document import Document
from app.services.embedding_service import semantic_search
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/qa", tags=["RAG 问答"])


# ===================== Schema =====================

class QARequest(BaseModel):
    """问答请求"""
    question: str = Field(..., min_length=1, description="用户问题")
    document_id: Optional[int] = Field(None, description="限定文档 ID（可选）")
    top_k: int = Field(5, ge=1, le=20, description="返回最多引用数")
    threshold: float = Field(0.3, ge=0.0, le=1.0, description="语义搜索相似度阈值")


class CitationItem(BaseModel):
    """引用片段"""
    chunk_id: int
    document_id: int
    document_title: str
    content: str
    chunk_index: int = 0
    relevance: float = 0.0


class QAResponse(BaseModel):
    """问答响应"""
    question: str
    answer: str
    citations: list[CitationItem]


# ===================== 简易文本搜索 =====================

def _simple_search(content: str, question: str) -> float:
    """简易相关性评分：关键词命中率

    将问题分词，计算在内容中出现的关键词比例。
    这是一个占位实现，后续应替换为向量相似度搜索。
    """
    if not content:
        return 0.0

    # 简单的空格分词 + 小写化
    keywords = [w.lower() for w in question.split() if len(w) > 1]
    if not keywords:
        return 0.0

    content_lower = content.lower()
    hits = sum(1 for kw in keywords if kw in content_lower)
    return round(hits / len(keywords), 3)


# ===================== 接口实现 =====================

@router.post("/ask", response_model=QAResponse)
async def ask_question(
    request: QARequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """RAG 问答接口

    搜索策略:
    1. 优先使用 pgvector 语义搜索（需要文档已生成 Embedding）
    2. 回退到关键词匹配（兼容无 Embedding 的场景）
    """
    # 尝试语义搜索
    search_mode = "semantic"
    try:
        results = await semantic_search(
            query=request.question,
            user_id=current_user.id,
            db=db,
            document_id=request.document_id,
            top_k=request.top_k,
            threshold=request.threshold,
        )
    except Exception as e:
        logger.warning("语义搜索失败，回退到关键词匹配: %s", e, exc_info=True)
        results = []
        search_mode = "keyword_fallback"

    # 如果语义搜索有结果，使用它
    if results:
        citations = [
            CitationItem(
                chunk_id=r["chunk_id"],
                document_id=r["document_id"],
                document_title=r["document_title"],
                chunk_index=r["chunk_index"],
                content=r["content"],
                relevance=r["similarity"],
            )
            for r in results
        ]

        answer = f"根据你上传的文档，找到 {len(citations)} 个相关内容：\n\n"
        for i, c in enumerate(citations, 1):
            answer += f"**{i}. {c.document_title}**（相似度: {c.relevance}）\n{c.content}\n\n"
        answer += "\n> 🔍 基于 pgvector 语义搜索"

        return QAResponse(
            question=request.question,
            answer=answer,
            citations=citations,
        )

    # 回退到关键词匹配
    conditions = [Document.user_id == current_user.id]
    if request.document_id is not None:
        conditions.append(Document.id == request.document_id)

    result = await db.execute(select(Document).where(*conditions))
    documents = result.scalars().all()

    if not documents:
        return QAResponse(
            question=request.question,
            answer="没有找到相关文档。请先上传学习材料。",
            citations=[],
        )

    scored: list[tuple[Document, float]] = []
    for doc in documents:
        score = _simple_search(doc.content or "", request.question)
        if score > 0:
            scored.append((doc, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    top_docs = scored[:request.top_k]

    citations = []
    for doc, score in top_docs:
        snippet = (doc.content or "")[:500]
        citations.append(CitationItem(
            chunk_id=0,
            document_id=doc.id,
            document_title=doc.title,
            chunk_index=0,
            content=snippet,
            relevance=score,
        ))

    if citations:
        answer = f"根据你上传的 {len(citations)} 份文档，以下是相关内容：\n\n"
        for i, c in enumerate(citations, 1):
            answer += f"**{i}. {c.document_title}**（相关度: {c.relevance}）\n{c.content}\n\n"
        answer += "\n> 💡 当前为关键词匹配模式。上传文档后运行 Embedding 可启用语义搜索。"
    else:
        answer = "在你的文档中没有找到与问题相关的内容。试试换一种方式提问。"

    return QAResponse(
        question=request.question,
        answer=answer,
        citations=citations,
    )
