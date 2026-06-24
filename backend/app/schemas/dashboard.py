"""
Dashboard 仪表盘 Pydantic 模型

与前端 types.ts 中的 DashboardOverview / HeatmapResponse / StreakResponse 对齐。
"""

from datetime import date
from typing import Optional
from pydantic import BaseModel


class DashboardOverview(BaseModel):
    """统计概览"""
    total_goals: int = 0
    active_goals: int = 0
    completed_goals: int = 0
    total_tasks: int = 0
    completed_tasks: int = 0
    todo_tasks: int = 0
    in_progress_tasks: int = 0
    total_review_cards: int = 0
    due_review_cards: int = 0
    total_documents: int = 0
    total_concepts: int = 0
    total_study_hours: float = 0.0
    total_study_days: int = 0
    today_tasks_completed: int = 0
    today_cards_reviewed: int = 0


class HeatmapItem(BaseModel):
    """热力图单日数据"""
    date: str  # YYYY-MM-DD
    duration_minutes: int = 0
    tasks_completed: int = 0
    cards_reviewed: int = 0


class HeatmapResponse(BaseModel):
    """热力图响应"""
    items: list[HeatmapItem]
    start_date: str
    end_date: str


class StreakResponse(BaseModel):
    """连续学习天数"""
    current_streak: int = 0
    current_start_date: Optional[str] = None
    longest_streak: int = 0
    longest_start_date: Optional[str] = None
    longest_end_date: Optional[str] = None


class StudySessionCreate(BaseModel):
    """记录学习会话"""
    duration_minutes: int = 0
    tasks_completed: int = 0
    cards_reviewed: int = 0
