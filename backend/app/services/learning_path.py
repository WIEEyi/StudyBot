"""
Learning Path Service

AI 驱动的个性化学习路径生成服务。

分析用户的学习数据（测验表现、复习卡片状态、知识图谱覆盖度、学习时长趋势），
生成针对性的学习建议和执行步骤。
"""

import logging
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.config import get_settings
from app.models.task import Task
from app.models.quiz import Quiz
from app.models.review_card import ReviewCard
from app.models.document import Document
from app.models.concept import Concept
from app.models.study_session import StudySession

logger = logging.getLogger(__name__)
settings = get_settings()


# --- LLM 结构化输出模型 ---

from pydantic import BaseModel, Field


class LLMPathStep(BaseModel):
    """LLM 生成的学习步骤"""
    step_number: int = Field(description="步骤序号")
    title: str = Field(description="步骤标题")
    description: str = Field(description="详细描述和建议")
    action_type: str = Field(description="行动类型: review / quiz / read / practice")
    priority: str = Field(description="优先级: high / medium / low")
    estimated_minutes: int = Field(default=15, description="预估用时（分钟）")


class LLMLearningPath(BaseModel):
    """LLM 生成的学习路径"""
    title: str = Field(description="路径标题")
    summary: str = Field(description="学习分析总结")
    steps: List[LLMPathStep] = Field(description="学习步骤列表")
    focus_areas: List[str] = Field(description="重点关注领域")


async def _collect_learning_context(db: AsyncSession, user_id: int) -> dict:
    """收集用户学习数据作为 AI 上下文"""
    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)

    # 1. 待完成任务
    pending_tasks_result = await db.execute(
        select(Task.title, Task.priority, Task.due_date)
        .where(Task.user_id == user_id, Task.status.in_(["todo", "in_progress"]))
        .order_by(Task.priority.desc(), Task.due_date)
        .limit(10)
    )
    pending_tasks = [
        {"title": row[0], "priority": row[1], "due_date": str(row[2]) if row[2] else None}
        for row in pending_tasks_result.all()
    ]

    # 2. 到期/过期的复习卡片
    due_cards = (await db.execute(
        select(func.count()).where(
            ReviewCard.user_id == user_id,
            (ReviewCard.next_review_at <= now) | (ReviewCard.next_review_at.is_(None)),
        )
    )).scalar() or 0

    # 3. 最近测验数据
    recent_quizzes = (await db.execute(
        select(func.count()).where(
            Quiz.user_id == user_id,
            Quiz.created_at >= seven_days_ago,
        )
    )).scalar() or 0

    # 4. 文档列表
    docs_result = await db.execute(
        select(Document.id, Document.title, Document.file_type)
        .where(Document.user_id == user_id)
        .order_by(Document.created_at.desc())
        .limit(10)
    )
    documents = [
        {"id": row[0], "title": row[1], "type": row[2]}
        for row in docs_result.all()
    ]

    # 5. 知识概念
    concept_count = (await db.execute(
        select(func.count()).where(Concept.user_id == user_id)
    )).scalar() or 0

    # 6. 近 7 天学习时长
    recent_minutes = (await db.execute(
        select(func.coalesce(func.sum(StudySession.duration_minutes), 0))
        .where(
            StudySession.user_id == user_id,
            StudySession.study_date >= date.today() - timedelta(days=7),
        )
    )).scalar()

    # 7. 总统计
    total_cards = (await db.execute(
        select(func.count()).where(ReviewCard.user_id == user_id)
    )).scalar() or 0

    total_tasks_done = (await db.execute(
        select(func.count()).where(Task.user_id == user_id, Task.status == "done")
    )).scalar() or 0

    return {
        "pending_tasks": pending_tasks,
        "due_review_cards": due_cards,
        "total_review_cards": total_cards,
        "recent_quizzes_7d": recent_quizzes,
        "documents": documents,
        "concept_count": concept_count,
        "recent_study_minutes_7d": recent_minutes,
        "total_tasks_completed": total_tasks_done,
    }


async def generate_learning_path(
    db: AsyncSession,
    user_id: int,
    focus: Optional[str] = None,
    document_id: Optional[int] = None,
    max_steps: int = 8,
) -> LLMLearningPath:
    """生成个性化学习路径

    Args:
        db: 数据库会话
        user_id: 用户 ID
        focus: 学习重点（可选）
        document_id: 基于特定文档（可选）
        max_steps: 最大步骤数

    Returns:
        LLMLearningPath 结构化结果
    """
    import json

    # 收集学习上下文
    ctx = await _collect_learning_context(db, user_id)

    # 如果有特定文档，补充文档内容
    doc_context = ""
    if document_id:
        doc_result = await db.execute(
            select(Document).where(Document.id == document_id, Document.user_id == user_id)
        )
        doc = doc_result.scalar_one_or_none()
        if doc and doc.content:
            doc_context = f"\n\n重点文档: {doc.title}\n内容摘要: {doc.content[:1500]}"

    # 构建 prompt
    system_prompt = """你是一个智能学习助手，负责根据学习数据生成个性化的学习路径。

你需要分析用户的学习状态，包括:
- 待完成的任务和截止日期
- 到期需要复习的卡片数量
- 最近的测验表现
- 已有的学习资源和文档
- 知识图谱覆盖度
- 近期学习时长趋势

然后生成一个具体的、可执行的学习计划，包含:
1. 清晰的步骤标题和描述
2. 每步的具体行动类型 (review/quiz/read/practice)
3. 合理的优先级排序
4. 预估用时

要求:
- 优先处理紧急和高优先级的任务
- 复习到期卡片应排在靠前位置
- 如果近期测验少，建议增加测验环节
- 关注薄弱知识点的强化
- 步骤数量控制在要求范围内
- 使用与用户相同的语言"""

    focus_text = f"\n学习重点: {focus}" if focus else ""
    user_prompt = f"""请根据以下学习数据，生成一个个性化的学习路径。
{focus_text}{doc_context}

当前学习数据:
{json.dumps(ctx, ensure_ascii=False, indent=2)}

请生成不超过 {max_steps} 个学习步骤。"""

    llm = ChatOpenAI(
        model=settings.LLM_MODEL_PREMIUM,
        openai_api_key=settings.LLM_API_KEY,
        openai_api_base=settings.LLM_API_BASE,
        temperature=0.7,
    )
    structured_llm = llm.with_structured_output(LLMLearningPath)

    response: LLMLearningPath = await structured_llm.ainvoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ])

    # 确保步骤数不超过限制
    response.steps = response.steps[:max_steps]

    return response
