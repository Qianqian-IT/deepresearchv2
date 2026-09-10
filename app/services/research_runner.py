"""调研执行器：把「一次调研」封装成可被 worker 调用的纯执行函数。

职责边界（刻意保持无 DB 依赖，便于单测）：
- 输入：已解密的目标 + BYOK 凭据 + 进度回调 + 发现落库钩子
- 输出：报告 / 计划 / 观察记录 / 统计 / 用量

DB 读写由 `app/workers/research_tasks.py` 负责（加载任务、解密密钥、回写结果）。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Callable

from deepresearchv2 import SearchTool, build_research_graph, initial_state
from deepresearchv2.graph import FindingsSink, ProgressFn
from deepresearchv2.llm import LLMClient


@dataclass
class ResearchOutcome:
    """一次调研的完整产出。"""
    report_md: str = ""
    plan: dict[str, Any] = field(default_factory=dict)
    observations: list[dict[str, Any]] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)
    usage: dict[str, Any] = field(default_factory=dict)


def _serialize_plan(plan) -> dict[str, Any]:
    if plan is None:
        return {}
    return {
        "topic": getattr(plan, "topic", ""),
        "questions": [
            {"question": pq.question, "q": pq.q, "domains": list(pq.domains)}
            for pq in getattr(plan, "questions", [])
        ],
    }


def _serialize_observations(observations) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for obs in observations or []:
        out.append({
            "query": obs.get("query", ""),
            "notes": [asdict(n) for n in obs.get("notes", [])],
        })
    return out


def execute_research(
    *,
    goal: str,
    provider: str,
    llm_api_key: str,
    tavily_api_key: str,
    model: str = "",
    base_url: str = "",
    progress: ProgressFn | None = None,
    findings_sink: FindingsSink | None = None,
    should_abort: Callable[[], bool] | None = None,
) -> ResearchOutcome:
    """跑完一次完整调研图（同步阻塞，供 Celery worker 调用）。

    Args:
        goal:            已澄清、已拼好【补充说明】的调研目标
        provider:        "deepseek" / "openai"
        llm_api_key:     BYOK 解密后的模型密钥（仅内存中存在）
        tavily_api_key:  BYOK 解密后的搜索密钥
        model / base_url: 可为空，空则用 config 默认（base_url 支持企业内网网关）
        progress:        进度回调（写 Redis/DB）
        findings_sink:   发现落库钩子（按 task_id 隔离）
        should_abort:    返回 True 时中止（用户取消任务；每个进度事件检查一次）
    """
    def _progress(event: dict) -> None:
        # 取消检查：每个进度事件都问一次，让取消能尽快生效
        if should_abort is not None and should_abort():
            from deepresearchv2 import ResearchAborted
            raise ResearchAborted("任务已被用户取消")
        if progress is not None:
            progress(event)

    llm = LLMClient(
        provider=provider,
        model=model or None,
        api_key=llm_api_key,
        base_url=base_url or None,
    )
    search_tool = SearchTool(tavily_api_key=tavily_api_key)

    app = build_research_graph(
        llm,
        search_tool,
        verbose=False,           # 服务层进度走 progress 通道，不打 stdout
        progress=_progress,
        findings_sink=findings_sink,
    )
    final = app.invoke(initial_state(goal))

    return ResearchOutcome(
        report_md=final.get("report", "") or "",
        plan=_serialize_plan(final.get("plan")),
        observations=_serialize_observations(final.get("observations")),
        stats={
            "searches": final.get("searches", 0),
            "steps": final.get("steps", 0),
            "notes": len(final.get("notes", [])),
            "results": len(final.get("all_results", [])),
            "covered": bool(final.get("covered")),
            "gaps": final.get("gaps", []),
        },
        usage=llm.usage_summary(),
    )
