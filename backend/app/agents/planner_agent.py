"""
PlannerAgent - AI 学习计划生成 Agent

基于 LangGraph 构建的三节点工作流:
1. analyze_goal: 从数据库加载目标信息
2. generate_plan: 调用 LLM 生成里程碑和任务
3. save_plan: 批量保存任务到数据库

每个节点通过 stream_callback 向 WebSocket 推送进度事件。
"""

import logging
from typing import Optional, Callable, Any, List, Dict
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.learning_goal import LearningGoal
from app.models.task import Task

logger = logging.getLogger(__name__)
settings = get_settings()


# ===================== LLM 结构化输出模型 =====================

class MilestoneOutput(BaseModel):
    """LLM 输出的里程碑结构"""
    title: str = Field(description="里程碑/阶段名称，如「阶段一：Python 基础」")
    order: int = Field(description="里程碑序号，从 1 开始", ge=1)


class TaskOutput(BaseModel):
    """LLM 输出的任务结构"""
    title: str = Field(description="任务标题")
    description: str = Field(description="任务详细描述，说明具体要学什么、做什么")
    milestone: str = Field(description="所属里程碑名称，与 MilestoneOutput.title 对应")
    priority: str = Field(description="优先级: low/medium/high", pattern="^(low|medium|high)$")
    estimated_minutes: int = Field(description="预估耗时（分钟）", ge=5, le=480)


class PlanOutput(BaseModel):
    """LLM 输出的完整计划"""
    milestones: List[MilestoneOutput] = Field(description="里程碑列表，3-5 个")
    tasks: List[TaskOutput] = Field(description="任务列表，每个里程碑下 3-8 个任务")


# ===================== Agent State =====================

class PlannerState(TypedDict):
    """PlannerAgent 的状态

    在 LangGraph 节点之间传递的共享状态字典。
    stream_callback 由 WebSocket 层注入，用于实时推送进度。
    """
    goal_id: int
    user_id: int
    goal_title: str
    goal_description: str
    goal_deadline: Optional[str]
    db_session: Any  # AsyncSession，由 WebSocket 层管理生命周期
    stream_callback: Optional[Callable]  # async def callback(event: str, data: dict)
    messages: List[BaseMessage]
    milestones: List[Dict]
    tasks: List[Dict]
    error: Optional[str]


# ===================== 节点实现 =====================

async def _stream(state: PlannerState, event: str, data: dict):
    """向 WebSocket 推送事件（如果 stream_callback 存在）

    这是一个内部辅助函数，统一处理事件推送逻辑。
    """
    callback = state.get("stream_callback")
    if callback:
        try:
            await callback(event, data)
        except Exception as e:
            logger.warning("stream_callback 调用失败: %s", e)


async def analyze_goal(state: PlannerState) -> PlannerState:
    """节点1: 分析目标 —— 从数据库加载目标信息

    验证目标存在性和用户归属权，填充 goal_title/goal_description。
    """
    goal_id = state["goal_id"]
    user_id = state["user_id"]
    db: AsyncSession = state["db_session"]

    await _stream(state, "thinking", {"event": "thinking", "message": "正在加载学习目标..."})

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

    # 填充目标信息到 state
    state["goal_title"] = goal.title
    state["goal_description"] = goal.description or ""
    state["goal_deadline"] = goal.deadline.isoformat() if goal.deadline else None

    logger.info("分析目标: id=%s, title=%s", goal_id, goal.title)
    await _stream(state, "thinking", {"event": "thinking", "message": f"正在分析学习目标「{goal.title}」..."})

    return state


async def generate_plan(state: PlannerState) -> PlannerState:
    """节点2: 调用 LLM 生成学习计划

    使用 ChatOpenAI + structured output 确保 LLM 返回格式正确的计划数据。
    在生成过程中逐条推送 milestone 和 task 事件。
    """
    if state.get("error"):
        return state

    await _stream(state, "thinking", {"event": "thinking", "message": "AI 正在生成学习计划..."})

    # 系统提示词：定义学习规划师的角色和输出要求
    system_prompt = """你是一个专业的学习路径规划师。用户有一个学习目标，你需要为其设计一个结构化的学习计划。

要求:
1. 将目标拆解为 3-5 个里程碑（阶段），每个里程碑是学习路径上的一个重要节点
2. 每个里程碑下生成 3-8 个具体的学习任务
3. 每个任务需要有清晰的标题和描述（说明学什么、怎么学）
4. 为每个任务分配优先级（high/medium/low）和预估耗时（分钟）
5. 确保里程碑按学习难度从基础到进阶排序
6. 任务之间要有合理的先后依赖关系

注意:
- estimated_minutes 最小 5 分钟，最大 480 分钟（8小时）
- priority 必须是 "low"、"medium" 或 "high" 之一
- 里程碑的 order 从 1 开始递增
- 所有任务的 milestone 字段必须与 milestones 列表中的 title 完全一致"""

    # 用户提示词：包含具体目标信息
    deadline_info = f"，截止日期: {state['goal_deadline']}" if state['goal_deadline'] else "，无截止日期"
    user_prompt = f"""学习目标: {state['goal_title']}
目标描述: {state['goal_description'] or '无'}
{deadline_info}

请为这个学习目标设计一个详细的学习计划。"""

    try:
        # 初始化 LLM，使用 Premium 模型（gpt-4o）获得更好的规划质量
        llm = ChatOpenAI(
            model=settings.LLM_MODEL_PREMIUM,
            openai_api_key=settings.OPENAI_API_KEY,
            openai_api_base=settings.OPENAI_API_BASE,
            temperature=0.7,
        )
        # with_structured_output 要求 LLM 返回符合 PlanOutput 结构的 JSON
        structured_llm = llm.with_structured_output(PlanOutput)

        response: PlanOutput = await structured_llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])

        # 推送里程碑事件
        for m in response.milestones:
            milestone_data = {"title": m.title, "order": m.order}
            state["milestones"].append(milestone_data)
            await _stream(state, "milestone", {"event": "milestone", "data": milestone_data})

        # 推送任务事件
        for t in response.tasks:
            task_data = {
                "title": t.title,
                "description": t.description,
                "milestone": t.milestone,
                "priority": t.priority,
                "estimated_minutes": t.estimated_minutes,
            }
            state["tasks"].append(task_data)
            await _stream(state, "task", {"event": "task", "data": task_data})

        logger.info("LLM 生成计划完成: milestones=%s, tasks=%s",
                     len(response.milestones), len(response.tasks))

    except Exception as e:
        logger.error("LLM 调用失败: %s", e)
        state["error"] = f"AI 生成失败: {str(e)}"
        await _stream(state, "error", {"event": "error", "message": state["error"]})

    return state


