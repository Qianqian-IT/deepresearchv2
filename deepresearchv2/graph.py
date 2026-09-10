"""LangGraph 编排：把 Planner + Researcher + Analyzer + ReportWriter 的调研流程声明为状态图。

节点（每个节点只做一件事，全部读写共享的 ResearchState）：
  planner → 出研究计划（写 state.plan）
  think   → 看全局决定本轮：出搜索词（写 state.query / target_q）或收工
            —— 唯一的决策者，收工判断 + 机械闸门都在这里
  act     → Tavily 搜索（写 state.results 瞬时、累积 state.all_results）
  observe → 筛选检索结果，保留有价值信息（追加 state.notes）
  analyze → 收工后按子问题分析全部 findings（两段式：先筛相关，再深度分析）
  report  → 消费 state.analysis，生成最终 markdown 调研报告（写 state.report）

边：
  planner → think →（条件边）→ act / analyze
  act → observe → think（回 think 判断下一轮）
  analyze → report → END

think 是唯一决策者，输出 SEARCH | 子问题序号 | 词 或 FINISH；
两个机械闸门兜底（图级路由，零 LLM 成本）：
  1. FINISH 但还有子问题没有发现支撑（且预算有剩余）→ 不许收工，机械补搜
  2. 预算上限 MAX_REACT_STEPS 到顶强制收工
覆盖判定（covered / gaps）全部机械计算：子问题计划词 q 是否出现在
notes 的 target_q 里（think 出词时声明本轮服务哪个子问题）。

产出 = state.all_results + state.notes + state.gaps + state.analysis + state.report。
"""

from __future__ import annotations

import json
import operator
from typing import Annotated, Any, Callable, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from . import config
from .analyzer import Analyzer
from .llm import LLMClient
from .planner import Planner, ResearchPlan
from .report_writer import ReportWriter
from .researcher import Note, Researcher
from .tools import SearchResult, SearchTool


# ============================================================
# 共享状态
# ============================================================

class ResearchState(TypedDict):
    """流经所有节点的共享状态。"""
    goal: str
    plan: ResearchPlan | None            # planner 节点的产物
    query: str                           # think 决议出的下一条搜索词（空串 = 收工）
    target_q: str                        # 本轮搜索服务于哪个子问题（计划词），归属/覆盖判定用
    done: bool                           # True 表示收工，路由到 END
    results: list[SearchResult]          # 最近一次 act 的产物，observe 消费（瞬时）
    all_results: Annotated[list[SearchResult], operator.add]  # 全部检索结果（产出）
    notes: Annotated[list[Note], operator.add]                # 筛选保留的有价值信息（产出）
    observations: Annotated[list[dict], operator.add]         # 每次 observe 的完整记录（产出）
                                                              # 每条 = {"query": 搜索词, "notes": [Note...]}，
                                                              # 按执行顺序累积，一次不丢
    done_queries: list[str]              # 已搜过的关键词
    searches: int                        # 已搜索次数
    steps: int                           # think 执行次数
    covered: bool                        # 机械判定：所有子问题都有发现支撑
    gaps: list[dict]                     # 机械生成：没有发现的子问题（产出）
    analysis: dict[str, dict]            # analyze 节点产物：{搜索词: AnalysisResult}
    report: str                          # report 节点产物：最终 markdown 调研报告


def _gaps_of(uncovered: list) -> list[dict]:
    """把无发现的子问题转成报告用的缺口列表。"""
    return [
        {"question": pq.question, "why": "该子问题还没有任何发现支撑"}
        for pq in uncovered
    ]


# ============================================================
# 节点
# ============================================================

def _planner_node(planner: Planner, log) -> "callable":
    def node(state: ResearchState) -> dict:
        plan = planner.plan(state["goal"])
        log(f"📋 研究计划（主题：{plan.topic}）", stage="planner")
        for i, q in enumerate(plan.questions, 1):
            log(f"   {i}. 子问题: {q.question}  q={q.q!r}", stage="planner")
        log(
            "研究计划已生成",
            stage="planner",
            payload={
                "topic": plan.topic,
                "questions": [
                    {"question": q.question, "q": q.q} for q in plan.questions
                ],
            },
        )
        return {"plan": plan}
    return node


