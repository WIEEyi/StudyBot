"""
Task Service

将任务状态变更的业务逻辑从路由层抽取。
"""

from datetime import datetime, timezone
from typing import Optional


def on_task_status_change(
    old_status: str,
    new_status: str,
    current_completed_at: Optional[datetime] = None,
) -> Optional[datetime]:
    """任务状态变更时处理 completed_at

    - 变为 done: 记录完成时间
    - 从 done 变为其他: 清空完成时间
    - 其他变更: 保持原值

    Returns:
        更新后的 completed_at 值，或 None 表示不需要更新
    """
    if new_status == "done" and old_status != "done":
        return datetime.now(timezone.utc)
    elif old_status == "done" and new_status != "done":
        return None  # 清空
    return current_completed_at  # 保持不变
