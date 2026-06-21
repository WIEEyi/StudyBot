"""
知识图谱 CRUD 路由

提供的接口:
- GET    /concepts                       — 概念分页列表（支持 category 过滤）
- GET    /concepts/{id}                  — 单个概念详情（含关系列表）
- POST   /concepts                       — 创建概念
- PUT    /concepts/{id}                  — 更新概念
- DELETE /concepts/{id}                  — 删除概念（级联删除关系）
- POST   /concepts/{id}/relations        — 创建概念关系
- DELETE /concepts/{id}/relations/{rel_id} — 删除概念关系
- GET    /graph                          — 获取完整知识图谱数据
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy import select, func
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
    GraphNode,
    GraphEdge,
    GraphResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/concepts", tags=["知识图谱"])

# 关系类型 → 中文标签映射
RELATION_LABELS = {
    "prerequisite": "前置知识",
    "related": "相关",
    "part_of": "包含",
}


# --- 辅助函数：检查概念归属 ---

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


async def _get_user_relation(
    relation_id: int, concept_id: int, user: User, db: AsyncSession
) -> ConceptRelation:
    """查找关系并校验：
    1. 关系是否存在 → 404
    2. 关系是否属于该概念 → 404（作为该概念不存在的变体）
    3. 源概念是否属于当前用户 → 403
    """
    result = await db.execute(
        select(ConceptRelation).where(ConceptRelation.id == relation_id)
    )
    rel = result.scalar_one_or_none()

    if rel is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"关系不存在: id={relation_id}",
        )

    if rel.source_id != concept_id:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"概念 {concept_id} 下不存在关系 {relation_id}",
        )

    # 通过源概念验证用户所有权
    await _get_user_concept(concept_id, user, db)

    return rel


# ===================== 概念 CRUD =====================


@router.get("", response_model=ConceptListResponse)
async def list_concepts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    category: str = Query(None, description="按分类过滤: subject/topic/subtopic/term/other"),
    offset: int = Query(0, ge=0, description="偏移量"),
    limit: int = Query(20, ge=1, le=100, description="每页条数"),
):
    """获取当前用户的概念分页列表
    支持按 category 过滤，按名称字母序排列
    """
    conditions = [Concept.user_id == current_user.id]
    if category is not None:
        conditions.append(Concept.category == category)

    # 查询总数
    count_query = select(func.count()).where(*conditions)
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 查询分页数据（按名称排序，概念列表更适合字母序）
    query = (
        select(Concept)
        .where(*conditions)
        .order_by(Concept.name.asc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    concepts = result.scalars().all()

    items = [ConceptResponse.model_validate(c) for c in concepts]

    return ConceptListResponse(items=items, total=total, offset=offset, limit=limit)


@router.get("/{concept_id}", response_model=ConceptDetailResponse)
async def get_concept(
    concept_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取单个概念详情，含出边和入边关系"""
    result = await db.execute(
        select(Concept)
        .where(Concept.id == concept_id)
        .options(
            selectinload(Concept.outgoing_relations),
            selectinload(Concept.incoming_relations),
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

    resp = ConceptDetailResponse.model_validate(concept)
    resp.outgoing_relations = [
        ConceptRelationResponse.model_validate(r) for r in concept.outgoing_relations
    ]
    resp.incoming_relations = [
        ConceptRelationResponse.model_validate(r) for r in concept.incoming_relations
    ]

    return resp


@router.post("", response_model=ConceptResponse, status_code=http_status.HTTP_201_CREATED)
async def create_concept(
    request: ConceptCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建新的概念节点"""
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
        concept.id,
        concept.name,
        concept.category,
        current_user.id,
    )

    return ConceptResponse.model_validate(concept)


@router.put("/{concept_id}", response_model=ConceptResponse)
async def update_concept(
    concept_id: int,
    request: ConceptUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新概念节点"""
    concept = await _get_user_concept(concept_id, current_user, db)

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

    return ConceptResponse.model_validate(concept)


@router.delete("/{concept_id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def delete_concept(
    concept_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除概念节点
    级联删除：关联的关系边会被自动删除（数据库 ondelete CASCADE）
    """
    concept = await _get_user_concept(concept_id, current_user, db)
    await db.delete(concept)
    await db.commit()

    logger.info("删除概念: id=%s, name=%s", concept_id, concept.name)


# ===================== 关系管理 =====================


@router.post(
    "/{concept_id}/relations",
    response_model=ConceptRelationResponse,
    status_code=http_status.HTTP_201_CREATED,
)
async def create_relation(
    concept_id: int,
    request: ConceptRelationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建概念关系（从 concept_id → target_id）

    校验：
    1. 源概念存在且属于当前用户
    2. 目标概念存在且属于当前用户
    3. 不允许自引用
    4. 不允许重复关系
    """
    # 校验源概念
    source = await _get_user_concept(concept_id, current_user, db)

    # 不允许自引用
    if concept_id == request.target_id:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="不能创建指向自身的关系",
        )

    # 校验目标概念
    target = await _get_user_concept(request.target_id, current_user, db)

    # 检查重复关系（相同 source + target + type）
    dup_result = await db.execute(
        select(ConceptRelation).where(
            ConceptRelation.source_id == concept_id,
            ConceptRelation.target_id == request.target_id,
            ConceptRelation.relation_type == request.relation_type,
        )
    )
    if dup_result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=f"关系已存在: {concept_id} --[{request.relation_type}]--> {request.target_id}",
        )

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
        source.name,
        request.relation_type,
        target.name,
    )

    return ConceptRelationResponse.model_validate(relation)


@router.delete(
    "/{concept_id}/relations/{relation_id}",
    status_code=http_status.HTTP_204_NO_CONTENT,
)
async def delete_relation(
    concept_id: int,
    relation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除概念关系"""
    relation = await _get_user_relation(relation_id, concept_id, current_user, db)
    await db.delete(relation)
    await db.commit()

    logger.info("删除关系: id=%s, %s → %s", relation_id, relation.source_id, relation.target_id)


# ===================== 知识图谱 =====================


@router.get("/graph", response_model=GraphResponse)
async def get_graph(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户的完整知识图谱数据

    返回所有概念节点和所有关系边，用于 vis-network 可视化。
    不包括孤立关系（source 或 target 概念不存在的情况）。
    """
    # 查询所有概念节点
    concept_result = await db.execute(
        select(Concept)
        .where(Concept.user_id == current_user.id)
        .order_by(Concept.name.asc())
    )
    concepts = concept_result.scalars().all()

    # 收集概念 ID 集合
    concept_ids = {c.id for c in concepts}

    # 查询所有相关的关系边（source 和 target 都在用户的概念中）
    # 由于 ConceptRelation 没有 user_id，需要关联查询
    relations_result = await db.execute(
        select(ConceptRelation).where(
            ConceptRelation.source_id.in_(concept_ids),
            ConceptRelation.target_id.in_(concept_ids),
        )
    )
    relations = relations_result.scalars().all()

    # 构建节点列表
    nodes = [
        GraphNode(
            id=c.id,
            name=c.name,
            category=c.category,
        )
        for c in concepts
    ]

    # 构建边列表
    edges = [
        GraphEdge(
            source=r.source_id,
            target=r.target_id,
            relation_type=r.relation_type,
            label=RELATION_LABELS.get(r.relation_type, r.relation_type),
        )
        for r in relations
    ]

    logger.info(
        "获取知识图谱: user_id=%s, nodes=%s, edges=%s",
        current_user.id,
        len(nodes),
        len(edges),
    )

    return GraphResponse(nodes=nodes, edges=edges)
