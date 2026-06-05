"""
Quiz 测验题相关的 Pydantic 请求/响应模型

Step 13: 自动出题 (QuizAgent)
"""

from datetime import datetime
from pydantic import BaseModel, Field


class QuizGenerateRequest(BaseModel):
    """AI 生成题目请求"""
    document_id: int = Field(
        ...,
        ge=1,
        description="基于哪个文档的内容生成题目",
    )
    num_questions: int = Field(
        5,
        ge=1,
        le=10,
        description="生成题目数量（1-10）",
    )


class QuizResponse(BaseModel):
    """测验题响应"""
    id: int
    user_id: int
    document_id: int | None = None
    question: str
    options: list[str] | None = None
    correct_answer: str
    explanation: str | None = None
    source: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class QuizListResponse(BaseModel):
    """分页列表"""
    items: list[QuizResponse]
    total: int
    offset: int
    limit: int
