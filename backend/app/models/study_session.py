"""
StudySession 学习会话模型

记录每次学习活动，用于仪表盘热力图和连续天数计算。
"""

from datetime import date
from typing import Optional, TYPE_CHECKING
from sqlalchemy import Integer, Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class StudySession(Base, TimestampMixin):
    """学习会话记录"""

    __tablename__ = "study_sessions"

    # 所属用户
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 学习日期
    study_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    # 学习时长（分钟）
    duration_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # 完成的任务数
    tasks_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # 复习的卡片数
    cards_reviewed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # --- 关系 ---
    user: Mapped["User"] = relationship("User", back_populates="study_sessions")

    def __repr__(self) -> str:
        return f"<StudySession(date={self.study_date}, min={self.duration_minutes})>"
