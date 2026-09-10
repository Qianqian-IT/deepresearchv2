"""Celery worker：执行一次调研任务。

设计要点：
- **不长期占用 DB 连接**：事件写入、状态更新都用短生命周期的 session_scope
- 进度双写：Redis pub/sub（实时 SSE）+ task_events 表（刷新后可回放）
- 取消：每个进度事件前检查 DB 状态，取消则抛 ResearchAborted 中止图执行
- 密钥：BYOK 在内存解密后只传给执行器，全程不落日志、不进异常栈
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from celery.exceptions import SoftTimeLimitExceeded
from sqlalchemy import func, select

from app import models
from app.db import session_scope
from app.models import TERMINAL_STATUSES, TaskStatus
from app.redis_client import publish_event, release_concurrency_sync
from app.services.research_runner import execute_research
from app.services.task_service import decrypt_credentials
from app.workers.celery_app import celery_app
from deepresearchv2 import ResearchAborted


def _now() -> datetime:
    return datetime.now(timezone.utc)


class _EventBus:
    """任务事件总线：落库 + 推 Redis + 取消检查（每次用独立 session）。"""

    def __init__(self, task_id: uuid.UUID, tenant_id: uuid.UUID):
        self.task_id = task_id
        self.tenant_id = tenant_id
        self._seq = self._load_max_seq()

    def _load_max_seq(self) -> int:
        with session_scope() as session:
            return int(session.execute(
                select(func.coalesce(func.max(models.TaskEvent.seq), 0))
                .where(models.TaskEvent.task_id == self.task_id)
            ).scalar_one() or 0)

    def is_cancelled(self) -> bool:
        """独立查一次状态（绕过 identity map，确保读到最新值）。"""
        with session_scope() as session:
            status_val = session.execute(
                select(models.Task.status).where(models.Task.id == self.task_id)
            ).scalar_one_or_none()
        return status_val == TaskStatus.CANCELLED

    def emit(self, event: dict, *, check_cancel: bool = True) -> None:
        """记录一条进度事件：先查取消 → 落库 → 推 Redis。"""
        if check_cancel and self.is_cancelled():
            raise ResearchAborted("任务已被用户取消")

        self._seq += 1
        record = {
            "seq": self._seq,
            "stage": event.get("stage", ""),
            "level": event.get("level", "info"),
            "message": event.get("message", ""),
            "payload": event.get("payload"),
        }
        with session_scope() as session:
            session.add(models.TaskEvent(
                task_id=self.task_id,
                tenant_id=self.tenant_id,
                seq=record["seq"],
                stage=record["stage"],
                level=record["level"],
                message=record["message"][:4000],
                payload=record["payload"],
            ))
        publish_event(self.task_id, record)


def _clone_session_from(cred: models.TenantCredential) -> models.TenantCredential:
    """把凭据读出的字段复制成游离对象，避免在长任务里持有 ORM 关联。"""
    detached = models.TenantCredential(
        tenant_id=cred.tenant_id,
        provider=cred.provider,
        llm_model=cred.llm_model,
        llm_base_url=cred.llm_base_url,
        llm_api_key_enc=cred.llm_api_key_enc,
        llm_api_key_hint=cred.llm_api_key_hint,
        tavily_api_key_enc=cred.tavily_api_key_enc,
        tavily_api_key_hint=cred.tavily_api_key_hint,
    )
    return detached


def _persist_usage(session, task: models.Task, usage: dict, provider: str, model: str) -> None:
    """把本次任务的每次 LLM 调用明细写入 llm_usage。"""
    for call in usage.get("per_call", []):
        session.add(models.LLMUsage(
            tenant_id=task.tenant_id,
            task_id=task.id,
            hint=call.get("hint", ""),
            provider=provider,
            model=model,
            input_tokens=int(call.get("input_tokens", 0)),
            output_tokens=int(call.get("output_tokens", 0)),
            prompt_chars=int(call.get("prompt_chars", 0)),
        ))


@celery_app.task(bind=True, name="research.run", max_retries=0)
def run_research_task(self, task_id: str) -> dict:
    """执行一个调研任务（Celery 入口）。"""
    tid = uuid.UUID(task_id)

    # ---- 1) 取任务与凭据（短 session）----
    with session_scope() as session:
        task = session.get(models.Task, tid)
        if task is None:
            return {"ok": False, "error": "task not found"}
        if task.status in TERMINAL_STATUSES:
            return {"ok": True, "skipped": task.status}

        tenant_id = task.tenant_id
        goal = (task.enriched_goal or task.goal).strip()

        cred = session.execute(
            select(models.TenantCredential).where(models.TenantCredential.tenant_id == tenant_id)
        ).scalar_one_or_none()
        if cred is None:
            task.status = TaskStatus.FAILED
            task.error = "租户未配置 BYOK 密钥"
            task.finished_at = _now()
            session.commit()
            release_concurrency_sync(tenant_id)
            return {"ok": False, "error": "no credentials"}
        detached_cred = _clone_session_from(cred)

        task.status = TaskStatus.RUNNING
        task.started_at = _now()
        task.celery_task_id = getattr(self.request, "id", "") or ""
        session.commit()

    try:
        creds = decrypt_credentials(detached_cred)
    except ValueError as e:
        with session_scope() as session:
            t = session.get(models.Task, tid)
            t.status = TaskStatus.FAILED
            t.error = str(e)
            t.finished_at = _now()
        release_concurrency_sync(tenant_id)
        return {"ok": False, "error": str(e)}

    bus = _EventBus(tid, tenant_id)
    bus.emit({"stage": "system", "message": "任务开始执行"})

    def findings_sink(record: dict) -> None:
        """发现落库钩子：按 task_id 隔离，结构化保存（含来源与信源分层）。"""
        notes = record.get("notes") or []
        if not notes:
            return
        bus.emit({
            "stage": "finding",
            "message": f"新增发现 {len(notes)} 条",
            "payload": record,
        }, check_cancel=False)   # 落库优先，取消检查交给下一个进度事件

    try:
        outcome = execute_research(
            goal=goal,
            provider=creds["provider"],
            llm_api_key=creds["llm_api_key"],
            tavily_api_key=creds["tavily_api_key"],
            model=creds["model"],
            base_url=creds["base_url"],
            progress=bus.emit,
            findings_sink=findings_sink,
            should_abort=bus.is_cancelled,
        )
    except ResearchAborted:
        with session_scope() as session:
            t = session.get(models.Task, tid)
            t.status = TaskStatus.CANCELLED
            t.finished_at = _now()
        bus.emit({"stage": "cancelled", "message": "任务已取消"}, check_cancel=False)
        release_concurrency_sync(tenant_id)
        return {"ok": True, "status": "cancelled"}
    except SoftTimeLimitExceeded:
        _fail(tid, "任务执行超时（超过硬性时限），已终止")
        bus.emit({"stage": "error", "level": "error", "message": "任务执行超时"},
                 check_cancel=False)
        release_concurrency_sync(tenant_id)
        return {"ok": False, "error": "timeout"}
    except Exception as e:   # noqa: BLE001 - 任何异常都要落到任务状态，不能静默
        msg = f"{type(e).__name__}: {e}"
        _fail(tid, msg)
        bus.emit({"stage": "error", "level": "error", "message": f"任务失败：{msg}"},
                 check_cancel=False)
        release_concurrency_sync(tenant_id)
        return {"ok": False, "error": msg}

    # ---- 2) 回写结果 ----
    with session_scope() as session:
        t = session.get(models.Task, tid)
        t.report_md = outcome.report_md
        t.plan_json = outcome.plan
        t.observations_json = {
            "observations": outcome.observations,
            "stats": outcome.stats,
        }
        t.stats = outcome.stats
        t.status = TaskStatus.SUCCEEDED
        t.finished_at = _now()
        _persist_usage(session, t, outcome.usage, creds["provider"], creds["model"] or "")
        session.commit()

    bus.emit({"stage": "done", "message": "调研完成"}, check_cancel=False)
    release_concurrency_sync(tenant_id)
    return {"ok": True, "status": "succeeded"}


def _fail(task_id: uuid.UUID, error: str) -> None:
    """把任务标记为失败（截断错误信息，避免污染 DB 与前端）。"""
    with session_scope() as session:
        t = session.get(models.Task, task_id)
        if t is None:
            return
        t.status = TaskStatus.FAILED
        t.error = (error or "")[:2000]
        t.finished_at = _now()
