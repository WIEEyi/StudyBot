"""
Concept 知识图谱 Schema

定义概念节点和关系的请求/响应数据结构。
"""

from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field


# ============================================================
# 创建 & 更新
# ============================================================

class ConceptCreate(BaseModel):
    """创建概念节点"""

    name: str = Field(min_length=1, max_length=255, description="概念名称")
    description: Optional[str] = Field(None, description="概念描述")
    category: Literal["subject", "topic", "subtopic", "term", "other"] = Field(
        "topic", description="概念分类"
    )


class ConceptUpdate(BaseModel):
    """更新概念节点 — 所有字段可选"""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[Literal["subject", "topic", "subtopic", "term", "other"]] = None


# ============================================================
# 响应
# ============================================================

class ConceptResponse(BaseModel):
    """概念节点响应"""

    id: int
    user_id: int
    name: str
    description: Optional[str] = None
    category: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConceptRelationResponse(BaseModel):
    """概念关系响应"""

    id: int
    source_id: int
    target_id: int
    relation_type: str

    model_config = {"from_attributes": True}


class ConceptDetailResponse(ConceptResponse):
    """概念详情响应 — 包含出边和入边关系"""

    outgoing_relations: list[ConceptRelationResponse] = Field(
        default_factory=list, description="以本概念为源的关系列表"
    )
    incoming_relations: list[ConceptRelationResponse] = Field(
        default_factory=list, description="以本概念为目标的关系列表"
    )


class ConceptListResponse(BaseModel):
    """概念分页列表"""

    items: list[ConceptResponse]
    total: int = Field(description="总记录数")
    offset: int = Field(description="当前偏移量")
    limit: int = Field(description="每页条数")


# ============================================================
# 关系管理
# ============================================================

class ConceptRelationCreate(BaseModel):
    """创建概念关系"""

    target_id: int = Field(description="目标概念 ID")
    relation_type: Literal["prerequisite", "related", "part_of"] = Field(
        description="关系类型: prerequisite=前置知识, related=相关, part_of=包含"
    )


# ============================================================
# 知识图谱
# ============================================================

class GraphNode(BaseModel):
    """图谱节点 — vis-network 用"""

    id: int
    name: str
    category: str  # 用于颜色映射: subject/topic/subtopic/term/other


class GraphEdge(BaseModel):
    """图谱边 — vis-network 用"""

    source: int  # concept id
    target: int  # concept id
    relation_type: str
    label: str  # 中文标签: 前置知识/相关/包含


class GraphResponse(BaseModel):
    """知识图谱完整数据"""

    nodes: list[GraphNode]
    edges: list[GraphEdge]
