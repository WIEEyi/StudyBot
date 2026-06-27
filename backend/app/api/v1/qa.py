"""
RAG 问答路由

提供的接口:
- POST /qa/ask — 基于文档的语义问答（RAG）

搜索策略:
1. 优先使用 pgvector 语义搜索（需要文档已嵌入向量）
2. 回退到关键词匹配（兼容无 Embedding API Key 的场景）

答案生成:
- 优先使用 LLM（DeepSeek）基于检索到的上下文生成综合回答
- LLM 不可用时回退到手动拼接
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
    conversation_id: Optional[int] = Field(None, description="对话 ID（可选，用于保存历史）")
    top_k: int = Field(5, ge=1, le=20, description="返回最多引用数")
    threshold: float = Field(0.3, ge=0.0, le=1.0, description="语义搜索相似度阈值")


class CitationItem(BaseModel):
    """引用片段"""
    chunk_id: int
    document_id: int
    document_title: str
    content: str
    chunk_index: int = 0
    similarity: float = 0.0


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


# ===================== LLM 答案生成 =====================

async def _generate_llm_answer(
    question: str,
    context_chunks: list[dict],
) -> str | None:
    """使用 LLM 基于检索上下文生成综合回答

    Args:
        question: 用户问题
        context_chunks: 检索到的文本块列表，每块含 {content, document_title, similarity}

    Returns:
        LLM 生成的回答文本，或 None（LLM 不可用时）
    """
    from app.config import get_settings
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import SystemMessage, HumanMessage

    settings = get_settings()
    if not settings.LLM_API_KEY or settings.LLM_API_KEY == "sk-your-api-key-here":
        logger.warning("LLM API Key 未配置，回退到手动拼接答案")
        return None

    try:
        # 构建上下文文本
        context_text_parts = []
        for i, chunk in enumerate(context_chunks, 1):
            context_text_parts.append(
                f"[来源 {i}] 文档「{chunk['document_title']}」（相关度: {chunk['similarity']:.0%}）:\n"
                f"{chunk['content']}"
            )
        context_text = "\n\n".join(context_text_parts)

        system_prompt = (
            "你是一个学习助手。根据用户提供的文档内容回答用户的问题。\n\n"
            "规则：\n"
            "1. 只使用提供的文档内容来回答，不要编造信息\n"
            "2. 如果文档内容不足以回答问题，请诚实地说明\n"
            "3. 回答应该简洁、准确、有组织\n"
            "4. 引用文档内容时使用 [来源 N] 标注\n"
            "5. 使用中文回答"
        )

        user_prompt = (
            f"用户问题：{question}\n\n"
            f"参考文档内容：\n{context_text}\n\n"
            "请根据以上文档内容回答用户的问题。"
        )

        llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            openai_api_key=settings.LLM_API_KEY,
            openai_api_base=settings.LLM_API_BASE,
            temperature=0.3,  # 低温度以获得更准确的事实性回答
        )

        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])

        answer = response.content
        if isinstance(answer, list):
            answer = "".join(str(b) for b in answer)
        answer = str(answer).strip()

        logger.info("LLM 生成答案: question_len=%d, context_chunks=%d, answer_len=%d",
                     len(question), len(context_chunks), len(answer))
        return answer

    except Exception as e:
        logger.warning("LLM 答案生成失败: %s", e)
        return None


def _build_fallback_answer(
    citations: list[CitationItem],
    search_mode: str,
) -> str:
    """手动拼接答案（LLM 不可用时的回退方案）"""
    if search_mode == "semantic":
        answer = f"根据你上传的文档，找到 {len(citations)} 个相关内容：\n\n"
        for i, c in enumerate(citations, 1):
            answer += f"**{i}. {c.document_title}**（相似度: {c.similarity:.0%}）\n{c.content}\n\n"
        answer += "\n> 🔍 基于 pgvector 语义搜索"
    else:
        answer = f"根据你上传的 {len(citations)} 份文档，以下是相关内容：\n\n"
        for i, c in enumerate(citations, 1):
            answer += f"**{i}. {c.document_title}**（相关度: {c.similarity:.0%}）\n{c.content}\n\n"
        answer += "\n> 💡 当前为关键词匹配模式。上传文档后运行 Embedding 可启用语义搜索。"
    return answer


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

    对话历史:
    - 提供 conversation_id 时自动保存消息
    """
    from app.models.conversation import Conversation, ChatMessage
    import json as _json

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
                similarity=r["similarity"],
            )
            for r in results
        ]

        # 尝试 LLM 生成答案
        context_chunks = [
            {
                "content": r["content"],
                "document_title": r["document_title"],
                "similarity": r["similarity"],
            }
            for r in results
        ]
        llm_answer = await _generate_llm_answer(request.question, context_chunks)

        if llm_answer:
            answer = llm_answer + f"\n\n> 🔍 基于 pgvector 语义搜索 + AI 生成"
        else:
            answer = _build_fallback_answer(citations, "semantic")

        # 保存聊天历史
        conv_id = await _save_chat_message(
            db, current_user.id, request, answer, citations, search_mode,
        )

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
        answer = "没有找到相关文档。请先上传学习材料。"
        await _save_chat_message(db, current_user.id, request, answer, [], "no_docs")
        return QAResponse(
            question=request.question,
            answer=answer,
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
            similarity=score,
        ))

    if citations:
        # 尝试 LLM 生成答案
        context_chunks = [
            {
                "content": c.content,
                "document_title": c.document_title,
                "similarity": c.similarity,
            }
            for c in citations
        ]
        llm_answer = await _generate_llm_answer(request.question, context_chunks)

        if llm_answer:
            answer = llm_answer + f"\n\n> 💡 当前为关键词匹配模式。上传文档后运行 Embedding 可启用语义搜索。"
        else:
            answer = _build_fallback_answer(citations, "keyword_fallback")
    else:
        answer = "在你的文档中没有找到与问题相关的内容。试试换一种方式提问。"

    # 保存聊天历史
    await _save_chat_message(db, current_user.id, request, answer, citations, search_mode)

    return QAResponse(
        question=request.question,
        answer=answer,
        citations=citations,
    )


