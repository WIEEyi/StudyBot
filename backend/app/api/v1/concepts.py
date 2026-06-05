"""
概念知识图谱 CRUD 路由

提供的接口:
- GET    /concepts                         — 概念分页列表（支持 category 过滤）
- POST   /concepts                         — 创建概念
- GET    /concepts/{id}                    — 概念详情（含关联关系）
- PUT    /concepts/{id}                    — 更新概念
- DELETE /concepts/{id}                    — 删除概念（级联删除关联关系）
- POST   /concepts/{id}/relations          — 创建概念关系
- DELETE /concepts/{id}/relations/{rel_id} — 删除概念关系
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.concept import Concept, CATEGORIES
from app.models.concept_relation import ConceptRelation, RELATION_TYPES
from app.schemas.concept import (
    ConceptCreate,
    ConceptUpdate,
    ConceptResponse,
    ConceptDetailResponse,
    ConceptListResponse,
    ConceptRelationCreate,
    ConceptRelationResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/concepts", tags=["知识图谱"])


# ===================== 辅助函数 =====================

async def _get_user_concept(
    concept_id: int, user: User, db: AsyncSession
) -> Concept:
    """查找概念并校验归属权
    1. 查概念是否存在 → 404
    2. 概念是否属于当前用户 → 403
    """
    result = await db.execute(
        select(Concept).where(Concept.id == concept_id)
    )
    concept = result.scalar_one_or_none()

    if concept is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"概念不存在: id={concept_id}",
        )

    if concept.user_id != user.id:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="无权操作此概念",
        )

    return concept


async def _get_concept_relation_count(concept_id: int, db: AsyncSession) -> int:
    """统计某个概念参与的关系总数（作为源 + 作为目标）"""
    outgoing_result = await db.execute(
        select(func.count()).where(ConceptRelation.source_id == concept_id)
    )
    incoming_result = await db.execute(
        select(func.count()).where(ConceptRelation.target_id == concept_id)
    )
    return outgoing_result.scalar() + incoming_result.scalar()


async def _build_concept_response(
    concept: Concept, db: AsyncSession
) -> ConceptResponse:
    """将 ORM 概念对象转换为响应模型（含 relation_count）"""
    resp = ConceptResponse.model_validate(concept)
    resp.relation_count = await _get_concept_relation_count(concept.id, db)
    return resp


def _build_relation_response(
    relation: ConceptRelation,
    source: Concept = None,
    target: Concept = None,
) -> ConceptRelationResponse:
    """将 ORM 关系对象转换为响应模型（含关联概念名称）"""
    data = {
        "id": relation.id,
        "source_id": relation.source_id,
        "target_id": relation.target_id,
        "relation_type": relation.relation_type,
        "created_at": relation.created_at,
    }
    if source:
        data["source_name"] = source.name
    if target:
        data["target_name"] = target.name
    return ConceptRelationResponse(**data)


# ===================== 概念 CRUD =====================

@router.get("", response_model=ConceptListResponse)
async def list_concepts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    category: str = Query(
        None, description="按分类过滤: subject/topic/subtopic/term/other"
    ),
    search: str = Query(
        None, description="按名称模糊搜索"
    ),
    offset: int = Query(0, ge=0, description="偏移量"),
    limit: int = Query(20, ge=1, le=100, description="每页条数"),
):
    """获取当前用户的概念分页列表
    支持按 category 过滤和按名称模糊搜索
    """
    # 构建查询条件
    conditions = [Concept.user_id == current_user.id]

    if category is not None:
        if category not in CATEGORIES:
            raise HTTPException(
                status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"无效的分类: {category}，可选: {CATEGORIES}",
            )
        conditions.append(Concept.category == category)

    if search is not None:
        # 按名称模糊搜索（ILIKE 不区分大小写）
        conditions.append(Concept.name.ilike(f"%{search}%"))

    # 查询总数
    count_query = select(func.count()).where(*conditions)
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 查询分页数据
    query = (
        select(Concept)
        .where(*conditions)
        .order_by(Concept.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    concepts = result.scalars().all()

    # 转换为响应模型
    items = []
    for c in concepts:
        resp = ConceptResponse.model_validate(c)
        resp.relation_count = await _get_concept_relation_count(c.id, db)
        items.append(resp)

    return ConceptListResponse(items=items, total=total, offset=offset, limit=limit)


@router.post("", response_model=ConceptResponse, status_code=http_status.HTTP_201_CREATED)
async def create_concept(
    request: ConceptCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建新概念"""
    # 校验 category
    if request.category not in CATEGORIES:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"无效的分类: {request.category}，可选: {CATEGORIES}",
        )

    concept = Concept(
        user_id=current_user.id,
        name=request.name,
        description=request.description,
        category=request.category,
    )
    db.add(concept)
    await db.commit()
    await db.refresh(concept)

    logger.info(
        "创建概念: id=%s, name=%s, category=%s, user_id=%s",
        concept.id, concept.name, concept.category, current_user.id,
    )

    resp = ConceptResponse.model_validate(concept)
    resp.relation_count = 0
    return resp


