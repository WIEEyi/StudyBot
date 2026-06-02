# Step 6: 数据库模型 + Alembic 迁移

**日期**: 2026-06-01 | **状态**: ✅ 完成

---

## 操作

1. 创建全部 7 个业务 ORM 模型
2. 更新 User 模型添加反向 relationship
3. 更新 models/__init__.py 统一导出
4. 初始化 Alembic + 配置 env.py
5. 移除 main.py 中的 create_all
6. stamp 基线 + 生成空迁移 + 验证

## 创建的模型文件

| 文件 | 表名 | 关键字段 |
|------|------|----------|
| `models/learning_goal.py` | learning_goals | user_id, title, description, deadline, status |
| `models/task.py` | tasks | user_id, goal_id, title, priority, due_date, status |
| `models/document.py` | documents | user_id, title, file_path, content, file_type |
| `models/review_card.py` | review_cards | user_id, document_id, front, back, ease_factor, interval |
| `models/quiz.py` | quizzes | user_id, document_id, question, options(JSON), correct_answer |
| `models/concept.py` | concepts | user_id, name, description, category |
| `models/concept_relation.py` | concept_relations | source_id, target_id, relation_type |

## alembic/env.py 关键配置

```python
# 导入 ORM 模型元数据
from app.models import Base
target_metadata = Base.metadata

# 从项目配置读取 URL（asyncpg -> psycopg2 转换）
from app.config import get_settings
sync_url = settings.DATABASE_URL.replace("+asyncpg", "+psycopg2")
config.set_main_option("sqlalchemy.url", sync_url)
```

## Alembic 关键发现

`DATABASE_URL` 使用 `asyncpg` 驱动，但 Alembic 需要同步驱动。在 `env.py` 中将 `+asyncpg` 替换为 `+psycopg2`。

## 修改的文件

- `backend/app/models/user.py` — 添加 6 个反向 relationship
- `backend/app/models/__init__.py` — 导出所有模型
- `backend/app/main.py` — 移除 `Base.metadata.create_all`
- `backend/alembic/env.py` — 指向 Base.metadata + 同步 URL
- `backend/alembic.ini` — (自动生成)

## 验证结果

- 8 张表全部存在 ✅
- Health check 正常 ✅
- autogenerate 生成空迁移（DB 与模型同步）✅
- `alembic upgrade head` 执行成功 ✅

## 日后修改表结构流程

```bash
# 1. 修改 ORM 模型代码
# 2. 生成迁移
docker compose exec backend alembic revision --autogenerate -m "描述你的改动"
# 3. 执行迁移
docker compose exec backend alembic upgrade head
```

---

[返回索引](../TASK_LOG.md)
