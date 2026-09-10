"""租户路由：BYOK 密钥管理、成员管理、配额与用量。

安全要点：密钥**只写不读** —— 读取接口只返回脱敏尾号，明文永不返回。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.db import get_session
from app.deps import AuthContext, enforce_rate_limit, load_credential, require_owner
from app.models import UserRole
from app.redis_client import quota_snapshot
from app.schemas import CredentialOut, CredentialUpsert, QuotaOut, UsageOut
from app.security import encrypt_secret, hash_password, mask_secret
from app.settings import get_settings

router = APIRouter(prefix="/api/tenants", tags=["tenants"])


# ============================================================
# 租户信息
# ============================================================

class TenantOut(BaseModel):
    id: str
    name: str
    slug: str
    plan: str


@router.get("/me", response_model=TenantOut)
async def tenant_me(ctx: AuthContext = Depends(enforce_rate_limit)) -> TenantOut:
    return TenantOut(
        id=str(ctx.tenant.id), name=ctx.tenant.name,
        slug=ctx.tenant.slug, plan=ctx.tenant.plan,
    )


# ============================================================
# BYOK 密钥
# ============================================================

def _to_out(cred: models.TenantCredential | None) -> CredentialOut:
    if cred is None:
        return CredentialOut(
            provider="deepseek", llm_model="", llm_base_url="",
            llm_api_key_hint="", tavily_api_key_hint="",
        )
    return CredentialOut(
        provider=cred.provider,
        llm_model=cred.llm_model,
        llm_base_url=cred.llm_base_url,
        llm_api_key_hint=cred.llm_api_key_hint,
        tavily_api_key_hint=cred.tavily_api_key_hint,
        updated_at=cred.updated_at,
        llm_configured=bool(cred.llm_api_key_enc),
        tavily_configured=bool(cred.tavily_api_key_enc),
    )


@router.get("/credentials", response_model=CredentialOut)
async def get_credentials(
    ctx: AuthContext = Depends(enforce_rate_limit),
    session: AsyncSession = Depends(get_session),
) -> CredentialOut:
    """查看密钥配置（只有脱敏尾号，无明文）。"""
    return _to_out(await load_credential(session, ctx.tenant_id))


@router.put("/credentials", response_model=CredentialOut)
async def upsert_credentials(
    payload: CredentialUpsert,
    ctx: AuthContext = Depends(require_owner),
    session: AsyncSession = Depends(get_session),
) -> CredentialOut:
    """配置 / 更新 BYOK 密钥（仅 owner）。

    未传的密钥字段表示"保持不变"；传空串等同于不修改；
    传新值则重新加密并更新脱敏尾号。
    """
    cred = await load_credential(session, ctx.tenant_id)
    if cred is None:
        cred = models.TenantCredential(tenant_id=ctx.tenant_id)
        session.add(cred)

    cred.provider = payload.provider
    cred.llm_base_url = payload.llm_base_url.strip()
    cred.llm_model = payload.llm_model.strip()

    if payload.llm_api_key:
        cred.llm_api_key_enc = encrypt_secret(payload.llm_api_key)
        cred.llm_api_key_hint = mask_secret(payload.llm_api_key)
    if payload.tavily_api_key:
        cred.tavily_api_key_enc = encrypt_secret(payload.tavily_api_key)
        cred.tavily_api_key_hint = mask_secret(payload.tavily_api_key)

    await session.commit()
    await session.refresh(cred)
    return _to_out(cred)


@router.delete("/credentials", response_model=CredentialOut, status_code=status.HTTP_200_OK)
async def delete_credentials(
    ctx: AuthContext = Depends(require_owner),
    session: AsyncSession = Depends(get_session),
) -> CredentialOut:
    """清空密钥（清空后无法创建调研任务）。"""
    cred = await load_credential(session, ctx.tenant_id)
    if cred is not None:
        cred.llm_api_key_enc = ""
        cred.llm_api_key_hint = ""
        cred.tavily_api_key_enc = ""
        cred.tavily_api_key_hint = ""
        await session.commit()
        await session.refresh(cred)
    return _to_out(cred)


# ============================================================
# 配额与用量
# ============================================================

@router.get("/quota", response_model=QuotaOut)
async def get_quota(ctx: AuthContext = Depends(enforce_rate_limit)) -> QuotaOut:
    settings = get_settings()
    snap = await quota_snapshot(
        ctx.tenant_id,
        settings.max_concurrent_tasks_per_tenant,
        settings.max_tasks_per_day_per_tenant,
    )
    return QuotaOut(**snap)


@router.get("/usage", response_model=UsageOut)
async def get_usage(
    ctx: AuthContext = Depends(enforce_rate_limit),
    session: AsyncSession = Depends(get_session),
) -> UsageOut:
    """租户累计 LLM 用量（计费基础）。"""
    stmt = select(
        func.count(models.LLMUsage.id),
        func.coalesce(func.sum(models.LLMUsage.input_tokens), 0),
        func.coalesce(func.sum(models.LLMUsage.output_tokens), 0),
    ).where(models.LLMUsage.tenant_id == ctx.tenant_id)
    calls, inp, out = (await session.execute(stmt)).one()
    return UsageOut(
        total_calls=int(calls or 0),
        total_input_tokens=int(inp or 0),
        total_output_tokens=int(out or 0),
        total_tokens=int(inp or 0) + int(out or 0),
    )


# ============================================================
# 成员管理
# ============================================================

class MemberCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    role: str = Field(default=UserRole.MEMBER.value, pattern="^(owner|member)$")


class MemberOut(BaseModel):
    id: str
    email: str
    role: str
    is_active: bool


@router.get("/members", response_model=list[MemberOut])
async def list_members(
    ctx: AuthContext = Depends(enforce_rate_limit),
    session: AsyncSession = Depends(get_session),
) -> list[MemberOut]:
    stmt = select(models.User).where(models.User.tenant_id == ctx.tenant_id)
    users = (await session.execute(stmt)).scalars().all()
    return [
        MemberOut(id=str(u.id), email=u.email, role=u.role, is_active=u.is_active)
        for u in users
    ]


@router.post("/members", response_model=MemberOut, status_code=status.HTTP_201_CREATED)
async def create_member(
    payload: MemberCreate,
    ctx: AuthContext = Depends(require_owner),
    session: AsyncSession = Depends(get_session),
) -> MemberOut:
    """新增成员（仅 owner）。email 在租户内唯一。"""
    exists = (await session.execute(
        select(models.User.id).where(
            models.User.tenant_id == ctx.tenant_id,
            models.User.email == payload.email.lower(),
        )
    )).scalar_one_or_none()
    if exists is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该邮箱已存在于本租户")

    user = models.User(
        tenant_id=ctx.tenant_id,
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
        role=payload.role,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return MemberOut(id=str(user.id), email=user.email, role=user.role, is_active=user.is_active)
