"""
Scheduler Service

动态计划调整：检测过期任务，智能重排截止日期和优先级。
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task

logger = logging.getLogger(__name__)


async def reschedule_goal_tasks(
    goal_id: int,
    user_id: int,
    db: AsyncSession,
    strategy: str = "balanced",
) -> dict:
    """重新排列目标下未完成任务的截止日期

    策略:
    - balanced: 按优先级分配天数（high=1-3天, medium=4-7天, low=8-14天）
    - aggressive: 所有任务压缩到 7 天内
    - relaxed: 所有任务 spread 到 30 天内

    Returns:
        调整报告 dict
    """
    now = datetime.now(timezone.utc)

    # 加载未完成任务
    result = await db.execute(
        select(Task).where(
            Task.goal_id == goal_id,
            Task.user_id == user_id,
            Task.status.in_(["todo", "in_progress"]),
        ).order_by(Task.priority.desc(), Task.due_date.asc().nullslast())
    )
    pending_tasks = result.scalars().all()

    if not pending_tasks:
        return {
            "goal_id": goal_id,
            "total_pending": 0,
            "rescheduled": 0,
            "overdue": 0,
            "message": "没有待完成的任务",
        }

    # 统计过期任务
    overdue_count = sum(
        1 for t in pending_tasks
        if t.due_date and t.due_date < now
    )

    # 按策略分配新截止日期
    strategy_days = {
        "balanced": {"high": 3, "medium": 7, "low": 14},
        "aggressive": {"high": 2, "medium": 4, "low": 7},
        "relaxed": {"high": 7, "medium": 14, "low": 30},
    }
    days_map = strategy_days.get(strategy, strategy_days["balanced"])

    rescheduled = 0
    priority_counters = {"high": 0, "medium": 0, "low": 0}

    for task in pending_tasks:
        priority = task.priority or "medium"
        base_days = days_map.get(priority, 7)
        counter = priority_counters.get(priority, 0)

        # 同优先级任务错开 1 天
        new_due = now + timedelta(days=base_days + counter)
        task.due_date = new_due
        priority_counters[priority] = counter + 1
        rescheduled += 1

    await db.commit()

    report = {
        "goal_id": goal_id,
        "total_pending": len(pending_tasks),
        "rescheduled": rescheduled,
        "overdue": overdue_count,
        "strategy": strategy,
        "message": f"已重排 {rescheduled} 个任务（{overdue_count} 个过期），策略: {strategy}",
    }

    logger.info("计划重排: %s", report["message"])
    return report
