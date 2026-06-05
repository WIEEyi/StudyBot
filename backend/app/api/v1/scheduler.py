"""
动态计划调整 API

提供的接口:
- POST /goals/{goal_id}/schedule — 触发 AI 进度分析和自动重排
- WS  /ws/schedule — WebSocket 实时进度（预留）
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status as http_status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.learning_goal import LearningGoal
from app.models.task import Task
from app.agents.scheduler_agent import run_scheduler
from app.schemas.scheduler import (
    ScheduleRequest,
    ScheduleResponse,
    ProgressReport,
    TaskAdjustment,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["动态计划调整"])


async def _build_schedule_response(state: dict, goal_id: int, applied: bool) -> ScheduleResponse:
    """将 SchedulerState 转换为 API 响应模型"""
    # 构建进度报告
    progress = ProgressReport(
        total_tasks=state.get("total_tasks", 0),
        done_tasks=state.get("done_tasks", 0),
        in_progress_tasks=state.get("in_progress_tasks", 0),
        todo_tasks=state.get("todo_tasks", 0),
        overdue_tasks=state.get("overdue_tasks", 0),
        completion_rate=state.get("completion_rate", 0.0),
        estimated_remaining_minutes=state.get("estimated_remaining_minutes", 0),
    )

    # 构建调整列表
    adjustments = []
    for adj in state.get("adjustments", []):
        # 查找任务原标题
        task_title = ""
        original_due_date = None
        original_priority = adj.get("suggested_priority", "medium")
        for t in state.get("tasks_summary", []):
            if t["id"] == adj["task_id"]:
                task_title = t["title"]
                original_due_date = t.get("due_date")
                original_priority = t.get("priority", "medium")
                break

        adjustments.append(TaskAdjustment(
            task_id=adj["task_id"],
            title=task_title,
            original_due_date=original_due_date,
            original_priority=original_priority,
            suggested_due_date=adj.get("suggested_due_date"),
            suggested_priority=adj.get("suggested_priority", original_priority),
            reason=adj.get("reason", ""),
        ))

    return ScheduleResponse(
        goal_id=goal_id,
        goal_title=state.get("goal_title", ""),
        analysis_summary=state.get("analysis_summary", ""),
        applied=applied,
        progress_report=progress,
        adjustments=adjustments,
        adjustments_count=len(adjustments),
    )


@router.post("/goals/{goal_id}/schedule", response_model=ScheduleResponse)
async def schedule_goal(
    goal_id: int,
    request: ScheduleRequest = ScheduleRequest(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """触发 AI 动态计划调整

    分析目标的当前进度，调用 AI 生成调整方案，可选择是否自动应用。

    业务规则:
    1. 目标必须存在且属于当前用户
    2. 目标下必须有任务（否则返回空调整方案）
    3. AI 只调整 todo/in_progress 状态的任务
    4. 调整后的截止日期不会超过目标截止日期

    Args:
        goal_id: 目标 ID
        request.apply_changes: true=自动应用调整到数据库, false=仅预览
    """
    # 运行 SchedulerAgent
    state = await run_scheduler(
        goal_id=goal_id,
        user_id=current_user.id,
        db_session=db,
        apply_changes=request.apply_changes,
    )

    # 检查 Agent 错误
    if state.get("error"):
        # 区分不同类型的错误
        error_msg = state["error"]
        if "不存在" in error_msg:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=error_msg,
            )
        if "无权" in error_msg:
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail=error_msg,
            )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg,
        )

    return await _build_schedule_response(state, goal_id, request.apply_changes)
