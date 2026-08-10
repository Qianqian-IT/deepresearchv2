"""Analyzer：两段式证据分析器 —— 对 researcher 的 findings 按子问题进行分析。

两段加载策略（控制上下文窗口）：
  Pass 1（过滤）：只传 fact 文本列表，LLM 判断哪些与当前子问题相关
  Pass 2（深度分析）：只对相关发现加载完整来源/摘要，LLM 做结构化分析

分析输出每条子问题一个 AnalysisResult，包含：
  - 相关发现列表
  - 合并/冲突/互补关系
  - 证据支撑的结论
  - 事实 vs 推导 vs 无法判断的区分
  - 现有证据缺口
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .llm import LLMClient

if TYPE_CHECKING:
    from .planner import PlanQuery
    from .researcher import Note


# ============================================================
# 数据结构
# ============================================================

@dataclass
class FindingDetail:
    """一条发现带完整来源信息（Pass 2 用）。"""
    index: int             # 对应 Pass 1 的序号
    fact: str              # 发现文本
    sources: list[dict] = field(default_factory=list)  # {url, title, source_tier, snippet}


@dataclass
class AnalysisResult:
    """一个子问题的分析结果。"""
    sub_question: str                          # 子问题文本
    search_term: str                           # 搜索词
    # 相关性过滤
    relevant_facts: list[str]                  # 判断相关的事实文本
    irrelevant_facts: list[str]                # 判断无关的事实文本
    # 深度分析
    merged_insights: list[str]                 # 合并同类发现后的洞察
    conflicts: list[str]                       # 冲突点
    supports_each_other: list[str]             # 互相支持的发现
    # 结论层级
    direct_evidence: list[str]                 # 证据直接支撑的事实
    inferred_analysis: list[str]               # 基于多证据推导的分析
    unsupported: list[str]                     # 当前证据无法支撑的判断
    # 缺口
    missing_info: list[str]                    # 仍缺少的信息


# ============================================================
# Analyzer
# ============================================================

class Analyzer:
    """两段式证据分析器。

    两个 pass 严格分开：
    1. filter_relevant：只传 fact 文本，不加载来源
    2. deep_analyze：只传相关发现 + 完整来源信息
    """

    def __init__(self, llm: LLMClient):
        self.llm = llm

    # ----------------------------------------------------------
    # 入口：按子问题逐条分析
    # ----------------------------------------------------------

    def analyze(
        self, goal: str, plan: "ResearchPlan", notes: list["Note"],
    ) -> dict[str, AnalysisResult]:
        """对每个子问题执行两段式分析，返回 {搜索词: AnalysisResult}。"""
        by_q = self._group_by_sub_question(plan, notes)
        results: dict[str, AnalysisResult] = {}

        for pq in plan.questions:
            q_notes = by_q.get(pq.q, [])
            if not q_notes:
                # 该子问题没有任何发现
                results[pq.q] = AnalysisResult(
                    sub_question=pq.question or pq.q,
                    search_term=pq.q,
                    missing_info=["该子问题没有任何发现支撑"],
                )
                continue

            # ---- Pass 1：仅传 fact，过滤相关 ----
            relevant, irrelevant = self._filter_relevant(goal, pq, q_notes)
            if not relevant:
                results[pq.q] = AnalysisResult(
                    sub_question=pq.question or pq.q,
                    search_term=pq.q,
                    relevant_facts=[n.fact for n in relevant],
                    irrelevant_facts=[n.fact for n in irrelevant],
                    missing_info=["所有发现均与子问题无关"],
                )
                continue

            # ---- Pass 2：相关发现 + 完整来源 → 深度分析 ----
            with_details = [
                FindingDetail(
                    index=i,
                    fact=n.fact,
                    sources=self._extract_sources(n),
                )
                for i, n in enumerate(relevant)
            ]
            deep_result = self._deep_analyze(goal, pq, with_details)

            results[pq.q] = AnalysisResult(
                sub_question=pq.question or pq.q,
                search_term=pq.q,
                relevant_facts=[n.fact for n in relevant],
                irrelevant_facts=[n.fact for n in irrelevant],
                merged_insights=deep_result.get("merged_insights", []),
                conflicts=deep_result.get("conflicts", []),
                supports_each_other=deep_result.get("supports_each_other", []),
                direct_evidence=deep_result.get("direct_evidence", []),
                inferred_analysis=deep_result.get("inferred_analysis", []),
                unsupported=deep_result.get("unsupported", []),
                missing_info=deep_result.get("missing_info", []),
            )

        return results

    # ----------------------------------------------------------
    # Pass 1：只传 fact，过滤相关
    # ----------------------------------------------------------

    def _filter_relevant(
        self, goal: str, pq: "PlanQuery", notes: list["Note"],
    ) -> tuple[list["Note"], list["Note"]]:
        """Pass 1：只传 fact 编号列表，让 LLM 判断相关性（不传来源/摘要）。

        返回 (relevant, irrelevant) 两个列表。
        """
        if len(notes) <= 5:
            # 发现很少时不用 LLM，全部视为相关
            return notes, []

        facts_list = "\n".join(
            f"[{i}] {n.fact}" for i, n in enumerate(notes)
        )
        prompt = f"""你是一个研究筛选助手。任务：过滤与子问题无关的发现。

调研目标：{goal}
子问题：{pq.question or pq.q}

