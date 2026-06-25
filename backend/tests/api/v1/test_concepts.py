"""
知识图谱 CRUD 单元测试

覆盖:
- 正常路径: 概念 CRUD + 关系 CRUD + 图谱查询
- 异常路径: 401 未认证 / 404 不存在 / 422 参数校验
"""

import pytest


# ===================== 正常路径测试 =====================

class TestCreateConcept:
    """POST /concepts — 创建概念"""

    @pytest.mark.asyncio
    async def test_create_with_all_fields(self, async_client):
        """创建带所有字段的概念"""
        response = await async_client.post("/api/v1/concepts", json={
            "name": "Python 编程",
            "description": "Python 是一门高级编程语言",
            "category": "subject",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Python 编程"
        assert data["description"] == "Python 是一门高级编程语言"
        assert data["category"] == "subject"
        assert "id" in data
        assert "created_at" in data

        await async_client.delete(f"/api/v1/concepts/{data['id']}")

    @pytest.mark.asyncio
    async def test_create_minimal(self, async_client):
        """只传名称"""
        response = await async_client.post("/api/v1/concepts", json={
            "name": "最小概念",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "最小概念"
        assert data["category"] == "topic"  # 默认值
        assert data["description"] is None

        await async_client.delete(f"/api/v1/concepts/{data['id']}")

    @pytest.mark.asyncio
    async def test_create_invalid_category(self, async_client):
        """无效分类 → 422"""
        response = await async_client.post("/api/v1/concepts", json={
            "name": "测试",
            "category": "invalid_category",
        })
        assert response.status_code == 422


class TestListConcepts:
    """GET /concepts — 分页列表"""

    @pytest.mark.asyncio
    async def test_list_empty(self, async_client):
        """空列表"""
        response = await async_client.get("/api/v1/concepts")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "offset" in data
        assert "limit" in data
        assert isinstance(data["items"], list)

    @pytest.mark.asyncio
    async def test_list_with_pagination(self, async_client):
        """分页参数验证"""
        response = await async_client.get("/api/v1/concepts?offset=0&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert data["offset"] == 0
        assert data["limit"] == 5

    @pytest.mark.asyncio
    async def test_list_filter_by_category(self, async_client):
        """按 category 过滤"""
        # 创建不同分类的概念
        r1 = await async_client.post("/api/v1/concepts", json={
            "name": "学科概念", "category": "subject"
        })
        r2 = await async_client.post("/api/v1/concepts", json={
            "name": "术语概念", "category": "term"
        })
        assert r1.status_code == 201
        assert r2.status_code == 201
        id1, id2 = r1.json()["id"], r2.json()["id"]

        # 只查 subject
        response = await async_client.get("/api/v1/concepts?category=subject")
        assert response.status_code == 200
        data = response.json()
        # 所有返回的概念都应该是 subject
        assert all(c["category"] == "subject" for c in data["items"])

        await async_client.delete(f"/api/v1/concepts/{id1}")
        await async_client.delete(f"/api/v1/concepts/{id2}")

    @pytest.mark.asyncio
    async def test_list_with_data(self, async_client):
        """有数据时列表正常"""
        r = await async_client.post("/api/v1/concepts", json={"name": "测试概念"})
        assert r.status_code == 201
        concept_id = r.json()["id"]

        response = await async_client.get("/api/v1/concepts")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

        await async_client.delete(f"/api/v1/concepts/{concept_id}")


class TestGetConcept:
    """GET /concepts/{id} — 详情"""

    @pytest.mark.asyncio
    async def test_get_existing(self, async_client):
        """获取存在的概念"""
        r = await async_client.post("/api/v1/concepts", json={
            "name": "详情概念",
            "description": "描述文本",
            "category": "subtopic",
        })
        assert r.status_code == 201
        concept_id = r.json()["id"]

        response = await async_client.get(f"/api/v1/concepts/{concept_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == concept_id
        assert data["name"] == "详情概念"
        assert data["description"] == "描述文本"
        assert "outgoing_relations" in data
        assert "incoming_relations" in data

        await async_client.delete(f"/api/v1/concepts/{concept_id}")

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, async_client):
        """获取不存在的概念 → 404"""
        response = await async_client.get("/api/v1/concepts/99999")
        assert response.status_code == 404


class TestUpdateConcept:
    """PUT /concepts/{id} — 更新"""

    @pytest.mark.asyncio
    async def test_update_all_fields(self, async_client):
        """更新所有字段"""
        r = await async_client.post("/api/v1/concepts", json={"name": "旧名称"})
        assert r.status_code == 201
        concept_id = r.json()["id"]

        response = await async_client.put(f"/api/v1/concepts/{concept_id}", json={
            "name": "新名称",
            "description": "新描述",
            "category": "term",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "新名称"
        assert data["description"] == "新描述"
        assert data["category"] == "term"

        await async_client.delete(f"/api/v1/concepts/{concept_id}")

    @pytest.mark.asyncio
    async def test_update_nonexistent(self, async_client):
        """更新不存在的概念 → 404"""
        response = await async_client.put("/api/v1/concepts/99999", json={
            "name": "test",
        })
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_empty_body(self, async_client):
        """更新空请求体 → 400"""
        r = await async_client.post("/api/v1/concepts", json={"name": "测试"})
        assert r.status_code == 201
        concept_id = r.json()["id"]

        response = await async_client.put(f"/api/v1/concepts/{concept_id}", json={})
        assert response.status_code == 400

        await async_client.delete(f"/api/v1/concepts/{concept_id}")


class TestDeleteConcept:
    """DELETE /concepts/{id} — 删除"""

    @pytest.mark.asyncio
    async def test_delete_existing(self, async_client):
        """删除存在的概念 → 204"""
        r = await async_client.post("/api/v1/concepts", json={"name": "待删除"})
        assert r.status_code == 201
        concept_id = r.json()["id"]

        response = await async_client.delete(f"/api/v1/concepts/{concept_id}")
        assert response.status_code == 204

        # 确认已删除
        get_r = await async_client.get(f"/api/v1/concepts/{concept_id}")
        assert get_r.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, async_client):
        """删除不存在的概念 → 404"""
        response = await async_client.delete("/api/v1/concepts/99999")
        assert response.status_code == 404


class TestCreateRelation:
    """POST /concepts/{id}/relations — 创建关系"""

    @pytest.mark.asyncio
    async def test_create_relation(self, async_client):
        """创建概念关系"""
        # 创建两个概念
        r1 = await async_client.post("/api/v1/concepts", json={"name": "Python"})
        r2 = await async_client.post("/api/v1/concepts", json={"name": "Django"})
        assert r1.status_code == 201
        assert r2.status_code == 201
        src_id, tgt_id = r1.json()["id"], r2.json()["id"]

        response = await async_client.post(
            f"/api/v1/concepts/{src_id}/relations",
            json={"target_id": tgt_id, "relation_type": "prerequisite"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["source_id"] == src_id
        assert data["target_id"] == tgt_id
        assert data["relation_type"] == "prerequisite"
        assert "id" in data

        # 清理（先删关系，再删概念）
        await async_client.delete(f"/api/v1/concepts/{src_id}/relations/{data['id']}")
        await async_client.delete(f"/api/v1/concepts/{src_id}")
        await async_client.delete(f"/api/v1/concepts/{tgt_id}")

    @pytest.mark.asyncio
    async def test_create_self_relation(self, async_client):
        """自引用关系 → 400"""
        r = await async_client.post("/api/v1/concepts", json={"name": "自引用"})
        assert r.status_code == 201
        concept_id = r.json()["id"]

        response = await async_client.post(
            f"/api/v1/concepts/{concept_id}/relations",
            json={"target_id": concept_id, "relation_type": "related"},
        )
        assert response.status_code == 400

        await async_client.delete(f"/api/v1/concepts/{concept_id}")

    @pytest.mark.asyncio
    async def test_create_duplicate_relation(self, async_client):
        """重复关系 → 409"""
        r1 = await async_client.post("/api/v1/concepts", json={"name": "A"})
        r2 = await async_client.post("/api/v1/concepts", json={"name": "B"})
        assert r1.status_code == 201
        assert r2.status_code == 201
        src_id, tgt_id = r1.json()["id"], r2.json()["id"]

        # 第一次创建成功
        r = await async_client.post(
            f"/api/v1/concepts/{src_id}/relations",
            json={"target_id": tgt_id, "relation_type": "related"},
        )
        assert r.status_code == 201
        rel_id = r.json()["id"]

        # 第二次重复 → 409
        r = await async_client.post(
            f"/api/v1/concepts/{src_id}/relations",
            json={"target_id": tgt_id, "relation_type": "related"},
        )
        assert r.status_code == 409

        await async_client.delete(f"/api/v1/concepts/{src_id}/relations/{rel_id}")
        await async_client.delete(f"/api/v1/concepts/{src_id}")
        await async_client.delete(f"/api/v1/concepts/{tgt_id}")

    @pytest.mark.asyncio
    async def test_create_relation_nonexistent_target(self, async_client):
        """目标概念不存在 → 404"""
        r = await async_client.post("/api/v1/concepts", json={"name": "源概念"})
        assert r.status_code == 201
        src_id = r.json()["id"]

        response = await async_client.post(
            f"/api/v1/concepts/{src_id}/relations",
            json={"target_id": 99999, "relation_type": "related"},
        )
        assert response.status_code == 404

        await async_client.delete(f"/api/v1/concepts/{src_id}")


class TestDeleteRelation:
    """DELETE /concepts/{id}/relations/{rel_id} — 删除关系"""

    @pytest.mark.asyncio
    async def test_delete_relation(self, async_client):
        """删除关系 → 204"""
        r1 = await async_client.post("/api/v1/concepts", json={"name": "源"})
        r2 = await async_client.post("/api/v1/concepts", json={"name": "目标"})
        assert r1.status_code == 201
        assert r2.status_code == 201
        src_id, tgt_id = r1.json()["id"], r2.json()["id"]

        cr = await async_client.post(
            f"/api/v1/concepts/{src_id}/relations",
            json={"target_id": tgt_id, "relation_type": "part_of"},
        )
        assert cr.status_code == 201
        rel_id = cr.json()["id"]

        response = await async_client.delete(
            f"/api/v1/concepts/{src_id}/relations/{rel_id}"
        )
        assert response.status_code == 204

        await async_client.delete(f"/api/v1/concepts/{src_id}")
        await async_client.delete(f"/api/v1/concepts/{tgt_id}")

    @pytest.mark.asyncio
    async def test_delete_nonexistent_relation(self, async_client):
        """删除不存在的关系 → 404"""
        r = await async_client.post("/api/v1/concepts", json={"name": "测试"})
        assert r.status_code == 201
        concept_id = r.json()["id"]

        response = await async_client.delete(
            f"/api/v1/concepts/{concept_id}/relations/99999"
        )
        assert response.status_code == 404

        await async_client.delete(f"/api/v1/concepts/{concept_id}")


class TestGetGraph:
    """GET /graph — 知识图谱数据"""

    @pytest.mark.asyncio
    async def test_get_graph_empty(self, async_client):
        """空图谱"""
        response = await async_client.get("/api/v1/concepts/graph")
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "edges" in data
        assert isinstance(data["nodes"], list)
        assert isinstance(data["edges"], list)

    @pytest.mark.asyncio
    async def test_get_graph_with_data(self, async_client):
        """有节点和边的图谱"""
        # 创建概念
        r1 = await async_client.post("/api/v1/concepts", json={"name": "Node1"})
        r2 = await async_client.post("/api/v1/concepts", json={"name": "Node2"})
        assert r1.status_code == 201
        assert r2.status_code == 201
        c1_id, c2_id = r1.json()["id"], r2.json()["id"]

        # 创建关系
        cr = await async_client.post(
            f"/api/v1/concepts/{c1_id}/relations",
            json={"target_id": c2_id, "relation_type": "related"},
        )
        assert cr.status_code == 201
        rel_id = cr.json()["id"]

        response = await async_client.get("/api/v1/concepts/graph")
        assert response.status_code == 200
        data = response.json()
        assert len(data["nodes"]) >= 2
        assert len(data["edges"]) >= 1

        # 验证节点结构
        node = data["nodes"][0]
        assert "id" in node
        assert "name" in node
        assert "category" in node

        # 验证边结构
        edge = data["edges"][0]
        assert "source" in edge
        assert "target" in edge
        assert "relation_type" in edge
        assert "label" in edge

        await async_client.delete(f"/api/v1/concepts/{c1_id}/relations/{rel_id}")
        await async_client.delete(f"/api/v1/concepts/{c1_id}")
        await async_client.delete(f"/api/v1/concepts/{c2_id}")


# ===================== 异常路径测试 =====================

class TestUnauthorized:
    """401 未认证"""

    @pytest.mark.asyncio
    async def test_list_without_auth(self, async_client):
        """无认证获取列表"""
        headers = dict(async_client.headers)
        del async_client.headers["Authorization"]
        try:
            response = await async_client.get("/api/v1/concepts")
            assert response.status_code in (401, 403)
        finally:
            async_client.headers.update(headers)

    @pytest.mark.asyncio
    async def test_create_without_auth(self, async_client):
        """无认证创建"""
        headers = dict(async_client.headers)
        del async_client.headers["Authorization"]
        try:
            response = await async_client.post("/api/v1/concepts", json={
                "name": "test",
            })
            assert response.status_code in (401, 403)
        finally:
            async_client.headers.update(headers)


class TestValidation:
    """422 参数校验"""

    @pytest.mark.asyncio
    async def test_create_empty_name(self, async_client):
        """空名称 → 422"""
        response = await async_client.post("/api/v1/concepts", json={
            "name": "",
        })
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_name_too_long(self, async_client):
        """名称过长 → 422"""
        response = await async_client.post("/api/v1/concepts", json={
            "name": "A" * 300,
        })
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_relation_invalid_type(self, async_client):
        """无效关系类型 → 422"""
        r1 = await async_client.post("/api/v1/concepts", json={"name": "A"})
        r2 = await async_client.post("/api/v1/concepts", json={"name": "B"})
        assert r1.status_code == 201
        assert r2.status_code == 201
        src_id, tgt_id = r1.json()["id"], r2.json()["id"]

        response = await async_client.post(
            f"/api/v1/concepts/{src_id}/relations",
            json={"target_id": tgt_id, "relation_type": "invalid"},
        )
        assert response.status_code == 422

        await async_client.delete(f"/api/v1/concepts/{src_id}")
        await async_client.delete(f"/api/v1/concepts/{tgt_id}")
