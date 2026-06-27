"""
测验题 CRUD 路由

提供的接口:
- GET    /quizzes                — 分页列表（支持 document_id 过滤）
- GET    /quizzes/{id}           — 单个测验题详情
- POST   /quizzes                — 创建测验题
- PUT    /quizzes/{id}           — 更新测验题
- DELETE /quizzes/{id}           — 删除测验题
- POST   /quizzes/generate       — AI 自动出题（DeepSeek V4 Pro）
- POST   /quizzes/grade          — 批改答题
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.quiz import Quiz
from app.models.document import Document
from app.services.quiz_service import generate_quizzes_with_llm, LLMQuizItem
from app.schemas.quiz import (
    QuizCreate,
    QuizUpdate,
    QuizResponse,
    QuizListResponse,
    QuizGenerateRequest,
    QuizGenerateResponse,
    QuizSubmission,
    QuizResultResponse,
    QuizScoreResponse,
)

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/quizzes", tags=["测验"])


# --- 辅助函数：检查测验归属 ---

async def _get_user_quiz(
    quiz_id: int, user: User, db: AsyncSession
) -> Quiz:
    """查找测验题并校验归属权
    1. 查测验题是否存在 → 404
    2. 测验题是否属于当前用户 → 403
    """
    result = await db.execute(
        select(Quiz).where(Quiz.id == quiz_id)
    )
    quiz = result.scalar_one_or_none()

    if quiz is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"测验题不存在: id={quiz_id}",
        )

    if quiz.user_id != user.id:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="无权操作此测验题",
        )

    return quiz


# --- 辅助函数：校验文档归属 ---

async def _verify_document_owner(
    document_id: int, user: User, db: AsyncSession
) -> Document:
    """校验文档存在且属于当前用户"""
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    doc = result.scalar_one_or_none()

    if doc is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"文档不存在: id={document_id}",
        )

    if doc.user_id != user.id:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="无权使用此文档",
        )

    return doc


# --- 辅助函数：将 ORM Quiz 转为响应（correct_answer str → int）---

def _quiz_to_response(quiz: Quiz) -> QuizResponse:
    """ORM Quiz 对象 → QuizResponse 响应
    处理 correct_answer 从数据库的 str 转为响应的 int
    """
    resp = QuizResponse.model_validate(quiz)
    # correct_answer 在数据库中存储为字符串索引
    resp.correct_answer = int(quiz.correct_answer)
    # options 可能是从 JSON 列读取的，确保是 list
    if isinstance(quiz.options, list):
        resp.options = quiz.options
    return resp


# ===================== 接口实现 =====================


@router.get("", response_model=QuizListResponse)
async def list_quizzes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    document_id: int = Query(None, description="按文档 ID 过滤"),
    offset: int = Query(0, ge=0, description="偏移量"),
    limit: int = Query(20, ge=1, le=100, description="每页条数"),
):
    """获取当前用户的测验题分页列表
    支持按 document_id 过滤
    """
    conditions = [Quiz.user_id == current_user.id]
    if document_id is not None:
        conditions.append(Quiz.document_id == document_id)

    # 查询总记录数
    count_query = select(func.count()).where(*conditions)
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 查询分页数据
    query = (
        select(Quiz)
        .where(*conditions)
        .order_by(Quiz.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    quizzes = result.scalars().all()

    items = [_quiz_to_response(q) for q in quizzes]

    return QuizListResponse(items=items, total=total, offset=offset, limit=limit)


@router.get("/{quiz_id}", response_model=QuizResponse)
async def get_quiz(
    quiz_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取单个测验题详情"""
    quiz = await _get_user_quiz(quiz_id, current_user, db)
    return _quiz_to_response(quiz)


@router.post("", response_model=QuizResponse, status_code=http_status.HTTP_201_CREATED)
async def create_quiz(
    request: QuizCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建新的测验题
    如果提供了 document_id，会校验文档归属
    """
    # 校验文档归属
    if request.document_id is not None:
        await _verify_document_owner(request.document_id, current_user, db)

    quiz = Quiz(
        user_id=current_user.id,
        document_id=request.document_id,
        question=request.question,
        options=request.options,  # list → SQLAlchemy 自动转为 JSON
        correct_answer=str(request.correct_answer),  # int → str 存储
        explanation=request.explanation,
        source=request.source,
    )
    db.add(quiz)
    await db.commit()
    await db.refresh(quiz)

    logger.info(
        "创建测验题: id=%s, question=%s..., user_id=%s",
        quiz.id,
        quiz.question[:30],
        current_user.id,
    )

    return _quiz_to_response(quiz)


@router.put("/{quiz_id}", response_model=QuizResponse)
async def update_quiz(
    quiz_id: int,
    request: QuizUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新测验题
    只更新传入的字段
    """
    quiz = await _get_user_quiz(quiz_id, current_user, db)

    update_data = request.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="没有提供需要更新的字段",
        )

    # 校验新文档归属
    new_doc_id = update_data.get("document_id")
    if new_doc_id is not None:
        await _verify_document_owner(new_doc_id, current_user, db)

    # 如果更新了 correct_answer，转为 str 存储
    if "correct_answer" in update_data:
        correct_answer = update_data["correct_answer"]
        # 确定 options：优先用更新的，否则用现有的
        final_options = update_data.get("options", quiz.options or [])
        if correct_answer >= len(final_options):
            raise HTTPException(
                status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"correct_answer ({correct_answer}) 必须小于 options 数量 ({len(final_options)})",
            )
        update_data["correct_answer"] = str(correct_answer)

    for field, value in update_data.items():
        setattr(quiz, field, value)

    await db.commit()
    await db.refresh(quiz)

    logger.info("更新测验题: id=%s, fields=%s", quiz_id, list(update_data.keys()))

    return _quiz_to_response(quiz)


