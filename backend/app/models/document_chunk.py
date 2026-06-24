"""
DocumentChunk 文档分块模型

用于 RAG 语义搜索：将文档文本分块后，每块生成向量嵌入存储到 pgvector。
"""

from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Text, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.document import Document


# Embedding 维度 (text-embedding-3-small = 1536)
EMBEDDING_DIM = 1536


class DocumentChunk(Base, TimestampMixin):
    """文档分块 — 每个 chunk 存储一段文本及其向量嵌入"""

    __tablename__ = "document_chunks"

    # 所属文档
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 块在文档中的序号
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    # 文本内容
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # 向量嵌入 (pgvector)
    embedding = mapped_column(Vector(EMBEDDING_DIM), nullable=True)

    # --- 关系 ---
    document: Mapped["Document"] = relationship("Document", back_populates="chunks")

    def __repr__(self) -> str:
        return f"<DocumentChunk(doc={self.document_id}, idx={self.chunk_index}, len={len(self.content)})>"
