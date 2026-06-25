"""SQLAlchemy 数据模型

导入所有模型确保 Base.metadata 包含完整的表定义。
Alembic --autogenerate 会扫描 Base.metadata 来生成迁移脚本。
"""

from app.models.base import Base, TimestampMixin
from app.models.user import User
from app.models.learning_goal import LearningGoal
from app.models.task import Task
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.review_card import ReviewCard
from app.models.quiz import Quiz
from app.models.concept import Concept
from app.models.concept_relation import ConceptRelation
from app.models.study_session import StudySession
from app.models.achievement import Achievement
from app.models.user_achievement import UserAchievement

__all__ = [
    "Base",
    "TimestampMixin",
    "User",
    "LearningGoal",
    "Task",
    "Document",
    "DocumentChunk",
    "ReviewCard",
    "Quiz",
    "Concept",
    "ConceptRelation",
    "StudySession",
    "Achievement",
    "UserAchievement",
]
