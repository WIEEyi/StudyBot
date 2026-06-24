"""
Quiz 测验题 Schema

定义测验题的请求/响应数据结构。
- QuizCreate: 创建测验（手动）
- QuizUpdate: 更新测验
- QuizResponse: 单个测验响应
- QuizGenerateRequest: AI 生成请求
- QuizSubmission: 答题提交
- QuizScoreResponse: 评分结果
"""

from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field, model_validator


# ============================================================
# 创建 & 更新
# ============================================================

class QuizCreate(BaseModel):
    """创建测验题 — 手动创建"""

    question: str = Field(min_length=1, description="题目内容")
    options: list[str] = Field(min_length=2, description="选项列表（至少 2 个选项）")
    correct_answer: int = Field(ge=0, description="正确答案在 options 中的索引（0-based）")
    explanation: Optional[str] = Field(None, description="答案解析")
    document_id: Optional[int] = Field(None, description="关联的文档 ID")
    source: Literal["manual", "ai_generated"] = Field("manual", description="题目来源")

    @model_validator(mode="after")
    def validate_correct_answer_index(self):
        """验证 correct_answer 在 options 索引范围内"""
        if self.correct_answer >= len(self.options):
            raise ValueError(
                f"correct_answer ({self.correct_answer}) 必须小于 options 数量 ({len(self.options)})"
            )
        return self


class QuizUpdate(BaseModel):
    """更新测验题 — 所有字段可选"""

    question: Optional[str] = Field(None, min_length=1)
    options: Optional[list[str]] = Field(None, min_length=2)
    correct_answer: Optional[int] = Field(None, ge=0)
    explanation: Optional[str] = None
    document_id: Optional[int] = None


# ============================================================
# 响应
# ============================================================

class QuizResponse(BaseModel):
    """测验题响应"""

    id: int
    user_id: int
    document_id: Optional[int] = None
    question: str
    options: list[str]
    correct_answer: int  # 路由层将 ORM 存储的 str 转为 int
    explanation: Optional[str] = None
    source: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class QuizListResponse(BaseModel):
    """测验题分页列表"""

    items: list[QuizResponse]
    total: int = Field(description="总记录数")
    offset: int = Field(description="当前偏移量")
    limit: int = Field(description="每页条数")


# ============================================================
# AI 生成
# ============================================================

class QuizGenerateRequest(BaseModel):
    """AI 自动出题请求"""

    document_id: int = Field(description="基于哪个文档生成题目")
    count: int = Field(3, ge=1, le=10, description="生成题目数量（1-10）")


class QuizGenerateResponse(BaseModel):
    """AI 生成题目响应"""

    quizzes: list[QuizResponse]
    document_id: int
    count: int


# ============================================================
# 答题 & 评分
# ============================================================

class QuizSubmission(BaseModel):
    """单题提交"""

    quiz_id: int = Field(description="测验题 ID")
    selected_index: int = Field(ge=0, description="用户选择的选项索引")


class QuizResultResponse(BaseModel):
    """单题评分结果"""

    quiz_id: int
    question: str
    selected_index: int
    correct_index: int
    is_correct: bool
    explanation: Optional[str] = None


class QuizScoreResponse(BaseModel):
    """整批评分结果"""

    results: list[QuizResultResponse]
    total: int = Field(description="提交总题数")
    graded: int = Field(default=0, description="实际批改的题数（排除跳过的）")
    skipped: int = Field(default=0, description="跳过的题数（不存在或无权限）")
    correct_count: int = Field(description="答对数")
    score_percent: float = Field(description="得分百分比（基于已批改题数）")
