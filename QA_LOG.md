# StudyBot 问题与回答记录

> 记录开发过程中你提出的问题和 Claude 的回答，方便回顾。

---

## 2026-06-27～28

### 会话总结

本次会话完成了 Steps 24-26（前端响应式完善 + RAG Celery 自动向量化 + LLM 集成和对话历史）以及全量代码审计。

**主要工作**:
- Step 24: 17 文件变更，新增 useWebSocket Hook + PlanProgress 组件，Navbar 汉堡菜单，10 页面响应式适配，9 页面 EmptyState/Skeleton 接入
- Step 25: 修复 QA Schema bug + Celery embedding 真实实现 + DB 迁移链修复
- Step 26: QA 接入 DeepSeek LLM + Conversation/ChatMessage ORM + 对话历史 CRUD API + 前端对话管理侧边栏
- 审计修复: 3 代理并行审计发现 10 项问题（HNSW 索引丢失、WebSocket 空 URL、对话 ID 断连等），全部修复

**问答记录**:
1. 用户要求拉取远程仓库 → 配置 Git 代理后 fetch + merge
2. 用户要求开始 Step 24 → 探索代码后制定 7 阶段计划 → 实现全部
3. 用户要求启动 Docker → 等待构建（langchain 依赖下载耗时较长）
4. 用户要求继续 → 执行 Step 25-26
5. 用户要求审计代码 → 3 代理并行审计 → 10 项发现 → 全部修复
6. 用户要求执行终止流程 → 更新所有追踪文档 + 推送

---

## 2026-05-31

### Q1: `__init__.py` 文件的作用是什么？

**问**: `__init__.py` 文件的作用这么巨大吗，他具体起到什么作用呢？

**答**: `__init__.py` 是 Python 包的"身份证"，有两个作用：

**1. 包标识符** — Python 靠它识别一个目录是"包"。没有 `__init__.py` 的目录不能通过 `import` 导入。

```python
backend/app/models/
├── __init__.py    ← 有这个 → Python 认为 models/ 是包
├── user.py

# from app.models.user import User  ✅ 可以工作
# 没有 __init__.py                    ❌ ImportError
```

**2. 包的入口大厅** — `__init__.py` 里的代码在包首次被导入时自动执行。

```python
# app/models/__init__.py
# 控制导出范围
__all__ = ["User", "Task"]

# 简化外部导入
from .user import User
# 效果：外部写 from app.models import User 即可
```

**对于本项目**，绝大部分 `__init__.py` 只需要一行注释说明包的用途即可，它的存在本身就完成了最重要的使命。

---

## 2026-06-01

### Q2: Windows 下 asyncpg 连 Docker PostgreSQL 始终失败，原因是什么？

**排查过程**:

1. asyncpg 使用默认 ProactorEventLoop → `WinError 64`（网络名称不再可用）
2. 切换 SelectorEventLoop → `WinError 10054`（远程主机强制关闭连接）
3. 换 psycopg2（同步）→ `OperationalError`（空消息）
4. 换 psycopg3（异步）→ 密码认证失败（但容器内 psql 用同样密码能通过 TCP 登录）
5. 改 pg_hba.conf 为 trust → 仍然密码认证失败，且 PostgreSQL 日志里**没有任何连接记录**
6. **最终证据**：用 Python 原始 socket 测试 127.0.0.1:5432 → TCP 三次握手成功，但 `recv()` 永远超时，收不到 PostgreSQL 的启动消息

**结论**: 不是任何 Python 驱动的问题。Docker Desktop Windows 的端口代理层有缺陷——TCP 连接能建立但数据帧不流通。PostgreSQL 根本收不到连接请求（日志无记录），客户端也收不到服务器的响应。

**解决方案**: 方案 B — 后端也进 Docker 容器，和 PostgreSQL 在同一 Docker 内网通信，不经过 Windows 端口代理。

---

### Q3: CI/CD 是什么？

**问**: CI/CD 是什么？

**答**: CI/CD 是两个概念的组合：

**CI — 持续集成（Continuous Integration）**

代码合并到主分支时，自动跑一遍：构建 → 测试 → 代码检查。目的是尽早发现"合进去的代码有没有搞坏东西"。

```
开发者 push 代码 → 自动触发 → pip install → 跑测试 → 语法检查 → 通过/失败通知
```

**CD — 持续交付/部署（Continuous Delivery/Deployment）**

CI 通过后，自动把代码部署到服务器。有两种级别：
- **持续交付**：自动打包好，按一下按钮才发布到生产环境
- **持续部署**：全自动，代码合进去就直接上线（要求测试覆盖率极高）

