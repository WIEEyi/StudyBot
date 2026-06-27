"""
Learning Path 学习路径 Schema

AI 生成的个性化学习路径数据结构。
"""

from typing import Optional
from pydantic import BaseModel, Field


class LearningPathStep(BaseModel):
    """学习路径单步"""
    step_number: int = Field(description="步骤序号")
    title: str = Field(description="步骤标题")
    description: str = Field(description="步骤描述/建议")
    action_type: str = Field(
        description="行动类型: review / quiz / read / practice"
    )
    priority: str = Field(
        default="medium",
        description="优先级: high / medium / low"
    )
    # 关联资源 ID（可选）
    resource_id: Optional[int] = Field(None, description="关联资源 ID")
    resource_type: Optional[str] = Field(None, description="资源类型: document / quiz / concept / review_card")
    # 预估时间
    estimated_minutes: int = Field(default=15, description="预估用时（分钟）")


class LearningPathResponse(BaseModel):
    """学习路径响应"""
    title: str = Field(description="路径标题")
    summary: str = Field(description="AI 生成的总结/分析")
    steps: list[LearningPathStep] = Field(description="学习步骤列表")
    total_estimated_minutes: int = Field(description="总预估用时")
    focus_areas: list[str] = Field(
        default_factory=list,
        description="重点关注领域"
    )


class LearningPathGenerateRequest(BaseModel):
    """生成学习路径请求"""
    focus: Optional[str] = Field(
        None,
        description="学习重点（可选），如 '复习薄弱点' / '准备考试'"
    )
    document_id: Optional[int] = Field(
        None,
        description="基于特定文档生成路径（可选）"
    )
    max_steps: int = Field(
        8, ge=3, le=15,
        description="最大步骤数 (3-15)"
    )
