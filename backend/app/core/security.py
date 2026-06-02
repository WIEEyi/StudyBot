"""
JWT 认证 + 密码哈希

安全模块提供两个核心能力:
1. 密码哈希与验证 (bcrypt)
2. JWT 令牌签发与解析 (HMAC-SHA256)

JWT 双令牌设计:
- access_token:  短期（15-30 分钟），用于每次 API 请求
- refresh_token: 长期（7 天），用于免登录刷新 access_token
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
import bcrypt
from jose import jwt, JWTError
from app.config import get_settings

settings = get_settings()


def hash_password(password: str) -> str:
    """对明文密码进行 bcrypt 哈希

    哈希结果示例: $2b$12$LJ3m... (60 字符)
    同一密码每次调用结果不同（随机盐值）
    """
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码是否与哈希值匹配"""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


# --- JWT ---

def create_access_token(user_id: int) -> str:
    """签发短期 access_token

    payload 包含:
    - sub: 用户 ID（JWT 标准字段 subject）
    - type: "access"（区分 token 类型，防止 access token 当 refresh token 用）
    - exp: 过期时间戳
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "type": "access",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    """签发长期 refresh_token"""
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """解析并验证 JWT token

    返回 payload dict，包含 sub/type/exp/iat。
    如果 token 过期、签名错误、格式不对，返回 None。
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError:
        return None
