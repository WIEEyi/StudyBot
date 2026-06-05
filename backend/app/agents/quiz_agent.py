"""
QuizAgent - AI 自动出题 Agent

基于 LangGraph 构建的三节点工作流:
1. load_document: 从数据库加载文档内容
2. generate_quizzes: 调用 LLM 基于文档内容生成测验题目
3. save_quizzes: 批量保存题目到数据库

题目类型:
- 选择题 (multiple_choice): 4 个选项 + 正确答案
- 判断题 (true_false): 2 个选项 + 正确答案
- 简答题 (short_answer): 无选项，正确答案
"""

import logging
from typing import Optional, List, Dict, Any
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.document import Document
from app.models.quiz import Quiz

logger = logging.getLogger(__name__)
settings = get_settings()


# ===================== LLM 结构化输出 =====================

class QuizItemOutput(BaseModel):
    """LLM 输出的单道题目"""
    type: str = Field(
        description="题目类型: multiple_choice / true_false / short_answer"
    )
    question: str = Field(description="题目内容")
    options: List[str] = Field(
        default_factory=list,
        description="选项列表（选择题 4 个选项，判断题 2 个选项，简答题为空数组）",
    )
    correct_answer: str = Field(description="正确答案（选择题填正确选项文本，判断题填'对'/'错'，简答题填答案摘要）")
    explanation: str = Field(description="答案解析，说明为什么这个答案是正确的")


class QuizOutput(BaseModel):
    """LLM 输出的一组题目"""
    quizzes: List[QuizItemOutput] = Field(description="生成的题目列表")


# ===================== Agent State =====================

class QuizState(TypedDict):
    """QuizAgent 的状态"""
    document_id: int
    user_id: int
    num_questions: int
    db_session: Any
    document_content: str
    document_title: str
    quizzes: List[Dict[str, Any]]
    quiz_objects: List[Quiz]
    error: Optional[str]


# ===================== 节点实现 =====================

async def load_document(state: QuizState) -> QuizState:
    """节点1: 加载文档 —— 从数据库读取文档内容和标题"""
    db: AsyncSession = state["db_session"]

    result = await db.execute(
        select(Document).where(Document.id == state["document_id"])
    )
    doc = result.scalar_one_or_none()

    if doc is None:
        state["error"] = f"文档不存在: id={state['document_id']}"
        return state

    if doc.user_id != state["user_id"]:
        state["error"] = "无权操作此文档"
        return state

    if not doc.content or not doc.content.strip():
        state["error"] = "文档内容为空，无法生成题目"
        return state

    state["document_content"] = doc.content
    state["document_title"] = doc.title
    logger.info("QuizAgent: 加载文档 '%s', 内容长度=%d", doc.title, len(doc.content))
    return state


async def generate_quizzes(state: QuizState) -> QuizState:
    """节点2: 调用 LLM 生成题目"""
    if state.get("error"):
        return state

    content = state["document_content"]
    # 如果内容太长，取前 12000 字符（约 3000 tokens），足够 LLM 理解并出题
    if len(content) > 12000:
        logger.info("文档内容较长 (%d 字符)，截取前 12000 字符用于出题", len(content))
        content = content[:12000]

    system_prompt = f"""你是一个专业的题目设计专家。请根据提供的文档内容，生成 {state['num_questions']} 道测验题。

要求:
1. 题目类型混合使用: 选择题(multiple_choice)、判断题(true_false)、简答题(short_answer)
2. 选择题必须有 4 个选项，1 个正确答案
3. 判断题必须有 2 个选项（"对"/"错" 或 "正确"/"错误"）
4. 简答题的 correct_answer 填写答案摘要（1-3 句话）
5. 每道题都要有答案解析 (explanation)，解释为什么这个答案是正确的
6. 题目应覆盖文档的核心知识点，避免过于细节或无关的内容
7. 题目之间不要重复，每题考察不同的知识点
8. 题目内容准确，答案必须与原文一致"""

    user_prompt = f"""文档标题: {state['document_title']}

文档内容:
---
{content}
---

请基于上述文档内容，生成 {state['num_questions']} 道测验题。"""

    try:
        llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            openai_api_key=settings.OPENAI_API_KEY,
            openai_api_base=settings.OPENAI_API_BASE,
            temperature=0.7,  # 稍高温度增加题目多样性
        )
        structured_llm = llm.with_structured_output(QuizOutput)
        response: QuizOutput = await structured_llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])

        state["quizzes"] = [q.model_dump() for q in response.quizzes]
        logger.info("QuizAgent: 生成 %d 道题目", len(response.quizzes))

    except Exception as e:
        logger.error("QuizAgent: LLM 调用失败: %s", e)
        state["error"] = f"AI 出题失败: {str(e)}"

    return state


async def save_quizzes(state: QuizState) -> QuizState:
    """节点3: 批量保存题目到数据库"""
    if state.get("error"):
        return state

    db: AsyncSession = state["db_session"]
    quiz_objects = []

    for q in state.get("quizzes", []):
        quiz = Quiz(
            user_id=state["user_id"],
            document_id=state["document_id"],
            question=q["question"],
            options=q.get("options"),
            correct_answer=q["correct_answer"],
            explanation=q.get("explanation"),
            source="ai_generated",
        )
        quiz_objects.append(quiz)

    if quiz_objects:
        db.add_all(quiz_objects)
        await db.commit()
        # refresh 每个对象以获取 id 等数据库生成的字段
        for q in quiz_objects:
            await db.refresh(q)

    state["quiz_objects"] = quiz_objects
    logger.info("QuizAgent: 保存 %d 道题目到数据库", len(quiz_objects))
    return state


# ===================== Graph 构建 =====================

def _should_generate(state: QuizState) -> str:
    if state.get("error"):
        return END
    return "generate_quizzes"


def _should_save(state: QuizState) -> str:
    if state.get("error"):
        return END
    return "save_quizzes"


def build_quiz_graph() -> StateGraph:
    workflow = StateGraph(QuizState)
    workflow.add_node("load_document", load_document)
    workflow.add_node("generate_quizzes", generate_quizzes)
    workflow.add_node("save_quizzes", save_quizzes)

    workflow.set_entry_point("load_document")
    workflow.add_conditional_edges("load_document", _should_generate, {
        "generate_quizzes": "generate_quizzes",
        END: END,
    })
    workflow.add_conditional_edges("generate_quizzes", _should_save, {
        "save_quizzes": "save_quizzes",
        END: END,
    })
    workflow.add_edge("save_quizzes", END)

    return workflow.compile()


# ===================== 公开接口 =====================

async def run_quiz_agent(
    document_id: int,
    user_id: int,
    db_session: AsyncSession,
    num_questions: int = 5,
) -> QuizState:
    """运行 QuizAgent

    Args:
        document_id: 来源文档 ID
        user_id: 当前用户 ID
        db_session: 数据库会话
        num_questions: 生成题目数量（默认 5）

    Returns:
        QuizState — 包含 quiz_objects 列表或 error 信息
    """
    graph = build_quiz_graph()

    initial_state: QuizState = {
        "document_id": document_id,
        "user_id": user_id,
        "num_questions": num_questions,
        "db_session": db_session,
        "document_content": "",
        "document_title": "",
        "quizzes": [],
        "quiz_objects": [],
        "error": None,
    }

    return await graph.ainvoke(initial_state)
