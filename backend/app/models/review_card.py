"""
ReviewCard 间隔复习卡片

SM-2 算法核心参数:
- ease_factor: 难度系数（默认 2.5，范围 1.3-2.5）
- interval: 当前复习间隔（天）
- repetitions: 连续正确次数
- next_review_at: 下次复习时间

SM-2 算法流程:
1. 用户评分 (0-5) →
2. 评分 >= 3: repetitions++，interval 按 ease_factor 递增
3. 评分 < 3: 重置 repetitions，重置 interval 为 1 天
4. 更新 ease_factor 和 next_review_at
"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Text, Float, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.document import Document


class ReviewCard(Base, TimestampMixin):
    """间隔复习卡片"""

    __tablename__ = "review_cards"

    # 所属用户
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 关联文档（可选）
    document_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # 卡片正面（问题/提示）
    front: Mapped[str] = mapped_column(Text, nullable=False)
    # 卡片背面（答案）
    back: Mapped[str] = mapped_column(Text, nullable=False)
    # 卡片来源（manual / ai_generated）
    source: Mapped[str] = mapped_column(String(20), default="manual", nullable=False)

    # --- SM-2 参数 ---
    # 难度系数（默认 2.5，越低越难）
    ease_factor: Mapped[float] = mapped_column(Float, default=2.5, nullable=False)
    # 当前复习间隔（天）
    interval: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # 连续正确次数
    repetitions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # 下次复习时间
    next_review_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # 上次复习时间
    last_reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # --- 关系 ---
    user: Mapped["User"] = relationship("User", back_populates="review_cards")
    document: Mapped[Optional["Document"]] = relationship("Document")

    def __repr__(self) -> str:
        return f"<ReviewCard(id={self.id}, interval={self.interval}d, ef={self.ease_factor})>"