下面是该子问题的所有发现（每条只给了事实描述，没有来源细节）：

{facts_list}

请判断每条发现是否与当前子问题相关。关联性标准：
- 直接讨论该子问题 → 相关
- 间接涉及，可能作为对比/背景 → 相关
- 与子问题主题无关，或讨论完全不同的对象 → 无关

严格只输出 JSON：
{{"relevant": [0, 2, 5], "irrelevant": [1, 3, 4]}}

序号必须来自上面列表中的 [N]。所有序号必须出现（合起来等于全部）。"""
        resp = self.llm.chat(prompt, hint="analyzer_filter")
        try:
            data = self._parse_json(resp)
            relevant_idx = set(data.get("relevant", []))
            relevant = [notes[i] for i in relevant_idx if 0 <= i < len(notes)]
            seen = set(relevant_idx)
            irrelevant = [notes[i] for i in range(len(notes)) if i not in seen]
            return relevant, irrelevant
        except Exception:
            # 解析失败，全部视为相关，宁可多看不少看
            return notes, []

    # ----------------------------------------------------------
    # Pass 2：相关发现 + 完整来源 → 深度分析
    # ----------------------------------------------------------

    def _deep_analyze(
        self, goal: str, pq: "PlanQuery", findings: list[FindingDetail],
    ) -> dict:
        """Pass 2：传入相关发现及其完整来源，做结构化深度分析。"""
        evidence_blocks = []
        for f in findings:
            block = f"[{f.index}] {f.fact}"
            for s in f.sources:
                tier_label = {1: "权威", 2: "普通", 3: "农场"}.get(
                    s.get("source_tier", 2), "未知"
                )
                block += (
                    f"\n    来源：{s.get('title', '未知标题')} "
                    f"[信源: {tier_label}] ({s.get('url', '')})"
                )
                if s.get("snippet"):
                    block += f"\n    摘要：{s['snippet'][:300]}"
            evidence_blocks.append(block)

        evidence_text = "\n\n".join(evidence_blocks)

        prompt = f"""你是一个严谨的证据分析师。围绕当前子问题，基于提供的发现材料进行分析。

调研目标：{goal}
当前子问题：{pq.question or pq.q}

## 分析材料

{evidence_text}

## 任务

请仔细分析这些材料，输出结构化 JSON：

1. **merged_insights**：将表达相同或相近意思的发现合并成一句洞察。不要复述每一条，而是提炼出综合理解。
2. **conflicts**：找出互相矛盾或抵触的发现。注明矛盾点的具体内容。
3. **supports_each_other**：找出互相支持、从不同角度印证同一件事的发现组。
4. **direct_evidence**：证据直接支撑的事实 —— 多源交叉印证，来源可靠。
5. **inferred_analysis**：基于多个证据推导出的分析 —— 不是找到的直接声明，而是你根据证据归纳出来的。
6. **unsupported**：当前证据无法支撑的判断 —— 没被证据覆盖到的问题面。
7. **missing_info**：你基于现有证据，判断还需要补充什么信息才能回答这个子问题。

## 约束

- 每条都必须有发现支撑，没有证据的不要编造
- 如果确实没有冲突，conflicts 返回空数组，不要硬找
- 注意区分：direct_evidence（材料直接说的）vs inferred_analysis（你推导的）
- unsupported 写"基于现有证据无法判断..."形式的表述
- 不用评价来源好坏，不用复述来源链接

严格只输出 JSON：
{{
  "merged_insights": ["洞察1", "洞察2"],
  "conflicts": ["冲突点描述"],
  "supports_each_other": ["发现X和发现Y都表明..."],
  "direct_evidence": ["证据直接支撑的事实"],
  "inferred_analysis": ["推导出的分析"],
  "unsupported": ["无法判断的内容"],
  "missing_info": ["仍缺少的信息"]
}}"""
        resp = self.llm.chat(prompt, hint="analyzer_deep")
        try:
            return self._parse_json(resp)
        except Exception:
            return {
                "merged_insights": [],
                "conflicts": [],
                "supports_each_other": [],
                "direct_evidence": [],
                "inferred_analysis": [],
                "unsupported": [],
                "missing_info": [f"分析解析失败，原始响应: {resp[:200]}..."],
            }

    # ----------------------------------------------------------
    # 工具方法
    # ----------------------------------------------------------

    def _group_by_sub_question(
        self, plan: "ResearchPlan", notes: list["Note"],
    ) -> dict[str, list["Note"]]:
        """按子问题搜索词分组 notes。"""
        by_q: dict[str, list] = {}
        for n in notes:
            key = n.target_q or n.query
            by_q.setdefault(key, []).append(n)
        return by_q

    def _extract_sources(self, note: "Note") -> list[dict]:
        """从 Note 中提取来源信息列表。"""
        sources = []
        for i, url in enumerate(note.sources):
            snippet = note.snippets[i] if i < len(note.snippets) else ""
            sources.append({
                "url": url,
                "snippet": snippet.replace("\n", " "),
            })
        return sources

    def _parse_json(self, text: str) -> dict:
        """从 LLM 响应中提取 JSON（容错）。"""
        text = text.strip()
        # 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # 尝试提取 ```json ... ``` 代码块
        import re
        m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass
        # 尝试找到第一个 { 到最后一个 }
        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
        raise ValueError(f"无法解析 JSON: {text[:200]}")