@router.delete("/{quiz_id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def delete_quiz(
    quiz_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除测验题"""
    quiz = await _get_user_quiz(quiz_id, current_user, db)
    await db.delete(quiz)
    await db.commit()

    logger.info("删除测验题: id=%s, question=%s...", quiz_id, quiz.question[:30])


# ===================== AI 生成（DeepSeek V4 Pro） =====================

@router.post("/generate", response_model=QuizGenerateResponse)
async def generate_quizzes(
    request: QuizGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AI 自动出题 — 基于文档内容使用 DeepSeek V4 Pro 生成测验题"""
    doc = await _verify_document_owner(request.document_id, current_user, db)

    content = (doc.content or "")[:3000]
    if not content.strip():
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="文档内容为空，无法生成题目。请先上传有内容的文档。",
        )

    logger.info(
        "AI 出题: 文档 id=%s (%s), 请求 %s 题, user_id=%s",
        request.document_id, doc.title, request.count, current_user.id,
    )

    try:
        # 调用 Quiz Service
        quiz_items = await generate_quizzes_with_llm(
            doc_title=doc.title,
            doc_content=content,
            count=request.count,
        )

        # 保存题目到数据库
        quiz_objects = []
        for item in quiz_items:
            quiz = Quiz(
                user_id=current_user.id,
                document_id=request.document_id,
                question=item.question,
                options=item.options,
                correct_answer=str(item.correct_answer),
                explanation=item.explanation,
                source="ai_generated",
            )
            quiz_objects.append(quiz)

        db.add_all(quiz_objects)
        await db.commit()

        # 刷新获取 ID 和时间戳
        for q in quiz_objects:
            await db.refresh(q)

        logger.info(
            "AI 出题完成: 文档 id=%s, 生成 %s 题",
            request.document_id, len(quiz_objects),
        )

        return QuizGenerateResponse(
            quizzes=[QuizResponse.model_validate(q) for q in quiz_objects],
            document_id=request.document_id,
            count=len(quiz_objects),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("AI 出题失败: %s", e, exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI 出题失败: {str(e)}",
        )


# ===================== 批改答题 =====================

@router.post("/grade", response_model=QuizScoreResponse)
async def grade_quizzes(
    submissions: list[QuizSubmission],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """批改答题提交

    接收一组答题记录，逐题比对正确答案，返回评分结果。
    """
    if not submissions:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="提交列表不能为空",
        )

    results: list[QuizResultResponse] = []
    correct_count = 0
    skipped_ids: list[int] = []

    for sub in submissions:
        try:
            quiz = await _get_user_quiz(sub.quiz_id, current_user, db)
        except HTTPException:
            # 题目不存在或无权限 — 记录跳过
            skipped_ids.append(sub.quiz_id)
            continue

        correct_index = int(quiz.correct_answer)
        is_correct = sub.selected_index == correct_index

        if is_correct:
            correct_count += 1

        results.append(
            QuizResultResponse(
                quiz_id=quiz.id,
                question=quiz.question,
                selected_index=sub.selected_index,
                correct_index=correct_index,
                is_correct=is_correct,
                explanation=quiz.explanation,
            )
        )

    graded_total = len(results)
    total = len(submissions)
    score_percent = round((correct_count / graded_total) * 100, 1) if graded_total > 0 else 0.0

    if skipped_ids:
        logger.warning(
            "批改跳过 %s 题 (不存在或无权限): ids=%s, user_id=%s",
            len(skipped_ids), skipped_ids, current_user.id,
        )

    logger.info(
        "批改完成: %s/%s 正确 (%.1f%%), 跳过 %s 题, user_id=%s",
        correct_count,
        graded_total,
        score_percent,
        len(skipped_ids),
        current_user.id,
    )

    return QuizScoreResponse(
        results=results,
        total=total,
        graded=graded_total,
        skipped=len(skipped_ids),
        correct_count=correct_count,
        score_percent=score_percent,
    )
