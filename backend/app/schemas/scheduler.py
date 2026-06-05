"""
SchedulerAgent — Pydantic 请求/响应模型

动态计划调整的进度分析和调度方案。
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ===================== 进度统计 =====================

class ProgressReport(BaseModel):
    """进度统计报告"""
    total_tasks: int = Field(description="任务总数")
    done_tasks: int = Field(description="已完成任务数")
    in_progress_tasks: int = Field(description="进行中任务数")
    todo_tasks: int = Field(description="待开始任务数")
    overdue_tasks: int = Field(description="已过期任务数（状态未完成但截止日期已过）")
    completion_rate: float = Field(description="完成率（0.0-1.0）")
    estimated_remaining_minutes: int = Field(description="剩余任务预估总耗时（分钟）")


# ===================== 任务调整 =====================

class TaskAdjustment(BaseModel):
    """单个任务的调整方案（调整前 vs 调整后）"""
    task_id: int = Field(description="任务 ID")
    title: str = Field(description="任务标题（调整前的原标题）")
    original_due_date: Optional[str] = Field(None, description="原始截止日期")
    original_priority: str = Field(description="原始优先级")
    suggested_due_date: Optional[str] = Field(None, description="建议的新截止日期")
    suggested_priority: str = Field(description="建议的新优先级")
    reason: str = Field(description="AI 给出的调整理由")


# ===================== API 响应 =====================

class ScheduleResponse(BaseModel):
    """调度方案响应"""
    goal_id: int = Field(description="目标 ID")
    goal_title: str = Field(description="目标标题")
    analysis_summary: str = Field(description="AI 进度分析摘要")
    applied: bool = Field(description="是否已应用到数据库")
    progress_report: ProgressReport = Field(description="进度统计")
    adjustments: List[TaskAdjustment] = Field(
        default_factory=list, description="调整方案列表"
    )
    adjustments_count: int = Field(0, description="调整的任务数量")


class ScheduleRequest(BaseModel):
    """调度请求"""
    apply_changes: bool = Field(
        default=True,
        description="是否自动应用调整（true=直接修改数据库，false=仅预览）"
    )
