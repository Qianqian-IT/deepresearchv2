"""请求 / 响应模型（Pydantic v2）。

安全约定：任何响应模型都**不得包含密钥明文字段**，只允许出现 *_hint（脱敏尾号）。
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


# ============================================================
# 认证
# ============================================================

class RegisterRequest(BaseModel):
    tenant_name: str = Field(..., min_length=2, max_length=200, description="企业名称")
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    tenant_name: str
    email: str
    role: str


# ============================================================
# 租户与 BYOK
# ============================================================

class CredentialUpsert(BaseModel):
    """配置 BYOK 密钥。密钥字段可选：不传表示"保持原值不变"。"""
    provider: str = Field(default="deepseek", pattern="^(deepseek|openai)$")
    llm_api_key: str | None = Field(default=None, max_length=400)
    llm_base_url: str = Field(default="", max_length=500, description="可填企业内网网关地址")
    llm_model: str = Field(default="", max_length=120)
    tavily_api_key: str | None = Field(default=None, max_length=400)

    @field_validator("llm_api_key", "tavily_api_key")
    @classmethod
    def _strip(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v or None   # 空串视为"不修改"


class CredentialOut(BaseModel):
    """密钥配置回显：只有脱敏尾号，永远没有明文。"""
    model_config = ConfigDict(from_attributes=True)

    provider: str
    llm_model: str
    llm_base_url: str
    llm_api_key_hint: str
    tavily_api_key_hint: str
    updated_at: datetime | None = None
    llm_configured: bool = False
    tavily_configured: bool = False


class QuotaOut(BaseModel):
    concurrent_running: int
    concurrent_limit: int
    tasks_today: int
    daily_limit: int


class UsageOut(BaseModel):
    total_calls: int
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int


# ============================================================
# 任务
# ============================================================

class TaskCreate(BaseModel):
    goal: str = Field(..., min_length=4, max_length=4000)
    skip_clarify: bool = Field(default=False, description="跳过澄清，直接开跑")


class ClarifyAnswer(BaseModel):
    question: str
    answer: str = ""


class ClarifySubmit(BaseModel):
    answers: list[ClarifyAnswer] = Field(default_factory=list)


class TaskSummary(BaseModel):
    """任务列表项（不含报告正文，避免列表接口过大）。"""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    goal: str
    status: str
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    stats: dict[str, Any] | None = None
    error: str = ""
    has_report: bool = False


class TaskDetail(TaskSummary):
    """任务详情（含澄清问答与计划，不含报告正文）。"""
    enriched_goal: str = ""
    clarify_questions: list[dict[str, Any]] | None = None
    clarify_answers: list[dict[str, Any]] | None = None
    plan_json: dict[str, Any] | None = None


class ReportOut(BaseModel):
    task_id: uuid.UUID
    goal: str
    markdown: str
    observations: dict[str, Any] | None = None


class TaskEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    seq: int
    stage: str
    level: str
    message: str
    payload: dict[str, Any] | None = None
    created_at: datetime
