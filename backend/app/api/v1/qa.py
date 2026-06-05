"""
RAG 知识库问答路由

POST /api/v1/qa/ask — 用户的自然语言问题 → 语义搜索 → LLM 生成带引用的答案

Step 11: RAG 问答 = 语义搜索 + AI 答案生成 (DigestAgent)

技术实现:
- 使用 DigestAgent（LangGraph 两节点工作流: search_chunks → generate_answer）
- 搜索结果复用 embedding_service.embed_query() + pgvector 余弦相似度
- LLM 使用 gpt-4o-mini（轻量模型，RAG 质量主要来自检索上下文）
- 权限隔离: 仅搜索当前用户自己的文档分块
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status as http_status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.document import Document
from app.schemas.qa import QARequest, QAResponse, CitationItem
from app.agents.digest_agent import run_digest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/qa", tags=["RAG 问答"])


@router.post("/ask", response_model=QAResponse)
async def ask_question(
    request: QARequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """RAG 知识库问答

    流程:
    1. 校验 document_id（如果指定了）的归属权
    2. 调用 DigestAgent 执行语义搜索 + LLM 答案生成
    3. 返回答案 + 引用列表

    搜索范围:
    - 不传 document_id: 搜索用户所有文档的分块
    - 传 document_id: 仅搜索指定文档的分块
    """
    # 1. 校验 document_id 归属权（如果用户指定了特定文档）
    if request.document_id is not None:
        result = await db.execute(
            select(Document).where(Document.id == request.document_id)
        )
        document = result.scalar_one_or_none()
        if document is None:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"文档不存在: id={request.document_id}",
            )
        if document.user_id != current_user.id:
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="无权访问此文档",
            )

    # 2. 运行 DigestAgent
    try:
        state = await run_digest(
            question=request.question,
            user_id=current_user.id,
            db_session=db,
            document_id=request.document_id,
            top_k=request.top_k,
        )
    except Exception as e:
        logger.error("DigestAgent 执行失败: %s", str(e))
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"问答服务暂不可用: {str(e)}",
        )

    # 3. 检查 Agent 是否返回了错误
    if state.get("error"):
        logger.error("DigestAgent 返回错误: %s", state["error"])
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=state["error"],
        )

    # 4. 构建响应
    citations = [
        CitationItem(
            chunk_id=c["chunk_id"],
            document_id=c["document_id"],
            document_title=c["document_title"],
            chunk_index=c["chunk_index"],
            content=c["content"],
            similarity=c["similarity"],
        )
        for c in state.get("citations", [])
    ]

    logger.info(
        "RAG 问答完成: question='%s', answer_len=%d, citations=%d",
        request.question[:50],
        len(state.get("answer", "")),
        len(citations),
    )

    return QAResponse(
        question=request.question,
        answer=state["answer"],
        citations=citations,
    )
