"""
知识图谱可视化 — Pydantic 响应模型

将概念（节点）和关系（边）转换为前端可视化组件（如 D3.js / Cytoscape.js）可直接使用的格式。
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    """图谱节点 — 对应一个概念

    前端可视化中每个节点代表一个学习概念。
    """
    id: int = Field(description="概念 ID")
    name: str = Field(description="概念名称")
    category: str = Field(description="概念分类: subject/topic/subtopic/term/other")
    description: Optional[str] = Field(None, description="概念描述（悬浮提示用）")
    relation_count: int = Field(0, description="关联关系数（决定节点大小/颜色）")


class GraphEdge(BaseModel):
    """图谱边 — 对应一个概念关系

    有向边，从 source_id 指向 target_id。
    """
    id: int = Field(description="关系 ID")
    source_id: int = Field(description="源概念 ID（起点）")
    target_id: int = Field(description="目标概念 ID（终点）")
    relation_type: str = Field(description="关系类型: prerequisite/related/part_of")
    source_name: Optional[str] = Field(None, description="源概念名称")
    target_name: Optional[str] = Field(None, description="目标概念名称")


class GraphResponse(BaseModel):
    """知识图谱完整数据 — 包含所有节点和边

    前端拿到 nodes + edges 后可直接渲染为力导向图或树图。
    """
    nodes: List[GraphNode] = Field(description="所有概念节点")
    edges: List[GraphEdge] = Field(description="所有关系边")
    total_nodes: int = Field(description="节点总数")
    total_edges: int = Field(description="边总数")


class GraphStatsResponse(BaseModel):
    """图谱统计信息"""
    total_concepts: int = Field(description="概念总数")
    total_relations: int = Field(description="关系总数")
    by_category: dict = Field(description="按分类统计的概念数量")
    by_relation_type: dict = Field(description="按关系类型统计的关系数量")
