"""
间隔复习卡片 CRUD + SM-2 评分路由

提供的接口:
- GET    /review-cards              — 卡片列表（支持 due_filter: overdue/today/all）
- POST   /review-cards              — 创建卡片
- PUT    /review-cards/{id}         — 更新卡片
- DELETE /review-cards/{id}         — 删除卡片
- POST   /review-cards/{id}/review  — SM-2 评分
"""

import logging
import math
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.review_card import ReviewCard
from app.services.sm2_service import sm2_calculate
from app.schemas.review_card import (
    ReviewCardCreate,
    ReviewCardUpdate,
    ReviewCardResponse,
    ReviewCardListResponse,
    ReviewSubmission,
    ReviewResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/review-cards", tags=["间隔复习"])


# ===================== 辅助函数 =====================

async def _get_user_card(card_id: int, user: User, db: AsyncSession) -> ReviewCard:
    """查找卡片并校验归属权"""
    result = await db.execute(select(ReviewCard).where(ReviewCard.id == card_id))
    card = result.scalar_one_or_none()

    if card is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"复习卡片不存在: id={card_id}",
        )
    if card.user_id != user.id:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="无权操作此卡片",
        )
    return card


# ===================== 接口实现 =====================

@router.get("", response_model=ReviewCardListResponse)
async def list_review_cards(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    due_filter: str = Query("all", description="到期过滤: overdue/today/all"),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """获取复习卡片列表

    due_filter:
    - overdue: 只显示到期需要复习的（next_review_at <= now）
    - today: 今天需要复习的
    - all: 显示全部
    """
    now = datetime.now(timezone.utc)
    conditions = [ReviewCard.user_id == current_user.id]

    if due_filter == "overdue":
        # 到期: next_review_at 已过 或 还没设过（新卡片）
        conditions.append(
            (ReviewCard.next_review_at <= now) | (ReviewCard.next_review_at.is_(None))
        )
    elif due_filter == "today":
        # 今天到期
        today_end = now.replace(hour=23, minute=59, second=59)
        conditions.append(
            (ReviewCard.next_review_at <= today_end) | (ReviewCard.next_review_at.is_(None))
        )

    # 总数
    count_q = select(func.count()).where(*conditions)
    total = (await db.execute(count_q)).scalar()

    # 分页（到期的排前面）
    query = (
        select(ReviewCard)
        .where(*conditions)
        .order_by(ReviewCard.next_review_at.asc().nullsfirst(), ReviewCard.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    cards = result.scalars().all()

    return ReviewCardListResponse(
        items=[ReviewCardResponse.model_validate(c) for c in cards],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.post("", response_model=ReviewCardResponse, status_code=http_status.HTTP_201_CREATED)
async def create_review_card(
    request: ReviewCardCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建复习卡片"""
    # 如果指定了 document_id，校验文档存在且属于当前用户
    if request.document_id is not None:
        from app.models.document import Document
        doc_result = await db.execute(
            select(Document).where(Document.id == request.document_id)
        )
        doc = doc_result.scalar_one_or_none()
        if doc is None or doc.user_id != current_user.id:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="关联文档不存在或无权访问",
            )

    card = ReviewCard(
        user_id=current_user.id,
        front=request.front,
        back=request.back,
        document_id=request.document_id,
    )
    db.add(card)
    await db.commit()
    await db.refresh(card)

    logger.info("创建复习卡片: id=%s, user_id=%s", card.id, current_user.id)
    return ReviewCardResponse.model_validate(card)


@router.put("/{card_id}", response_model=ReviewCardResponse)
async def update_review_card(
    card_id: int,
    request: ReviewCardUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新复习卡片"""
    card = await _get_user_card(card_id, current_user, db)

    update_data = request.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="没有提供需要更新的字段",
        )

    for field, value in update_data.items():
        setattr(card, field, value)

    await db.commit()
    await db.refresh(card)

    logger.info("更新复习卡片: id=%s, fields=%s", card_id, list(update_data.keys()))
    return ReviewCardResponse.model_validate(card)


@router.delete("/{card_id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def delete_review_card(
    card_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除复习卡片"""
    card = await _get_user_card(card_id, current_user, db)
    await db.delete(card)
    await db.commit()
    logger.info("删除复习卡片: id=%s", card_id)


@router.post("/{card_id}/review", response_model=ReviewResponse)
async def review_card(
    card_id: int,
    request: ReviewSubmission,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """提交 SM-2 评分

    评分 0-5:
    - 0: 完全忘记
    - 1: 有印象但回忆不出
    - 2: 勉强回忆
    - 3: 回忆正确但有困难
    - 4: 回忆正确较流畅
    - 5: 完美回忆
    """
    card = await _get_user_card(card_id, current_user, db)

    # 记录旧值
    old_ef = card.ease_factor
    old_interval = card.interval
    old_repetitions = card.repetitions

    # 调用 SM-2 Service
    new_ef, new_interval, new_repetitions, next_review_at = sm2_calculate(
        card.ease_factor, card.interval, card.repetitions, request.rating
    )

    # 更新卡片
    now = datetime.now(timezone.utc)
    card.ease_factor = new_ef
    card.interval = new_interval
    card.repetitions = new_repetitions
    card.last_reviewed_at = now
    card.next_review_at = next_review_at

    await db.commit()
    await db.refresh(card)

    logger.info(
        "SM-2 评分: card_id=%s, rating=%d, interval %d→%d, ef %.2f→%.2f",
        card_id, request.rating, old_interval, new_interval, old_ef, new_ef,
    )

    return ReviewResponse(
        card_id=card.id,
        rating=request.rating,
        old_ease_factor=old_ef,
        new_ease_factor=new_ef,
        old_interval=old_interval,
        new_interval=new_interval,
        old_repetitions=old_repetitions,
        new_repetitions=new_repetitions,
        next_review_at=card.next_review_at,
    )
