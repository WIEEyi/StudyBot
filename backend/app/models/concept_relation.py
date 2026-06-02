"""
ConceptRelation 知识图谱关系边

表示两个概念之间的有向关系。
- prerequisite: A 是 B 的前置知识
- related: A 与 B 相关
- part_of: B 包含 A（A 是 B 的一部分）
"""

from typing import TYPE_CHECKING
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.concept import Concept

# 关系类型
RELATION_TYPES = ("prerequisite", "related", "part_of")


class ConceptRelation(Base, TimestampMixin):
    """概念关系边"""

    __tablename__ = "concept_relations"

    # 源概念（关系的起点）
    source_id: Mapped[int] = mapped_column(
        ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 目标概念（关系的终点）
    target_id: Mapped[int] = mapped_column(
        ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 关系类型
    relation_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )

    # --- 关系 ---
    source: Mapped["Concept"] = relationship(
        "Concept", foreign_keys=[source_id], back_populates="outgoing_relations"
    )
    target: Mapped["Concept"] = relationship(
        "Concept", foreign_keys=[target_id], back_populates="incoming_relations"
    )

    def __repr__(self) -> str:
        return f"<ConceptRelation({self.source_id} --[{self.relation_type}]--> {self.target_id})>"
