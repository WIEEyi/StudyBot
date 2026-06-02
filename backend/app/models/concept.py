"""
Concept 知识图谱节点

知识图谱中的概念节点，可与其他概念建立关系。
"""

from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.concept_relation import ConceptRelation

# 概念分类
CATEGORIES = ("subject", "topic", "subtopic", "term", "other")


class Concept(Base, TimestampMixin):
    """知识图谱概念节点"""

    __tablename__ = "concepts"

    # 所属用户
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 概念名称
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # 概念描述
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # 概念分类
    category: Mapped[str] = mapped_column(
        String(20), default="topic", nullable=False
    )

    # --- 关系 ---
    user: Mapped["User"] = relationship("User", back_populates="concepts")
    # 以本概念为源的关系
    outgoing_relations: Mapped[List["ConceptRelation"]] = relationship(
        "ConceptRelation", foreign_keys="ConceptRelation.source_id", back_populates="source"
    )
    # 以本概念为目标的关系
    incoming_relations: Mapped[List["ConceptRelation"]] = relationship(
        "ConceptRelation", foreign_keys="ConceptRelation.target_id", back_populates="target"
    )

    def __repr__(self) -> str:
        return f"<Concept(id={self.id}, name={self.name}, category={self.category})>"
