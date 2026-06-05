"""
DocumentChunk 文档分块模型

文档文本被 LangChain RecursiveCharacterTextSplitter 分割为多个重叠块，
每块通过 OpenAI text-embedding-3-small 生成 1536 维嵌入向量，
存入 pgvector，用于 Step 10 语义搜索和 Step 11 RAG 问答。

向量维度耦合说明:
- text-embedding-3-small = 1536 维（硬编码在 Vector(1536)）
- 如果切换到 text-embedding-3-large (3072 维)，需修改 Vector 维度 + 新建迁移
"""

from typing import Optional, TYPE_CHECKING
from sqlalchemy import Text, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.user import User


class DocumentChunk(Base, TimestampMixin):
    """文档分块 + 嵌入向量

    每个 Document 可以有 N 个 DocumentChunk（1:N），
    删文档时 CASCADE 自动删除所有分块。
    user_id 是冗余字段，用于高效用户范围搜索（避免 JOIN documents 表）。
    """

    __tablename__ = "document_chunks"

    # --- 外键 ---
    # 所属文档 (CASCADE: 删文档时自动删分块)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # 所属用户 (冗余字段，用于高效用户范围向量搜索)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # --- 分块数据 ---
    # 分块序号（0-based，保持原文顺序，用于 RAG 上下文拼装）
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    # 分块文本内容
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # OpenAI text-embedding-3-small 嵌入向量 (1536 维)
    # nullable: 允许先创建分块、后异步填充向量
    embedding: Mapped[Optional[list[float]]] = mapped_column(
        Vector(1536), nullable=True
    )
    # token 数量（tiktoken 计算，用于成本追踪）
    token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # --- 关系 ---
    document: Mapped["Document"] = relationship("Document", back_populates="chunks")
    user: Mapped["User"] = relationship("User", back_populates="document_chunks")

    def __repr__(self) -> str:
        return (
            f"<DocumentChunk(id={self.id}, doc_id={self.document_id}, "
            f"idx={self.chunk_index}, tokens={self.token_count})>"
        )
