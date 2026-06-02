"""
任务 CRUD 路由

提供的接口:
- GET    /tasks              — 分页列表（支持 goal_id/status/priority 过滤）
- GET    /tasks/{id}         — 单个任务详情
- POST   /tasks              — 创建任务
- PUT    /tasks/{id}         — 更新任务
- DELETE /tasks/{id}         — 删除任务
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.learning_goal import LearningGoal
from app.models.task import Task, TASK_STATUSES, PRIORITIES
from app.schemas.task import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    TaskListResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["任务"])


# --- 辅助函数：检查任务归属 ---

async def _get_user_task(
    task_id: int, user: User, db: AsyncSession
) -> Task:
    """查找任务并校验归属权"""
    result = await db.execute(
        select(Task).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务不存在: id={task_id}",
        )

    if task.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权操作此任务",
        )

    return task


# ===================== 接口实现 =====================

@router.get("", response_model=TaskListResponse)
async def list_tasks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    goal_id: int = Query(None, description="按目标 ID 过滤"),
    task_status: str = Query(None, alias="status", description="按状态过滤: todo/in_progress/done/cancelled"),
    priority: str = Query(None, description="按优先级过滤: low/medium/high"),
    offset: int = Query(0, ge=0, description="偏移量"),
    limit: int = Query(20, ge=1, le=100, description="每页条数"),
):
    """获取当前用户的任务分页列表
    支持按 goal_id / status / priority 过滤
    """
    conditions = [Task.user_id == current_user.id]
    if goal_id is not None:
        conditions.append(Task.goal_id == goal_id)
    if task_status is not None:
        conditions.append(Task.status == task_status)
    if priority is not None:
        conditions.append(Task.priority == priority)

    # 查询总记录数
    count_query = select(func.count()).where(*conditions)
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 查询分页数据
    query = (
        select(Task)
        .where(*conditions)
        .options(selectinload(Task.goal))
        .order_by(Task.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    tasks = result.scalars().all()

    items = [TaskResponse.model_validate(t) for t in tasks]

    return TaskListResponse(items=items, total=total, offset=offset, limit=limit)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取单个任务详情"""
    result = await db.execute(
        select(Task)
        .where(Task.id == task_id)
        .options(selectinload(Task.goal))
    )
    task = result.scalar_one_or_none()

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务不存在: id={task_id}",
        )

    if task.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权操作此任务",
        )

    return TaskResponse.model_validate(task)


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    request: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建新任务
    如果指定了 goal_id，会校验目标是否存在且属于当前用户
    """
    # 如果指定了 goal_id，先校验目标归属
    if request.goal_id is not None:
        result = await db.execute(
            select(LearningGoal).where(LearningGoal.id == request.goal_id)
        )
        goal = result.scalar_one_or_none()
        if goal is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"关联目标不存在: id={request.goal_id}",
            )
        if goal.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权关联此目标",
            )

    task = Task(
        user_id=current_user.id,
        goal_id=request.goal_id,
        title=request.title,
        description=request.description,
        milestone=request.milestone,
        priority=request.priority,
        due_date=request.due_date,
        estimated_minutes=request.estimated_minutes,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    logger.info("创建任务: id=%s, title=%s, user_id=%s", task.id, task.title, current_user.id)

    return TaskResponse.model_validate(task)


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    request: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新任务
    只更新传入的字段（部分更新语义）
    如果修改了 goal_id，会校验新目标是否存在且属于当前用户
    """
    task = await _get_user_task(task_id, current_user, db)

    update_data = request.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="没有提供需要更新的字段",
        )

    # 如果修改了 goal_id，校验新目标的归属
    new_goal_id = update_data.get("goal_id")
    if new_goal_id is not None:
        result = await db.execute(
            select(LearningGoal).where(LearningGoal.id == new_goal_id)
        )
        goal = result.scalar_one_or_none()
        if goal is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"关联目标不存在: id={new_goal_id}",
            )
        if goal.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权关联此目标",
            )

    for field, value in update_data.items():
        setattr(task, field, value)

    await db.commit()
    await db.refresh(task)

    logger.info("更新任务: id=%s, fields=%s", task_id, list(update_data.keys()))

    return TaskResponse.model_validate(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除任务"""
    task = await _get_user_task(task_id, current_user, db)
    await db.delete(task)
    await db.commit()

    logger.info("删除任务: id=%s, title=%s", task_id, task.title)
