"""
对话历史 API

提供对话会话的 CRUD 接口：
- GET    /qa/conversations        — 对话列表
- POST   /qa/conversations        — 创建新对话
- GET    /qa/conversations/{id}   — 对话详情（含消息）
- DELETE /qa/conversations/{id}   — 删除对话
"""

import json
import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, Query, status as http_status
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.conversation import Conversation, ChatMessage
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/qa/conversations", tags=["对话历史"])


# ===================== Schema =====================

class MessageResponse(BaseModel):
    """消息响应"""
    id: int
    question: str
    answer: str
    citations: list[dict] = []
    created_at: str

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    """对话响应"""
    id: int
    title: str
    document_id: int | None = None
    message_count: int = 0
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ConversationDetailResponse(ConversationResponse):
    """对话详情（含消息列表）"""
    messages: list[MessageResponse] = []


class ConversationListResponse(BaseModel):
    """对话列表响应"""
    items: list[ConversationResponse]
    total: int
    offset: int
    limit: int


class ConversationCreate(BaseModel):
    """创建对话请求"""
    title: str = Field("新对话", min_length=1, max_length=200)
    document_id: int | None = None


# ===================== 接口实现 =====================

@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
):
    """获取当前用户的对话列表"""
    # 总数
    count_query = select(func.count()).select_from(Conversation).where(
        Conversation.user_id == current_user.id
    )
    total = (await db.execute(count_query)).scalar() or 0

    # 列表
    query = (
        select(Conversation)
        .where(Conversation.user_id == current_user.id)
        .order_by(desc(Conversation.updated_at))
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    conversations = result.scalars().all()

    items = []
    for conv in conversations:
        # 获取消息数量
        msg_count_query = select(func.count()).select_from(ChatMessage).where(
            ChatMessage.conversation_id == conv.id
        )
        msg_count = (await db.execute(msg_count_query)).scalar() or 0

        items.append(ConversationResponse(
            id=conv.id,
            title=conv.title,
            document_id=conv.document_id,
            message_count=msg_count,
            created_at=conv.created_at.isoformat(),
            updated_at=conv.updated_at.isoformat(),
        ))

    return ConversationListResponse(items=items, total=total, offset=offset, limit=limit)


@router.post("", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    request: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建新对话"""
    conv = Conversation(
        user_id=current_user.id,
        title=request.title,
        document_id=request.document_id,
    )
    db.add(conv)
    await db.commit()
    await db.refresh(conv)

    return ConversationResponse(
        id=conv.id,
        title=conv.title,
        document_id=conv.document_id,
        message_count=0,
        created_at=conv.created_at.isoformat(),
        updated_at=conv.updated_at.isoformat(),
    )


@router.get("/{conv_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conv_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取对话详情（含消息列表）"""
    # 查对话
    query = select(Conversation).where(
        Conversation.id == conv_id,
        Conversation.user_id == current_user.id,
    )
    result = await db.execute(query)
    conv = result.scalar_one_or_none()

    if not conv:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="对话不存在")

    # 查消息
    msg_query = (
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conv.id)
        .order_by(ChatMessage.created_at)
    )
    msg_result = await db.execute(msg_query)
    messages = msg_result.scalars().all()

    msg_responses = []
    for msg in messages:
        citations = []
        if msg.citations_json:
            try:
                citations = json.loads(msg.citations_json)
            except json.JSONDecodeError:
                pass

        msg_responses.append(MessageResponse(
            id=msg.id,
            question=msg.question,
            answer=msg.answer,
            citations=citations,
            created_at=msg.created_at.isoformat(),
        ))

    return ConversationDetailResponse(
        id=conv.id,
        title=conv.title,
        document_id=conv.document_id,
        message_count=len(messages),
        created_at=conv.created_at.isoformat(),
        updated_at=conv.updated_at.isoformat(),
        messages=msg_responses,
    )


@router.delete("/{conv_id}", status_code=204)
async def delete_conversation(
    conv_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除对话"""
    query = select(Conversation).where(
        Conversation.id == conv_id,
        Conversation.user_id == current_user.id,
    )
    result = await db.execute(query)
    conv = result.scalar_one_or_none()

    if not conv:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="对话不存在")

    await db.delete(conv)
    await db.commit()
