# StudyBot 问题与回答记录

> 记录开发过程中你提出的问题和 Claude 的回答，方便回顾。

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
