"""
学习仪表盘服务层

提供统计聚合、热力图数据生成、连续天数计算、学习会话 Upsert、AI 每周洞察等功能。
所有函数均为模块级纯函数，不依赖类实例。
"""

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import literal_column

from app.models.user import User
from app.models.learning_goal import LearningGoal
from app.models.task import Task
from app.models.document import Document
from app.models.review_card import ReviewCard
from app.models.concept import Concept
from app.models.study_session import StudySession
from app.schemas.dashboard import (
    DashboardOverview,
    HeatmapItem,
    HeatmapResponse,
    StreakResponse,
    StudySessionCreate,
    StudySessionResponse,
    WeeklyInsightStats,
    WeeklyInsightResponse,
)

logger = logging.getLogger(__name__)


# ============================================================================
# AI 洞察 — LLM 结构化输出模型
# ============================================================================

class _WeeklyInsightOutput(BaseModel):
    """LLM 结构化输出：每周学习洞察"""
    insight: str = Field(description="个性化的学习洞察报告，包含对本周学习情况的分析、鼓励和改进建议")


# ============================================================================
# 概览统计
# ============================================================================

async def get_overview(user_id: int, db: AsyncSession) -> DashboardOverview:
    """获取用户整体学习统计概览

    一次查询获取全部统计数据（除今日指标），避免 N+1 查询问题。
    """
    now = datetime.now(timezone.utc)
    today = now.date()
    today_start = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)

    # 按目标状态分组统计
    goal_counts = await db.execute(
        select(
            func.count(LearningGoal.id).label("total"),
            func.count(case((LearningGoal.status == "active", 1))).label("active"),
            func.count(case((LearningGoal.status == "completed", 1))).label("completed"),
        ).where(LearningGoal.user_id == user_id)
    )
    gc = goal_counts.one()

    # 按任务状态分组统计
    task_counts = await db.execute(
        select(
            func.count(Task.id).label("total"),
            func.count(case((Task.status == "done", 1))).label("completed"),
            func.count(case((Task.status == "todo", 1))).label("todo"),
            func.count(case((Task.status == "in_progress", 1))).label("in_progress"),
        ).where(Task.user_id == user_id)
    )
    tc = task_counts.one()

    # 复习卡片统计
    card_counts = await db.execute(
        select(
            func.count(ReviewCard.id).label("total"),
            func.count(case((ReviewCard.next_review_at <= now, 1))).label("due"),
        ).where(ReviewCard.user_id == user_id)
    )
    cc = card_counts.one()

    # 文档统计
    doc_total = await db.execute(
        select(func.count(Document.id)).where(Document.user_id == user_id)
    )

    # 概念统计
    concept_total = await db.execute(
        select(func.count(Concept.id)).where(Concept.user_id == user_id)
    )

    # StudySession 汇总
    session_stats = await db.execute(
        select(
            func.coalesce(func.sum(StudySession.duration_minutes), 0).label("total_minutes"),
            func.coalesce(func.count(StudySession.id), 0).label("total_days"),
        ).where(StudySession.user_id == user_id)
    )
    ss = session_stats.one()

    # 今日统计
    today_tasks = await db.execute(
        select(func.count(Task.id)).where(
            and_(Task.user_id == user_id, Task.completed_at >= today_start)
        )
    )
    today_cards = await db.execute(
        select(func.count(ReviewCard.id)).where(
            and_(ReviewCard.user_id == user_id, ReviewCard.last_reviewed_at >= today_start)
        )
    )

    total_minutes = int(ss.total_minutes)
    total_hours = round(total_minutes / 60, 1)

    return DashboardOverview(
        total_goals=gc.total,
        active_goals=gc.active,
        completed_goals=gc.completed,
        total_tasks=tc.total,
        completed_tasks=tc.completed,
        todo_tasks=tc.todo,
        in_progress_tasks=tc.in_progress,
        total_review_cards=cc.total,
        due_review_cards=cc.due,
        total_documents=doc_total.scalar(),
        total_concepts=concept_total.scalar(),
        total_study_hours=total_hours,
        total_study_days=ss.total_days,
        today_tasks_completed=today_tasks.scalar(),
        today_cards_reviewed=today_cards.scalar(),
    )


