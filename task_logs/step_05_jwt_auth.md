# Step 5: 用户认证系统 (JWT)

**日期**: 2026-06-01 | **时间**: 20:50 - 21:10 | **状态**: ✅ 完成

---

## 操作

1. 创建 `backend/app/models/base.py` — SQLAlchemy 声明式基类 + TimestampMixin
2. 创建 `backend/app/models/user.py` — User 模型
3. 创建 `backend/app/core/security.py` — JWT 编解码 + bcrypt 密码哈希
4. 创建 `backend/app/schemas/auth.py` — Pydantic 请求/响应模型
5. 创建 `backend/app/api/deps.py` — get_current_user 依赖注入
6. 创建 `backend/app/api/v1/__init__.py` — v1 路由包
7. 创建 `backend/app/api/v1/auth.py` — POST /register, /login, /refresh
8. 创建 `backend/app/api/v1/users.py` — GET /users/me
9. 修改 `backend/app/main.py` — 注册 v1 路由，启动时自动建表
10. 修改 `backend/requirements.txt` — 添加 bcrypt==4.2.1

## 关键 Bug: passlib 与 bcrypt 兼容性

初始使用 passlib 的 CryptContext:
```python
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
```

首次注册时报错:
```
ValueError: password cannot be longer than 72 bytes, truncate manually if necessary
```

原因: passlib 1.7.4 的 `detect_wrap_bug()` 与新版 bcrypt 不兼容。

修复: 改用 bcrypt 直接调用:
```python
import bcrypt

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
```

## 验证结果

| 端点 | 方法 | 状态码 | 响应 |
|------|------|--------|------|
| `/api/v1/auth/register` | POST | 201 | access_token + refresh_token + token_type |
| `/api/v1/auth/login` | POST | 200 | access_token + refresh_token + token_type |
| `/api/v1/auth/refresh` | POST | 200 | 新 access_token + 滚动 refresh_token |
| `/api/v1/users/me` | GET | 200 | id, email, username, is_active, created_at, updated_at |

## 创建的文件

- `backend/app/models/base.py`
- `backend/app/models/user.py`
- `backend/app/core/security.py`
- `backend/app/schemas/auth.py`
- `backend/app/api/deps.py`
- `backend/app/api/v1/__init__.py`
- `backend/app/api/v1/auth.py`
- `backend/app/api/v1/users.py`

## 修改的文件

- `backend/app/main.py` — 注册路由 + 自动建表
- `backend/requirements.txt` — 加 bcrypt==4.2.1

---

[返回索引](../TASK_LOG.md)
