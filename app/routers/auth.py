"""认证路由：企业注册、登录、当前身份。

注册即「创建租户 + 首个 owner 用户」；后续成员由 owner 邀请（见 tenants 路由）。
"""

from __future__ import annotations

import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.db import get_session
from app.deps import AuthContext, enforce_rate_limit, get_auth_context
from app.models import UserRole
from app.schemas import LoginRequest, RegisterRequest, TokenResponse
from app.security import create_access_token, hash_password, verify_password
from app.settings import get_settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _slugify(name: str) -> str:
    """企业名 → slug；非字母数字转 '-'，兜底随机串。"""
    s = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return s or f"tenant-{uuid.uuid4().hex[:8]}"


async def _unique_slug(session: AsyncSession, base: str) -> str:
    """保证 slug 唯一：冲突时追加短随机后缀。"""
    slug = base
    for _ in range(5):
        exists = (await session.execute(
            select(models.Tenant.id).where(models.Tenant.slug == slug)
        )).scalar_one_or_none()
        if exists is None:
            return slug
        slug = f"{base}-{uuid.uuid4().hex[:6]}"
    return f"{base}-{uuid.uuid4().hex[:10]}"


def _token_response(user: models.User, tenant: models.Tenant) -> TokenResponse:
    settings = get_settings()
    token = create_access_token(user_id=user.id, tenant_id=tenant.id, role=user.role)
    return TokenResponse(
        access_token=token,
        expires_in=settings.jwt_expire_minutes * 60,
        user_id=user.id,
        tenant_id=tenant.id,
        tenant_name=tenant.name,
        email=user.email,
        role=user.role,
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, session: AsyncSession = Depends(get_session)) -> TokenResponse:
    """注册企业 + 首个管理员账号。"""
    slug = await _unique_slug(session, _slugify(payload.tenant_name))

    tenant = models.Tenant(name=payload.tenant_name.strip(), slug=slug)
    session.add(tenant)
    await session.flush()   # 拿到 tenant.id

    user = models.User(
        tenant_id=tenant.id,
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
        role=UserRole.OWNER,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    await session.refresh(tenant)

    return _token_response(user, tenant)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, session: AsyncSession = Depends(get_session)) -> TokenResponse:
    """登录。邮箱在租户内唯一，这里按邮箱全局查（同邮箱多租户场景可用子域/邀请链接区分）。"""
    stmt = select(models.User).where(models.User.email == payload.email.lower())
    users = (await session.execute(stmt)).scalars().all()
    if not users:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="邮箱或密码错误")

    for user in users:
        if user.is_active and verify_password(payload.password, user.hashed_password):
            tenant = await session.get(models.Tenant, user.tenant_id)
            if tenant is None or not tenant.is_active:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="租户已停用")
            return _token_response(user, tenant)

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="邮箱或密码错误")


@router.get("/me", response_model=TokenResponse)
async def me(ctx: AuthContext = Depends(enforce_rate_limit)) -> TokenResponse:
    """当前登录身份（前端刷新页面时校验登录态用）。"""
    return _token_response(ctx.user, ctx.tenant)