# ============================================================================
# 热力图数据
# ============================================================================

async def get_heatmap_data(
    user_id: int, start_date: date, end_date: date, db: AsyncSession
) -> HeatmapResponse:
    """获取日期范围内的每日学习活动数据（缺失日期补零）

    数据源合并三条线：
    1. StudySession.session_date（学习会话记录）
    2. Task.completed_at（任务完成记录）
    3. ReviewCard.last_reviewed_at（卡片复习记录）
    """

    # 1. 从 StudySession 查询已有的每日记录
    ss_result = await db.execute(
        select(StudySession).where(
            and_(
                StudySession.user_id == user_id,
                StudySession.session_date >= start_date,
                StudySession.session_date <= end_date,
            )
        )
    )
    sessions = {s.session_date: s for s in ss_result.scalars().all()}

    # 2. 按日期分组统计 task completions
    task_dates = await db.execute(
        select(
            func.date(Task.completed_at).label("d"),
            func.count(Task.id).label("cnt"),
        ).where(
            and_(
                Task.user_id == user_id,
                Task.completed_at.isnot(None),
                func.date(Task.completed_at) >= start_date,
                func.date(Task.completed_at) <= end_date,
            )
        ).group_by(func.date(Task.completed_at))
    )
    task_counts = {row.d: row.cnt for row in task_dates.all()}

    # 3. 按日期分组统计 review card reviews
    card_dates = await db.execute(
        select(
            func.date(ReviewCard.last_reviewed_at).label("d"),
            func.count(ReviewCard.id).label("cnt"),
        ).where(
            and_(
                ReviewCard.user_id == user_id,
                ReviewCard.last_reviewed_at.isnot(None),
                func.date(ReviewCard.last_reviewed_at) >= start_date,
                func.date(ReviewCard.last_reviewed_at) <= end_date,
            )
        ).group_by(func.date(ReviewCard.last_reviewed_at))
    )
    card_counts = {row.d: row.cnt for row in card_dates.all()}

    # 4. 构建完整日期范围（缺失的补零）
    items = []
    current = start_date
    while current <= end_date:
        session = sessions.get(current)
        items.append(HeatmapItem(
            session_date=current,
            duration_minutes=session.duration_minutes if session else 0,
            tasks_completed=task_counts.get(current, 0),
            cards_reviewed=card_counts.get(current, 0),
        ))
        current += timedelta(days=1)

    return HeatmapResponse(items=items, start_date=start_date, end_date=end_date)


# ============================================================================
# 连续天数
# ============================================================================

