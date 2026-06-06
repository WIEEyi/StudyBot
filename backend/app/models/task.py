"""
Task 任务模型

用户学习/工作中待执行的任务，可关联到学习目标。
"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Text, Integer, DateTime, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.learning_goal import LearningGoal

# 优先级枚举
PRIORITIES = ("low", "medium", "high")
# 任务状态枚举
TASK_STATUSES = ("todo", "in_progress", "done", "cancelled")


class Task(Base, TimestampMixin):
    """任务

    关系:
    - user: 所属用户（多对一）
    - goal: 关联的学习目标（多对一，可选）
    """

    __tablename__ = "tasks"

    # 所属用户
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 关联目标（可选：独立任务可以不绑目标）
    goal_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("learning_goals.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # 任务标题
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    # 任务描述
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # 优先级
    priority: Mapped[str] = mapped_column(
        Enum(*PRIORITIES, name="task_priority"), default="medium", nullable=False
    )
    # 截止日期（精确到天即可）
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    # 任务状态
    status: Mapped[str] = mapped_column(
        Enum(*TASK_STATUSES, name="task_status"), default="todo", nullable=False
    )
    # 预估耗时（分钟）
    estimated_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # 里程碑名称（AI 生成计划时用于分组，如"阶段一：Python 基础"）
    milestone: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # 里程碑序号（用于前端按阶段顺序展示任务，1-based）
    milestone_order: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # 任务完成时间戳（status 变为 done 时自动设置，用于仪表盘统计）
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # --- 关系 ---
    user: Mapped["User"] = relationship("User", back_populates="tasks")
    goal: Mapped[Optional["LearningGoal"]] = relationship("LearningGoal", back_populates="tasks")

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, title={self.title}, status={self.status})>"
