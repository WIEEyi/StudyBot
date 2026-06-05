"""
Concept 知识图谱 — Pydantic 请求/响应模型

概念节点 + 概念关系的请求和响应模型。
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ===================== 概念请求模型 =====================

class ConceptCreate(BaseModel):
    """创建概念请求"""
    name: str = Field(min_length=1, max_length=255, description="概念名称")
    description: Optional[str] = Field(None, description="概念描述")
    category: str = Field(
        default="topic",
        description="概念分类: subject/topic/subtopic/term/other"
    )


class ConceptUpdate(BaseModel):
    """更新概念请求 — 所有字段可选（部分更新）"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = None


# ===================== 关系请求模型 =====================

class ConceptRelationCreate(BaseModel):
    """创建概念关系请求"""
    target_id: int = Field(description="目标概念 ID")
    relation_type: str = Field(
        description="关系类型: prerequisite/related/part_of"
    )


# ===================== 关系响应模型 =====================

class ConceptRelationResponse(BaseModel):
    """概念关系响应"""
    id: int
    source_id: int
    target_id: int
    relation_type: str
    # 目标概念的摘要信息（方便前端展示）
    target_name: Optional[str] = Field(None, description="目标概念名称")
    source_name: Optional[str] = Field(None, description="源概念名称")
    created_at: datetime

    model_config = {"from_attributes": True}


# ===================== 概念响应模型 =====================

class ConceptResponse(BaseModel):
    """概念响应（基本信息）"""
    id: int
    user_id: int
    name: str
    description: Optional[str] = None
    category: str
    relation_count: int = Field(0, description="关联的关系总数")
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConceptDetailResponse(ConceptResponse):
    """概念详情响应（含关系列表）"""
    outgoing_relations: List[ConceptRelationResponse] = Field(
        default_factory=list, description="以本概念为源的关系"
    )
    incoming_relations: List[ConceptRelationResponse] = Field(
        default_factory=list, description="以本概念为目标的关系"
    )


class ConceptListResponse(BaseModel):
    """概念分页列表响应"""
    items: List[ConceptResponse]
    total: int = Field(description="总记录数")
    offset: int = Field(description="当前偏移量")
    limit: int = Field(description="每页条数")