async def get_streak(user_id: int, db: AsyncSession) -> StreakResponse:
    """计算当前连续学习天数和历史最长连续天数

    数据源：StudySession.session_date + Task.completed_at 日期 + ReviewCard.last_reviewed_at 日期
    对三者的日期取并集去重后按从早到晚排序，然后扫描连续区间。
    """

    # 1. 收集所有有活动的日期
    ss_dates = await db.execute(
        select(StudySession.session_date).where(StudySession.user_id == user_id)
    )
    task_dates = await db.execute(
        select(func.date(Task.completed_at)).where(
            and_(Task.user_id == user_id, Task.completed_at.isnot(None))
        )
    )
    card_dates = await db.execute(
        select(func.date(ReviewCard.last_reviewed_at)).where(
            and_(ReviewCard.user_id == user_id, ReviewCard.last_reviewed_at.isnot(None))
        )
    )

    # 合并去重排序
    active_dates = set()
    for row in ss_dates.scalars().all():
        active_dates.add(row)
    for row in task_dates.scalars().all():
        if row:
            active_dates.add(row)
    for row in card_dates.scalars().all():
        if row:
            active_dates.add(row)

    if not active_dates:
        return StreakResponse(current_streak=0)

    sorted_dates = sorted(active_dates)

    # 2. 计算最长连续
    longest_streak = 1
    longest_start = sorted_dates[0]
    longest_end = sorted_dates[0]
    current_run = 1
    current_run_start = sorted_dates[0]

    for i in range(1, len(sorted_dates)):
        if (sorted_dates[i] - sorted_dates[i - 1]).days == 1:
            current_run += 1
        else:
            if current_run > longest_streak:
                longest_streak = current_run
                longest_start = current_run_start
                longest_end = sorted_dates[i - 1]
            current_run = 1
            current_run_start = sorted_dates[i]

    # 最后一段
    if current_run > longest_streak:
        longest_streak = current_run
        longest_start = current_run_start
        longest_end = sorted_dates[-1]

    # 3. 计算当前连续（从今天往前）
    today = date.today()
    current_streak = 0
    current_start = None
    check_date = today
    while check_date in active_dates:
        current_streak += 1
        current_start = check_date
        check_date -= timedelta(days=1)

    return StreakResponse(
        current_streak=current_streak,
        current_start_date=current_start,
        longest_streak=longest_streak,
        longest_start_date=longest_start,
        longest_end_date=longest_end,
    )


# ============================================================================
# 学习会话 Upsert
# ============================================================================

async def upsert_study_session(
    user_id: int, data: StudySessionCreate, db: AsyncSession
) -> StudySession:
    """创建或更新当日学习会话（Upsert）

    同一天多次调用会累加数值，适合前端定期上报学习活动。
    """
    today = date.today()

    # 查找今天的记录
    result = await db.execute(
        select(StudySession).where(
            and_(
                StudySession.user_id == user_id,
                StudySession.session_date == today,
            )
        )
    )
    session = result.scalar_one_or_none()

    if session:
        # 更新：累加数值
        session.duration_minutes += data.duration_minutes
        session.tasks_completed += data.tasks_completed
        session.cards_reviewed += data.cards_reviewed
        logger.info(
            "更新学习会话: user_id=%s, date=%s, duration=%s",
            user_id, today, session.duration_minutes,
        )
    else:
        # 新建
        session = StudySession(
            user_id=user_id,
            session_date=today,
            duration_minutes=data.duration_minutes,
            tasks_completed=data.tasks_completed,
            cards_reviewed=data.cards_reviewed,
        )
        db.add(session)
        logger.info(
            "创建学习会话: user_id=%s, date=%s, duration=%s",
            user_id, today, data.duration_minutes,
        )

    await db.commit()
    await db.refresh(session)
    return session


# ============================================================================
# AI 每周洞察
# ============================================================================

async def generate_weekly_insight(
    user_id: int, db: AsyncSession
) -> WeeklyInsightResponse:
    """汇总近 7 天学习数据，调用 LLM 生成个性化学习洞察

    返回：
    - week_start / week_end：统计周期
    - insight：AI 生成的文本洞察
    - stats：本周统计数字

    如果 LLM 不可用（如测试环境），返回默认鼓励性文本。
    """
    today = date.today()
    week_start = today - timedelta(days=6)  # 含今天共 7 天
    week_end = today

    # 1. 计算本周统计
    heatmap = await get_heatmap_data(user_id, week_start, week_end, db)

    tasks_completed = sum(item.tasks_completed for item in heatmap.items)
    cards_reviewed = sum(item.cards_reviewed for item in heatmap.items)
    total_minutes = sum(item.duration_minutes for item in heatmap.items)
    active_days = sum(
        1 for item in heatmap.items
        if item.duration_minutes > 0 or item.tasks_completed > 0 or item.cards_reviewed > 0
    )
    avg_daily = total_minutes // 7

    # 找最产出的一天
    most_productive = None
    max_productivity = 0
    for item in heatmap.items:
        productivity = item.duration_minutes + item.tasks_completed * 10 + item.cards_reviewed * 3
        if productivity > max_productivity:
            max_productivity = productivity
            most_productive = item.session_date

    stats = WeeklyInsightStats(
        tasks_completed=tasks_completed,
        cards_reviewed=cards_reviewed,
        total_study_minutes=total_minutes,
        avg_daily_minutes=avg_daily,
        most_productive_day=most_productive,
        active_days=active_days,
    )

    # 2. 调用 LLM 生成洞察
    insight_text = await _call_llm_for_insight(stats)

    return WeeklyInsightResponse(
        week_start=week_start,
        week_end=week_end,
        insight=insight_text,
        stats=stats,
    )


