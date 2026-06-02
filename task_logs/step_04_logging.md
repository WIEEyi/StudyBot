# Step 4: 日志系统改进

**日期**: 2026-06-01 | **时间**: 17:35 - 20:45 | **状态**: ✅ 完成

---

## 第一阶段: 代码实现 (17:35 - 17:50)

### 创建的文件

- `backend/app/core/logging_config.py` — 日志配置模块
  - `setup_logging()` — 清空 root + uvicorn handler，统一用自定义格式
  - 格式: `2026-06-01 17:30:00 | INFO     | app.main | 数据库连接成功`
  - 控制台 handler → stdout（Docker logs 可见）
  - 文件 handler → `/app/logs/app.log`（落盘 `backend/logs/app.log`）
  - 抑制 SQLAlchemy engine 和 uvicorn.access 的 INFO 日志

### 修改的文件

- `backend/app/main.py` — 8 处 `print` 替换为 `logging.info/error`
- `backend/.dockerignore` — 新增 `logs/` 排除

---

## 第二阶段: 验证 + 修复 SQLAlchemy 日志重复 (20:35 - 20:45)

### 发现的问题

`docker compose restart backend` 后，SQLAlchemy engine 日志重复输出:
```
# 重复的日志:
2026-06-01 12:35:10,568 INFO sqlalchemy.engine.Engine select pg_catalog.version()  # uvicorn 格式
2026-06-01 12:35:10 | INFO     | sqlalchemy.engine.Engine | select pg_catalog.version()  # 我们的格式
```

### 原因分析

`database.py` 中 `echo=settings.APP_DEBUG` 使 SQLAlchemy 添加了自己的 StreamHandler，与我们的自定义 handler 同时输出。

### 修复方案

修改 `logging_config.py`:
1. 新增 `_clear_logger_handlers()` 辅助函数，递归清除子 logger handler
2. 把 `sqlalchemy.engine` 加入 `LOGGERS_TO_CLEAR` 列表
3. `sqlalchemy.engine` 级别改为根据调试模式动态设置（DEBUG → INFO，否则 WARNING）

### 验证结果

- 控制台日志: ✅ 无重复，全部管道格式
- 文件日志: ✅ `backend/logs/app.log` 正常生成，内容完整
- Docker 服务: ✅ 全部 healthy

---

[返回索引](../TASK_LOG.md)