def _think_node(researcher: Researcher, log) -> "callable":
    def node(state: ResearchState) -> dict:
        """决定本轮：出搜索词或收工；两个机械闸门兜底（防偷懒、防超预算）。"""
        plan = state["plan"]
        done = set(state["done_queries"])
        steps = state["steps"] + 1
        covered_q = {n.target_q for n in state["notes"]}
        uncovered = [pq for pq in plan.questions if pq.q not in covered_q]

        # 闸门 2：预算兜底，到步数上限强制收工
        if steps > config.MAX_REACT_STEPS:
            log(f"[think] 达到最大步数 {config.MAX_REACT_STEPS}，强制收工。", stage="think")
            return {
                "steps": steps, "query": "", "done": True,
                "covered": not uncovered, "gaps": _gaps_of(uncovered),
            }

        decision = researcher.think(state["goal"], plan, state["notes"], done)
        action = decision.get("action", "")

        if action == "finish":
            # 闸门 1：还有子问题没有发现且预算有剩余 → 不许收工，机械补搜它的计划词
            fill = next((pq for pq in uncovered if pq.q not in done), None)
            if fill:
                log(f"[think] FINISH 被闸门拦截（子问题还缺发现），机械补搜 {fill.q!r}", stage="think")
                return {
                    "steps": steps, "query": fill.q, "target_q": fill.q,
                    "done": False, "gaps": _gaps_of(uncovered),
                }
            if uncovered:
                log(f"[think] 无可搜索项（{len(uncovered)} 个子问题已尽力），收工。", stage="think")
            else:
                log("[think] ✅ 所有子问题都有发现支撑，收工。", stage="think")
            return {
                "steps": steps, "query": "", "done": True,
                "covered": not uncovered, "gaps": _gaps_of(uncovered),
            }

        # 继续搜索：解析子问题序号 + 搜索词
        query = decision.get("query", "")
        target_q = query  # 没给序号时默认归属到搜索词本身
        target = decision.get("target")
        if isinstance(target, int) and 1 <= target <= len(plan.questions):
            target_q = plan.questions[target - 1].q
        if not query or query in done:
            # think 空转（解析失败 / 重复词）：兜底走还没搜过的计划项
            pending = [pq for pq in plan.questions if pq.q not in done]
            if not pending:
                log("[think] 无可搜索项，收工。", stage="think")
                return {
                    "steps": steps, "query": "", "done": True,
                    "covered": not uncovered, "gaps": _gaps_of(uncovered),
                }
            pq = pending[0]
            query, target_q = pq.q, pq.q
            log(f"[think] think 空转，兜底跑计划项 {query!r}", stage="think")
        else:
            log(f"[think] → 搜索 {query!r}（服务子问题 {target_q!r}）", stage="think")
        return {"steps": steps, "query": query, "target_q": target_q, "done": False}
    return node


def _act_node(search_tool: SearchTool, log) -> "callable":
    def node(state: ResearchState) -> dict:
        query = state["query"]
        # 用本轮目标子问题的权威域名做白名单；全部建议域名交给信源打分
        plan = state["plan"]
        domains: list[str] = []
        topic_domains: set[str] = set()
        for pq in plan.questions:
            topic_domains.update(pq.domains)
            if pq.q == state.get("target_q", ""):
                domains = pq.domains
        results = search_tool.search(
            query, include_domains=domains or None, topic_domains=topic_domains,
        )
        if not results and domains:
            # 白名单建议不准（空结果）→ 降级为不限域名重搜，保底不丢
            log("[act] 权威白名单无结果，降级为不限域名重搜", stage="act")
            results = search_tool.search(query, topic_domains=topic_domains)
        log(f"[act] Tavily 返回 {len(results)} 条（{query!r}）", stage="act")
        if results:
            tiers = [r.source_tier for r in results]
            log(
                f"[act] 信源分层: 权威 {tiers.count(1)} 条 / "
                f"普通 {tiers.count(2)} 条 / 农场 {tiers.count(3)} 条",
                stage="act",
                payload={
                    "query": query,
                    "count": len(results),
                    "tier1": tiers.count(1),
                    "tier2": tiers.count(2),
                    "tier3": tiers.count(3),
                },
            )
        return {
            "results": results,                     # observe 消费（瞬时）
            "all_results": results,                 # 累积为产出
            "searches": state["searches"] + 1,
            "done_queries": state["done_queries"] + [query],
        }
    return node


ProgressFn = Callable[[dict], None]
FindingsSink = Callable[[dict], None]


class ResearchAborted(Exception):
    """由进度回调抛出以中止调研（服务层用于「用户取消任务」）。

    只有这个异常会穿透 `_Emitter` 的保护；其它异常一律吞掉，
    保证"进度通道出问题不影响调研主流程"。
    """


class _Emitter:
    """节点输出的双通道出口：本地日志 + 外部进度回调。

    服务化后 `progress` 由 worker 注入（写 Redis pub/sub + task_events 表）；
    CLI 场景不传，退化为纯 print，行为与改造前一致。
    """

    def __init__(self, verbose: bool, progress: ProgressFn | None = None):
        self.verbose = verbose
        self.progress = progress

    def __call__(
        self, message: str, *, stage: str = "", level: str = "info",
        payload: dict | None = None,
    ) -> None:
        if self.verbose:
            print(message)
        if self.progress:
            try:
                self.progress({
                    "stage": stage, "level": level,
                    "message": message, "payload": payload,
                })
            except ResearchAborted:
                raise
            except Exception:   # noqa: BLE001 - 进度回调失败绝不能打断调研
                pass