async def _call_llm_for_insight(stats: WeeklyInsightStats) -> str:
    """调用 LLM 生成每周学习洞察文本

    如果 LLM 配置无效或调用失败，返回默认文本。
    """
    system_prompt = """你是一位专业的学习教练，负责为用户生成每周学习总结报告。

你的报告应该：
1. 简要总结本周的学习情况（用具体数字）
2. 给出真诚的鼓励和肯定
3. 如果学习活动较少，提供温和的改进建议
4. 保持积极向上的语气
5. 输出不超过 300 字

请用中文回复。"""

    user_prompt = f"""以下是用户本周（近 7 天）的学习数据：

- 完成任务数：{stats.tasks_completed} 个
- 复习卡片数：{stats.cards_reviewed} 张
- 总学习时长：{stats.total_study_minutes} 分钟（约 {stats.total_study_minutes / 60:.1f} 小时）
- 日均学习时长：{stats.avg_daily_minutes} 分钟
- 有活动天数：{stats.active_days} 天（共 7 天）
- 最高效日期：{stats.most_productive_day or '无'}

请根据以上数据生成一份个性化的本周学习总结报告。"""

    try:
        from app.config import get_settings
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import SystemMessage, HumanMessage

        settings = get_settings()

        # 检查 LLM 配置是否有效
        if settings.OPENAI_API_KEY in ("sk-your-api-key-here", "", None):
            logger.warning("LLM API Key 未配置，使用默认洞察文本")
            return _default_insight(stats)

        llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            openai_api_key=settings.OPENAI_API_KEY,
            openai_api_base=settings.OPENAI_API_BASE,
            temperature=0.3,
        )
        structured_llm = llm.with_structured_output(_WeeklyInsightOutput)

        response: _WeeklyInsightOutput = await structured_llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])

        logger.info("AI 每周洞察生成成功")
        return response.insight

    except Exception as e:
        logger.error("LLM 调用失败，使用默认洞察文本: %s", e)
        return _default_insight(stats)


def _default_insight(stats: WeeklyInsightStats) -> str:
    """当 LLM 不可用时，生成默认的鼓励性文本"""
    if stats.active_days == 0:
        return "本周暂时还没有学习记录。新的一周，不妨给自己定一个小目标：每天学习 15 分钟。千里之行，始于足下！"

    parts = [f"本周你保持了 {stats.active_days} 天的学习习惯"]

    if stats.tasks_completed > 0:
        parts.append(f"完成了 {stats.tasks_completed} 个学习任务")

    if stats.cards_reviewed > 0:
        parts.append(f"复习了 {stats.cards_reviewed} 张卡片")

    if stats.total_study_minutes > 0:
        parts.append(f"累计学习了 {stats.total_study_minutes // 60} 小时 {stats.total_study_minutes % 60} 分钟")

    insight = "，".join(parts) + "。"

    if stats.active_days < 3:
        insight += " 学习贵在坚持，尝试每天固定一个时间段学习，哪怕只有 15 分钟，也能让习惯更加稳固。"
    elif stats.active_days >= 6:
        insight += " 太棒了！你的学习习惯非常稳固，继续保持这个节奏！"
    else:
        insight += " 继续加油，争取本周达到全勤！"

    return insight
