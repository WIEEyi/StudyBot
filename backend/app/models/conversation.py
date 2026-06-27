"""
对话历史模型

存储用户的 QA 对话记录，支持：
- 多个对话会话（每个文档或主题一个会话）
- 每个会话包含多轮问答消息
- 引用信息以 JSON 格式存储
"""

import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, ForeignKey, Text, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin


class Conversation(Base, TimestampMixin):
    """对话会话

    每个会话属于一个用户，可关联一个文档。
    """
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(
        String(200), nullable=False, default="新对话", comment="对话标题（自动生成或用户编辑）"
    )
    document_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True, comment="关联的文档（可选）"
    )

    # 反向关系
    user: Mapped["User"] = relationship("User", back_populates="conversations")
    messages: Mapped[List["ChatMessage"]] = relationship(
        "ChatMessage", back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )

    def __repr__(self) -> str:
        return f"<Conversation id={self.id} title='{self.title}' user_id={self.user_id}>"


class ChatMessage(Base, TimestampMixin):
    """对话消息

    单轮问答记录：一个问题 + 一个回答 + 引用列表。
    """
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    question: Mapped[str] = mapped_column(Text, nullable=False, comment="用户问题")
    answer: Mapped[str] = mapped_column(Text, nullable=False, comment="AI 回答")
    citations_json: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="引用列表（JSON 字符串）"
    )

    # 反向关系
    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="messages"
    )

    def __repr__(self) -> str:
        return f"<ChatMessage id={self.id} conv_id={self.conversation_id}>"