```
CI 通过 → 构建 Docker 镜像 → 推送到镜像仓库 → 部署到测试/生产服务器
```

**和本项目的关系**：我们选方案 B（后端进 Docker），正是为未来的 CI/CD 做准备。有了 Dockerfile，后续配 GitHub Actions 等 CI 工具时，`docker build && docker push` 两行命令就能完成构建和部署。

---

### Q4: Alembic 是什么？

**问**: 你在第六步中提到的 Alembic 是什么呢？

**答**: Alembic 是 SQLAlchemy 官方配套的数据库迁移工具，像 Git 管理代码一样管理数据库表结构变更。

**为什么需要它**：目前我们用 `Base.metadata.create_all()` 在启动时自动建表，这只适合开发阶段。生产环境已有数据，不能删表重建。Alembic 能增量地修改表结构（加列、改类型等），还能回滚。

**工作流程**:
```
1. 修改 ORM 模型（如 User 加了 avatar_url 列）
2. alembic revision --autogenerate -m "给用户加头像"
   -> 自动对比模型 vs 当前数据库，生成迁移脚本
3. alembic upgrade head
   -> 执行迁移（ALTER TABLE users ADD COLUMN avatar_url...）
4. 出问题了: alembic downgrade -1
   -> 回滚到上一版本
```

**不用 Alembic 的后果**：上线后要改表结构就得手动连数据库写 `ALTER TABLE` SQL，容易出错，无法回滚。

---

### Q5: 任务执行日志会越来越长，是否该拆分？

**问**: 任务执行记录会不会后期过于冗长？是否按 Step 切片？

**答**: 同意拆分。最终方案：

- `TASK_LOG.md` → 改为索引文件（Step 编号 + 链接 + 状态表）
- `task_logs/step_01_project_skeleton.md` … `step_06_models_migration.md` — 每 Step 独立文件
- **PROJECT_TRACKER.md** — 不建议拆，它是"神经中枢"，拆了反而增加恢复成本
- **QA_LOG.md** — 暂时不需要，观察后续增长速度再决定

---

### Q6: PROJECT_TRACKER.md 和 QA_LOG.md 需要拆分吗？

**问**: 其他两个文档有拆分的必要吗？

**答**:
- PROJECT_TRACKER.md — 不建议拆。它是每次新会话的"记忆恢复卡"，拆散了反而增加负担。顶部固定区域紧凑，Step 详情完成后会精简为摘要。
- QA_LOG.md — 暂时不需要。目前只有几个问题，远未到冗长的程度。如果将来积累到 20+ 个再考虑。

结论：只拆 TASK_LOG 就够了。

---

## 2026-06-24

### Q7: 代理连接 GitHub 失败怎么办？

**问**: 克隆仓库时 `git clone` 连接 GitHub 超时，代理端口也连不上。

**答**: 排查步骤：
1. 先确认代理服务器是否可达（`ping` 代理 IP）
2. 检查端口是否开放（`nc -zv IP PORT`）
3. 发现代理实际运行在本地 `127.0.0.1` 而非远程 IP
4. 配置 git 使用本地代理：`git config --global http.proxy http://127.0.0.1:8890`

**经验**: 代理客户端通常在本机运行并转发流量，所以 git 应该配 localhost 端口而非远程 IP。

---

### Q8: Alembic 初始迁移为空怎么办？

**问**: `alembic upgrade head` 报错 `relation "tasks" does not exist`，初始迁移文件是空的（只有 `pass`）。

**答**: 初始迁移为空是因为 `autogenerate` 时数据库已经有表（或模型没变化）。解决方案：
1. 删除有问题的迁移文件
2. 重新 `alembic revision --autogenerate -m "initial schema"`
3. 这次会正确检测所有表和索引
4. `alembic upgrade head` 应用

---

### Q9: FastAPI 路由 `/concepts/graph` 返回 422 怎么排查？

**问**: 测试 `/api/v1/concepts/graph` 返回 422 Unprocessable Entity。

**答**: 这是 FastAPI 路由优先级问题。当 `/{concept_id}` 路由在 `/graph` 之前注册时，FastAPI 会把 "graph" 当成 `concept_id` 尝试解析为 int，失败返回 422。

**修复**: 把 `/graph` 路由移到 `/{concept_id}` 之前。FastAPI 路由匹配是按注册顺序的，具体路由必须在参数化路由之前。

---

## 2026-06-24

### Q10: E2E 测试是什么？

**问**: 你知道 e2e 吗

