"""
ReviewCard 间隔复习卡片相关的 Pydantic 请求/响应模型

Step 12: 间隔复习 (SM-2 算法)
"""

from datetime import datetime
from pydantic import BaseModel, Field


class ReviewCardCreate(BaseModel):
    """创建复习卡片请求"""
    front: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="卡片正面（问题/提示）",
    )
    back: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="卡片背面（答案）",
    )
    document_id: int | None = Field(
        None,
        ge=1,
        description="可选，关联的文档 ID",
    )


class ReviewCardUpdate(BaseModel):
    """更新复习卡片内容（不修改 SM-2 参数）"""
    front: str | None = Field(None, min_length=1, max_length=2000, description="卡片正面")
    back: str | None = Field(None, min_length=1, max_length=5000, description="卡片背面")
    document_id: int | None = Field(None, ge=1, description="关联的文档 ID")


class ReviewCardResponse(BaseModel):
    """复习卡片响应"""
    id: int
    user_id: int
    document_id: int | None = None
    front: str
    back: str
    source: str
    ease_factor: float
    interval: int
    repetitions: int
    next_review_at: datetime | None = None
    last_reviewed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReviewCardListResponse(BaseModel):
    """分页列表响应"""
    items: list[ReviewCardResponse]
    total: int
    offset: int
    limit: int


class ReviewSubmission(BaseModel):
    """提交复习评分请求"""
    rating: int = Field(
        ...,
        ge=0,
        le=5,
        description="回忆质量评分: 0=完全忘记, 5=完美回忆",
    )


class ReviewResponse(BaseModel):
    """复习评分响应（含更新后的 SM-2 参数）"""
    id: int
    rating: int = Field(description="本次评分")
    previous_interval: int = Field(description="之前的复习间隔（天）")
    new_interval: int = Field(description="新的复习间隔（天）")
    ease_factor: float = Field(description="更新后的难度系数")
    repetitions: int = Field(description="更新后的连续正确次数")
    next_review_at: datetime = Field(description="下次复习时间")
