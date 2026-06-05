"""
SM-2 间隔复习算法模块

实现 SuperMemo 2 算法，用于自动计算复习间隔。

SM-2 算法核心公式:
1. 评分 q (0-5) → 计算新 ease_factor
   EF' = EF + (0.1 - (5-q) * (0.08 + (5-q) * 0.02))
   如果 EF' < 1.3 → EF' = 1.3

2. 评分 >= 3（正确回忆）:
   - 第 1 次正确: interval = 1 天
   - 第 2 次正确: interval = 6 天
   - 第 3+ 次正确: interval = 当前 interval * ease_factor
   - repetitions += 1

3. 评分 < 3（遗忘）:
   - repetitions = 0
   - interval = 1 天（从头开始）

4. next_review_at = last_reviewed_at + interval 天
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# SM-2 常量
MIN_EASE_FACTOR = 1.3  # 最小难度系数
DEFAULT_EASE_FACTOR = 2.5  # 初始难度系数
FIRST_INTERVAL = 1  # 第一次正确后的间隔（天）
SECOND_INTERVAL = 6  # 第二次正确后的间隔（天）


def calculate_sm2(
    rating: int,
    current_interval: int,
    current_repetitions: int,
    current_ease_factor: float,
    review_time: datetime | None = None,
) -> dict:
    """SM-2 算法核心计算

    根据用户对卡片的评分，计算新的 SM-2 参数。

    Args:
        rating: 用户评分 (0-5)
            0 = 完全忘记 (complete blackout)
            1 = 几乎忘记 (incorrect, but upon seeing the answer remembered)
            2 = 勉强回忆 (incorrect, but answer seemed easy to recall)
            3 = 正确但有困难 (correct with serious difficulty)
            4 = 正确（稍作犹豫）(correct after hesitation)
            5 = 完美回忆 (perfect response)
        current_interval: 当前复习间隔（天）
        current_repetitions: 当前连续正确次数
        current_ease_factor: 当前难度系数
        review_time: 复习时间（默认 now UTC）

    Returns:
        {
            "ease_factor": float,     # 新的难度系数
            "interval": int,          # 新的复习间隔（天）
            "repetitions": int,       # 新的连续正确次数
            "next_review_at": datetime,  # 下次复习时间
            "rating": int,            # 本次评分
            "previous_interval": int, # 旧的间隔（用于响应）
        }
    """
    # 校验评分范围
    if not 0 <= rating <= 5:
        raise ValueError(f"评分必须在 0-5 之间，收到: {rating}")

    review_time = review_time or datetime.now(timezone.utc)

    # 1. 计算新的难度系数 (ease_factor)
    # q = rating
    # EF' = EF + (0.1 - (5-q) * (0.08 + (5-q) * 0.02))
    quality = rating
    new_ease_factor = (
        current_ease_factor
        + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    )
    # 确保不低于最小难度系数
    if new_ease_factor < MIN_EASE_FACTOR:
        new_ease_factor = MIN_EASE_FACTOR

    # 2. 计算新的间隔和重复次数
    previous_interval = current_interval

    if quality >= 3:
        # 正确回忆：间隔逐渐增大
        new_repetitions = current_repetitions + 1
        if new_repetitions == 1:
            new_interval = FIRST_INTERVAL  # 第 1 次正确 = 1 天
        elif new_repetitions == 2:
            new_interval = SECOND_INTERVAL  # 第 2 次正确 = 6 天
        else:
            # 第 3+ 次正确 = 当前间隔 * 难度系数（四舍五入取整）
            new_interval = round(current_interval * new_ease_factor)
            # 确保间隔至少比原来大（除非 ease_factor 降到 1.3）
            if new_interval <= current_interval:
                new_interval = current_interval + 1
    else:
        # 遗忘：重置到初始状态
        new_repetitions = 0
        new_interval = FIRST_INTERVAL  # 重新从 1 天开始

    # 3. 计算下次复习时间
    next_review_at = datetime.fromtimestamp(
        review_time.timestamp() + new_interval * 86400,  # 86400 = 24*60*60
        tz=timezone.utc,
    )

    result = {
        "ease_factor": round(new_ease_factor, 4),
        "interval": new_interval,
        "repetitions": new_repetitions,
        "next_review_at": next_review_at,
        "rating": rating,
        "previous_interval": previous_interval,
    }

    logger.info(
        "SM-2 计算完成: rating=%d, EF: %.2f→%.2f, interval: %d→%d d, reps: %d→%d, next=%s",
        rating,
        current_ease_factor,
        new_ease_factor,
        previous_interval,
        new_interval,
        current_repetitions,
        new_repetitions,
        next_review_at.strftime("%Y-%m-%d"),
    )

    return result


def is_card_due(card_next_review_at: datetime | None, now: datetime | None = None) -> bool:
    """判断卡片是否已到期需要复习

    Args:
        card_next_review_at: 卡片的下次复习时间
        now: 当前时间（默认 now UTC）

    Returns:
        True 如果卡片已到期（现在时间 >= next_review_at）
    """
    if card_next_review_at is None:
        # 从未复习过 → 需要复习
        return True
    now = now or datetime.now(timezone.utc)
    return now >= card_next_review_at