async def save_plan(state: PlannerState) -> PlannerState:
    """节点3: 批量保存任务到数据库

    将生成的所有 task 一次性批量 INSERT，减少数据库往返。
    保存完成后推送 complete 事件（含总任务数和总耗时）。
    """
    if state.get("error"):
        return state

    db: AsyncSession = state["db_session"]
    task_objects = []

    for t in state.get("tasks", []):
        task_obj = Task(
            user_id=state["user_id"],
            goal_id=state["goal_id"],
            title=t["title"],
            description=t.get("description"),
            milestone=t.get("milestone"),
            priority=t.get("priority", "medium"),
            estimated_minutes=t.get("estimated_minutes"),
        )
        task_objects.append(task_obj)

    if task_objects:
        db.add_all(task_objects)
        await db.commit()
        logger.info("保存学习计划: goal_id=%s, tasks=%s", state["goal_id"], len(task_objects))

    # 计算总耗时
    total_minutes = sum(t.get("estimated_minutes", 0) for t in state.get("tasks", []))
    await _stream(state, "complete", {
        "event": "complete",
        "data": {
            "total_tasks": len(task_objects),
            "total_minutes": total_minutes,
        }
    })

    return state


# ===================== 条件边函数 =====================

def _should_continue(state: PlannerState) -> str:
    """条件边: 分析完成后决定是继续生成还是结束"""
    if state.get("error"):
        return END
    return "generate_plan"


def _should_save(state: PlannerState) -> str:
    """条件边: 生成完成后决定是保存还是结束"""
    if state.get("error"):
        return END
    return "save_plan"


# ===================== 构建 Graph =====================

def build_planner_graph() -> StateGraph:
    """构建 PlannerAgent 的 LangGraph 工作流

    Graph 结构:
    START → analyze_goal → generate_plan → save_plan → END
                ↓ (error)       ↓ (error)
               END              END
    """
    workflow = StateGraph(PlannerState)

    # 添加节点
    workflow.add_node("analyze_goal", analyze_goal)
    workflow.add_node("generate_plan", generate_plan)
    workflow.add_node("save_plan", save_plan)

    # 设置入口
    workflow.set_entry_point("analyze_goal")

    # 条件边：有错误则直接结束
    workflow.add_conditional_edges("analyze_goal", _should_continue, {
        "generate_plan": "generate_plan",
        END: END,
    })
    workflow.add_conditional_edges("generate_plan", _should_save, {
        "save_plan": "save_plan",
        END: END,
    })
    workflow.add_edge("save_plan", END)

    return workflow.compile()


# ===================== 公开接口 =====================

async def run_planner(
    goal_id: int,
    user_id: int,
    db_session: AsyncSession,
    stream_callback: Optional[Callable] = None,
) -> PlannerState:
    """运行 PlannerAgent

    这是 PlannerAgent 的唯一公开入口。调用方（WebSocket 层）不需要了解
    LangGraph 的内部细节，只需提供必要的参数即可。

    Args:
        goal_id: 目标 ID
        user_id: 当前用户 ID
        db_session: 数据库会话（由调用方管理生命周期，包含 commit/rollback）
        stream_callback: 可选的异步回调，签名: async def callback(event_name: str, data: dict)

    Returns:
        PlannerState — 包含 milestones、tasks 列表或 error 信息

    Example:
        state = await run_planner(
            goal_id=1,
            user_id=1,
            db_session=db,
            stream_callback=websocket.send_json,
        )
        if state["error"]:
            print(f"失败: {state['error']}")
        else:
            print(f"成功: {len(state['tasks'])} 个任务已保存")
    """
    graph = build_planner_graph()

    initial_state: PlannerState = {
        "goal_id": goal_id,
        "user_id": user_id,
        "goal_title": "",
        "goal_description": "",
        "goal_deadline": None,
        "db_session": db_session,
        "stream_callback": stream_callback,
        "messages": [],
        "milestones": [],
        "tasks": [],
        "error": None,
    }

    final_state = await graph.ainvoke(initial_state)
    return final_state
