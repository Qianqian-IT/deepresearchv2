"""FastAPI 依赖：认证上下文、租户上下文、角色校验、限流。

核心隔离点：`AuthContext` 是唯一可信的租户来源 ——
所有业务查询都必须用 `ctx.tenant_id` 过滤，**绝不接受客户端传入的 tenant_id**。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.db import get_session
from app.models import UserRole
from app.redis_client import hit_rate_limit
from app.security import decode_access_token
from app.settings import get_settings

_bearer = HTTPBearer(auto_error=False)


@dataclass
class AuthContext:
    """一次请求的认证上下文（租户隔离的唯一依据）。"""
    user: models.User
    tenant: models.Tenant

    @property
    def tenant_id(self) -> uuid.UUID:
        return self.tenant.id

    @property
    def user_id(self) -> uuid.UUID:
        return self.user.id

    @property
    def role(self) -> str:
        return self.user.role


async def resolve_auth_context(
    token: str | None, request: Request, session: AsyncSession,
) -> AuthContext:
    """由 token 字符串解析认证上下文（HTTP 与 SSE 复用同一套校验）。"""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少访问令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_access_token(token)
        user_id = uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="访问令牌无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    user = await session.get(models.User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已停用")

    tenant = await session.get(models.Tenant, user.tenant_id)
    if tenant is None or not tenant.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="租户不存在或已停用")

    if payload.get("tid") and payload["tid"] != str(tenant.id):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="访问令牌与租户不匹配")

    request.state.tenant_id = str(tenant.id)
    request.state.user_id = str(user.id)
    return AuthContext(user=user, tenant=tenant)


async def get_auth_context(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
) -> AuthContext:
    """解析 Bearer token → 加载用户与租户（委托给 resolve_auth_context）。

    注意：token 里的 tenant_id 只作快速校验，最终以 DB 中的用户记录为准，
    避免 token 伪造或用户被移除租户后仍可访问。
    """
    return await resolve_auth_context(
        credentials.credentials if credentials else None, request, session,
    )


async def enforce_rate_limit(
    ctx: AuthContext = Depends(get_auth_context),
) -> AuthContext:
    """租户级每分钟限流（Redis 原子计数，跨副本生效）。"""
    settings = get_settings()
    if await hit_rate_limit(ctx.tenant_id, settings.rate_limit_per_minute):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"请求过于频繁，已超过每分钟 {settings.rate_limit_per_minute} 次限制",
        )
    return ctx


async def require_owner(
    ctx: AuthContext = Depends(get_auth_context),
) -> AuthContext:
    """仅租户管理员（owner）可操作：改密钥、加成员等。"""
    if ctx.role != UserRole.OWNER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要租户管理员权限")
    return ctx


async def load_credential(session: AsyncSession, tenant_id: uuid.UUID) -> models.TenantCredential | None:
    """读出租户 BYOK 配置（供路由复用）。"""
    stmt = select(models.TenantCredential).where(models.TenantCredential.tenant_id == tenant_id)
    return (await session.execute(stmt)).scalar_one_or_none()