def _build_findings_record(
    query: str, notes: list[Note], results: list[SearchResult], target_q: str = "",
) -> dict:
    """把一次 observe 的保留发现组装成一条可落库/落盘的记录。"""
    url2res = {r.url: r for r in results}
    note_records = []
    for n in notes:
        sources_detail = []
        for i, url in enumerate(n.sources):
            r = url2res.get(url)
            if r:
                snippet = (n.snippets[i] if i < len(n.snippets) else r.snippet or "")
                snippet = snippet.replace("\n", " ")
                sources_detail.append({
                    "url": url,
                    "title": r.title,
                    "source_tier": r.source_tier,
                    "snippet": snippet,
                })
            else:
                sources_detail.append({"url": url})
        note_records.append({
            "fact": n.fact,
            "query": n.query,
            "target_q": n.target_q,
            "sources": sources_detail,
        })
    return {"query": query, "target_q": target_q or None, "notes": note_records}


def _local_findings_jsonl_sink(record: dict) -> None:
    """默认 sink：追加到 CWD 下 findings/research-findings.jsonl（CLI 兼容行为）。

    服务层会注入按 task_id 隔离的 sink，避免多副本/多任务互相串写。
    """
    if not record.get("notes"):
        return
    from pathlib import Path

    path = Path("findings") / "research-findings.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _observe_node(researcher: Researcher, log, findings_sink: FindingsSink) -> "callable":
    def node(state: ResearchState) -> dict:
        new_notes = researcher.observe(
            state["query"], state["results"], state.get("target_q", ""),
            state["notes"],  # 已有发现：observe 里用于跨轮去重
        )
        for n in new_notes:
            log(f"[observe] 保留: {n.fact[:60]}", stage="observe", payload={"fact": n.fact})
        if not new_notes:
            log("[observe] 本轮无有价值信息，全部过滤", stage="observe")
        # 筛选保留的发现经 sink 落库/落盘（按任务隔离由调用方决定）
        findings_sink(_build_findings_record(
            state["query"], new_notes, state["results"], state.get("target_q", ""),
        ))
        # 每次 observe 的完整记录都进 state.observations，落盘时一条不丢
        record = {"query": state["query"], "notes": new_notes}
        return {"notes": new_notes, "observations": [record]}
    return node


def _analyze_node(analyzer: Analyzer, log) -> "callable":
    def node(state: ResearchState) -> dict:
        """收工后：对每个子问题的发现做两段式深度分析。"""
        plan = state["plan"]
        notes = state["notes"]
        if not notes:
            log("[analyze] 无发现，跳过分析", stage="analyze")
            return {"analysis": {}}

        log(f"[analyze] 开始分析 {len(plan.questions)} 个子问题（{len(notes)} 条发现）...", stage="analyze")
        results = analyzer.analyze(state["goal"], plan, notes)

        # 转成可序列化 dict 存进 state
        serialized: dict[str, dict] = {}
        for q_key, ar in results.items():
            serialized[q_key] = {
                "sub_question": ar.sub_question,
                "search_term": ar.search_term,
                "relevant_facts": ar.relevant_facts,
                "irrelevant_facts": ar.irrelevant_facts,
                "merged_insights": ar.merged_insights,
                "conflicts": ar.conflicts,
                "supports_each_other": ar.supports_each_other,
                "direct_evidence": ar.direct_evidence,
                "inferred_analysis": ar.inferred_analysis,
                "unsupported": ar.unsupported,
                "missing_info": ar.missing_info,
            }
            rel = len(ar.relevant_facts)
            total = rel + len(ar.irrelevant_facts)
            log(
                f"[analyze] {ar.search_term}: "
                f"{rel}/{total} 相关, {len(ar.merged_insights)} 洞察, "
                f"{len(ar.conflicts)} 冲突, {len(ar.missing_info)} 缺口",
                stage="analyze",
                payload={
                    "search_term": ar.search_term,
                    "relevant": rel,
                    "total": total,
                    "insights": len(ar.merged_insights),
                    "conflicts": len(ar.conflicts),
                    "gaps": len(ar.missing_info),
                },
            )

        log("分析完成", stage="analyze", payload={"sub_questions": len(serialized)})
        return {"analysis": serialized}
    return node


