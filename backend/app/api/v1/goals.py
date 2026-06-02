"""
学习目标 CRUD 路由

提供的接口:
- GET    /goals              — 分页列表（支持 status 过滤）
- GET    /goals/{id}         — 单个目标详情（含 task 列表）
- POST   /goals              — 创建目标
- PUT    /goals/{id}         — 更新目标
- DELETE /goals/{id}         — 删除目标
- PATCH  /goals/{id}/status  — 切换状态
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.learning_goal import LearningGoal, GOAL_STATUSES
from app.models.task import Task
from app.schemas.goal import (
    GoalCreate,
    GoalUpdate,
    GoalResponse,
    GoalDetailResponse,
    GoalListResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/goals", tags=["学习目标"])


# --- 辅助函数：检查目标归属 ---

async def _get_user_goal(
    goal_id: int, user: User, db: AsyncSession
) -> LearningGoal:
    """查找目标并校验归属权
    1. 查目标是否存在 → 404
    2. 目标是否属于当前用户 → 403
    返回找到的目标对象
    """
    result = await db.execute(
        select(LearningGoal).where(LearningGoal.id == goal_id)
    )
    goal = result.scalar_one_or_none()

    if goal is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"目标不存在: id={goal_id}",
        )

    if goal.user_id != user.id:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="无权操作此目标",
        )

    return goal


# ===================== 接口实现 =====================

@router.get("", response_model=GoalListResponse)
async def list_goals(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    goal_status: str = Query(None, description="按状态过滤: active/completed/paused"),
    offset: int = Query(0, ge=0, description="偏移量"),
    limit: int = Query(20, ge=1, le=100, description="每页条数"),
):
    """获取当前用户的学习目标分页列表
    支持按 status 过滤，默认返回前 20 条
    """
    # 构建查询：先查总数
    conditions = [LearningGoal.user_id == current_user.id]
    if goal_status is not None:
        conditions.append(LearningGoal.status == goal_status)

    # 查询总记录数
    count_query = select(func.count()).where(*conditions)
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 查询分页数据，预加载 task 数量
    query = (
        select(LearningGoal)
        .where(*conditions)
        .options(selectinload(LearningGoal.tasks))
        .order_by(LearningGoal.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    goals = result.scalars().all()

    # 转换为响应模型，手动填 task_count
    items = []
    for g in goals:
        resp = GoalResponse.model_validate(g)
        resp.task_count = len(g.tasks)
        items.append(resp)

    return GoalListResponse(items=items, total=total, offset=offset, limit=limit)


@router.get("/{goal_id}", response_model=GoalDetailResponse)
async def get_goal(
    goal_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取单个学习目标详情，含关联的任务列表"""
    # 查找并校验归属
    result = await db.execute(
        select(LearningGoal)
        .where(LearningGoal.id == goal_id)
        .options(selectinload(LearningGoal.tasks))
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

    # 构造包含 task 列表的响应
    resp = GoalDetailResponse.model_validate(goal)
    resp.task_count = len(goal.tasks)
    # 仅返回任务的基本信息（避免循环引用）
    from app.schemas.task import TaskResponse
    resp.tasks = [TaskResponse.model_validate(t) for t in goal.tasks]

    return resp


@router.post("", response_model=GoalResponse, status_code=http_status.HTTP_201_CREATED)
async def create_goal(
    request: GoalCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建新的学习目标"""
    goal = LearningGoal(
        user_id=current_user.id,
        title=request.title,
        description=request.description,
        deadline=request.deadline,
    )
    db.add(goal)
    await db.commit()
    await db.refresh(goal)

    logger.info("创建目标: id=%s, title=%s, user_id=%s", goal.id, goal.title, current_user.id)

    resp = GoalResponse.model_validate(goal)
    resp.task_count = 0
    return resp


@router.put("/{goal_id}", response_model=GoalResponse)
async def update_goal(
    goal_id: int,
    request: GoalUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新学习目标
    只更新传入的字段（部分更新 PATCH 语义，但使用 PUT 方法更符合 REST 习惯）
    """
    goal = await _get_user_goal(goal_id, current_user, db)

    # 只更新非 None 的字段
    update_data = request.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="没有提供需要更新的字段",
        )

    for field, value in update_data.items():
        setattr(goal, field, value)

    await db.commit()
    await db.refresh(goal)

    logger.info("更新目标: id=%s, fields=%s", goal_id, list(update_data.keys()))

    # 查 task 数量
    count_result = await db.execute(
        select(func.count()).where(Task.goal_id == goal_id)
    )
    task_count = count_result.scalar()

    resp = GoalResponse.model_validate(goal)
    resp.task_count = task_count
    return resp


@router.delete("/{goal_id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def delete_goal(
    goal_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除学习目标
    级联删除：目标下的任务会被自动解除关联（goal_id 设为 NULL）
    """
    goal = await _get_user_goal(goal_id, current_user, db)
    await db.delete(goal)
    await db.commit()

    logger.info("删除目标: id=%s, title=%s", goal_id, goal.title)


@router.patch("/{goal_id}/status", response_model=GoalResponse)
async def toggle_goal_status(
    goal_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    status: str = Query(..., description="目标状态: active/completed/paused"),
):
    """切换学习目标状态"""
    if status not in GOAL_STATUSES:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"无效的状态值: {status}，可选: {GOAL_STATUSES}",
        )

    goal = await _get_user_goal(goal_id, current_user, db)
    goal.status = status
    await db.commit()
    await db.refresh(goal)

    logger.info("切换目标状态: id=%s, status=%s", goal_id, status)

    # 查 task 数量
    count_result = await db.execute(
        select(func.count()).where(Task.goal_id == goal_id)
    )
    task_count = count_result.scalar()

    resp = GoalResponse.model_validate(goal)
    resp.task_count = task_count
    return resp
