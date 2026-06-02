"""
Goal 相关的 Pydantic 请求/响应模型
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ===================== 请求模型 =====================

class GoalCreate(BaseModel):
    """创建学习目标请求"""
    title: str = Field(min_length=1, max_length=255, description="目标标题")
    description: Optional[str] = Field(None, description="目标详细描述")
    deadline: Optional[datetime] = Field(None, description="截止日期")


class GoalUpdate(BaseModel):
    """更新学习目标请求
    所有字段可选，只传需要修改的字段（部分更新）
    """
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    status: Optional[str] = None  # 也可以通过 PUT 直接改状态


# ===================== 响应模型 =====================

class GoalResponse(BaseModel):
    """学习目标响应（含基本信息）"""
    id: int
    user_id: int
    title: str
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    status: str
    task_count: int = Field(0, description="关联的任务数量")
    created_at: datetime
    updated_at: datetime

    # 允许从 ORM 对象自动转换
    model_config = {"from_attributes": True}


class GoalDetailResponse(GoalResponse):
    """学习目标详情响应（含任务列表）"""
    tasks: list = Field(default_factory=list, description="关联的任务列表")


class GoalListResponse(BaseModel):
    """学习目标分页列表响应"""
    items: list[GoalResponse]
    total: int = Field(description="总记录数")
    offset: int = Field(description="当前偏移量")
    limit: int = Field(description="每页条数")
