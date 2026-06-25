"""
学习路径路由

提供的接口:
- POST /learning-path/generate — AI 生成个性化学习路径
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status as http_status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.learning_path import (
    LearningPathResponse,
    LearningPathGenerateRequest,
    LearningPathStep,
)
from app.services.learning_path import generate_learning_path

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/learning-path", tags=["学习路径"])


@router.post("/generate", response_model=LearningPathResponse)
async def generate_path(
    request: LearningPathGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AI 生成个性化学习路径

    基于用户的学习数据（任务、复习卡片、测验、文档等），
    使用 LLM 分析并生成具体的学习步骤。
    """
    try:
        result = await generate_learning_path(
            db=db,
            user_id=current_user.id,
            focus=request.focus,
            document_id=request.document_id,
            max_steps=request.max_steps,
        )

        steps = [
            LearningPathStep(
                step_number=s.step_number,
                title=s.title,
                description=s.description,
                action_type=s.action_type,
                priority=s.priority,
                estimated_minutes=s.estimated_minutes,
            )
            for s in result.steps
        ]

        total_minutes = sum(s.estimated_minutes for s in steps)

        logger.info(
            "生成学习路径: user_id=%s, %d 步骤, 预估 %d 分钟",
            current_user.id, len(steps), total_minutes,
        )

        return LearningPathResponse(
            title=result.title,
            summary=result.summary,
            steps=steps,
            total_estimated_minutes=total_minutes,
            focus_areas=result.focus_areas,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("学习路径生成失败: %s", e, exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="学习路径生成失败，请稍后重试",
        )
