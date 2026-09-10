"""任务生命周期服务：创建 / 澄清 / 入队 / 取消 / 状态流转。

状态机：
    pending_clarify --(提交澄清答案)--> queued --> running --> succeeded
    pending_clarify / queued / running --(用户取消)--> cancelled
    任意状态 --(异常)--> failed
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.deps import load_credential
from app.models import TaskStatus, TERMINAL_STATUSES
from app.redis_client import acq_concurrency, acq_daily, release_concurrency
from app.security import decrypt_secret
from app.settings import get_settings


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ============================================================
# 凭据
# ============================================================

async def require_credentials(session: AsyncSession, tenant_id: uuid.UUID) -> models.TenantCredential:
    """任务创建前必须已配置 BYOK；缺哪个就明确告知缺哪个。"""
    cred = await load_credential(session, tenant_id)
    if cred is None or not cred.llm_api_key_enc or not cred.tavily_api_key_enc:
        missing = []
        if cred is None or not cred.llm_api_key_enc:
            missing.append("模型密钥")
        if cred is None or not cred.tavily_api_key_enc:
            missing.append("搜索密钥（Tavily）")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"尚未配置 BYOK 密钥：{'、'.join(missing)}。请先到「租户设置」填写。",
        )
    return cred


def decrypt_credentials(cred: models.TenantCredential) -> dict:
    """解密 BYOK（只在内存中存在，严禁写日志）。"""
    return {
        "provider": cred.provider or "deepseek",
        "model": cred.llm_model or "",
        "base_url": cred.llm_base_url or "",
        "llm_api_key": decrypt_secret(cred.llm_api_key_enc),
        "tavily_api_key": decrypt_secret(cred.tavily_api_key_enc),
    }


# ============================================================
# 配额
# ============================================================

async def acquire_quota(tenant_id: uuid.UUID) -> None:
    """入队前占配额：并发槽 + 当日额度。任一超限即拒绝（429）。"""
    settings = get_settings()
    if not await acq_daily(tenant_id, settings.max_tasks_per_day_per_tenant):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"今日任务数已达上限（{settings.max_tasks_per_day_per_tenant}），请明日再试",
        )
    if not await acq_concurrency(tenant_id, settings.max_concurrent_tasks_per_tenant):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"同时运行的任务已达上限（{settings.max_concurrent_tasks_per_tenant}），请等待现有任务完成",
        )


async def release_quota(tenant_id: uuid.UUID) -> None:
    await release_concurrency(tenant_id)


# ============================================================
# 创建 / 澄清
# ============================================================

async def create_task(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    goal: str,
    skip_clarify: bool,
) -> models.Task:
    """创建任务。

    - skip_clarify=True：直接 QUEUED 并入队
    - 否则调 Clarifier.analyze 判断信息是否足够：
        · 无问题 → QUEUED 并入队
        · 有问题 → PENDING_CLARIFY，等前端提交答案
    """
    from deepresearchv2 import Clarifier
    from deepresearchv2.llm import LLMClient

    cred = await require_credentials(session, tenant_id)
    creds = decrypt_credentials(cred)

    task = models.Task(
        tenant_id=tenant_id,
        created_by=user_id,
        goal=goal.strip(),
        status=TaskStatus.PENDING_CLARIFY,
    )
    session.add(task)
    await session.flush()

    if skip_clarify:
        task.status = TaskStatus.QUEUED
        await session.commit()
        await _enqueue_and_mark(session, task)
        return task

    # 澄清判定（一次轻量 LLM 调用；失败则降级为"直接开跑"，不阻塞用户）
    questions: list[dict] = []
    try:
        llm = LLMClient(
            provider=creds["provider"],
            model=creds["model"] or None,
            api_key=creds["llm_api_key"],
            base_url=creds["base_url"] or None,
        )
        questions = Clarifier(llm).analyze(task.goal)
        await record_llm_usage(session, tenant_id, task.id, llm, creds)
    except Exception as e:   # noqa: BLE001 - 澄清是增强项，失败不应阻断建任务
        questions = []
        task.error = f"澄清阶段调用失败，已直接开跑：{e}"

    if questions:
        task.clarify_questions = questions
        task.status = TaskStatus.PENDING_CLARIFY
        await session.commit()
        return task

    task.status = TaskStatus.QUEUED
    await session.commit()
    await _enqueue_and_mark(session, task)
    return task


async def submit_clarify(
    session: AsyncSession,
    task: models.Task,
    answers: list[dict],
) -> models.Task:
    """提交澄清答案 → 拼进 goal → 入队运行。"""
    from deepresearchv2 import Clarifier

    if task.status != TaskStatus.PENDING_CLARIFY:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"任务当前状态为 {task.status}，不接受澄清答案",
        )

    questions = task.clarify_questions or []
    task.clarify_answers = answers
    task.enriched_goal = Clarifier.enrich_with_answers(task.goal, questions, answers)
    task.status = TaskStatus.QUEUED
    await session.commit()
    await _enqueue_and_mark(session, task)
    return task


# ============================================================
# 入队 / 取消
# ============================================================

async def _enqueue_and_mark(session: AsyncSession, task: models.Task) -> None:
    """入队并把 Celery 任务 id 回写，便于后续 revoke。"""
    task.celery_task_id = await enqueue_research(task)
    await session.commit()


async def enqueue_research(task: models.Task) -> str:
    """占配额后投递 Celery 任务（延迟 import，避免 API 进程强依赖 celery）。"""
    await acquire_quota(task.tenant_id)
    try:
        from app.workers.research_tasks import run_research_task
        async_result = run_research_task.delay(str(task.id))
        return async_result.id
    except Exception as e:   # noqa: BLE001 - 入队失败必须归还配额，避免槽位泄漏
        await release_quota(task.tenant_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"任务队列不可用：{e}",
        ) from e


async def cancel_task(session: AsyncSession, task: models.Task) -> models.Task:
    """取消任务。

    - 尚未开始（pending_clarify / queued）：直接置 cancelled 并归还并发槽
    - 运行中：置 cancelled，worker 会在下一个进度事件处自行中止
    """
    if task.status in TERMINAL_STATUSES:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="任务已结束，无法取消")

    was_running = task.status == TaskStatus.RUNNING
    task.status = TaskStatus.CANCELLED
    task.finished_at = _now()
    await session.commit()

    # 未真正开跑的任务，其并发槽由 API 侧占用，需要在这里归还；
    # 运行中的任务由 worker 结束时归还（见 research_tasks）。
    if not was_running:
        await release_quota(task.tenant_id)

    # 尽力通知 Celery 撤销（已开始执行的 revoke 不一定生效，靠上面的状态检查兜底）
    try:
        from app.workers.celery_app import celery_app
        if task.celery_task_id:
            celery_app.control.revoke(task.celery_task_id, terminate=False)
    except Exception:   # noqa: BLE001
        pass
    return task


# ============================================================
# 用量记录
# ============================================================

async def record_llm_usage(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    task_id: uuid.UUID | None,
    llm,
    creds: dict,
) -> None:
    """把 LLMClient 的累计用量明细写入 llm_usage（计费基础）。"""
    summary = llm.usage_summary()
    for call in summary.get("per_call", []):
        session.add(models.LLMUsage(
            tenant_id=tenant_id,
            task_id=task_id,
            hint=call.get("hint", ""),
            provider=creds.get("provider", ""),
            model=llm.model,
            input_tokens=int(call.get("input_tokens", 0)),
            output_tokens=int(call.get("output_tokens", 0)),
            prompt_chars=int(call.get("prompt_chars", 0)),
        ))
    await session.commit()


async def list_tasks(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    status_filter: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[models.Task]:
    """列出本租户任务（强制 tenant_id 过滤）。"""
    stmt = select(models.Task).where(models.Task.tenant_id == tenant_id)
    if status_filter:
        stmt = stmt.where(models.Task.status == status_filter)
    stmt = stmt.order_by(models.Task.created_at.desc()).limit(limit).offset(offset)
    return list((await session.execute(stmt)).scalars().all())


async def get_task(
    session: AsyncSession, tenant_id: uuid.UUID, task_id: uuid.UUID,
) -> models.Task:
    """按租户取任务；不存在或非本租户一律 404（不泄露存在性）。"""
    stmt = select(models.Task).where(
        models.Task.id == task_id,
        models.Task.tenant_id == tenant_id,
    )
    task = (await session.execute(stmt)).scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    return task
