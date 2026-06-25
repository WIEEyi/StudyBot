"""
UserAchievement 用户成就关联模型

记录用户获得的成就:
- 每个用户-成就组合唯一（同一成就不会重复获得）
- 记录获得时间和触发时的进度值
"""

from typing import TYPE_CHECKING
from sqlalchemy import Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.achievement import Achievement


class UserAchievement(Base, TimestampMixin):
    """用户-成就关联表

    unique constraint: (user_id, achievement_id) 确保同一成就不重复获得
    """

    __tablename__ = "user_achievements"
    __table_args__ = (
        UniqueConstraint("user_id", "achievement_id", name="uq_user_achievement"),
    )

    # 所属用户
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 关联成就
    achievement_id: Mapped[int] = mapped_column(
        ForeignKey("achievements.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 触发时的进度值（如连续天数、完成任务数等）
    progress_value: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # --- 关系 ---
    user: Mapped["User"] = relationship("User", back_populates="user_achievements")
    achievement: Mapped["Achievement"] = relationship(
        "Achievement", back_populates="user_achievements"
    )

    def __repr__(self) -> str:
        return f"<UserAchievement(user_id={self.user_id}, achievement_id={self.achievement_id})>"
