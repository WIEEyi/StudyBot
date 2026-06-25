"""
Achievement Service

成就检查和颁发逻辑:
1. 预定义所有成就的条件
2. 在关键事件后调用 check_and_award() 检查是否有新成就达成
3. 自动创建 UserAchievement 记录

成就类别:
- streak: 连续学习天数（7/30/100 天）
- task: 任务完成里程碑（10/50/100 个）
- quiz: 测验表现（首次满分、10 次满分）
- review: 复习卡片里程碑（50/200/500 张）
- upload: 文档上传（1/5/20 份）
- concept: 知识图谱节点（10/50 个）
"""

import logging
from datetime import date, timedelta
from typing import List, Tuple

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.models.achievement import Achievement
from app.models.user_achievement import UserAchievement
from app.models.study_session import StudySession
from app.models.task import Task
from app.models.quiz import Quiz
from app.models.review_card import ReviewCard
from app.models.document import Document
from app.models.concept import Concept

logger = logging.getLogger(__name__)


# ===================== 成就定义 =====================

ACHIEVEMENT_DEFS = [
    # --- 连续学习 ---
    {"code": "streak_7", "name": "一周坚持", "description": "连续学习 7 天", "icon": "🔥", "category": "consistency", "rarity": "common", "threshold": 7},
    {"code": "streak_30", "name": "月度学霸", "description": "连续学习 30 天", "icon": "🔥", "category": "consistency", "rarity": "rare", "threshold": 30},
    {"code": "streak_100", "name": "百日精进", "description": "连续学习 100 天", "icon": "💎", "category": "consistency", "rarity": "epic", "threshold": 100},
    # --- 任务完成 ---
    {"code": "task_10", "name": "初露锋芒", "description": "完成 10 个任务", "icon": "✅", "category": "learning", "rarity": "common", "threshold": 10},
    {"code": "task_50", "name": "效率达人", "description": "完成 50 个任务", "icon": "✅", "category": "learning", "rarity": "rare", "threshold": 50},
    {"code": "task_100", "name": "百炼成钢", "description": "完成 100 个任务", "icon": "🏅", "category": "learning", "rarity": "epic", "threshold": 100},
    # --- 测验 ---
    {"code": "quiz_first", "name": "初次测验", "description": "完成第一次测验", "icon": "📝", "category": "quiz", "rarity": "common", "threshold": 1},
    {"code": "quiz_10", "name": "测验常客", "description": "完成 10 次测验", "icon": "📝", "category": "quiz", "rarity": "common", "threshold": 10},
    # --- 复习 ---
    {"code": "review_50", "name": "复习新手", "description": "复习 50 张卡片", "icon": "🃏", "category": "review", "rarity": "common", "threshold": 50},
    {"code": "review_200", "name": "记忆大师", "description": "复习 200 张卡片", "icon": "🃏", "category": "review", "rarity": "rare", "threshold": 200},
    {"code": "review_500", "name": "不忘之星", "description": "复习 500 张卡片", "icon": "⭐", "category": "review", "rarity": "epic", "threshold": 500},
    # --- 文档上传 ---
    {"code": "upload_1", "name": "知识入门", "description": "上传第一份文档", "icon": "📄", "category": "milestone", "rarity": "common", "threshold": 1},
    {"code": "upload_5", "name": "知识收集者", "description": "上传 5 份文档", "icon": "📚", "category": "milestone", "rarity": "common", "threshold": 5},
    {"code": "upload_20", "name": "知识图书馆", "description": "上传 20 份文档", "icon": "🏛️", "category": "milestone", "rarity": "rare", "threshold": 20},
    # --- 知识图谱 ---
    {"code": "concept_10", "name": "概念探索者", "description": "创建 10 个知识概念", "icon": "🧠", "category": "learning", "rarity": "common", "threshold": 10},
    {"code": "concept_50", "name": "知识架构师", "description": "创建 50 个知识概念", "icon": "🧠", "category": "learning", "rarity": "rare", "threshold": 50},
    # --- 学习时长 ---
    {"code": "study_10h", "name": "十小时学者", "description": "累计学习 10 小时", "icon": "⏱️", "category": "learning", "rarity": "common", "threshold": 600},
    {"code": "study_50h", "name": "五十小时达人", "description": "累计学习 50 小时", "icon": "⏱️", "category": "learning", "rarity": "rare", "threshold": 3000},
    {"code": "study_100h", "name": "百小时大师", "description": "累计学习 100 小时", "icon": "🎓", "category": "learning", "rarity": "epic", "threshold": 6000},
]


async def ensure_achievement_seeds(db: AsyncSession) -> None:
    """确保成就定义已写入数据库（幂等操作）

    在成就接口首次调用时执行，避免手动 seed。
    """
    for defn in ACHIEVEMENT_DEFS:
        result = await db.execute(
            select(Achievement).where(Achievement.code == defn["code"])
        )
        if result.scalar_one_or_none() is None:
            db.add(Achievement(**defn))

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()


