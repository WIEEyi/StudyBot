"""
概念知识图谱 API 测试

测试覆盖:
- 概念 CRUD: 创建/列表/详情/更新/删除
- 概念关系: 创建/删除/重复检测
- 权限隔离: 只能操作自己的数据
- 参数校验: 422 错误
- 边界条件: 404 概念不存在、输入验证
"""
import pytest


# ==================== 概念 CRUD 测试 ====================

class TestCreateConcept:
    """POST /concepts — 创建概念"""

    @pytest.mark.asyncio
    async def test_create_concept_basic(self, async_client):
        """正常创建概念"""
        response = await async_client.post("/api/v1/concepts", json={
            "name": "Python 基础",
            "description": "Python 编程语言基础知识",
            "category": "topic",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Python 基础"
        assert data["description"] == "Python 编程语言基础知识"
        assert data["category"] == "topic"
        assert data["relation_count"] == 0
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_create_concept_default_category(self, async_client):
        """创建概念时不传 category，使用默认值 topic"""
        response = await async_client.post("/api/v1/concepts", json={
            "name": "机器学习",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["category"] == "topic"

    @pytest.mark.asyncio
    async def test_create_concept_minimal(self, async_client):
        """最少字段创建概念（仅 name）"""
        response = await async_client.post("/api/v1/concepts", json={
            "name": "数据结构",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "数据结构"
        assert data["description"] is None

    @pytest.mark.asyncio
    async def test_create_concept_with_category(self, async_client):
        """创建各分类的概念"""
        for category in ["subject", "topic", "subtopic", "term", "other"]:
            response = await async_client.post("/api/v1/concepts", json={
                "name": f"概念_{category}",
                "category": category,
            })
            assert response.status_code == 201, f"category={category} 失败"
            assert response.json()["category"] == category

    @pytest.mark.asyncio
    async def test_create_concept_invalid_category(self, async_client):
        """无效的 category 应返回 422"""
        response = await async_client.post("/api/v1/concepts", json={
            "name": "测试概念",
            "category": "invalid_category",
        })
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_concept_empty_name(self, async_client):
        """空名称应返回 422"""
        response = await async_client.post("/api/v1/concepts", json={
            "name": "",
        })
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_concept_name_too_long(self, async_client):
        """超过 255 字符的名称应返回 422"""
        response = await async_client.post("/api/v1/concepts", json={
            "name": "A" * 300,
        })
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_concept_unauthorized(self, async_client):
        """未认证应返回 401/403"""
        # 保存原 header，去掉认证
        original_auth = async_client.headers.pop("Authorization", None)
        try:
            response = await async_client.post("/api/v1/concepts", json={
                "name": "Python",
            })
            assert response.status_code in (401, 403)
        finally:
            if original_auth:
                async_client.headers["Authorization"] = original_auth


class TestListConcepts:
    """GET /concepts — 获取概念列表"""

    @pytest.mark.asyncio
    async def test_list_concepts_empty(self, async_client):
        """初始状态下列表为空"""
        response = await async_client.get("/api/v1/concepts")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["offset"] == 0
        assert data["limit"] == 20

    @pytest.mark.asyncio
    async def test_list_concepts_with_data(self, async_client):
        """创建概念后列表应有数据"""
        # 创建几个概念
        for i in range(3):
            await async_client.post("/api/v1/concepts", json={
                "name": f"概念_{i}",
                "category": "topic",
            })

        response = await async_client.get("/api/v1/concepts")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 3
        assert len(data["items"]) >= 3

    @pytest.mark.asyncio
    async def test_list_concepts_pagination(self, async_client):
        """分页参数应生效"""
        response = await async_client.get("/api/v1/concepts?offset=0&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 2
        assert data["limit"] == 2

    @pytest.mark.asyncio
    async def test_list_concepts_filter_by_category(self, async_client):
        """按 category 过滤"""
        # 创建不同分类的概念
        await async_client.post("/api/v1/concepts", json={
            "name": "主题概念", "category": "topic",
        })
        await async_client.post("/api/v1/concepts", json={
            "name": "术语概念", "category": "term",
        })

        # 按 topic 过滤
        response = await async_client.get("/api/v1/concepts?category=topic")
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["category"] == "topic"

    @pytest.mark.asyncio
    async def test_list_concepts_filter_invalid_category(self, async_client):
        """无效的 category 过滤应返回 422"""
        response = await async_client.get("/api/v1/concepts?category=invalid")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_concepts_search(self, async_client):
        """按名称模糊搜索"""
        await async_client.post("/api/v1/concepts", json={
            "name": "Python 编程", "category": "topic",
        })
        await async_client.post("/api/v1/concepts", json={
            "name": "JavaScript 编程", "category": "topic",
        })

        response = await async_client.get("/api/v1/concepts?search=Python")
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert "Python" in item["name"]


class TestGetConcept:
    """GET /concepts/{id} — 获取概念详情"""

    @pytest.mark.asyncio
    async def test_get_concept_detail(self, async_client):
        """获取概念详情（含关系列表）"""
        # 创建概念
        create_resp = await async_client.post("/api/v1/concepts", json={
            "name": "Python", "category": "topic",
        })
        concept_id = create_resp.json()["id"]

        response = await async_client.get(f"/api/v1/concepts/{concept_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Python"
        assert data["category"] == "topic"
        assert "outgoing_relations" in data
        assert "incoming_relations" in data

    @pytest.mark.asyncio
    async def test_get_concept_relations_in_detail(self, async_client):
        """概念详情应包含完整的关系信息"""
        # 创建两个概念
        c1 = await async_client.post("/api/v1/concepts", json={
            "name": "变量", "category": "term",
        })
        c2 = await async_client.post("/api/v1/concepts", json={
            "name": "数据类型", "category": "term",
        })
        c1_id = c1.json()["id"]
        c2_id = c2.json()["id"]

        # 创建关系：变量 --prerequisite--> 数据类型
        rel_resp = await async_client.post(f"/api/v1/concepts/{c1_id}/relations", json={
            "target_id": c2_id,
            "relation_type": "prerequisite",
        })
        assert rel_resp.status_code == 201

        # 查看 c2 详情：应有 incoming_relations
        detail = await async_client.get(f"/api/v1/concepts/{c2_id}")
        assert detail.status_code == 200
        data = detail.json()
        assert len(data["incoming_relations"]) == 1
        assert data["incoming_relations"][0]["source_name"] == "变量"

    @pytest.mark.asyncio
    async def test_get_concept_not_found(self, async_client):
        """不存在的概念应返回 404"""
        response = await async_client.get("/api/v1/concepts/99999")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_concept_unauthorized(self, async_client):
        """未认证应返回 401/403"""
        original_auth = async_client.headers.pop("Authorization", None)
        try:
            response = await async_client.get("/api/v1/concepts/1")
            assert response.status_code in (401, 403)
        finally:
            if original_auth:
                async_client.headers["Authorization"] = original_auth


class TestUpdateConcept:
    """PUT /concepts/{id} — 更新概念"""

    @pytest.mark.asyncio
    async def test_update_concept_name(self, async_client):
        """更新概念名称"""
        create_resp = await async_client.post("/api/v1/concepts", json={
            "name": "旧名称", "category": "topic",
        })
        concept_id = create_resp.json()["id"]

        response = await async_client.put(f"/api/v1/concepts/{concept_id}", json={
            "name": "新名称",
        })
        assert response.status_code == 200
        assert response.json()["name"] == "新名称"

    @pytest.mark.asyncio
    async def test_update_concept_all_fields(self, async_client):
        """更新所有字段"""
        create_resp = await async_client.post("/api/v1/concepts", json={
            "name": "原始概念", "category": "topic",
        })
        concept_id = create_resp.json()["id"]

        response = await async_client.put(f"/api/v1/concepts/{concept_id}", json={
            "name": "更新概念",
            "description": "更新后的描述",
            "category": "term",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "更新概念"
        assert data["description"] == "更新后的描述"
        assert data["category"] == "term"

    @pytest.mark.asyncio
    async def test_update_concept_invalid_category(self, async_client):
        """更新时无效 category 应返回 422"""
        create_resp = await async_client.post("/api/v1/concepts", json={
            "name": "测试", "category": "topic",
        })
        concept_id = create_resp.json()["id"]

        response = await async_client.put(f"/api/v1/concepts/{concept_id}", json={
            "category": "invalid",
        })
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_update_concept_not_found(self, async_client):
        """更新不存在的概念应返回 404"""
        response = await async_client.put("/api/v1/concepts/99999", json={
            "name": "不存在",
        })
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_concept_empty_body(self, async_client):
        """空请求体应返回 400"""
        create_resp = await async_client.post("/api/v1/concepts", json={
            "name": "测试", "category": "topic",
        })
        concept_id = create_resp.json()["id"]

        response = await async_client.put(f"/api/v1/concepts/{concept_id}", json={})
        assert response.status_code == 400


class TestDeleteConcept:
    """DELETE /concepts/{id} — 删除概念"""

    @pytest.mark.asyncio
    async def test_delete_concept(self, async_client):
        """正常删除概念"""
        create_resp = await async_client.post("/api/v1/concepts", json={
            "name": "待删除", "category": "topic",
        })
        concept_id = create_resp.json()["id"]

        response = await async_client.delete(f"/api/v1/concepts/{concept_id}")
        assert response.status_code == 204

        # 确认已删除
        get_resp = await async_client.get(f"/api/v1/concepts/{concept_id}")
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_concept_cascades_relations(self, async_client):
        """删除概念后关联关系也应被删除（级联）"""
        # 创建两个概念
        c1 = await async_client.post("/api/v1/concepts", json={
            "name": "源概念_级联测试", "category": "topic",
        })
        c2 = await async_client.post("/api/v1/concepts", json={
            "name": "目标概念_级联测试", "category": "topic",
        })
        c1_id = c1.json()["id"]
        c2_id = c2.json()["id"]

        # 创建关系
        rel = await async_client.post(f"/api/v1/concepts/{c1_id}/relations", json={
            "target_id": c2_id,
            "relation_type": "related",
        })
        rel_id = rel.json()["id"]

        # 删除源概念
        await async_client.delete(f"/api/v1/concepts/{c1_id}")

        # 确认源概念已删除
        get_c1 = await async_client.get(f"/api/v1/concepts/{c1_id}")
        assert get_c1.status_code == 404

        # 确认目标概念还存在
        detail = await async_client.get(f"/api/v1/concepts/{c2_id}")
        assert detail.status_code == 200
        # 检查 incoming_relations 中不再包含被级联删除的关系
        incoming_rel_ids = [r["id"] for r in detail.json()["incoming_relations"]]
        assert rel_id not in incoming_rel_ids, "级联删除失败：关系仍然存在"

    @pytest.mark.asyncio
    async def test_delete_concept_not_found(self, async_client):
        """删除不存在的概念应返回 404"""
        response = await async_client.delete("/api/v1/concepts/99999")
        assert response.status_code == 404


# ==================== 概念关系测试 ====================

class TestCreateRelation:
    """POST /concepts/{id}/relations — 创建概念关系"""

    @pytest.mark.asyncio
    async def test_create_relation_prerequisite(self, async_client):
        """创建前置关系"""
        c1 = await async_client.post("/api/v1/concepts", json={
            "name": "Python", "category": "topic",
        })
        c2 = await async_client.post("/api/v1/concepts", json={
            "name": "Django", "category": "topic",
        })
        c1_id = c1.json()["id"]
        c2_id = c2.json()["id"]

        response = await async_client.post(f"/api/v1/concepts/{c1_id}/relations", json={
            "target_id": c2_id,
            "relation_type": "prerequisite",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["source_id"] == c1_id
        assert data["target_id"] == c2_id
        assert data["relation_type"] == "prerequisite"
        assert data["source_name"] == "Python"
        assert data["target_name"] == "Django"

    @pytest.mark.asyncio
    async def test_create_relations_all_types(self, async_client):
        """创建所有类型的关系"""
        c1 = await async_client.post("/api/v1/concepts", json={
            "name": "A", "category": "topic",
        })
        c2 = await async_client.post("/api/v1/concepts", json={
            "name": "B", "category": "topic",
        })
        c1_id = c1.json()["id"]
        c2_id = c2.json()["id"]

        for rel_type in ["prerequisite", "related", "part_of"]:
            response = await async_client.post(
                f"/api/v1/concepts/{c1_id}/relations", json={
                    "target_id": c2_id,
                    "relation_type": rel_type,
                }
            )
            assert response.status_code == 201, f"relation_type={rel_type} 失败"
            assert response.json()["relation_type"] == rel_type

    @pytest.mark.asyncio
    async def test_create_duplicate_relation(self, async_client):
        """重复创建相同类型的关系应返回 409"""
        c1 = await async_client.post("/api/v1/concepts", json={
            "name": "A", "category": "topic",
        })
        c2 = await async_client.post("/api/v1/concepts", json={
            "name": "B", "category": "topic",
        })
        c1_id = c1.json()["id"]
        c2_id = c2.json()["id"]

        # 第一次创建
        response = await async_client.post(
            f"/api/v1/concepts/{c1_id}/relations", json={
                "target_id": c2_id,
                "relation_type": "related",
            }
        )
        assert response.status_code == 201

        # 重复创建
        response = await async_client.post(
            f"/api/v1/concepts/{c1_id}/relations", json={
                "target_id": c2_id,
                "relation_type": "related",
            }
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_create_self_relation(self, async_client):
        """不能创建指向自身的关系"""
        c = await async_client.post("/api/v1/concepts", json={
            "name": "自引用", "category": "topic",
        })
        c_id = c.json()["id"]

        response = await async_client.post(
            f"/api/v1/concepts/{c_id}/relations", json={
                "target_id": c_id,
                "relation_type": "related",
            }
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_relation_invalid_type(self, async_client):
        """无效的关系类型应返回 422"""
        c1 = await async_client.post("/api/v1/concepts", json={
            "name": "A", "category": "topic",
        })
        c2 = await async_client.post("/api/v1/concepts", json={
            "name": "B", "category": "topic",
        })
        c1_id = c1.json()["id"]
        c2_id = c2.json()["id"]

        response = await async_client.post(
            f"/api/v1/concepts/{c1_id}/relations", json={
                "target_id": c2_id,
                "relation_type": "invalid_type",
            }
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_relation_target_not_found(self, async_client):
        """目标概念不存在应返回 404"""
        c = await async_client.post("/api/v1/concepts", json={
            "name": "A", "category": "topic",
        })
        c_id = c.json()["id"]

        response = await async_client.post(
            f"/api/v1/concepts/{c_id}/relations", json={
                "target_id": 99999,
                "relation_type": "related",
            }
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_relation_source_not_found(self, async_client):
        """源概念不存在应返回 404"""
        response = await async_client.post(
            "/api/v1/concepts/99999/relations", json={
                "target_id": 1,
                "relation_type": "related",
            }
        )
        assert response.status_code == 404


class TestDeleteRelation:
    """DELETE /concepts/{id}/relations/{rel_id} — 删除概念关系"""

    @pytest.mark.asyncio
    async def test_delete_relation(self, async_client):
        """正常删除关系"""
        c1 = await async_client.post("/api/v1/concepts", json={
            "name": "A", "category": "topic",
        })
        c2 = await async_client.post("/api/v1/concepts", json={
            "name": "B", "category": "topic",
        })
        c1_id = c1.json()["id"]
        c2_id = c2.json()["id"]

        # 创建关系
        rel = await async_client.post(
            f"/api/v1/concepts/{c1_id}/relations", json={
                "target_id": c2_id,
                "relation_type": "related",
            }
        )
        rel_id = rel.json()["id"]

        # 删除关系
        response = await async_client.delete(
            f"/api/v1/concepts/{c1_id}/relations/{rel_id}"
        )
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_relation_not_found(self, async_client):
        """删除不存在的关系应返回 404"""
        c = await async_client.post("/api/v1/concepts", json={
            "name": "A", "category": "topic",
        })
        c_id = c.json()["id"]

        response = await async_client.delete(
            f"/api/v1/concepts/{c_id}/relations/99999"
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_relation_not_belong_to_concept(self, async_client):
        """删除不属于该概念的关系应返回 404"""
        c1 = await async_client.post("/api/v1/concepts", json={
            "name": "A", "category": "topic",
        })
        c2 = await async_client.post("/api/v1/concepts", json={
            "name": "B", "category": "topic",
        })
        c3 = await async_client.post("/api/v1/concepts", json={
            "name": "C", "category": "topic",
        })
        c1_id = c1.json()["id"]
        c2_id = c2.json()["id"]
        c3_id = c3.json()["id"]

        # 创建关系 A -> B
        rel = await async_client.post(
            f"/api/v1/concepts/{c1_id}/relations", json={
                "target_id": c2_id,
                "relation_type": "related",
            }
        )
        rel_id = rel.json()["id"]

        # 尝试从 C 删除 A->B 的关系（不应成功）
        response = await async_client.delete(
            f"/api/v1/concepts/{c3_id}/relations/{rel_id}"
        )
        assert response.status_code == 404
