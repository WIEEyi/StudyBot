"""
SchedulerAgent - AI 动态计划调整 Agent

基于 LangGraph 构建的三节点工作流:
1. analyze_progress: 加载目标 + 所有任务，统计完成进度
2. generate_schedule: 调用 LLM 分析进度并生成调整方案
3. apply_schedule: 将调整方案应用到数据库

支持通过 stream_callback 向 WebSocket 推送进度事件。
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Callable, Any, List, Dict
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.learning_goal import LearningGoal
from app.models.task import Task, PRIORITIES

logger = logging.getLogger(__name__)
settings = get_settings()


# ===================== LLM 结构化输出模型 =====================

class TaskAdjustmentOutput(BaseModel):
    """LLM 输出的单个任务调整方案"""
    task_id: int = Field(description="需要调整的任务 ID")
    suggested_due_date: Optional[str] = Field(
        None, description="建议的新截止日期，ISO 8601 格式 (YYYY-MM-DD)，不调整则为 null"
    )
    suggested_priority: str = Field(
        description="建议的新优先级: low/medium/high", pattern="^(low|medium|high)$"
    )
    reason: str = Field(description="调整理由，简洁说明为什么这样调整")


class ScheduleOutput(BaseModel):
    """LLM 输出的完整调度方案"""
    analysis_summary: str = Field(description="进度分析摘要，概述当前学习状况")
    adjustments: List[TaskAdjustmentOutput] = Field(
        description="需要调整的任务列表，按紧急程度排序"
    )


# ===================== Agent State =====================

class SchedulerState(TypedDict):
    """SchedulerAgent 的状态"""
    goal_id: int
    user_id: int
    goal_title: str
    goal_description: str
    goal_deadline: Optional[str]
    db_session: Any
    stream_callback: Optional[Callable]
    messages: List[BaseMessage]
    # 进度统计
    total_tasks: int
    done_tasks: int
    in_progress_tasks: int
    todo_tasks: int
    overdue_tasks: int
    completion_rate: float
    estimated_remaining_minutes: int
    # 任务数据（用于 LLM 分析）
    tasks_summary: List[Dict]
    # LLM 生成的调整方案
    analysis_summary: str
    adjustments: List[Dict]
    error: Optional[str]


# ===================== 内部辅助函数 =====================

async def _stream(state: SchedulerState, event: str, data: dict):
    """向 WebSocket 推送事件"""
    callback = state.get("stream_callback")
    if callback:
        try:
            await callback(event, data)
        except Exception as e:
            logger.warning("stream_callback 调用失败: %s", e)


def _format_optional_date(dt) -> Optional[str]:
    """将 datetime 对象格式化为 YYYY-MM-DD 字符串"""
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%d")


def _parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """将 YYYY-MM-DD 字符串解析为 timezone-aware datetime"""
    if date_str is None:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


# ===================== 节点实现 =====================

async def analyze_progress(state: SchedulerState) -> SchedulerState:
    """节点1: 分析进度 —— 加载目标信息和任务统计

    从数据库查询目标的所有任务，计算完成率、过期数等关键指标。
    """
    goal_id = state["goal_id"]
    user_id = state["user_id"]
    db: AsyncSession = state["db_session"]

    await _stream(state, "thinking", {"event": "thinking", "message": "正在加载目标和任务数据..."})

    # 查询目标
    result = await db.execute(
        select(LearningGoal).where(LearningGoal.id == goal_id)
    )
    goal = result.scalar_one_or_none()

    if goal is None:
        state["error"] = f"目标不存在: id={goal_id}"
        await _stream(state, "error", {"event": "error", "message": state["error"]})
        return state

    if goal.user_id != user_id:
        state["error"] = "无权操作此目标"
        await _stream(state, "error", {"event": "error", "message": state["error"]})
        return state

    state["goal_title"] = goal.title
    state["goal_description"] = goal.description or ""
    state["goal_deadline"] = _format_optional_date(goal.deadline)

    # 查询所有任务
    result = await db.execute(
        select(Task)
        .where(Task.goal_id == goal_id)
        .order_by(Task.milestone_order, Task.created_at)
    )
    tasks: List[Task] = result.scalars().all()

    # 统计
    now = datetime.now(timezone.utc)
    total = len(tasks)
    done = sum(1 for t in tasks if t.status == "done")
    cancelled = sum(1 for t in tasks if t.status == "cancelled")
    todo = sum(1 for t in tasks if t.status == "todo")
    in_progress = sum(1 for t in tasks if t.status == "in_progress")

    # 过期任务：状态未完成且截止日期已过
    overdue = 0
    for t in tasks:
        if t.status in ("todo", "in_progress") and t.due_date and t.due_date < now:
            overdue += 1

    # 活跃任务（排除 done 和 cancelled）
    active_tasks = total - done - cancelled
    completion_rate = done / max(total, 1)

    # 估算剩余时间（活跃任务中未完成的预估分钟数）
    remaining_minutes = sum(
        t.estimated_minutes or 0 for t in tasks if t.status in ("todo", "in_progress")
    )

    state["total_tasks"] = total
    state["done_tasks"] = done
    state["in_progress_tasks"] = in_progress
    state["todo_tasks"] = todo
    state["overdue_tasks"] = overdue
    state["completion_rate"] = round(completion_rate, 2)
    state["estimated_remaining_minutes"] = remaining_minutes

    # 构建任务摘要（供 LLM 分析使用）
    tasks_summary = []
    for t in tasks:
        if t.status in ("done", "cancelled"):
            continue  # LLM 只需要分析未完成的任务
        tasks_summary.append({
            "id": t.id,
            "title": t.title,
            "description": t.description or "",
            "priority": t.priority,
            "status": t.status,
            "due_date": _format_optional_date(t.due_date),
            "estimated_minutes": t.estimated_minutes or 0,
            "milestone": t.milestone or "",
            "is_overdue": t.due_date is not None and t.due_date < now,
        })
    state["tasks_summary"] = tasks_summary

    logger.info(
        "进度分析: goal_id=%s, total=%s, done=%s, overdue=%s, rate=%s",
        goal_id, total, done, overdue, completion_rate,
    )
    await _stream(state, "progress", {
        "event": "progress",
        "data": {
            "total_tasks": total,
            "done_tasks": done,
            "overdue_tasks": overdue,
            "completion_rate": completion_rate,
            "remaining_minutes": remaining_minutes,
        }
    })

    return state


async def generate_schedule(state: SchedulerState) -> SchedulerState:
    """节点2: 调用 LLM 分析进度并生成调整方案

    LLM 综合考虑: 目标截止日期、完成率、过期任务数、任务优先级、预估耗时
    输出: 分析摘要 + 需要调整的任务列表（新截止日期/新优先级/调整理由）
    """
    if state.get("error"):
        return state

    await _stream(state, "thinking", {"event": "thinking", "message": "AI 正在分析进度并生成调整方案..."})

    deadline_info = f"目标截止日期: {state['goal_deadline']}" if state['goal_deadline'] else "无截止日期"

    # 构建任务列表文本
    tasks_text = ""
    for t in state["tasks_summary"]:
        overdue_mark = " ⚠️已过期" if t["is_overdue"] else ""
        tasks_text += (
            f"- [ID:{t['id']}] {t['title']} | 优先级:{t['priority']} | "
            f"状态:{t['status']} | 截止:{t['due_date'] or '未设置'} | "
            f"预估:{t['estimated_minutes']}分钟 | 里程碑:{t['milestone']}{overdue_mark}\n"
        )

    system_prompt = """你是一个专业的学习进度管理顾问。你需要分析学生的学习进度，并为落后的任务制定调整方案。

