"""
Task 相关的 Pydantic 请求/响应模型
"""

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field


# ===================== 请求模型 =====================

class TaskCreate(BaseModel):
    """创建任务请求"""
    title: str = Field(min_length=1, max_length=255, description="任务标题")
    description: Optional[str] = Field(None, description="任务描述")
    goal_id: Optional[int] = Field(None, description="关联的学习目标 ID（可选）")
    milestone: Optional[str] = Field(None, max_length=100, description="里程碑名称（AI 计划生成时自动填写）")
    milestone_order: Optional[int] = Field(None, ge=1, description="里程碑序号（1-based，用于排序展示）")
    priority: Literal["low", "medium", "high"] = Field("medium", description="优先级: low/medium/high")
    due_date: Optional[datetime] = Field(None, description="截止日期")
    estimated_minutes: Optional[int] = Field(None, ge=1, description="预估耗时（分钟）")


class TaskUpdate(BaseModel):
    """更新任务请求
    所有字段可选，只传需要修改的字段
    """
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    goal_id: Optional[int] = None
    milestone: Optional[str] = Field(None, max_length=100)
    milestone_order: Optional[int] = Field(None, ge=1)
    priority: Optional[str] = None
    due_date: Optional[datetime] = None
    status: Optional[str] = None  # 也支持直接修改状态
    estimated_minutes: Optional[int] = Field(None, ge=1)


# ===================== 响应模型 =====================

class TaskResponse(BaseModel):
    """任务响应"""
    id: int
    user_id: int
    goal_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    milestone: Optional[str] = None
    milestone_order: Optional[int] = None
    priority: str
    due_date: Optional[datetime] = None
    status: str
    estimated_minutes: Optional[int] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    # 允许从 ORM 对象自动转换
    model_config = {"from_attributes": True}


class TaskListResponse(BaseModel):
    """任务分页列表响应"""
    items: list[TaskResponse]
    total: int = Field(description="总记录数")
    offset: int = Field(description="当前偏移量")
    limit: int = Field(description="每页条数")
