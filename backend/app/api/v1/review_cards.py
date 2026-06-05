"""
间隔复习卡片 CRUD 路由

提供的接口:
- POST   /review-cards           — 创建复习卡片
- GET    /review-cards           — 分页列表（支持 overdue/today 过滤）
- GET    /review-cards/{id}      — 卡片详情
- PUT    /review-cards/{id}      — 更新卡片内容
- DELETE /review-cards/{id}      — 删除卡片
- POST   /review-cards/{id}/review — 提交复习评分（SM-2 算法核心端点）

Step 12: 间隔复习 (SM-2 算法)
"""

import logging
from datetime import datetime, timezone
from fastapi import (
    APIRouter, Depends, HTTPException, Query, status as http_status,
)
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.review_card import ReviewCard
from app.schemas.review_card import (
    ReviewCardCreate,
    ReviewCardUpdate,
    ReviewCardResponse,
    ReviewCardListResponse,
    ReviewSubmission,
    ReviewResponse,
)
from app.services.sm2_service import calculate_sm2, is_card_due

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/review-cards", tags=["间隔复习"])


# ===================== 辅助函数 =====================

async def _get_user_card(
    card_id: int, user: User, db: AsyncSession
) -> ReviewCard:
    """查找复习卡片并校验归属权"""
    result = await db.execute(
        select(ReviewCard).where(ReviewCard.id == card_id)
    )
    card = result.scalar_one_or_none()
    if card is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"卡片不存在: id={card_id}",
        )
    if card.user_id != user.id:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="无权操作此卡片",
        )
    return card


# ===================== CRUD 端点 =====================

@router.post("", response_model=ReviewCardResponse, status_code=201)
async def create_review_card(
    request: ReviewCardCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建一张新的复习卡片

    初始化 SM-2 参数: ease_factor=2.5, interval=0, repetitions=0
    """
    card = ReviewCard(
        user_id=current_user.id,
        front=request.front,
        back=request.back,
        document_id=request.document_id,
        source="manual",
        ease_factor=2.5,
        interval=0,
        repetitions=0,
    )
    db.add(card)
    await db.commit()
    await db.refresh(card)

    logger.info("复习卡片创建成功: id=%d, front='%s'", card.id, card.front[:30])
    return card


@router.get("", response_model=ReviewCardListResponse)
async def list_review_cards(
    due_filter: str = Query(
        None, alias="due_filter",
        description="到期过滤: overdue(已过期), today(今天到期), all",
    ),
    source: str = Query(None, description="来源过滤: manual, ai_generated"),
    offset: int = Query(0, ge=0, description="分页偏移量"),
    limit: int = Query(20, ge=1, le=100, description="每页条数（最大 100）"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户的复习卡片列表（分页）

    支持按到期状态过滤:
    - overdue: 已过期的卡片（next_review_at <= now，包括从未复习的）
    - today: 今天到期的卡片
    - all 或不传: 所有卡片
    """
    conditions = [ReviewCard.user_id == current_user.id]

    # 来源过滤
    if source is not None:
        if source not in ("manual", "ai_generated"):
            raise HTTPException(
                status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"无效的来源类型: {source}，支持: manual, ai_generated",
            )
        conditions.append(ReviewCard.source == source)

    # 到期过滤校验
    valid_due_filters = (None, "overdue", "today", "all")
    if due_filter not in valid_due_filters:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"无效的 due_filter: {due_filter}，支持: overdue, today, all",
        )

    now = datetime.now(timezone.utc)
    if due_filter == "overdue":
        # 已过期: next_review_at 为空（从未复习）或 next_review_at <= now
        conditions.append(
            (ReviewCard.next_review_at.is_(None)) |
            (ReviewCard.next_review_at <= now)
        )
    elif due_filter == "today":
        # 今天到期: next_review_at 在今天范围内
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start.replace(hour=23, minute=59, second=59, microsecond=999999)
        conditions.append(ReviewCard.next_review_at.between(today_start, today_end))

    # 查总数和分页数据
    total_result = await db.execute(
        select(func.count(ReviewCard.id)).where(*conditions)
    )
    total = total_result.scalar()

    result = await db.execute(
        select(ReviewCard)
        .where(*conditions)
        .order_by(ReviewCard.next_review_at.asc().nullsfirst(), ReviewCard.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    cards = result.scalars().all()

    return ReviewCardListResponse(
        items=[ReviewCardResponse.model_validate(c) for c in cards],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/{card_id}", response_model=ReviewCardResponse)
async def get_review_card(
    card_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取单张复习卡片的详情"""
    card = await _get_user_card(card_id, current_user, db)
    return card


@router.put("/{card_id}", response_model=ReviewCardResponse)
async def update_review_card(
    card_id: int,
    request: ReviewCardUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新复习卡片的内容（不影响 SM-2 参数）"""
    card = await _get_user_card(card_id, current_user, db)

    # 部分更新：只修改用户传了的字段
    if request.front is not None:
        card.front = request.front
    if request.back is not None:
        card.back = request.back
    if request.document_id is not None:
        card.document_id = request.document_id

    await db.commit()
    await db.refresh(card)

    logger.info("复习卡片更新: id=%d", card_id)
    return card


@router.delete("/{card_id}", status_code=204)
async def delete_review_card(
    card_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除复习卡片"""
    card = await _get_user_card(card_id, current_user, db)
    await db.delete(card)
    await db.commit()
    logger.info("复习卡片删除: id=%d", card_id)


# ===================== SM-2 复习评分端点 =====================

@router.post("/{card_id}/review", response_model=ReviewResponse)
async def review_card(
    card_id: int,
    submission: ReviewSubmission,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """提交复习评分 — SM-2 算法核心端点

    1. 校验卡片归属权
    2. 调用 SM-2 算法计算新的 ease_factor、interval、repetitions
    3. 更新卡片并返回新的 SM-2 参数
    """
    card = await _get_user_card(card_id, current_user, db)

    # 调用 SM-2 算法
    try:
        sm2_result = calculate_sm2(
            rating=submission.rating,
            current_interval=card.interval,
            current_repetitions=card.repetitions,
            current_ease_factor=card.ease_factor,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    # 更新卡片的 SM-2 参数
    card.ease_factor = sm2_result["ease_factor"]
    card.interval = sm2_result["interval"]
    card.repetitions = sm2_result["repetitions"]
    card.next_review_at = sm2_result["next_review_at"]
    card.last_reviewed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(card)

    logger.info(
        "复习评分完成: card_id=%d, rating=%d, interval: %d→%d d, EF=%.2f",
        card_id, submission.rating,
        sm2_result["previous_interval"], sm2_result["interval"],
        sm2_result["ease_factor"],
    )

    return ReviewResponse(
        id=card.id,
        rating=submission.rating,
        previous_interval=sm2_result["previous_interval"],
        new_interval=sm2_result["interval"],
        ease_factor=sm2_result["ease_factor"],
        repetitions=sm2_result["repetitions"],
        next_review_at=sm2_result["next_review_at"],
    )