def _report_node(writer: ReportWriter, log) -> "callable":
    def node(state: ResearchState) -> dict:
        """消费 state.analysis + state.plan + state.goal，生成最终报告。"""
        analysis = state.get("analysis", {})
        if not analysis:
            log("[report] 无分析结果，跳过报告生成", stage="report")
            return {"report": writer._empty_report(state["goal"])}

        plan_raw = state["plan"]
        # ResearchPlan → dict
        plan_dict = {
            "topic": plan_raw.topic if hasattr(plan_raw, "topic") else "",
            "sub_questions": [
                {"question": pq.question, "q": pq.q}
                for pq in plan_raw.questions
            ] if plan_raw and hasattr(plan_raw, "questions") else [],
        }

        log("[report] 正在生成最终调研报告...", stage="report")
        report_md = writer.write(state["goal"], plan_dict, analysis)
        # 追加附录：分析覆盖度、原始发现
        appendix = _build_appendix(state)
        report_md = report_md.rstrip() + "\n\n" + appendix
        log("[report] 报告生成完成", stage="report", payload={"chars": len(report_md)})
        return {"report": report_md}
    return node


def _build_appendix(state: ResearchState) -> str:
    """构建报告附录：原始发现 + 检索统计 + 覆盖率。"""
    parts: list[str] = []
    notes: list = state.get("notes", [])  # type: ignore[assignment]

    # 检索统计
    parts.append("---\n")
    parts.append("## 附录 A：检索统计\n")
    parts.append(f"- 搜索次数: {state.get('searches', 0)}")
    parts.append(f"- 执行步数: {state.get('steps', 0)}")
    parts.append(f"- 有效发现: {len(notes)} 条")
    parts.append(f"- 覆盖率: {'全部覆盖' if state.get('covered') else '部分覆盖'}\n")

    # 缺口
    gaps = state.get("gaps", [])
    if gaps:
        parts.append("### 数据缺口\n")
        for g in gaps:
            parts.append(f"- **{g.get('question', g)}**: {g.get('why', '')}")
        parts.append("")

    # 全部发现
    if notes:
        parts.append("## 附录 B：全部原始发现\n")
        # 按 target_q 分组
        groups: dict[str, list] = {}
        for n in notes:
            k = getattr(n, "target_q", "") or "(未归类)"
            groups.setdefault(k, []).append(n)
        for tq, ns in groups.items():
            parts.append(f"### {tq}\n")
            for n in ns:
                fact = getattr(n, "fact", "")
                parts.append(f"- {fact}")
            parts.append("")

    return "\n".join(parts)


# ============================================================
# 条件边
# ============================================================

def _route_after_think(state: ResearchState) -> str:
    """think 的条件路由：收工（done）→ analyze，否则 → act 继续搜。"""
    return "analyze" if state["done"] else "act"


# ============================================================
# 组装
# ============================================================

def build_research_graph(
    llm: LLMClient,
    search_tool: SearchTool,
    *,
    planner: Planner | None = None,
    researcher: Researcher | None = None,
    analyzer: Analyzer | None = None,
    report_writer: ReportWriter | None = None,
    verbose: bool = True,
    progress: ProgressFn | None = None,
    findings_sink: FindingsSink | None = None,
) -> CompiledStateGraph:
    """组装并编译完整的调研图：planner → think ↔ (act → observe)，覆盖后 → analyze → report → END。

    扩展点（服务化用，CLI 不传即保持原行为）：
    - progress:       进度回调，收到 {stage, level, message, payload}
    - findings_sink:  发现落库/落盘钩子；默认写 CWD 下 findings/（按任务隔离由调用方注入）
    """
    planner = planner or Planner(llm)
    researcher = researcher or Researcher(llm, verbose=verbose)
    analyzer = analyzer or Analyzer(llm)
    report_writer = report_writer or ReportWriter(llm)
    log = _Emitter(verbose=verbose, progress=progress)
    sink: FindingsSink = findings_sink or _local_findings_jsonl_sink

    g = StateGraph(ResearchState)
    g.add_node("planner", _planner_node(planner, log))
    g.add_node("think", _think_node(researcher, log))
    g.add_node("act", _act_node(search_tool, log))
    g.add_node("observe", _observe_node(researcher, log, sink))
    g.add_node("analyze", _analyze_node(analyzer, log))
    g.add_node("report", _report_node(report_writer, log))

    g.add_edge(START, "planner")
    g.add_edge("planner", "think")
    g.add_conditional_edges("think", _route_after_think, {"act": "act", "analyze": "analyze"})
    g.add_edge("act", "observe")
    g.add_edge("observe", "think")
    g.add_edge("analyze", "report")
    g.add_edge("report", END)

    return g.compile()


def initial_state(goal: str) -> dict:
    """构造初始状态：除了 goal，其余都是空值。"""
    return {
        "goal": goal,
        "plan": None,
        "query": "",
        "target_q": "",
        "done": False,
        "results": [],
        "all_results": [],
        "notes": [],
        "observations": [],
        "done_queries": [],
        "searches": 0,
        "steps": 0,
        "covered": False,
        "gaps": [],
        "analysis": {},
        "report": "",
    }