你的职责:
1. 分析当前进度状况（完成率、是否有过期任务、与目标截止日期的距离）
2. 为进度落后的任务建议新的截止日期和优先级
3. 每个调整建议必须有理有据

调整原则:
- 只调整状态为 todo 或 in_progress 的任务（不要碰 done/cancelled 的任务）
- 如果目标有截止日期（deadline），所有建议的新截止日期不能超过目标截止日期
- 优先调整过期（overdue）任务，给它们一个新的截止日期
- 如果有多个过期任务，按优先级排列（high > medium > low）
- 高优先级任务的新截止日期应该比低优先级任务更早
- 考虑任务之间的依赖关系（同一里程碑内的任务通常有先后顺序）
- 如果没有问题（进度正常），adjustments 返回空数组
- 日期格式必须是 YYYY-MM-DD（不含时间部分）

注意:
- task_id 必须与输入数据中的 ID 完全一致
- suggested_priority 必须是 "low"、"medium" 或 "high" 之一
- suggested_due_date 为 null 表示不调整截止日期（只调优先级）
- adjustments 按紧迫程度排序（最需要调整的排在最前面）"""

    user_prompt = f"""学习目标: {state['goal_title']}
{deadline_info}
目标描述: {state['goal_description'] or '无'}

当前进度统计:
- 总任务数: {state['total_tasks']}
- 已完成: {state['done_tasks']}
- 进行中: {state['in_progress_tasks']}
- 待开始: {state['todo_tasks']}
- 已过期: {state['overdue_tasks']}
- 完成率: {int(state['completion_rate'] * 100)}%
- 预估剩余时间: {state['estimated_remaining_minutes']} 分钟

未完成任务列表:
{tasks_text}

