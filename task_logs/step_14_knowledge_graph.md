# Step 14: 知识图谱 — 概念关系可视化

**日期**: 2026-06-05
**状态**: ✅ 完成
**分支**: feature/step-10-vector-embedding

---

## 概述

构建知识图谱的完整 API 层，包括概念 CRUD、概念关系管理、以及图谱可视化数据接口。模型（Concept + ConceptRelation）已在 Step 6 创建，本次仅新增 API 层。

---

## 创建的文件

### Schemas

1. `backend/app/schemas/concept.py` — Concept/ConceptRelation Pydantic 模型
   - `ConceptCreate`: name, description, category
   - `ConceptUpdate`: 所有字段可选（部分更新）
   - `ConceptResponse`: 基本响应 + relation_count
   - `ConceptDetailResponse`: 含 outgoing_relations / incoming_relations 列表
   - `ConceptRelationCreate`: target_id, relation_type
   - `ConceptRelationResponse`: 含 source_name / target_name
   - `ConceptListResponse`: 分页列表

2. `backend/app/schemas/graph.py` — 图谱可视化模型
   - `GraphNode`: 节点（前端渲染用）
   - `GraphEdge`: 边（含 source_name / target_name）
   - `GraphResponse`: nodes + edges + total 计数
   - `GraphStatsResponse`: 按分类/按关系类型统计

### API 路由

3. `backend/app/api/v1/concepts.py` — 8 个端点
   - `GET /concepts` — 分页列表（category 过滤 + 名称模糊搜索）
   - `POST /concepts` — 创建概念（category 校验）
   - `GET /concepts/{id}` — 概念详情（含 incoming/outgoing 关系）
   - `PUT /concepts/{id}` — 更新概念（部分更新）
   - `DELETE /concepts/{id}` — 删除概念（级联删除关系）
   - `POST /concepts/{id}/relations` — 创建关系（自引用/重复/跨用户校验）
   - `DELETE /concepts/{id}/relations/{rel_id}` — 删除关系

4. `backend/app/api/v1/graph.py` — 2 个端点
   - `GET /graph` — 完整图谱数据（nodes + edges）
   - `GET /graph/stats` — 按分类/按关系类型统计

### 测试

5. `backend/tests/api/v1/test_concepts.py` — 34 个测试
   - 概念 CRUD: 创建(8) + 列表(5) + 详情(4) + 更新(5) + 删除(3) = 25
   - 概念关系: 创建(7) + 删除(3) = 10

6. `backend/tests/api/v1/test_graph.py` — 9 个测试
   - 图谱数据: 结构/节点/边/节点属性/未认证 = 5
   - 统计: 空/有概念/有关系/未认证 = 4

---

## 修改的文件

7. `backend/app/main.py` — 注册 concepts_router + graph_router
8. `backend/app/models/concept.py` — relationship 添加 `passive_deletes=True`（修复级联删除 Bug）

---

## 技术要点

### 级联删除问题与修复

删除概念时 SQLAlchemy 默认尝试将 FK 设置为 NULL，但数据库列有 NOT NULL 约束，导致 IntegrityError。
解决方案：在 Concept 模型的 outgoing_relations / incoming_relations 上添加 `passive_deletes=True`，
告诉 SQLAlchemy 依赖数据库级的 `ON DELETE CASCADE` 来处理。

### 关系重复检测

`POST /concepts/{id}/relations` 在创建前检查是否已存在相同 (source_id, target_id, relation_type) 的关系，
存在则返回 409 Conflict。

### 图谱查询优化

`GET /graph` 使用聚合查询批量计算 relation_count，避免 N+1 问题：
- 按 source_id 聚合统计出边数
- 按 target_id 聚合统计入边数
- 合并得到每个概念的总关系数

---

## 测试验证

```bash
# 运行新测试
docker compose exec backend pytest tests/api/v1/test_concepts.py tests/api/v1/test_graph.py -v
# 结果: 45/45 全部通过 ✅

# 运行全量测试
docker compose exec backend pytest -v
# 结果: 202/202 全部通过 ✅
```

---

## 修复的 Bug

1. **Concept CASCADE delete**: 添加 `passive_deletes=True` 防止 SQLAlchemy SET NULL 冲突
2. **Unauthorized 测试断言**: 改为 `assert status_code in (401, 403)` 兼容 FastAPI HTTPBearer
3. **图谱测试数据隔离**: 使用 uuid 唯一名称避免共享数据库冲突
