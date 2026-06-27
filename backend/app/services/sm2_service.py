"""
SM-2 间隔复习算法 Service

将 SM-2 核心算法从路由层抽取，便于复用和独立测试。
"""

from datetime import datetime, timedelta, timezone


def sm2_calculate(
    ease_factor: float,
    interval: int,
    repetitions: int,
    rating: int,
) -> tuple[float, int, int, datetime]:
    """执行 SM-2 算法，返回新的参数和下次复习时间

    Args:
        ease_factor: 当前难度系数（默认 2.5，最低 1.3）
        interval: 当前复习间隔（天）
        repetitions: 连续正确次数
        rating: 用户评分 (0-5)

    Returns:
        (new_ease_factor, new_interval, new_repetitions, next_review_at)
    """
    # 更新 ease_factor
    new_ef = ease_factor + (0.1 - (5 - rating) * (0.08 + (5 - rating) * 0.02))
    new_ef = max(1.3, new_ef)

    if rating >= 3:
        # 回忆正确
        if repetitions == 0:
            new_interval = 1
        elif repetitions == 1:
            new_interval = 6
        else:
            new_interval = round(interval * new_ef)
        new_repetitions = repetitions + 1
    else:
        # 回忆失败 → 重置
        new_repetitions = 0
        new_interval = 1

    now = datetime.now(timezone.utc)
    next_review_at = now + timedelta(days=new_interval)

    return new_ef, new_interval, new_repetitions, next_review_at
