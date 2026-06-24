"""
SchedulerAgent — 动态计划调整路由

提供的接口:
- POST /goals/{goal_id}/reschedule — 智能重排未完成任务的截止日期
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.learning_goal import LearningGoal
from app.services.scheduler_service import reschedule_goal_tasks

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/goals", tags=["计划调整"])


@router.post("/{goal_id}/reschedule")
async def reschedule_goal(
    goal_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    strategy: str = Query("balanced", description="重排策略: balanced/aggressive/relaxed"),
):
    """智能重排目标下未完成任务的截止日期

    策略说明:
    - balanced: 按优先级分配（high=1-3天, medium=4-7天, low=8-14天）
    - aggressive: 所有任务压缩到 7 天内
    - relaxed: 所有任务分散到 30 天内
    """
    if strategy not in ("balanced", "aggressive", "relaxed"):
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"无效的策略: {strategy}，可选: balanced/aggressive/relaxed",
        )

    # 校验目标归属
    result = await db.execute(
        select(LearningGoal).where(LearningGoal.id == goal_id)
    )
    goal = result.scalar_one_or_none()
    if goal is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"目标不存在: id={goal_id}",
        )
    if goal.user_id != current_user.id:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="无权操作此目标",
        )

    # 调用 Scheduler Service
    try:
        report = await reschedule_goal_tasks(
            goal_id=goal_id,
            user_id=current_user.id,
            db=db,
            strategy=strategy,
        )
    except Exception as e:
        logger.error("计划重排失败: goal_id=%s, error=%s", goal_id, e, exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="计划重排失败，请稍后重试",
        )

    return report
