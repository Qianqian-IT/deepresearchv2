"""安全基元：密码哈希、JWT 签发校验、BYOK 密钥加解密与脱敏。

安全约定：
- 本模块是**唯一**接触密钥明文的地方，且只在内存中短暂存在。
- 对外接口一律只返回 `mask_secret()` 的结果（尾号），明文永不出库、出日志。
"""

from __future__ import annotations

import base64
import hashlib
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from cryptography.fernet import Fernet, InvalidToken

from app.settings import get_settings

# ============================================================
# 密码
# ============================================================

_BCRYPT_MAX_BYTES = 72   # bcrypt 只认前 72 字节


def hash_password(password: str) -> str:
    """bcrypt 加盐哈希。"""
    pw = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """校验密码；哈希损坏等情况一律返回 False，不抛异常。"""
    try:
        pw = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
        return bcrypt.checkpw(pw, hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# ============================================================
# JWT
# ============================================================

def create_access_token(*, user_id: uuid.UUID, tenant_id: uuid.UUID, role: str) -> str:
    """签发访问令牌。payload 里带 tenant_id，服务层据此做隔离。"""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "tid": str(tenant_id),
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.jwt_expire_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """校验并解出 payload；无效/过期抛 jwt.PyJWTError。"""
    settings = get_settings()
    return jwt.decode(
        token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm],
    )


# ============================================================
# BYOK 密钥加解密
# ============================================================

def _fernet() -> Fernet:
    """取加密器：优先用显式配置的 BYOK_ENCRYPTION_KEY，否则从 JWT 密钥派生。

    派生方式：sha256(jwt_secret) 取 32 字节 → url-safe base64，满足 Fernet 要求。
    """
    settings = get_settings()
    key = settings.byok_encryption_key
    if key:
        raw = key.encode("utf-8")
        if len(raw) != 44:
            # 容错：不是标准 Fernet key 就按同一规则派生，保证服务仍可用
            raw = base64.urlsafe_b64encode(hashlib.sha256(raw).digest())
    else:
        secret = settings.jwt_secret_key.encode("utf-8")
        raw = base64.urlsafe_b64encode(hashlib.sha256(secret).digest())
    return Fernet(raw)


def encrypt_secret(plain: str) -> str:
    """加密密钥明文（空串也加密，保持字段非空）。"""
    if plain is None:
        plain = ""
    return _fernet().encrypt(plain.encode("utf-8")).decode("utf-8")


def decrypt_secret(cipher: str) -> str:
    """解密；密文损坏时抛 ValueError（调用方负责转成业务错误）。"""
    if not cipher:
        return ""
    try:
        return _fernet().decrypt(cipher.encode("utf-8")).decode("utf-8")
    except InvalidToken as e:
        raise ValueError(
            "BYOK 密钥解密失败（BYOK_ENCRYPTION_KEY 可能已变更，请重新配置密钥）"
        ) from e


def mask_secret(plain: str) -> str:
    """脱敏：只保留尾号 4 位，其余打码。空值返回空串。"""
    if not plain:
        return ""
    tail = plain[-4:] if len(plain) > 4 else plain
    return f"****{tail}"
