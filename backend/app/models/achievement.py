"""
Achievement 成就模型

定义系统中的成就徽章:
- 预设成就（如 "坚持7天"、"100% 测验正确率"）
- 每个成就有唯一 code、显示名称、描述、分类和稀有度
"""

from typing import List, TYPE_CHECKING
from sqlalchemy import String, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user_achievement import UserAchievement


class Achievement(Base, TimestampMixin):
    """成就定义表

    code: 唯一标识（如 'streak_7', 'quiz_perfect'）
    category: 分类（learning / quiz / review / consistency / milestone）
    rarity: 稀有度（common / rare / epic / legendary）
    """

    __tablename__ = "achievements"

    # 成就唯一标识
    code: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )
    # 显示名称
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # 描述
    description: Mapped[str] = mapped_column(Text, nullable=False)
    # 图标（emoji 或图标名）
    icon: Mapped[str] = mapped_column(String(10), default="🏆", nullable=False)
    # 分类
    category: Mapped[str] = mapped_column(
        String(30), default="learning", nullable=False, index=True
    )
    # 稀有度
    rarity: Mapped[str] = mapped_column(
        String(20), default="common", nullable=False
    )
    # 达成所需数量（如连续 7 天 → threshold=7）
    threshold: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # --- 关系 ---
    user_achievements: Mapped[List["UserAchievement"]] = relationship(
        "UserAchievement", back_populates="achievement"
    )

    def __repr__(self) -> str:
        return f"<Achievement(code={self.code}, name={self.name})>"