请分析当前状况并给出调整方案。"""

    try:
        llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            openai_api_key=settings.OPENAI_API_KEY,
            openai_api_base=settings.OPENAI_API_BASE,
            temperature=0.3,  # 低温度，确保输出稳定
        )
        structured_llm = llm.with_structured_output(ScheduleOutput)

        response: ScheduleOutput = await structured_llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])

        state["analysis_summary"] = response.analysis_summary
        state["adjustments"] = [
            {
                "task_id": a.task_id,
                "suggested_due_date": a.suggested_due_date,
                "suggested_priority": a.suggested_priority,
                "reason": a.reason,
            }
            for a in response.adjustments
        ]

        logger.info("LLM 生成调整方案: adjustments=%s", len(response.adjustments))
        await _stream(state, "schedule", {
            "event": "schedule",
            "data": {
                "analysis_summary": response.analysis_summary,
                "adjustments_count": len(response.adjustments),
            }
        })

    except Exception as e:
        logger.error("LLM 调用失败: %s", e)
        state["error"] = f"AI 分析失败: {str(e)}"
        await _stream(state, "error", {"event": "error", "message": state["error"]})

    return state


async def apply_schedule(state: SchedulerState) -> SchedulerState:
    """节点3: 将调整方案应用到数据库

    遍历 adjustments 列表，更新每个任务的新截止日期和优先级。
    """
    if state.get("error"):
        return state

    db: AsyncSession = state["db_session"]
    applied_count = 0

    for adj in state.get("adjustments", []):
        task_id = adj["task_id"]

        # 查询任务
        result = await db.execute(
            select(Task).where(Task.id == task_id, Task.user_id == state["user_id"])
        )
        task = result.scalar_one_or_none()

        if task is None:
            logger.warning("跳过不存在的任务: id=%s", task_id)
            continue

        # 不修改已完成或已取消的任务
        if task.status in ("done", "cancelled"):
            logger.warning("跳过已完成/取消的任务: id=%s, status=%s", task_id, task.status)
            continue

        # 应用调整
        if adj.get("suggested_due_date"):
            parsed_date = _parse_date(adj["suggested_due_date"])
            if parsed_date:
                task.due_date = parsed_date

        if adj.get("suggested_priority") in PRIORITIES:
            task.priority = adj["suggested_priority"]

        applied_count += 1

    if applied_count > 0:
        await db.commit()
        logger.info("应用调整方案: goal_id=%s, applied=%s", state["goal_id"], applied_count)

    await _stream(state, "complete", {
        "event": "complete",
        "data": {
            "analysis_summary": state.get("analysis_summary", ""),
            "adjustments_applied": applied_count,
            "total_adjustments": len(state.get("adjustments", [])),
        }
    })

    return state


# ===================== 条件边函数 =====================

def _should_generate(state: SchedulerState) -> str:
    if state.get("error"):
        return END
    # 如果没有未完成任务，直接结束
    if state.get("total_tasks", 0) == 0:
        state["analysis_summary"] = "该目标下没有任务，无需调整。"
        state["adjustments"] = []
        return END
    return "generate_schedule"


def _should_apply(state: SchedulerState) -> str:
    if state.get("error"):
        return END
    return "apply_schedule"


# ===================== 构建 Graph =====================

def build_scheduler_graph() -> StateGraph:
    """构建 SchedulerAgent 的 LangGraph 工作流

    Graph 结构:
    START → analyze_progress → generate_schedule → apply_schedule → END
                ↓ (error/empty)     ↓ (error)
               END                  END
    """
    workflow = StateGraph(SchedulerState)

    workflow.add_node("analyze_progress", analyze_progress)
    workflow.add_node("generate_schedule", generate_schedule)
    workflow.add_node("apply_schedule", apply_schedule)

    workflow.set_entry_point("analyze_progress")

    workflow.add_conditional_edges("analyze_progress", _should_generate, {
        "generate_schedule": "generate_schedule",
        END: END,
    })
    workflow.add_conditional_edges("generate_schedule", _should_apply, {
        "apply_schedule": "apply_schedule",
        END: END,
    })
    workflow.add_edge("apply_schedule", END)

    return workflow.compile()


# ===================== 公开接口 =====================

async def run_scheduler(
    goal_id: int,
    user_id: int,
    db_session: AsyncSession,
    stream_callback: Optional[Callable] = None,
    apply_changes: bool = True,
) -> SchedulerState:
    """运行 SchedulerAgent

    这是 SchedulerAgent 的唯一公开入口。

    Args:
        goal_id: 目标 ID
        user_id: 当前用户 ID
        db_session: 数据库会话（由调用方管理生命周期）
        stream_callback: 可选的异步回调，签名: async def callback(event_name: str, data: dict)
        apply_changes: 是否将调整方案应用到数据库（False 则仅生成预览）

    Returns:
        SchedulerState — 包含进度统计、分析摘要、调整方案或 error 信息
    """
    graph = build_scheduler_graph()

    initial_state: SchedulerState = {
        "goal_id": goal_id,
        "user_id": user_id,
        "goal_title": "",
        "goal_description": "",
        "goal_deadline": None,
        "db_session": db_session,
        "stream_callback": stream_callback,
        "messages": [],
        "total_tasks": 0,
        "done_tasks": 0,
        "in_progress_tasks": 0,
        "todo_tasks": 0,
        "overdue_tasks": 0,
        "completion_rate": 0.0,
        "estimated_remaining_minutes": 0,
        "tasks_summary": [],
        "analysis_summary": "",
        "adjustments": [],
        "error": None,
    }

    final_state = await graph.ainvoke(initial_state)
    return final_state
