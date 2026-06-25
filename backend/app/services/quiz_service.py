"""
Quiz Service

将 LLM 出题逻辑从路由层抽取，便于复用和测试。
"""

import logging
from typing import List
from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# --- LLM 结构化输出模型 ---

class LLMQuizItem(BaseModel):
    """LLM 生成的单道测验题"""
    question: str = Field(description="题目内容")
    options: List[str] = Field(description="4 个选项", min_length=4, max_length=4)
    correct_answer: int = Field(description="正确选项索引 (0-3)", ge=0, le=3)
    explanation: str = Field(description="答案解析")


class LLMQuizOutput(BaseModel):
    """LLM 输出的完整测验题集"""
    quizzes: List[LLMQuizItem] = Field(description="生成的测验题列表")


async def generate_quizzes_with_llm(
    doc_title: str,
    doc_content: str,
    count: int,
) -> List[LLMQuizItem]:
    """调用 LLM 生成测验题

    Args:
        doc_title: 文档标题
        doc_content: 文档内容（已截取前 3000 字符）
        count: 生成题目数量

    Returns:
        LLMQuizItem 列表

    Raises:
        Exception: LLM 调用失败时抛出
    """
    system_prompt = """你是一个专业的教育内容生成器。你的任务是基于提供的学习材料，生成高质量的选择题测验。

要求:
1. 每道题必须有 4 个选项（A/B/C/D）
2. 只有一个正确答案
3. 题目应该测试对材料核心概念的理解，而非简单的记忆
4. 选项之间应该有合理的区分度，干扰项要有一定迷惑性
5. 每道题必须有清晰的答案解析
6. correct_answer 是正确选项的索引（0=A, 1=B, 2=C, 3=D）
7. 题目之间不要重复或过于相似
8. 使用与原文相同的语言"""

    user_prompt = f"""基于以下学习材料，生成 {count} 道选择题。

文档标题: {doc_title}
文档内容:
---
{doc_content}
---

请生成 {count} 道高质量的选择题。"""

    llm = ChatOpenAI(
        model=settings.LLM_MODEL_PREMIUM,
        openai_api_key=settings.LLM_API_KEY,
        openai_api_base=settings.LLM_API_BASE,
        temperature=0.8,
    )
    structured_llm = llm.with_structured_output(LLMQuizOutput)

    response: LLMQuizOutput = await structured_llm.ainvoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ])

    return response.quizzes[:count]