@router.get("/{concept_id}", response_model=ConceptDetailResponse)
async def get_concept(
    concept_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取概念详情，含所有关联关系"""
    # 查找概念，预加载关系
    result = await db.execute(
        select(Concept)
        .where(Concept.id == concept_id)
        .options(
            selectinload(Concept.outgoing_relations).selectinload(ConceptRelation.target),
            selectinload(Concept.incoming_relations).selectinload(ConceptRelation.source),
        )
    )
    concept = result.scalar_one_or_none()

    if concept is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"概念不存在: id={concept_id}",
        )

    if concept.user_id != current_user.id:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="无权操作此概念",
        )

    # 构造响应
    resp = ConceptDetailResponse.model_validate(concept)
    resp.relation_count = len(concept.outgoing_relations) + len(concept.incoming_relations)

    # 填充关系列表（含关联概念名称）
    resp.outgoing_relations = [
        _build_relation_response(r, target=r.target)
        for r in concept.outgoing_relations
    ]
    resp.incoming_relations = [
        _build_relation_response(r, source=r.source)
        for r in concept.incoming_relations
    ]

    return resp


@router.put("/{concept_id}", response_model=ConceptResponse)
async def update_concept(
    concept_id: int,
    request: ConceptUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新概念 — 只更新传入的字段（部分更新）"""
    concept = await _get_user_concept(concept_id, current_user, db)

    # 校验 category（如果传入）
    if request.category is not None and request.category not in CATEGORIES:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"无效的分类: {request.category}，可选: {CATEGORIES}",
        )

    update_data = request.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="没有提供需要更新的字段",
        )

    for field, value in update_data.items():
        setattr(concept, field, value)

    await db.commit()
    await db.refresh(concept)

    logger.info("更新概念: id=%s, fields=%s", concept_id, list(update_data.keys()))

    return await _build_concept_response(concept, db)


@router.delete("/{concept_id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def delete_concept(
    concept_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除概念
    级联删除：所有关联的关系（作为源或目标）都会被自动删除（数据库 CASCADE）
    """
    concept = await _get_user_concept(concept_id, current_user, db)
    await db.delete(concept)
    await db.commit()

    logger.info("删除概念: id=%s, name=%s", concept_id, concept.name)


# ===================== 概念关系管理 =====================

@router.post(
    "/{concept_id}/relations",
    response_model=ConceptRelationResponse,
    status_code=http_status.HTTP_201_CREATED,
)
async def create_concept_relation(
    concept_id: int,
    request: ConceptRelationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建概念关系 — 以当前概念为源，指向目标概念

    业务规则:
    1. 源概念和目标概念必须都存在且属于当前用户
    2. 不能创建指向自身的关系
    3. 关系类型必须有效
    """
    # 校验关系类型
    if request.relation_type not in RELATION_TYPES:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"无效的关系类型: {request.relation_type}，可选: {RELATION_TYPES}",
        )

    # 不能指向自己
    if concept_id == request.target_id:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="不能创建指向自身的关系",
        )

    # 查找源概念
    source = await _get_user_concept(concept_id, current_user, db)

    # 查找目标概念
    target = await _get_user_concept(request.target_id, current_user, db)

    # 检查是否已存在相同关系（避免重复）
    existing = await db.execute(
        select(ConceptRelation).where(
            ConceptRelation.source_id == concept_id,
            ConceptRelation.target_id == request.target_id,
            ConceptRelation.relation_type == request.relation_type,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail="相同类型的关系已存在",
        )

    # 创建关系
    relation = ConceptRelation(
        source_id=concept_id,
        target_id=request.target_id,
        relation_type=request.relation_type,
    )
    db.add(relation)
    await db.commit()
    await db.refresh(relation)

    logger.info(
        "创建关系: %s --[%s]--> %s",
        source.name, request.relation_type, target.name,
    )

    return _build_relation_response(relation, source=source, target=target)


@router.delete(
    "/{concept_id}/relations/{relation_id}",
    status_code=http_status.HTTP_204_NO_CONTENT,
)
async def delete_concept_relation(
    concept_id: int,
    relation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除概念关系

    业务规则:
    1. 关系必须存在且属于当前概念（作为源或目标）
    2. 级联校验：关系涉及的概念必须属于当前用户
    """
    # 先确认概念属于当前用户
    await _get_user_concept(concept_id, current_user, db)

    # 查找关系（该概念是源或目标）
    result = await db.execute(
        select(ConceptRelation).where(
            ConceptRelation.id == relation_id,
            or_(
                ConceptRelation.source_id == concept_id,
                ConceptRelation.target_id == concept_id,
            ),
        )
    )
    relation = result.scalar_one_or_none()

    if relation is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"关系不存在或不属于该概念: relation_id={relation_id}",
        )

    # 校验关系涉及的概念都属于当前用户（防止跨用户操作）
    source_concept = await db.get(Concept, relation.source_id)
    target_concept = await db.get(Concept, relation.target_id)
    if source_concept.user_id != current_user.id or target_concept.user_id != current_user.id:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="无权操作此关系",
        )

    await db.delete(relation)
    await db.commit()

    logger.info("删除关系: id=%s, %s --[%s]--> %s", relation_id, source_concept.name, relation.relation_type, target_concept.name)
