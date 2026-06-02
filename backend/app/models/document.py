"""
Document 文档模型

用户上传的学习资料，用于 RAG 知识库检索。
"""

from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class Document(Base, TimestampMixin):
    """上传文档

    文档内容提取后存入 content 字段，用于语义搜索。
    """

    __tablename__ = "documents"

    # 所属用户
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 文档标题（默认取文件名）
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    # 文件在磁盘上的路径（Docker 内路径）
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    # 提取后的文本内容（用于 embedding 和全文搜索）
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # 文件类型（pdf / md / txt / html）
    file_type: Mapped[str] = mapped_column(String(20), nullable=False, default="txt")

    # --- 关系 ---
    user: Mapped["User"] = relationship("User", back_populates="documents")

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, title={self.title}, type={self.file_type})>"
