"""
Quiz 测验题模型

支持单选题（options 是 JSON 数组，correct_answer 是正确答案索引）。
"""

from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Text, Integer, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.document import Document


class Quiz(Base, TimestampMixin):
    """测验题

    options: JSON 数组，如 ["选项A", "选项B", "选项C", "选项D"]
    correct_answer: 正确答案在 options 数组中的索引（0-based）
    explanation: 答案解析
    """

    __tablename__ = "quizzes"

    # 所属用户
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 关联文档（可选）
    document_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # 题目内容
    question: Mapped[str] = mapped_column(Text, nullable=False)
    # 选项列表（JSON 数组）
    options: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # 正确答案索引
    correct_answer: Mapped[str] = mapped_column(String(255), nullable=False)
    # 答案解析
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # 来源（manual / ai_generated）
    source: Mapped[str] = mapped_column(String(20), default="manual", nullable=False)

    # --- 关系 ---
    user: Mapped["User"] = relationship("User", back_populates="quizzes")
    document: Mapped[Optional["Document"]] = relationship("Document")

    def __repr__(self) -> str:
        return f"<Quiz(id={self.id}, question={self.question[:30]}...)>"