# ===================== 聊天历史保存 =====================

async def _save_chat_message(
    db: AsyncSession,
    user_id: int,
    request: QARequest,
    answer: str,
    citations: list[CitationItem],
    search_mode: str,
) -> int | None:
    """保存问答消息到对话历史

    Args:
        db: 数据库会话
        user_id: 用户 ID
        request: QA 请求
        answer: AI 回答
        citations: 引用列表
        search_mode: 搜索模式

    Returns:
        对话 ID，失败返回 None
    """
    from app.models.conversation import Conversation, ChatMessage
    import json as _json

    try:
        # 获取或创建对话
        conv: Conversation | None = None
        if request.conversation_id:
            query = select(Conversation).where(
                Conversation.id == request.conversation_id,
                Conversation.user_id == user_id,
            )
            result = await db.execute(query)
            conv = result.scalar_one_or_none()

        if not conv:
            # 自动创建新对话，用第一个问题作为标题
            title = request.question[:50] + ("..." if len(request.question) > 50 else "")
            conv = Conversation(
                user_id=user_id,
                title=title,
                document_id=request.document_id,
            )
            db.add(conv)
            await db.flush()  # 获取 conv.id

        # 保存消息
        msg = ChatMessage(
            conversation_id=conv.id,
            question=request.question,
            answer=answer,
            citations_json=_json.dumps(
                [c.model_dump() for c in citations], ensure_ascii=False
            ),
        )
        db.add(msg)
        await db.commit()

        return conv.id

    except Exception as e:
        logger.warning("保存聊天历史失败: %s", e)
        await db.rollback()
        return None
