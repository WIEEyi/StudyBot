"""
知识图谱可视化 API

提供的接口:
- GET /graph       — 获取当前用户完整图谱数据（节点 + 边）
- GET /graph/stats — 获取图谱统计信息
"""

import logging
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.concept import Concept
from app.models.concept_relation import ConceptRelation
from app.schemas.graph import (
    GraphResponse,
    GraphNode,
    GraphEdge,
    GraphStatsResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/graph", tags=["知识图谱"])


@router.get("", response_model=GraphResponse)
async def get_graph(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户的完整知识图谱数据

    返回所有概念（节点）和关系（边），格式适合前端可视化组件直接使用。
    前端可用 D3.js / Cytoscape.js / vis.js 等渲染为力导向图或树图。

    业务规则:
    1. 仅返回当前用户自己的概念和关系
    2. 节点按概念 ID 自然顺序排列
    3. 每个节点含 category（决定颜色）和 relation_count（决定大小）
    """
    # 查询用户所有概念
    concepts_result = await db.execute(
        select(Concept)
        .where(Concept.user_id == current_user.id)
        .order_by(Concept.id)
    )
    concepts = concepts_result.scalars().all()

    # 收集所有概念 ID
    concept_ids = [c.id for c in concepts]
    concept_map = {c.id: c for c in concepts}

    # 计算每个概念的关系数（通过数据库聚合查询，避免 N+1）
    relation_counts = {}
    if concept_ids:
        # 作为源的关系数
        source_counts = await db.execute(
            select(
                ConceptRelation.source_id,
                func.count(ConceptRelation.id),
            )
            .where(ConceptRelation.source_id.in_(concept_ids))
            .group_by(ConceptRelation.source_id)
        )
        for source_id, count in source_counts.all():
            relation_counts[source_id] = relation_counts.get(source_id, 0) + count

        # 作为目标的关系数
        target_counts = await db.execute(
            select(
                ConceptRelation.target_id,
                func.count(ConceptRelation.id),
            )
            .where(ConceptRelation.target_id.in_(concept_ids))
            .group_by(ConceptRelation.target_id)
        )
        for target_id, count in target_counts.all():
            relation_counts[target_id] = relation_counts.get(target_id, 0) + count

    # 构建节点列表
    nodes = [
        GraphNode(
            id=c.id,
            name=c.name,
            category=c.category,
            description=c.description,
            relation_count=relation_counts.get(c.id, 0),
        )
        for c in concepts
    ]

    # 查询这些概念之间的所有关系
    edges = []
    total_edges = 0
    if concept_ids:
        relations_result = await db.execute(
            select(ConceptRelation)
            .where(
                ConceptRelation.source_id.in_(concept_ids),
                ConceptRelation.target_id.in_(concept_ids),
            )
            .order_by(ConceptRelation.id)
        )
        relations = relations_result.scalars().all()

        # 构建边列表
        edges = [
            GraphEdge(
                id=r.id,
                source_id=r.source_id,
                target_id=r.target_id,
                relation_type=r.relation_type,
                source_name=concept_map[r.source_id].name if r.source_id in concept_map else None,
                target_name=concept_map[r.target_id].name if r.target_id in concept_map else None,
            )
            for r in relations
        ]
        total_edges = len(edges)

    return GraphResponse(
        nodes=nodes,
        edges=edges,
        total_nodes=len(nodes),
        total_edges=total_edges,
    )


@router.get("/stats", response_model=GraphStatsResponse)
async def get_graph_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户的知识图谱统计信息

    返回概念总数、关系总数、按分类统计、按关系类型统计。
    """
    # 按分类统计概念数
    category_stats_result = await db.execute(
        select(
            Concept.category,
            func.count(Concept.id),
        )
        .where(Concept.user_id == current_user.id)
        .group_by(Concept.category)
    )
    by_category = {row[0]: row[1] for row in category_stats_result.all()}

    # 获取用户所有概念 ID
    user_concept_ids_result = await db.execute(
        select(Concept.id).where(Concept.user_id == current_user.id)
    )
    user_concept_ids = [row[0] for row in user_concept_ids_result.all()]

    # 按关系类型统计（仅限于用户自己的概念之间的关系）
    by_relation_type = {}
    total_relations = 0
    if user_concept_ids:
        relation_stats_result = await db.execute(
            select(
                ConceptRelation.relation_type,
                func.count(ConceptRelation.id),
            )
            .where(
                ConceptRelation.source_id.in_(user_concept_ids),
                ConceptRelation.target_id.in_(user_concept_ids),
            )
            .group_by(ConceptRelation.relation_type)
        )
        for rel_type, count in relation_stats_result.all():
            by_relation_type[rel_type] = count
            total_relations += count

    return GraphStatsResponse(
        total_concepts=len(user_concept_ids),
        total_relations=total_relations,
        by_category=by_category,
        by_relation_type=by_relation_type,
    )
