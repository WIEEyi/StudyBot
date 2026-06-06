"""
学习仪表盘 API

提供的接口:
- GET  /dashboard/overview        — 整体学习统计概览
- GET  /dashboard/heatmap         — 每日学习热力图数据
- GET  /dashboard/streak          — 连续学习天数
- POST /dashboard/study-session   — 记录/更新当日学习会话
- POST /dashboard/weekly-insight  — AI 生成每周学习洞察
"""

import logging
from datetime import date, datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.dashboard import (
    DashboardOverview,
    HeatmapResponse,
    StreakResponse,
    StudySessionCreate,
    StudySessionResponse,
    WeeklyInsightResponse,
)
from app.services.dashboard_service import (
    get_overview,
    get_heatmap_data,
    get_streak,
    upsert_study_session,
    generate_weekly_insight,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["学习仪表盘"])


# ============================================================================
# GET /dashboard/overview — 整体统计概览
# ============================================================================

@router.get("/overview", response_model=DashboardOverview)
async def dashboard_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户的整体学习统计概览

    返回目标数、任务数、完成率、复习卡片、今日学习情况等汇总数据。
    """
    return await get_overview(current_user.id, db)


# ============================================================================
# GET /dashboard/heatmap — 每日学习热力图
# ============================================================================

@router.get("/heatmap", response_model=HeatmapResponse)
async def dashboard_heatmap(
    start_date: date = Query(..., description="起始日期（YYYY-MM-DD）"),
    end_date: date = Query(..., description="结束日期（YYYY-MM-DD）"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取指定日期范围内的每日学习热力图数据

    缺失的日期自动补零，确保前端热力图连续显示。
    数据来源：StudySession + Task.completed_at + ReviewCard.last_reviewed_at。

    约束规则:
    - start_date 不能晚于 end_date
    - 最大查询范围 365 天
    """
    if start_date > end_date:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="start_date 不能晚于 end_date",
        )

    # 限制最大查询范围
    if (end_date - start_date).days > 365:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="查询范围不能超过 365 天",
        )

    return await get_heatmap_data(current_user.id, start_date, end_date, db)


# ============================================================================
# GET /dashboard/streak — 连续学习天数
# ============================================================================

@router.get("/streak", response_model=StreakResponse)
async def dashboard_streak(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前连续学习天数和历史最长连续天数

    数据来源（取并集去重）：StudySession.session_date + Task.completed_at + ReviewCard.last_reviewed_at。
    从今天往前扫描，遇到无活动日期即停止。
    """
    return await get_streak(current_user.id, db)


# ============================================================================
# POST /dashboard/study-session — 记录/更新学习会话
# ============================================================================

@router.post("/study-session", response_model=StudySessionResponse, status_code=http_status.HTTP_201_CREATED)
async def record_study_session(
    request: StudySessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """记录或更新当日学习活动（Upsert）

    自动使用今天的日期。同一天多次调用会累加数值。

    Args:
        request.duration_minutes: 本次学习时长（分钟），默认 0
        request.tasks_completed: 本次完成任务数，默认 0
        request.cards_reviewed: 本次复习卡片数，默认 0
    """
    session = await upsert_study_session(current_user.id, request, db)
    return StudySessionResponse.model_validate(session)


# ============================================================================
# POST /dashboard/weekly-insight — AI 每周洞察
# ============================================================================

@router.post("/weekly-insight", response_model=WeeklyInsightResponse)
async def weekly_insight(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """生成 AI 每周学习洞察报告

    汇总近 7 天学习数据，调用 LLM 生成个性化的学习分析和改进建议。
    如果 LLM 不可用（如测试环境），返回默认鼓励性文本。
    """
    return await generate_weekly_insight(current_user.id, db)
