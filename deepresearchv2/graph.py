"""LangGraph 编排：把 Planner + Researcher 的调研流程声明为状态图。

节点（每个节点只做一件事，全部读写共享的 ResearchState）：
  planner → 出研究计划（写 state.plan）
  think   → 看全局决定本轮：出搜索词（写 state.query / target_q）或收工
             —— 唯一的决策者，收工判断 + 机械闸门都在这里
  act     → Tavily 搜索（写 state.results 瞬时、累积 state.all_results）
  observe → 筛选检索结果，保留有价值信息（追加 state.notes）

边：
  planner → think →（条件边）→ act / END
  act → observe → think（回 think 判断下一轮）

think 是唯一决策者，输出 SEARCH | 子问题序号 | 词 或 FINISH；
两个机械闸门兜底（图级路由，零 LLM 成本）：
  1. FINISH 但还有子问题没有发现支撑（且预算有剩余）→ 不许收工，机械补搜
  2. 预算上限 MAX_REACT_STEPS 到顶强制收工
覆盖判定（covered / gaps）全部机械计算：子问题计划词 q 是否出现在
notes 的 target_q 里（think 出词时声明本轮服务哪个子问题）。

产出 = state.all_results（检索结果）+ state.notes（筛选保留的有价值信息）+ state.gaps。
"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from . import config
from .llm import LLMClient
from .planner import Planner, ResearchPlan
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
        log(f"📋 研究计划（主题：{plan.topic}）")
        for i, q in enumerate(plan.questions, 1):
            log(f"   {i}. 子问题: {q.question}  q={q.q!r}")
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
            log(f"[think] 达到最大步数 {config.MAX_REACT_STEPS}，强制收工。")
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
                log(f"[think] FINISH 被闸门拦截（子问题还缺发现），机械补搜 {fill.q!r}")
                return {
                    "steps": steps, "query": fill.q, "target_q": fill.q,
                    "done": False, "gaps": _gaps_of(uncovered),
                }
            if uncovered:
                log(f"[think] 无可搜索项（{len(uncovered)} 个子问题已尽力），收工。")
            else:
                log("[think] ✅ 所有子问题都有发现支撑，收工。")
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
                log("[think] 无可搜索项，收工。")
                return {
                    "steps": steps, "query": "", "done": True,
                    "covered": not uncovered, "gaps": _gaps_of(uncovered),
                }
            pq = pending[0]
            query, target_q = pq.q, pq.q
            log(f"[think] think 空转，兜底跑计划项 {query!r}")
        else:
            log(f"[think] → 搜索 {query!r}（服务子问题 {target_q!r}）")
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
            log("[act] 权威白名单无结果，降级为不限域名重搜")
            results = search_tool.search(query, topic_domains=topic_domains)
        log(f"[act] Tavily 返回 {len(results)} 条（{query!r}）")
        if results:
            tiers = [r.source_tier for r in results]
            log(
                f"[act] 信源分层: 权威 {tiers.count(1)} 条 / "
                f"普通 {tiers.count(2)} 条 / 农场 {tiers.count(3)} 条"
            )
        return {
            "results": results,                     # observe 消费（瞬时）
            "all_results": results,                 # 累积为产出
            "searches": state["searches"] + 1,
            "done_queries": state["done_queries"] + [query],
        }
    return node


def _observe_node(researcher: Researcher, log) -> "callable":
    def node(state: ResearchState) -> dict:
        new_notes = researcher.observe(
            state["query"], state["results"], state.get("target_q", ""),
        )
        for n in new_notes:
            log(f"[observe] 保留: {n.fact[:60]}")
        if not new_notes:
            log("[observe] 本轮无有价值信息，全部过滤")
        # 每次 observe 的完整记录都进 state.observations，落盘时一条不丢
        record = {"query": state["query"], "notes": new_notes}
        return {"notes": new_notes, "observations": [record]}
    return node


# ============================================================
# 条件边
# ============================================================

def _route_after_think(state: ResearchState) -> str:
    """think 的条件路由：收工（done）→ END，否则 → act 继续搜。"""
    return END if state["done"] else "act"


# ============================================================
# 组装
# ============================================================

def build_research_graph(
    llm: LLMClient,
    search_tool: SearchTool,
    *,
    planner: Planner | None = None,
    researcher: Researcher | None = None,
    verbose: bool = True,
) -> CompiledStateGraph:
    """组装并编译完整的调研图：planner → think ↔ (act → observe)，覆盖或预算用尽即 END。"""
    planner = planner or Planner(llm)
    researcher = researcher or Researcher(llm, verbose=verbose)
    log = (lambda msg: print(msg)) if verbose else (lambda msg: None)

    g = StateGraph(ResearchState)
    g.add_node("planner", _planner_node(planner, log))
    g.add_node("think", _think_node(researcher, log))
    g.add_node("act", _act_node(search_tool, log))
    g.add_node("observe", _observe_node(researcher, log))

    g.add_edge(START, "planner")
    g.add_edge("planner", "think")
    g.add_conditional_edges("think", _route_after_think, {"act": "act", END: END})
    g.add_edge("act", "observe")
    g.add_edge("observe", "think")

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
    }
