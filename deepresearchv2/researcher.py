
"""Researcher：ReAct 循环的"决策提供者"（think / observe）。

ReAct 的循环编排（think→act→observe→think...）由 LangGraph 状态图负责
（见 graph.py），本类只提供每一步的具体逻辑：

  think   看全部子问题 + 已接受的发现，决定这一轮搜什么（或收工）
  observe 筛选本次检索结果：有价值的保留（引用原文），没价值的丢弃

调研产出 = 检索回来的 SearchResult + observe 筛选保留的 Note。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .llm import LLMClient
from .planner import ResearchPlan
from .tools import TIER_LABEL, SearchResult


@dataclass
class Note:
    """一次 observe 筛选保留的有价值信息。"""
    fact: str
    sources: list[str] = field(default_factory=list)   # 来源 URL 列表
    snippets: list[str] = field(default_factory=list)  # 来源对应的原始摘要（与 sources 一一对应）
    query: str = ""                                    # 由哪条搜索得到
    target_q: str = ""                                 # 服务于哪个子问题（计划词），覆盖判定/归属用


# 垃圾行黑名单：LLM 把 prompt 示例/分隔线/说明文字当输出时，直接过滤
_BAD_FACT_PREFIX = re.compile(
    r"^(?:关键信息|有价值的检索结果|搜索结果|以下|说明|---|#+)\s*"
)
_FACT_NUM_PREFIX = re.compile(r"^\[\d+\]\s*")   # "[1] 残留序号" 前缀
_LIST_PREFIX = re.compile(r"^(?:[-*•]\s|\d+[.)]\s)")  # 行首列表符：- / 1. （要求后接空白，避免误伤 "3.14"、"---"）


def _clean_fact(fact: str) -> str:
    """清理 fact 里的垃圾前缀/残留；清完为空返回空串（调用方丢弃）。"""
    f = _LIST_PREFIX.sub("", fact)
    f = _FACT_NUM_PREFIX.sub("", f)
    f = _BAD_FACT_PREFIX.sub("", f)
    return f.strip()


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

    def observe(
        self, query: str, results: list[SearchResult],
        target_q: str = "", notes: list[Note] | None = None,
    ) -> list[Note]:
        """observe：筛选本次检索结果 —— 提炼有价值的要点，丢弃没价值的。

        输出是"提炼式要点"而非原文照抄：一句话说清 主体 + 事实 + 数据，
        每条必须挂真实存在的来源序号；已有发现（notes）展示给 LLM 避免
        重复归纳，解析层再做精确匹配兜底。
        """
        if not results:
            return []
        notes = notes or []

        notes_text = "\n".join(f"- {n.fact}" for n in notes) or "（还没有发现）"
        results_text = "\n".join(
            f"[{i}] 标题: {r.title}\n    URL: {r.url}\n"
            f"    信源: {TIER_LABEL.get(r.source_tier, '未知')}\n"
            f"    摘要: {(r.snippet or '')[:300]}"
            for i, r in enumerate(results, 1)  # 编号 1 起步，匹配人/LLM 的计数习惯
        )
        prompt = f"""
你是调研的信息筛选员。下面是一次搜索的结果，从中提炼有价值的信息要点。

搜索词：{query}
本搜索服务于子问题：{target_q or "（未指定）"}

已有发现（结果里出现相同信息时跳过，不要重复归纳）：
{notes_text}

检索结果：
{results_text}

输出：每行一条，严格格式：
{{要点}} | {{来源序号}}

要点规范：
- 一句话说清：什么主体 + 什么事实 + 什么数据/指标/时间；没有数据就不写，不要编造
- 直接写主体名（产品/基准/论文/机构），不要用"它/该文/本文"指代
- 不超过 100 字；长句拆短，修饰词全删；要点里不要用 "|" 符号
- 信息必须能直接支撑调研目标，可验证、可溯源；不满足就跳过这一条
- 整批都没有价值：只输出一行 SKIP

来源序号 = 结果列表里的编号（1 起步：第一条是 1，不是 0），必须真实存在
""".strip()
        resp = self.llm.chat(prompt, hint="researcher_observe")

        existing = {n.fact for n in notes}
        new_notes: list[Note] = []
        for line in (resp or "").splitlines():
            note = self._parse_observe_line(line, results, query, target_q)
            if note is None:
                continue
            if note.fact in existing:  # 机械兜底：与已有发现完全相同的丢弃
                continue
            existing.add(note.fact)
            new_notes.append(note)
        return new_notes

    @staticmethod
    def _parse_observe_line(
        line: str, results: list[SearchResult], query: str, target_q: str,
    ) -> Note | None:
        """解析一行 observe 输出；垃圾行 / 无真实来源的行返回 None。

        硬规则：没有 `|` 分隔、或来源序号全部无效的行一律丢弃 ——
        "[1]"、"关键信息"、"---" 这类残留不再可能混进 notes。
        """
        line = line.strip()
        if not line or line.upper().startswith("SKIP"):
            return None
        parts = [p.strip() for p in line.split("|")]
        fact, idxes = parts[0], parts[1] if len(parts) >= 2 else ""
        if not fact or not idxes:
            return None  # 没有来源序号 = 不是合法输出
        fact = _clean_fact(fact)
        if not fact:
            return None
        urls: list[str] = []
        snippets: list[str] = []
        for idx_str in idxes.split(","):
            try:
                idx = int(idx_str.strip()) - 1  # 编号 1 起步，转回 0 基索引
                if 0 <= idx < len(results):
                    urls.append(results[idx].url)
                    snippets.append(results[idx].snippet or "")
            except ValueError:
                pass
        if not urls:
            return None  # 序号全部无效 → 垃圾行
        return Note(
            fact=fact, sources=urls, snippets=snippets,
            query=query, target_q=target_q or query,
        )

    # ---- 日志 ----

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(f"[Researcher] {msg}")
