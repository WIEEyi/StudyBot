"""
RAG 问答路由

提供的接口:
- POST /qa/ask — 基于文档的语义问答（RAG）

当前实现:
- 基于 Document.content 的全文搜索 + 简单文本匹配
- 后续可升级为 pgvector 语义搜索 + LLM 生成答案
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
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/qa", tags=["RAG 问答"])


# ===================== Schema =====================

class QARequest(BaseModel):
    """问答请求"""
    question: str = Field(..., min_length=1, description="用户问题")
    document_id: Optional[int] = Field(None, description="限定文档 ID（可选）")
    top_k: int = Field(5, ge=1, le=20, description="返回最多引用数")


class CitationItem(BaseModel):
    """引用片段"""
    document_id: int
    document_title: str
    content: str
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

    当前为简易实现（关键词匹配），后续升级为 pgvector 语义搜索 + LLM。

    流程:
    1. 从数据库加载用户的文档（或指定文档）
    2. 对每个文档的 content 进行相关性评分
    3. 返回 top_k 个最相关的片段作为引用
    4. 拼接引用内容生成答案
    """
    # 加载文档
    conditions = [Document.user_id == current_user.id]
    if request.document_id is not None:
        conditions.append(Document.id == request.document_id)

    result = await db.execute(
        select(Document).where(*conditions)
    )
    documents = result.scalars().all()

    if not documents:
        return QAResponse(
            question=request.question,
            answer="没有找到相关文档。请先上传学习材料。",
            citations=[],
        )

    # 对每个文档评分
    scored: list[tuple[Document, float]] = []
    for doc in documents:
        score = _simple_search(doc.content or "", request.question)
        if score > 0:
            scored.append((doc, score))

    # 按相关性排序，取 top_k
    scored.sort(key=lambda x: x[1], reverse=True)
    top_docs = scored[:request.top_k]

    # 构建引用
    citations = []
    context_parts = []
    for doc, score in top_docs:
        # 截取内容前 500 字符作为引用片段
        snippet = (doc.content or "")[:500]
        citations.append(CitationItem(
            document_id=doc.id,
            document_title=doc.title,
            content=snippet,
            relevance=score,
        ))
        context_parts.append(f"[{doc.title}]: {snippet}")

    # 生成答案（简易版：拼接引用内容）
    if citations:
        answer = f"根据你上传的 {len(citations)} 份文档，以下是相关内容：\n\n"
        for i, c in enumerate(citations, 1):
            answer += f"**{i}. {c.document_title}**（相关度: {c.relevance}）\n{c.content}\n\n"
        answer += "\n> 💡 当前为关键词匹配模式，配置 OPENAI_API_KEY 后可启用 AI 智能问答。"
    else:
        answer = "在你的文档中没有找到与问题相关的内容。试试换一种方式提问。"

    return QAResponse(
        question=request.question,
        answer=answer,
        citations=citations,
    )
