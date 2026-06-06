"""
StudySession 学习会话模型

记录每日学习活动汇总，一个用户一天最多一条记录。
用于仪表盘热力图、连续天数等统计。
"""

from datetime import date
from typing import TYPE_CHECKING
from sqlalchemy import Date, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class StudySession(Base, TimestampMixin):
    """每日学习会话

    一个用户一天只存在一条记录，后续调用通过 Upsert 累加数值。
    """

    __tablename__ = "study_sessions"

    # 所属用户
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 学习日期（与 user_id 组合唯一）
    session_date: Mapped[date] = mapped_column(
        Date, nullable=False, index=True
    )
    # 当日累计学习时长（分钟）
    duration_minutes: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    # 当日完成任务数
    tasks_completed: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    # 当日复习卡片数
    cards_reviewed: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )

    # --- 关系 ---
    user: Mapped["User"] = relationship("User", back_populates="study_sessions")

    # --- 约束 ---
    __table_args__ = (
        UniqueConstraint("user_id", "session_date", name="uq_user_date"),
    )

    def __repr__(self) -> str:
        return (
            f"<StudySession(id={self.id}, user_id={self.user_id}, "
            f"date={self.session_date}, duration={self.duration_minutes}m)>"
        )
