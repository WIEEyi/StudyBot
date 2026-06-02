"""
LearningGoal 学习目标模型

用户设定学习目标，可关联多个 Task。
目标有状态机: active -> completed / paused
"""

from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Text, DateTime, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.task import Task

# 目标状态枚举值
GOAL_STATUSES = ("active", "completed", "paused")


class LearningGoal(Base, TimestampMixin):
    """学习目标

    关系:
    - user: 所属用户（多对一）
    - tasks: 关联的任务列表（一对多）
    """

    __tablename__ = "learning_goals"

    # 所属用户
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 目标标题
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    # 目标详细描述
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # 截止日期
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    # 目标状态
    status: Mapped[str] = mapped_column(
        Enum(*GOAL_STATUSES, name="goal_status"), default="active", nullable=False
    )

    # --- 关系 ---
    user: Mapped["User"] = relationship("User", back_populates="goals")
    tasks: Mapped[List["Task"]] = relationship("Task", back_populates="goal")

    def __repr__(self) -> str:
        return f"<LearningGoal(id={self.id}, title={self.title}, status={self.status})>"
