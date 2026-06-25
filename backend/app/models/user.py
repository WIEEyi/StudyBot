"""
User 数据库模型

用户表存储认证所需的基本信息:
- email / username 唯一标识用户
- hashed_password 存储 bcrypt 哈希后的密码（永不存明文）
- is_active 用于软删除/禁用账户
"""

from typing import List, TYPE_CHECKING
from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.learning_goal import LearningGoal
    from app.models.task import Task
    from app.models.document import Document
    from app.models.review_card import ReviewCard
    from app.models.quiz import Quiz
    from app.models.concept import Concept
    from app.models.study_session import StudySession
    from app.models.user_achievement import UserAchievement


class User(Base, TimestampMixin):
    """用户模型

    索引策略:
    - email 和 username 都建了唯一索引，因为登录可以通过邮箱或用户名
    """

    __tablename__ = "users"

    # 邮箱: 唯一 + 索引（登录主键）
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    # 用户名: 唯一 + 索引（显示名，也可用于登录）
    username: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )
    # 密码哈希（bcrypt 固定 60 字符）
    hashed_password: Mapped[str] = mapped_column(
        String(128), nullable=False
    )
    # 账户状态 (False = 禁用/软删除)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    # --- 反向关系 ---
    goals: Mapped[List["LearningGoal"]] = relationship("LearningGoal", back_populates="user")
    tasks: Mapped[List["Task"]] = relationship("Task", back_populates="user")
    documents: Mapped[List["Document"]] = relationship("Document", back_populates="user")
    review_cards: Mapped[List["ReviewCard"]] = relationship("ReviewCard", back_populates="user")
    quizzes: Mapped[List["Quiz"]] = relationship("Quiz", back_populates="user")
    concepts: Mapped[List["Concept"]] = relationship("Concept", back_populates="user")
    study_sessions: Mapped[List["StudySession"]] = relationship("StudySession", back_populates="user")
    user_achievements: Mapped[List["UserAchievement"]] = relationship("UserAchievement", back_populates="user")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, username={self.username})>"
