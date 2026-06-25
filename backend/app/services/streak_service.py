"""
Streak 计算工具

提供连续学习天数的计算逻辑，供成就系统和仪表盘共享。
避免在 achievement_service.py 和 dashboard.py 中重复实现。
"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.study_session import StudySession


@dataclass
class StreakInfo:
    """连续学习天数信息"""
    count: int = 0
    start_date: Optional[date] = None


async def _get_active_dates(db: AsyncSession, user_id: int) -> list:
    """获取用户所有活跃学习日期（降序）"""
    result = await db.execute(
        select(StudySession.study_date)
        .where(StudySession.user_id == user_id)
        .distinct()
        .order_by(StudySession.study_date.desc())
    )
    return sorted({row[0] for row in result.all()}, reverse=True)


async def calculate_current_streak(db: AsyncSession, user_id: int) -> int:
    """计算当前连续学习天数（简化接口，供成就系统使用）"""
    info = await get_current_streak_info(db, user_id)
    return info.count


async def get_current_streak_info(db: AsyncSession, user_id: int) -> StreakInfo:
    """计算当前连续学习天数（含起始日期，供仪表盘使用）

    逻辑:
    - 有学习会话记录的日期视为"活跃日"
    - 从今天（或昨天）往回数连续活跃天数
    """
    active_dates = await _get_active_dates(db, user_id)

    if not active_dates:
        return StreakInfo()

    today = date.today()
    streak = 0
    start_date = None
    check_date = today

    for d in active_dates:
        if d == check_date:
            streak += 1
            start_date = d
            check_date -= timedelta(days=1)
        elif d < check_date:
            break

    # 如果今天没有记录，检查昨天
    if streak == 0 and active_dates[0] == today - timedelta(days=1):
        check_date = today - timedelta(days=1)
        for d in active_dates:
            if d == check_date:
                streak += 1
                start_date = d
                check_date -= timedelta(days=1)
            elif d < check_date:
                break

    return StreakInfo(count=streak, start_date=start_date)


async def calculate_longest_streak(db: AsyncSession, user_id: int) -> StreakInfo:
    """计算历史最长连续学习天数

    Returns:
        StreakInfo 含 count、start_date（end_date 通过 start + count - 1 推算）
    """
    active_dates = await _get_active_dates(db, user_id)

    if not active_dates:
        return StreakInfo()

    sorted_dates = sorted(active_dates)  # 升序
    longest_streak = 1
    longest_start = sorted_dates[0]
    longest_end = sorted_dates[0]
    temp_streak = 1
    temp_start = sorted_dates[0]

    for i in range(1, len(sorted_dates)):
        if sorted_dates[i] - sorted_dates[i - 1] == timedelta(days=1):
            temp_streak += 1
        else:
            if temp_streak > longest_streak:
                longest_streak = temp_streak
                longest_start = temp_start
                longest_end = sorted_dates[i - 1]
            temp_streak = 1
            temp_start = sorted_dates[i]

    if temp_streak > longest_streak:
        longest_streak = temp_streak
        longest_start = temp_start
        longest_end = sorted_dates[-1]

    return StreakInfo(count=longest_streak, start_date=longest_start)
