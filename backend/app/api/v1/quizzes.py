"""
测验题管理路由

提供的接口:
- POST   /quizzes/generate  — AI 基于文档生成题目 (QuizAgent)
- GET    /quizzes           — 分页列表（支持 document_id/source 过滤）
- GET    /quizzes/{id}      — 题目详情
- DELETE /quizzes/{id}      — 删除题目

Step 13: 自动出题 (QuizAgent)
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.quiz import Quiz
from app.schemas.quiz import (
    QuizGenerateRequest, QuizResponse, QuizListResponse,
)
from app.agents.quiz_agent import run_quiz_agent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/quizzes", tags=["测验题"])


# ===================== 辅助函数 =====================

async def _get_user_quiz(quiz_id: int, user: User, db: AsyncSession) -> Quiz:
    result = await db.execute(select(Quiz).where(Quiz.id == quiz_id))
    quiz = result.scalar_one_or_none()
    if quiz is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=f"题目不存在: id={quiz_id}")
    if quiz.user_id != user.id:
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="无权操作此题目")
    return quiz


# ===================== API =====================

@router.post("/generate", status_code=201)
async def generate_quizzes(
    request: QuizGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AI 生成测验题 — QuizAgent 核心端点

    1. 校验文档归属权
    2. 调用 QuizAgent (LangGraph) 加载文档内容 + LLM 生成题目 + 保存
    3. 返回生成的题目列表
    """
    try:
        state = await run_quiz_agent(
            document_id=request.document_id,
            user_id=current_user.id,
            db_session=db,
            num_questions=request.num_questions,
        )
    except Exception as e:
        logger.error("QuizAgent 执行失败: %s", str(e))
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"出题服务暂不可用: {str(e)}",
        )

    if state.get("error"):
        error_msg = state["error"]
        if "不存在" in error_msg:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=error_msg)
        elif "无权" in error_msg:
            raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail=error_msg)
        elif "为空" in error_msg:
            raise HTTPException(status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error_msg)
        else:
            raise HTTPException(status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg)

    quizzes = state["quiz_objects"]
    return {
        "document_id": request.document_id,
        "quizzes": [QuizResponse.model_validate(q) for q in quizzes],
        "total": len(quizzes),
    }


@router.get("", response_model=QuizListResponse)
async def list_quizzes(
    document_id: int = Query(None, description="按文档过滤"),
    source: str = Query(None, description="按来源过滤: manual, ai_generated"),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取测验题列表（分页）"""
    conditions = [Quiz.user_id == current_user.id]
    if document_id is not None:
        conditions.append(Quiz.document_id == document_id)
    if source is not None:
        if source not in ("manual", "ai_generated"):
            raise HTTPException(status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
                              detail=f"无效来源: {source}，支持: manual, ai_generated")
        conditions.append(Quiz.source == source)

    total_result = await db.execute(select(func.count(Quiz.id)).where(*conditions))
    total = total_result.scalar()

    result = await db.execute(
        select(Quiz).where(*conditions).order_by(Quiz.created_at.desc()).offset(offset).limit(limit)
    )
    quizzes = result.scalars().all()

    return QuizListResponse(
        items=[QuizResponse.model_validate(q) for q in quizzes],
        total=total, offset=offset, limit=limit,
    )


@router.get("/{quiz_id}", response_model=QuizResponse)
async def get_quiz(quiz_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """获取题目详情"""
    return await _get_user_quiz(quiz_id, current_user, db)


@router.delete("/{quiz_id}", status_code=204)
async def delete_quiz(quiz_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """删除题目"""
    quiz = await _get_user_quiz(quiz_id, current_user, db)
    await db.delete(quiz)
    await db.commit()
    logger.info("题目删除: id=%d", quiz_id)
