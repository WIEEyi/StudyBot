"""
学习仪表盘 — Pydantic 请求/响应模型

为前端仪表盘页面提供数据结构：
- 概览统计 / 热力图 / 连续天数 / 学习会话记录 / AI 周报
"""

from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, Field


# ============================================================================
# 概览统计
# ============================================================================

class DashboardOverview(BaseModel):
    """整体学习统计概览 — 汇总当前用户的各项学习指标"""
    total_goals: int = Field(description="总目标数")
    active_goals: int = Field(description="进行中的目标数")
    completed_goals: int = Field(description="已完成的目标数")
    total_tasks: int = Field(description="总任务数")
    completed_tasks: int = Field(description="已完成任务数")
    todo_tasks: int = Field(description="待办任务数")
    in_progress_tasks: int = Field(description="进行中任务数")
    total_review_cards: int = Field(description="总复习卡片数")
    due_review_cards: int = Field(description="到期待复习卡片数")
    total_documents: int = Field(description="总文档数")
    total_concepts: int = Field(description="总概念数")
    total_study_hours: float = Field(0.0, description="累计学习时长（小时，保留一位小数）")
    total_study_days: int = Field(0, description="累计学习天数")
    today_tasks_completed: int = Field(0, description="今日完成任务数")
    today_cards_reviewed: int = Field(0, description="今日复习卡片数")


# ============================================================================
# 热力图
# ============================================================================

class HeatmapItem(BaseModel):
    """热力图单日数据 — 某一天的学习活动汇总"""
    session_date: date = Field(alias="date", description="日期（YYYY-MM-DD）")
    duration_minutes: int = Field(0, description="当日学习时长（分钟）")
    tasks_completed: int = Field(0, description="当日完成任务数")
    cards_reviewed: int = Field(0, description="当日复习卡片数")

    model_config = {"populate_by_name": True}


class HeatmapResponse(BaseModel):
    """热力图响应 — 日期范围内的每日学习数据（缺失日期补零）"""
    items: List[HeatmapItem] = Field(description="每日学习数据列表")
    start_date: date = Field(description="查询起始日期")
    end_date: date = Field(description="查询结束日期")


# ============================================================================
# 连续天数
# ============================================================================

class StreakResponse(BaseModel):
    """连续学习天数 — 当前连续 + 历史最长"""
    current_streak: int = Field(0, description="当前连续学习天数（从今天往前算）")
    current_start_date: Optional[date] = Field(None, description="当前连续开始日期")
    longest_streak: int = Field(0, description="历史最长连续学习天数")
    longest_start_date: Optional[date] = Field(None, description="最长连续开始日期")
    longest_end_date: Optional[date] = Field(None, description="最长连续结束日期")


# ============================================================================
# 学习会话记录
# ============================================================================

class StudySessionCreate(BaseModel):
    """记录/更新当日学习会话请求 — 所有字段可选，默认值为 0"""
    duration_minutes: int = Field(0, ge=0, description="学习时长（分钟）")
    tasks_completed: int = Field(0, ge=0, description="完成任务数")
    cards_reviewed: int = Field(0, ge=0, description="复习卡片数")


class StudySessionResponse(BaseModel):
    """学习会话响应"""
    id: int = Field(description="会话记录 ID")
    session_date: date = Field(description="学习日期")
    duration_minutes: int = Field(description="累计学习时长（分钟）")
    tasks_completed: int = Field(description="累计完成任务数")
    cards_reviewed: int = Field(description="累计复习卡片数")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="最后更新时间")

    model_config = {"from_attributes": True}


# ============================================================================
# AI 每周洞察
# ============================================================================

class WeeklyInsightStats(BaseModel):
    """一周学习统计数据 — 嵌入在 AI 洞察响应中"""
    tasks_completed: int = Field(0, description="本周完成任务数")
    cards_reviewed: int = Field(0, description="本周复习卡片数")
    total_study_minutes: int = Field(0, description="本周总学习时长（分钟）")
    avg_daily_minutes: int = Field(0, description="日均学习时长（分钟）")
    most_productive_day: Optional[date] = Field(None, description="本周最高效日期")
    active_days: int = Field(0, description="本周有活动天数")


class WeeklyInsightResponse(BaseModel):
    """AI 每周学习洞察响应"""
    week_start: date = Field(description="统计周期起始日期")
    week_end: date = Field(description="统计周期结束日期")
    insight: str = Field(description="AI 生成的学习洞察文本")
    stats: WeeklyInsightStats = Field(description="本周统计数据")
