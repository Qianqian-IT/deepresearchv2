"""Researcher：ReAct 循环的"决策提供者"（think / observe）。

ReAct 的循环编排（think→act→observe→think...）由 LangGraph 状态图负责
（见 graph.py），本类只提供每一步的具体逻辑：

  think   看全部子问题 + 已接受的发现，决定这一轮搜什么（或收工）
  observe 筛选本次检索结果：有价值的保留（引用原文），没价值的丢弃

调研产出 = 检索回来的 SearchResult + observe 筛选保留的 Note。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .llm import LLMClient
from .planner import ResearchPlan
from .tools import TIER_LABEL, SearchResult


@dataclass
class Note:
    """一次 observe 筛选保留的有价值信息。"""
    fact: str
    sources: list[str] = field(default_factory=list)   # 来源 URL 列表
    query: str = ""                                    # 由哪条搜索得到
    target_q: str = ""                                 # 服务于哪个子问题（计划词），覆盖判定/归属用


class Researcher:
    """检索执行者：think / observe 两步的 LLM 逻辑。"""

    def __init__(self, llm: LLMClient, *, verbose: bool = True):
        self.llm = llm
        self.verbose = verbose

    # ---- ReAct 两步 ----

    def think(
        self, goal: str, plan: ResearchPlan,
        notes: list[Note], done_queries: set[str],
    ) -> dict:
        """think：看全局决定本轮 —— 继续搜（出词）或收工。

        返回 {"action": "finish"}，或
        {"action": "search", "query": 搜索词, "target": 子问题序号 1~N}；
        解析失败返回 {}（图节点兜底走未搜计划项）。
        收工与否由 think 判断，但图里有机械闸门兜底：还有子问题没有发现就不许收工。
        """
        covered = {n.target_q for n in notes}
        questions_text = "\n".join(
            f"- {i}. {pq.question or pq.q} ｜ 计划词: {pq.q!r} ｜ "
            f"{'✅ 已有发现' if pq.q in covered else '❌ 还没有发现'}"
            f"{'  [已搜过]' if pq.q in done_queries else ''}"
            for i, pq in enumerate(plan.questions, 1)
        )
        notes_text = "\n".join(
            f"- [{i}] {n.fact}（来源: {', '.join(n.sources[:2]) or '无'}）"
            for i, n in enumerate(notes, 1)
        ) or "（还没有发现）"

        prompt = f"""
你是深度调研的执行者。下面是调研目标拆出的子问题清单，请决定这一轮搜什么。

调研目标：{goal}

子问题清单（每个子问题都必须有发现支撑才能收工）：
{questions_text}

已接受的发现：
{notes_text}

已搜过的关键词：{sorted(done_queries) or "无"}

请严格输出一行，二选一：
- 继续搜索：SEARCH | 子问题序号 | 具体搜索关键词
- 收工：FINISH

规则：
1. 还有 ❌ 的子问题就继续搜，只有全部 ✅ 才输出 FINISH
2. 优先给 ❌ 的子问题出搜索词；词要具体（对象 + 场景/用途 + 时间限定），
   不要和已搜过的关键词重复；同一个子问题要换新角度（数据/案例/对比/最新），
   不要只换说法
3. 搜索词里不要预设调研目标没提到的具体实体（产品名/基准名），命名交给检索发现
4. 子问题序号必须是 1~N 的数字
""".strip()
        resp = self.llm.chat(prompt, hint="researcher_think")
        first_line = (resp or "").strip().splitlines()[0] if resp and resp.strip() else ""
        parts = [p.strip() for p in first_line.split("|")]
        action = parts[0].upper() if parts else ""
        if action == "FINISH":
            return {"action": "finish"}
        if action == "SEARCH" and len(parts) >= 2:
            target = None
            if len(parts) >= 3:
                try:
                    target = int(parts[1])
                except ValueError:
                    target = None
            return {"action": "search", "query": parts[-1], "target": target}
        return {}  # 解析失败：图节点兜底

    def observe(self, query: str, results: list[SearchResult], target_q: str = "") -> list[Note]:
        """observe：筛选本次检索结果 —— 有价值的保留（引用原文），没价值的丢弃。"""
        if not results:
            return []

        results_text = "\n".join(
            f"[{i}] 标题: {r.title}\n    URL: {r.url}\n"
            f"    信源: {TIER_LABEL.get(r.source_tier, '未知')}\n"
            f"    摘要: {(r.snippet or '')[:300]}"
            for i, r in enumerate(results)
        )
        prompt = f"""
你是调研的信息筛选员。下面是一次搜索的结果，判断每条结果有没有保留价值。

搜索词：{query}
本搜索服务于子问题：{target_q or "（未指定）"}

检索结果：
{results_text}

输出规则：
- 有价值的：每行一条，严格格式 关键信息 | 来源序号(逗号分隔，最多3个)
- 没价值的：不输出该行；整批都没有价值：只输出一行 SKIP

判断标准：
1. 有价值 = 信息直接支撑调研目标、内容具体可溯源（数据/事实/结论）、来源可信
2. 关键信息 = 引用原文关键句或客观事实，不要转述发挥、不要加自己的判断
3. 一手/权威信源优先；转载农场的结论除非没有更优信源，否则不要保留
4. 与已输出的信息重复时，保留来源更权威的那条
""".strip()
        resp = self.llm.chat(prompt, hint="researcher_observe")

        notes: list[Note] = []
        for line in (resp or "").splitlines():
            line = line.strip()
            if not line or line.upper() == "SKIP":
                continue
            parts = [p.strip() for p in line.split("|")]
            fact, idxes = parts[0], parts[1] if len(parts) >= 2 else ""
            urls: list[str] = []
            for idx_str in idxes.split(","):
                try:
                    idx = int(idx_str.strip())
                    if 0 <= idx < len(results):
                        urls.append(results[idx].url)
                except ValueError:
                    pass
            if fact:
                notes.append(Note(
                    fact=fact, sources=urls, query=query, target_q=target_q or query,
                ))
        return notes

    # ---- 日志 ----

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(f"[Researcher] {msg}")