async def _get_current_streak(db: AsyncSession, user_id: int) -> int:
    """计算当前连续学习天数"""
    result = await db.execute(
        select(StudySession.study_date)
        .where(StudySession.user_id == user_id)
        .distinct()
        .order_by(StudySession.study_date.desc())
    )
    active_dates = sorted({row[0] for row in result.all()}, reverse=True)

    if not active_dates:
        return 0

    today = date.today()
    streak = 0
    check_date = today

    for d in active_dates:
        if d == check_date:
            streak += 1
            check_date -= timedelta(days=1)
        elif d < check_date:
            break

    # 如果今天没有记录，检查昨天
    if streak == 0 and active_dates and active_dates[0] == today - timedelta(days=1):
        check_date = today - timedelta(days=1)
        for d in active_dates:
            if d == check_date:
                streak += 1
                check_date -= timedelta(days=1)
            elif d < check_date:
                break

    return streak


async def _get_progress_map(db: AsyncSession, user_id: int) -> dict:
    """获取用户所有成就相关的进度值"""
    progress = {}

    # 连续学习天数
    progress["streak"] = await _get_current_streak(db, user_id)

    # 完成任务数
    completed_tasks = (await db.execute(
        select(func.count()).where(Task.user_id == user_id, Task.status == "done")
    )).scalar() or 0
    progress["task"] = completed_tasks

    # 测验次数（用 quiz 总数近似）
    quiz_count = (await db.execute(
        select(func.count()).where(Quiz.user_id == user_id)
    )).scalar() or 0
    progress["quiz"] = quiz_count

    # 复习卡片数
    review_cards = (await db.execute(
        select(func.count()).where(ReviewCard.user_id == user_id, ReviewCard.repetitions > 0)
    )).scalar() or 0
    progress["review"] = review_cards

    # 文档上传数
    doc_count = (await db.execute(
        select(func.count()).where(Document.user_id == user_id)
    )).scalar() or 0
    progress["upload"] = doc_count

    # 知识概念数
    concept_count = (await db.execute(
        select(func.count()).where(Concept.user_id == user_id)
    )).scalar() or 0
    progress["concept"] = concept_count

    # 累计学习时长（分钟）
    total_minutes = (await db.execute(
        select(func.coalesce(func.sum(StudySession.duration_minutes), 0))
        .where(StudySession.user_id == user_id)
    )).scalar()
    progress["study_minutes"] = total_minutes

    return progress


# code → 进度 key 映射
_CODE_TO_PROGRESS_KEY = {
    "streak_7": "streak", "streak_30": "streak", "streak_100": "streak",
    "task_10": "task", "task_50": "task", "task_100": "task",
    "quiz_first": "quiz", "quiz_10": "quiz",
    "review_50": "review", "review_200": "review", "review_500": "review",
    "upload_1": "upload", "upload_5": "upload", "upload_20": "upload",
    "concept_10": "concept", "concept_50": "concept",
    "study_10h": "study_minutes", "study_50h": "study_minutes", "study_100h": "study_minutes",
}


async def check_and_award(db: AsyncSession, user_id: int) -> List[Achievement]:
    """检查并颁发新成就

    Returns:
        新获得的成就列表
    """
    await ensure_achievement_seeds(db)

    # 获取用户已有的成就 code
    earned_result = await db.execute(
        select(Achievement.code)
        .join(UserAchievement, UserAchievement.achievement_id == Achievement.id)
        .where(UserAchievement.user_id == user_id)
    )
    earned_codes = {row[0] for row in earned_result.all()}

    # 获取当前进度
    progress = await _get_progress_map(db, user_id)

    # 检查每个成就
    new_achievements = []
    for defn in ACHIEVEMENT_DEFS:
        code = defn["code"]
        if code in earned_codes:
            continue

        progress_key = _CODE_TO_PROGRESS_KEY.get(code, "")
        current_value = progress.get(progress_key, 0)

        if current_value >= defn["threshold"]:
            # 查找 achievement id
            ach_result = await db.execute(
                select(Achievement).where(Achievement.code == code)
            )
            achievement = ach_result.scalar_one()

            ua = UserAchievement(
                user_id=user_id,
                achievement_id=achievement.id,
                progress_value=current_value,
            )
            db.add(ua)
            new_achievements.append(achievement)
            logger.info("成就颁发: user_id=%s, achievement=%s", user_id, code)

    if new_achievements:
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            logger.warning("成就颁发冲突回滚: user_id=%s", user_id)
            new_achievements = []  # 回滚后清空，避免返回未持久化的数据

    return new_achievements


async def get_achievement_progress(db: AsyncSession, user_id: int) -> list:
    """获取所有成就及其进度

    Returns:
        list of (Achievement, current_progress, is_earned) tuples
    """
    await ensure_achievement_seeds(db)

    # 已有成就
    earned_result = await db.execute(
        select(Achievement.code)
        .join(UserAchievement, UserAchievement.achievement_id == Achievement.id)
        .where(UserAchievement.user_id == user_id)
    )
    earned_codes = {row[0] for row in earned_result.all()}

    # 进度
    progress = await _get_progress_map(db, user_id)

    # 所有成就
    all_result = await db.execute(select(Achievement).order_by(Achievement.category, Achievement.threshold))
    all_achievements = all_result.scalars().all()

    result = []
    for ach in all_achievements:
        progress_key = _CODE_TO_PROGRESS_KEY.get(ach.code, "")
        current_value = progress.get(progress_key, 0)
        threshold = ach.threshold
        percent = min(100.0, (current_value / threshold * 100) if threshold > 0 else 100.0)

        result.append({
            "achievement": ach,
            "current_progress": current_value,
            "threshold": threshold,
            "percent": round(percent, 1),
            "is_earned": ach.code in earned_codes,
        })

    return result