**答**: E2E (End-to-End) 测试模拟真实用户从前端到后端的完整操作流程。与单元测试（测单个函数）和集成测试（测多模块协作）不同，E2E 测试覆盖完整的用户链路：打开浏览器 → 注册 → 创建目标 → AI 生成计划 → 上传文档 → 提问 → 验证回答。本项目使用 Playwright 框架，15 个 E2E 测试覆盖 auth/goals/documents/qa/review/quiz/planner 7 个核心流程。

---

### Q11: 异常处理审计发现了哪些问题？

**答**: 按严重程度分三级：

**🔴 严重 (3)**:
1. 无全局异常处理器 → 未捕获异常泄露堆栈信息
2. 注册接口无 IntegrityError 兜底 → 并发请求暴露 DB schema
3. 24 处 db.commit() 无 rollback 保护 → 异常时 session 脏状态

**🟡 重要 (5)**:
4. 无 API 限流 → 暴力破解 + LLM 额度耗尽风险
5. 文件上传全量读入内存再检查大小 → 内存耗尽攻击
6. QA 语义搜索异常静默吞掉 → 运维无法发现故障
7. Scheduler 端点无异常处理 → 未处理 500
8. 前端 5xx 原始错误文本 → 用户不友好

**🟢 改进 (4)**:
9. Quiz 批改静默跳过不存在的题目 → 分数不准
10. Dashboard 热力图加载失败无提示
11. 前端错误消息风格不一致（硬编码 vs ApiError.detail）
12. CORS 配置过于宽松 (allow_methods=["*"])

---

### Q12: 为什么限流器导致测试全部失败？

**问**: 添加 slowapi 限流后 137 个测试级联报错

**答**: 限流器按 IP 地址计 key，所有测试请求来自同一 IP (localhost)，注册端点限制 5次/分钟。前几个测试用完配额后，后续测试全部返回 429 Too Many Requests。修复方案：在 conftest.py 中设置 `os.environ["APP_ENV"] = "test"`，限流器检测到测试环境时自动禁用 (`enabled=False`)。

**本次会话无技术问答**。会话内容为 Step 19 前端扩展开发（间隔复习页面 + AI 问答页面），全程按 PROJECT_TRACKER.md 指令执行，无额外技术概念讨论。

---

## 2026-06-21

### Q1: Steps 8-16 标记为完成，但后端 API 路由缺失怎么办？

**问**: PROJECT_TRACKER.md 显示 Steps 8-16 ✅ 已完成，但实际代码中 `backend/app/api/v1/` 只有 auth/users/goals/tasks 四个路由文件。Quiz、Concept、Document、ReviewCard 的 ORM 模型存在但 API 路由和 Schema 从未实现。如何继续 Step 20？

**答**: 需要先补齐后端 API。Step 20 的任务是"前端自动出题页面 + 知识图谱可视化"，这两个功能直接依赖 Quiz 和 Concept 模块的后端 API。推荐策略是**先补后端再前端**：为 Quiz 和 Concept 创建完整的 API 路由 + Schema + 测试，再开发前端页面。其他缺失模块（Documents、ReviewCards、Dashboard 等）可在 Step 21 统一补齐。

### Q2: Quiz 模型 `options` 字段类型不匹配

**问**: Quiz 模型的 `options` 列定义为 `Mapped[Optional[dict]]`（JSON），但实际存储的是选项列表（如 `["A", "B", "C", "D"]`）。Schema 应该用 `list[str]` 还是 `dict`？

**答**: Schema 使用 `list[str]`。SQLAlchemy 的 JSON 列可以存储任何 JSON 可序列化的值（包括数组），不限于 dict。Pydantic 的 `list[str]` 会在存入数据库时自动序列化为 JSON 数组，读取时自动反序列化回 Python list。

### Q3: Quiz 模型 `correct_answer` 类型不匹配

**问**: 模型注释说 `correct_answer` 是"正确答案在 options 数组中的索引（0-based）"，但列类型是 `String(255)`。Schema 应该用什么类型？

**答**: Schema 使用 `int`（带 `ge=0` 验证），路由层做转换：`str(answer_index)` 存入数据库，`int(stored_value)` 在响应中返回。这样既保持了数据库兼容性，又提供了前端的类型安全。

### Q4: ConceptRelation 没有 user_id，如何做权限隔离？

**问**: ConceptRelation 模型只有 source_id 和 target_id，没有 user_id 字段。如何防止用户 A 操作用户 B 创建的关系？

**答**: 通过 source concept 间接验证。在创建/删除关系前，先通过 `_get_user_concept` 验证 source concept 属于当前用户。由于 source concept 有 user_id，这确保了只有概念的所有者可以管理其关系。
