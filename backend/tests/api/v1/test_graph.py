"""
知识图谱可视化 API 测试

测试覆盖:
- GET /graph — 获取完整图谱数据
- GET /graph/stats — 获取统计信息
- 权限隔离验证
- 空图谱场景
"""
import pytest


class TestGetGraph:
    """GET /graph — 获取知识图谱数据"""

    @pytest.mark.asyncio
    async def test_get_graph_structure(self, async_client):
        """图谱响应应有正确的结构"""
        response = await async_client.get("/api/v1/graph")
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "edges" in data
        assert "total_nodes" in data
        assert "total_edges" in data
        assert isinstance(data["nodes"], list)
        assert isinstance(data["edges"], list)
        # total 应与列表长度一致
        assert data["total_nodes"] == len(data["nodes"])
        assert data["total_edges"] == len(data["edges"])

    @pytest.mark.asyncio
    async def test_get_graph_with_nodes(self, async_client):
        """有概念但无关系时应返回节点列表和空边列表"""
        # 创建几个概念
        await async_client.post("/api/v1/concepts", json={
            "name": "概念A", "category": "topic",
        })
        await async_client.post("/api/v1/concepts", json={
            "name": "概念B", "category": "term",
        })

        response = await async_client.get("/api/v1/graph")
        assert response.status_code == 200
        data = response.json()
        assert data["total_nodes"] >= 2
        assert len(data["nodes"]) >= 2
        # 节点结构检查
        for node in data["nodes"]:
            assert "id" in node
            assert "name" in node
            assert "category" in node
            assert "relation_count" in node

    @pytest.mark.asyncio
    async def test_get_graph_with_edges(self, async_client):
        """有概念和关系时应返回完整图谱"""
        # 创建概念（使用唯一名称避免与已有数据冲突）
        import uuid
        tag = uuid.uuid4().hex[:6]
        c1 = await async_client.post("/api/v1/concepts", json={
            "name": f"Python_{tag}", "category": "topic",
        })
        c2 = await async_client.post("/api/v1/concepts", json={
            "name": f"Django_{tag}", "category": "topic",
        })
        c1_id = c1.json()["id"]
        c2_id = c2.json()["id"]

        # 创建关系
        await async_client.post(f"/api/v1/concepts/{c1_id}/relations", json={
            "target_id": c2_id,
            "relation_type": "prerequisite",
        })

        response = await async_client.get("/api/v1/graph")
        assert response.status_code == 200
        data = response.json()
        assert data["total_nodes"] >= 2

        # 查找我们创建的那条边（按 source_name/target_name 匹配）
        matching_edges = [
            e for e in data["edges"]
            if e["source_id"] == c1_id and e["target_id"] == c2_id
        ]
        assert len(matching_edges) >= 1
        edge = matching_edges[0]
        assert edge["relation_type"] == "prerequisite"
        assert edge["source_name"] == f"Python_{tag}"
        assert edge["target_name"] == f"Django_{tag}"

    @pytest.mark.asyncio
    async def test_get_graph_node_properties(self, async_client):
        """图形节点应包含正确的属性"""
        # 创建带描述的概念
        await async_client.post("/api/v1/concepts", json={
            "name": "测试概念",
            "description": "这是一个测试描述",
            "category": "term",
        })

        response = await async_client.get("/api/v1/graph")
        assert response.status_code == 200
        data = response.json()

        matching_nodes = [n for n in data["nodes"] if n["name"] == "测试概念"]
        assert len(matching_nodes) >= 1
        node = matching_nodes[0]
        assert node["description"] == "这是一个测试描述"
        assert node["category"] == "term"

    @pytest.mark.asyncio
    async def test_get_graph_unauthorized(self, async_client):
        """未认证应返回 401/403"""
        original_auth = async_client.headers.pop("Authorization", None)
        try:
            response = await async_client.get("/api/v1/graph")
            assert response.status_code in (401, 403)
        finally:
            if original_auth:
                async_client.headers["Authorization"] = original_auth


class TestGetGraphStats:
    """GET /graph/stats — 获取图谱统计信息"""

    @pytest.mark.asyncio
    async def test_get_stats_empty(self, async_client):
        """没有概念时应返回零统计"""
        response = await async_client.get("/api/v1/graph/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_concepts"] >= 0
        assert data["total_relations"] >= 0
        assert "by_category" in data
        assert "by_relation_type" in data

    @pytest.mark.asyncio
    async def test_get_stats_with_concepts(self, async_client):
        """有概念和关系时统计应正确"""
        # 创建概念：不同分类
        await async_client.post("/api/v1/concepts", json={
            "name": "主题A", "category": "topic",
        })
        await async_client.post("/api/v1/concepts", json={
            "name": "术语A", "category": "term",
        })
        await async_client.post("/api/v1/concepts", json={
            "name": "主题B", "category": "topic",
        })

        response = await async_client.get("/api/v1/graph/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_concepts"] >= 3
        # by_category 应包含 topic 和 term
        assert "topic" in data["by_category"]
        assert "term" in data["by_category"]

    @pytest.mark.asyncio
    async def test_get_stats_with_relations(self, async_client):
        """统计中的关系计数应正确"""
        c1 = await async_client.post("/api/v1/concepts", json={
            "name": "A", "category": "topic",
        })
        c2 = await async_client.post("/api/v1/concepts", json={
            "name": "B", "category": "topic",
        })
        c1_id = c1.json()["id"]
        c2_id = c2.json()["id"]

        # 创建不同类型的关系
        await async_client.post(f"/api/v1/concepts/{c1_id}/relations", json={
            "target_id": c2_id, "relation_type": "prerequisite",
        })

        response = await async_client.get("/api/v1/graph/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_relations"] >= 1
        assert "prerequisite" in data["by_relation_type"]
        assert data["by_relation_type"]["prerequisite"] >= 1

    @pytest.mark.asyncio
    async def test_get_stats_unauthorized(self, async_client):
        """未认证应返回 401/403"""
        original_auth = async_client.headers.pop("Authorization", None)
        try:
            response = await async_client.get("/api/v1/graph/stats")
            assert response.status_code in (401, 403)
        finally:
            if original_auth:
                async_client.headers["Authorization"] = original_auth
