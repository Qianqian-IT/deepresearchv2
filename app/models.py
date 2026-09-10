"""ORM 模型：多租户数据层。

隔离原则：**所有业务表都带 tenant_id**，服务层查询一律经租户上下文过滤，
禁止任何不带 tenant_id 条件的跨租户查询。
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


# ============================================================
# 枚举（以字符串落库，避免 PG 原生 enum 迁移麻烦）
# ============================================================

class UserRole(StrEnum):
    OWNER = "owner"
    MEMBER = "member"


class TaskStatus(StrEnum):
    PENDING_CLARIFY = "pending_clarify"   # 已创建，等待用户回答澄清问题
    QUEUED = "queued"                     # 已入队，等待 worker
    RUNNING = "running"                   # worker 执行中
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


# 终态：不可再流转（用纯字符串集合，避免 enum 的 hash 语义坑）
TERMINAL_STATUSES = {
    TaskStatus.SUCCEEDED.value,
    TaskStatus.FAILED.value,
    TaskStatus.CANCELLED.value,
}


# ============================================================
# 表
# ============================================================

class Tenant(Base):
    """企业租户。"""
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    plan: Mapped[str] = mapped_column(String(50), default="standard", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    users: Mapped[list["User"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    credentials: Mapped["TenantCredential | None"] = relationship(
        back_populates="tenant", cascade="all, delete-orphan", uselist=False,
    )


class User(Base):
    """租户成员。email 在租户内唯一。"""
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_tenant_email", "tenant_id", "email", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default=UserRole.MEMBER, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    tenant: Mapped[Tenant] = relationship(back_populates="users")


class TenantCredential(Base):
    """BYOK：租户自带的模型与搜索密钥。

    安全约束：
    - llm_api_key_enc / tavily_api_key_enc 存 Fernet 密文，任何接口都不回显明文
    - 只在 worker 运行时于内存解密，用后即弃
    """
    __tablename__ = "tenant_credentials"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    provider: Mapped[str] = mapped_column(String(50), default="deepseek", nullable=False)
    llm_model: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    llm_base_url: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    llm_api_key_enc: Mapped[str] = mapped_column(Text, default="", nullable=False)
    llm_api_key_hint: Mapped[str] = mapped_column(String(20), default="", nullable=False)  # 尾号脱敏
    tavily_api_key_enc: Mapped[str] = mapped_column(Text, default="", nullable=False)
    tavily_api_key_hint: Mapped[str] = mapped_column(String(20), default="", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False,
    )

    tenant: Mapped[Tenant] = relationship(back_populates="credentials")


class Task(Base):
    """一次调研任务。"""
    __tablename__ = "tasks"
    __table_args__ = (
        Index("ix_tasks_tenant_status", "tenant_id", "status"),
        Index("ix_tasks_tenant_created", "tenant_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    goal: Mapped[str] = mapped_column(Text, nullable=False)                  # 原始目标
    enriched_goal: Mapped[str] = mapped_column(Text, default="", nullable=False)  # 澄清后的目标

    status: Mapped[str] = mapped_column(
        String(30), default=TaskStatus.PENDING_CLARIFY, nullable=False,
    )
    # 澄清：问题列表 / 用户回答
    clarify_questions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    clarify_answers: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # 产出
    plan_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    report_md: Mapped[str] = mapped_column(Text, default="", nullable=False)
    observations_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    stats: Mapped[dict | None] = mapped_column(JSON, nullable=True)   # searches/steps/notes/covered

    error: Mapped[str] = mapped_column(Text, default="", nullable=False)
    celery_task_id: Mapped[str] = mapped_column(String(120), default="", nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    events: Mapped[list["TaskEvent"]] = relationship(
        back_populates="task", cascade="all, delete-orphan",
    )


class TaskEvent(Base):
    """任务进度事件（SSE 落库备份，刷新页面也能回放）。"""
    __tablename__ = "task_events"
    __table_args__ = (
        Index("ix_task_events_task_seq", "task_id", "seq"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    task_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)      # 任务内递增序号
    stage: Mapped[str] = mapped_column(String(40), default="", nullable=False)  # plan/act/observe/analyze/report
    level: Mapped[str] = mapped_column(String(20), default="info", nullable=False)
    message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    task: Mapped[Task] = relationship(back_populates="events")


class LLMUsage(Base):
    """每次 LLM 调用的用量明细（按租户计量 / 计费基础）。"""
    __tablename__ = "llm_usage"
    __table_args__ = (
        Index("ix_llm_usage_tenant_created", "tenant_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True,
    )
    hint: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    provider: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    model: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    prompt_chars: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
