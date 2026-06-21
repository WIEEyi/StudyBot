# Step 20: 前端扩展 — 自动出题页面 + 知识图谱可视化

**日期**: 2026-06-21
**分支**: feature/step-20-quiz-concepts
**状态**: ✅ 完成

---

## 概述

开发测验（Quiz）和知识图谱（Concept/Graph）两个模块的完整前后端功能。由于后端 Quiz 和 Concept API 路由不存在，本次同时补齐后端 API + Schema + 测试 + 前端页面。

---

## 执行记录

### Phase 1: 后端 Schema（2 个文件）

**新建 `backend/app/schemas/quiz.py`**:
- `QuizCreate` — 创建测验题（question + options + correct_answer + explanation + document_id + source）
- `QuizUpdate` — 更新测验题（所有字段可选）
- `QuizResponse` — 测验题响应（含 id/user_id/时间戳）
- `QuizListResponse` — 分页列表（items + total + offset + limit）
- `QuizGenerateRequest` — AI 出题请求（document_id + count）
- `QuizGenerateResponse` — AI 出题响应
- `QuizSubmission` — 答题提交（quiz_id + selected_index）
- `QuizResultResponse` — 单题评分结果
- `QuizScoreResponse` — 整批评分结果
- 内置 model_validator：验证 correct_answer < len(options)

**新建 `backend/app/schemas/concept.py`**:
- `ConceptCreate` / `ConceptUpdate` — 概念 CRUD
- `ConceptResponse` / `ConceptDetailResponse` / `ConceptListResponse` — 概念响应
- `ConceptRelationCreate` / `ConceptRelationResponse` — 关系管理
- `GraphNode` / `GraphEdge` / `GraphResponse` — 图谱数据

### Phase 2: 后端 API 路由（2 个新文件 + 1 个修改）

**新建 `backend/app/api/v1/quizzes.py`** — 7 个端点:
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /quizzes | 分页列表（支持 document_id 过滤） |
| GET | /quizzes/{id} | 单个测验题详情 |
| POST | /quizzes | 创建测验题（校验文档归属） |
| PUT | /quizzes/{id} | 更新测验题（部分更新） |
| DELETE | /quizzes/{id} | 删除测验题 (204) |
| POST | /quizzes/generate | AI 自动出题（stub，返回 mock 数据） |
| POST | /quizzes/grade | 批改答题（计算正确数和百分比） |

**新建 `backend/app/api/v1/concepts.py`** — 8 个端点:
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /concepts | 分页列表（支持 category 过滤） |
| GET | /concepts/{id} | 单个概念详情（含关系列表） |
| POST | /concepts | 创建概念 |
| PUT | /concepts/{id} | 更新概念 |
| DELETE | /concepts/{id} | 删除概念（级联删除关系） |
| POST | /concepts/{id}/relations | 创建关系（防自引用+重复） |
| DELETE | /concepts/{id}/relations/{rel_id} | 删除关系 |
| GET | /concepts/graph | 获取完整图谱数据（nodes+edges） |

**修改 `backend/app/main.py`**:
- 注册 quizzes_router 和 concepts_router

### Phase 3: 后端测试（2 个文件）

**新建 `backend/tests/api/v1/test_quizzes.py`** — 18 个测试:
- TestCreateQuiz (3): 全字段创建、最简创建、无效答案索引
- TestListQuizzes (4): 空列表、分页、按文档过滤、有数据
- TestGetQuiz (2): 存在、不存在
- TestUpdateQuiz (3): 全字段更新、不存在、空请求体
- TestDeleteQuiz (2): 存在、不存在
- TestGenerateQuiz (1): stub 返回 404（无文档）
- TestGradeQuiz (3): 全对、部分对、空提交
- TestUnauthorized (2): 无认证列表、无认证创建
- TestValidation (4): 空题目、缺选项、单选项、负数索引

**新建 `backend/tests/api/v1/test_concepts.py`** — 25 个测试:
- TestCreateConcept (3): 全字段、最简、无效分类
- TestListConcepts (4): 空列表、分页、按分类过滤、有数据
- TestGetConcept (2): 存在、不存在
- TestUpdateConcept (3): 全字段、不存在、空请求体
- TestDeleteConcept (2): 存在、不存在
- TestCreateRelation (4): 正常、自引用、重复、不存在目标
- TestDeleteRelation (2): 正常、不存在
- TestGetGraph (2): 空图谱、有数据
- TestUnauthorized (2): 无认证
- TestValidation (3): 空名称、名称过长、无效关系类型

### Phase 4: 前端（4 个新文件 + 3 个修改 + npm install）

**安装依赖**: `vis-network` + `vis-data`

**新建 `frontend/src/types/vis-network.d.ts`** — vis-network standalone 最小类型声明

**新建 `frontend/src/components/KnowledgeGraphCanvas.tsx`** — vis-network React 封装:
- 力导向布局（forceAtlas2Based 物理引擎）
- 分类颜色映射（学科蓝/主题绿/子主题紫/术语橙/其他灰）
- 关系样式映射（前置知识红实线/相关灰虚线/包含蓝实线）
- 节点点击回调 → 打开侧边面板
- 空状态提示

**新建 `frontend/src/app/quiz/page.tsx`** — 测验页面:
- 列表模式：题目管理 + 文档筛选 + 复选框选择 + CRUD
- 做题模式：逐题作答 + 进度条 + 选项高亮 + 提交评分 + 结果回顾
- AI 出题对话框：选文档 + 设置题数 + 生成
- CRUD 对话框：题目 + 选项列表（支持增删）+ 标记正确答案 + 解析

**新建 `frontend/src/app/concepts/page.tsx`** — 知识图谱页面:
- 列表/图谱双视图切换（Tab）
- 列表模式：分类筛选 + 概念卡片 + 关系详情面板
- 图谱模式：vis-network 可视化 + 图例 + 侧边详情面板
- 关系管理：添加/删除关系对话框

**修改 `frontend/src/lib/types.ts`** — 新增 25 个 TS 类型:
- Quiz 相关: Quiz, QuizListResponse, QuizCreate, QuizUpdate, QuizGenerateRequest/Response, QuizSubmission, QuizResultResponse, QuizScoreResponse
- Concept 相关: Concept, ConceptDetail, ConceptListResponse, ConceptCreate, ConceptUpdate, ConceptRelationResponse/RelationCreate
- Graph 相关: GraphNode, GraphEdge, GraphResponse

**修改 `frontend/src/components/Navbar.tsx`** — 添加"测验"和"知识图谱"导航链接

### Phase 5: 验证

- ✅ 前端 Next.js build 成功（12/12 pages，含 quiz 和 concepts）
- ✅ Python 语法检查全部通过（6 个文件）
- ⏳ 后端 pytest（需 Docker 运行，下次启动时验证）

---

## 技术要点

1. **correct_answer 转换**: Schema 用 `int`，ORM 层用 `str` 存储，路由层做 int↔str 转换
2. **options 字段**: Schema 用 `list[str]`，SQLAlchemy JSON 列自动序列化/反序列化
3. **AI 出题 Stub**: 返回 mock 数据，logger.warning 提示未实现，待 AI Agent 系统就绪
4. **ConceptRelation 权限**: 通过 source concept 的 user_id 间接验证，防止跨用户操作
5. **图谱去重**: ConceptRelation 允许防自引用（400）和防重复（409）
6. **图谱隔离**: get_graph 只返回当前用户的概念和关系

---

## 下一步

更新 PROJECT_TRACKER.md 标记 Step 20 完成，定义 Step 21
