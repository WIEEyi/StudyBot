# Step 3: FastAPI 项目初始化 + Docker 化

**日期**: 2026-05-31 ~ 2026-06-01 | **时间**: 多个会话 | **状态**: ✅ 完成

---

## 第一阶段: 代码编写 (2026-05-31 22:00)

### 创建的文件

**配置与基础设施**:
- `backend/requirements.txt` — Python 依赖清单（40+ 包）
- `backend/app/config.py` — Pydantic Settings 配置管理
  - `class Settings(BaseSettings)` — 所有环境变量读取 + 类型校验
  - `get_settings()` — lru_cache 单例模式
- `backend/app/core/database.py` — SQLAlchemy 异步引擎
  - `engine` — create_async_engine, pool_size=10
  - `AsyncSessionLocal` — async_sessionmaker
  - `get_db()` — FastAPI 依赖注入，自动管理会话生命周期
- `backend/app/core/redis_client.py` — Redis 异步连接池

**应用入口**:
- `backend/app/main.py` — FastAPI 入口
  - `lifespan()` — @asynccontextmanager，管理启动/关闭
  - CORS 中间件（允许 localhost:3000）
  - `/health` 健康检查接口
  - `/` 根路径欢迎接口
  - 启动时自动测试数据库连接

状态: 代码已写，依赖未装，等待启动验证

---

## 第二阶段: 编码问题修复 (2026-06-01)

### 问题

`pip install -r requirements.txt` 成功后，`uvicorn` 启动报错:
```
UnicodeEncodeError: 'gbk' codec can't encode character '\U0001f680'
```

### 原因

Windows cmd/PowerShell 默认 GBK 编码，不支持 emoji（🚀 🛑 ✅ ❌）

### 修复

将 `main.py` 中所有 emoji 替换为纯文本标记:
- 🚀 → `[启动]`
- ✅ → `[OK]`
- ❌ → `[ERROR]`
- 🛑 → `[关闭]`

---

## 第三阶段: Windows Docker 网络问题 + 方案 B 改造 (2026-06-01 17:30)

### 排查过程

1. Docker 服务全部 healthy，uvicorn 启动数据库连接失败
2. 安装 pgvector 扩展（`CREATE EXTENSION vector`）
3. asyncpg + ProactorEventLoop → WinError 64
4. asyncpg + SelectorEventLoop → WinError 10054
5. psycopg2、psycopg3 同样失败；改 pg_hba.conf 为 trust 仍失败
6. **Python 裸 socket 测试** → TCP 握手成功但 recv() 超时
7. **根因**: Docker Desktop Windows 端口代理层缺陷，TCP 能建立但数据帧不流通

### 决策: 方案 B — 后端进 Docker，容器内网直连

**创建的文件**:
- `backend/Dockerfile` — Python 3.11-slim，libpq-dev
- `backend/.dockerignore` — 排除 __pycache__/.venv/.git/.env

**修改的文件**:
- `docker-compose.yml` — 新增 backend 服务（bind mount `./backend:/app`）
- `backend/.env` / `.env.example` — host: localhost → postgres/redis/rabbitmq
- `backend/app/config.py` — 默认 URL 同步更新

### 验证结果

```bash
$ curl http://localhost:8000/health
{"status":"ok","app":"StudyBot","environment":"development"}

$ curl http://localhost:8000/
{"message":"欢迎使用 StudyBot API","docs":"/docs","health":"/health"}
```

数据库连接成功 ✅ | 日志正常 ✅ | Application startup complete ✅

### 日常开发命令

```bash
docker compose up -d backend     # 启动
docker compose logs -f backend   # 看日志
docker compose restart backend   # 重启
docker compose build backend     # 重建镜像（新增 pip 包时）
```

---

[返回索引](../TASK_LOG.md)
