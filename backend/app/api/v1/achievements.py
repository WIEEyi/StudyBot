"""
成就路由

提供的接口:
- GET  /achievements           — 获取所有成就（含进度）
- GET  /achievements/earned    — 获取已获得的成就
- POST /achievements/check     — 检查并颁发新成就
"""

import logging
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.achievement import Achievement
from app.models.user_achievement import UserAchievement
from app.schemas.achievement import (
    AchievementResponse,
    AchievementListResponse,
    AchievementProgressResponse,
    UserAchievementResponse,
)
from app.services.achievement_service import (
    check_and_award,
    get_achievement_progress,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/achievements", tags=["成就"])


@router.get("", response_model=AchievementListResponse)
async def list_achievements(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取所有成就列表（标注已获得）"""
    # get_achievement_progress 内部已调用 ensure_achievement_seeds
    progress_list = await get_achievement_progress(db, current_user.id)

    earned_codes = [p["achievement"].code for p in progress_list if p["is_earned"]]
    items = [AchievementResponse.model_validate(p["achievement"]) for p in progress_list]

    return AchievementListResponse(
        items=items,
        earned_codes=earned_codes,
        total=len(items),
        earned_count=len(earned_codes),
    )


@router.get("/progress", response_model=list[AchievementProgressResponse])
async def get_progress(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取所有成就的详细进度"""
    progress_list = await get_achievement_progress(db, current_user.id)

    return [
        AchievementProgressResponse(
            achievement=AchievementResponse.model_validate(p["achievement"]),
            current_progress=p["current_progress"],
            threshold=p["threshold"],
            percent=p["percent"],
            is_earned=p["is_earned"],
        )
        for p in progress_list
    ]


@router.get("/earned", response_model=list[UserAchievementResponse])
async def list_earned(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取已获得的所有成就"""
    result = await db.execute(
        select(UserAchievement)
        .where(UserAchievement.user_id == current_user.id)
        .options(selectinload(UserAchievement.achievement))
        .order_by(UserAchievement.created_at.desc())
    )
    user_achievements = result.scalars().all()

    return [
        UserAchievementResponse.from_orm_model(ua)
        for ua in user_achievements
    ]


@router.post("/check")
async def check_achievements(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """手动检查并颁发新成就

    返回新获得的成就列表。
    通常在完成任务、复习、上传等操作后由前端调用。
    """
    new_achievements = await check_and_award(db, current_user.id)

    return {
        "new_achievements": [
            AchievementResponse.model_validate(ach).model_dump()
            for ach in new_achievements
        ],
        "count": len(new_achievements),
    }
