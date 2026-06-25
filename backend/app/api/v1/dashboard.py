"""
学习仪表盘路由

提供的接口:
- GET  /dashboard/overview    — 统计概览（各模块计数 + 今日活动）
- GET  /dashboard/heatmap     — 热力图数据（按日期范围）
- GET  /dashboard/streak      — 连续学习天数
- POST /dashboard/session     — 记录学习会话
"""

import logging
from datetime import datetime, date, timedelta, timezone

from fastapi import APIRouter, Depends, Query, status as http_status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.learning_goal import LearningGoal
from app.models.task import Task
from app.models.review_card import ReviewCard
from app.models.document import Document
from app.models.concept import Concept
from app.models.study_session import StudySession
from app.services.streak_service import get_current_streak_info, calculate_longest_streak
from app.schemas.dashboard import (
    DashboardOverview,
    HeatmapItem,
    HeatmapResponse,
    StreakResponse,
    StudySessionCreate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["学习仪表盘"])


# ===================== 接口实现 =====================

@router.get("/overview", response_model=DashboardOverview)
async def get_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取统计概览数据"""
    uid = current_user.id
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # --- Goals 统计 ---
    total_goals = (await db.execute(
        select(func.count()).where(LearningGoal.user_id == uid)
    )).scalar() or 0
    active_goals = (await db.execute(
        select(func.count()).where(LearningGoal.user_id == uid, LearningGoal.status == "active")
    )).scalar() or 0
    completed_goals = (await db.execute(
        select(func.count()).where(LearningGoal.user_id == uid, LearningGoal.status == "completed")
    )).scalar() or 0

    # --- Tasks 统计 ---
    total_tasks = (await db.execute(
        select(func.count()).where(Task.user_id == uid)
    )).scalar() or 0
    completed_tasks = (await db.execute(
        select(func.count()).where(Task.user_id == uid, Task.status == "done")
    )).scalar() or 0
    todo_tasks = (await db.execute(
        select(func.count()).where(Task.user_id == uid, Task.status == "todo")
    )).scalar() or 0
    in_progress_tasks = (await db.execute(
        select(func.count()).where(Task.user_id == uid, Task.status == "in_progress")
    )).scalar() or 0

    # --- ReviewCards 统计 ---
    total_review_cards = (await db.execute(
        select(func.count()).where(ReviewCard.user_id == uid)
    )).scalar() or 0
    due_review_cards = (await db.execute(
        select(func.count()).where(
            ReviewCard.user_id == uid,
            (ReviewCard.next_review_at <= now) | (ReviewCard.next_review_at.is_(None)),
        )
    )).scalar() or 0

    # --- Documents / Concepts ---
    total_documents = (await db.execute(
        select(func.count()).where(Document.user_id == uid)
    )).scalar() or 0
    total_concepts = (await db.execute(
        select(func.count()).where(Concept.user_id == uid)
    )).scalar() or 0

    # --- StudySession 统计 ---
    total_minutes = (await db.execute(
        select(func.coalesce(func.sum(StudySession.duration_minutes), 0))
        .where(StudySession.user_id == uid)
    )).scalar()
    total_study_hours = round(total_minutes / 60, 1)

    total_study_days = (await db.execute(
        select(func.count(func.distinct(StudySession.study_date)))
        .where(StudySession.user_id == uid)
    )).scalar() or 0

    # --- 今日活动 ---
    today_tasks_completed = (await db.execute(
        select(func.count()).where(
            Task.user_id == uid, Task.status == "done",
            Task.updated_at >= today_start,
        )
    )).scalar() or 0

    today_cards_reviewed = (await db.execute(
        select(func.coalesce(func.sum(StudySession.cards_reviewed), 0))
        .where(StudySession.user_id == uid, StudySession.study_date == date.today())
    )).scalar()

    return DashboardOverview(
        total_goals=total_goals,
        active_goals=active_goals,
        completed_goals=completed_goals,
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        todo_tasks=todo_tasks,
        in_progress_tasks=in_progress_tasks,
        total_review_cards=total_review_cards,
        due_review_cards=due_review_cards,
        total_documents=total_documents,
        total_concepts=total_concepts,
        total_study_hours=total_study_hours,
        total_study_days=total_study_days,
        today_tasks_completed=today_tasks_completed,
        today_cards_reviewed=today_cards_reviewed,
    )


@router.get("/heatmap", response_model=HeatmapResponse)
async def get_heatmap(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    start_date: str = Query(..., description="起始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD"),
):
    """获取热力图数据（按日聚合学习会话）"""
    try:
        sd = date.fromisoformat(start_date)
        ed = date.fromisoformat(end_date)
    except ValueError:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="日期格式错误，请使用 YYYY-MM-DD",
        )

    # 查询日期范围内的学习会话
    result = await db.execute(
        select(StudySession)
        .where(
            StudySession.user_id == current_user.id,
            StudySession.study_date >= sd,
            StudySession.study_date <= ed,
        )
        .order_by(StudySession.study_date)
    )
    sessions = result.scalars().all()

    # 按日期聚合
    date_map: dict[str, HeatmapItem] = {}
    for s in sessions:
        key = s.study_date.isoformat()
        if key not in date_map:
            date_map[key] = HeatmapItem(date=key)
        date_map[key].duration_minutes += s.duration_minutes
        date_map[key].tasks_completed += s.tasks_completed
        date_map[key].cards_reviewed += s.cards_reviewed

    return HeatmapResponse(
        items=list(date_map.values()),
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/streak", response_model=StreakResponse)
async def get_streak(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """计算连续学习天数

    使用共享的 streak_service 模块，避免重复实现。
    """
    current = await get_current_streak_info(db, current_user.id)
    longest = await calculate_longest_streak(db, current_user.id)

    if current.count == 0 and longest.count == 0:
        return StreakResponse()

    return StreakResponse(
        current_streak=current.count,
        current_start_date=current.start_date.isoformat() if current.start_date else None,
        longest_streak=longest.count,
        longest_start_date=longest.start_date.isoformat() if longest.count > 0 else None,
        longest_end_date=(longest.start_date + timedelta(days=longest.count - 1)).isoformat() if longest.count > 0 and longest.start_date else None,
    )


@router.post("/session", status_code=http_status.HTTP_201_CREATED)
async def record_session(
    request: StudySessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """记录一次学习会话（今天）"""
    today = date.today()

    # 查找今天的会话，存在则累加，不存在则创建
    result = await db.execute(
        select(StudySession).where(
            StudySession.user_id == current_user.id,
            StudySession.study_date == today,
        )
    )
    session = result.scalar_one_or_none()

    if session:
        session.duration_minutes += request.duration_minutes
        session.tasks_completed += request.tasks_completed
        session.cards_reviewed += request.cards_reviewed
    else:
        session = StudySession(
            user_id=current_user.id,
            study_date=today,
            duration_minutes=request.duration_minutes,
            tasks_completed=request.tasks_completed,
            cards_reviewed=request.cards_reviewed,
        )
        db.add(session)

    await db.commit()
    await db.refresh(session)

    logger.info(
        "记录学习会话: user_id=%s, date=%s, +%d min",
        current_user.id, today, request.duration_minutes,
    )

    return {
        "study_date": today.isoformat(),
        "duration_minutes": session.duration_minutes,
        "tasks_completed": session.tasks_completed,
        "cards_reviewed": session.cards_reviewed,
    }
