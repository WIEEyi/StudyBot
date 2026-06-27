"""
ReviewCard 间隔复习卡片 Pydantic 模型

SM-2 算法参数:
- ease_factor: 难度系数（默认 2.5，最低 1.3）
- interval: 复习间隔（天）
- repetitions: 连续正确次数
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ReviewCardCreate(BaseModel):
    """创建复习卡片"""
    front: str = Field(..., min_length=1, description="卡片正面（问题）")
    back: str = Field(..., min_length=1, description="卡片背面（答案）")
    document_id: Optional[int] = Field(None, description="关联文档 ID")


class ReviewCardUpdate(BaseModel):
    """更新复习卡片"""
    front: Optional[str] = Field(None, min_length=1)
    back: Optional[str] = Field(None, min_length=1)
    document_id: Optional[int] = None


class ReviewCardResponse(BaseModel):
    """卡片响应"""
    id: int
    user_id: int
    document_id: Optional[int] = None
    front: str
    back: str
    source: str
    ease_factor: float
    interval: int
    repetitions: int
    next_review_at: Optional[datetime] = None
    last_reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReviewCardListResponse(BaseModel):
    """卡片分页列表"""
    items: list[ReviewCardResponse]
    total: int
    offset: int
    limit: int


class ReviewSubmission(BaseModel):
    """SM-2 评分提交"""
    rating: int = Field(..., ge=0, le=5, description="评分 0-5")


class ReviewResponse(BaseModel):
    """SM-2 评分结果"""
    card_id: int
    rating: int
    old_ease_factor: float
    new_ease_factor: float
    old_interval: int
    new_interval: int
    old_repetitions: int
    new_repetitions: int
    next_review_at: Optional[datetime] = None
