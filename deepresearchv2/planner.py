"""Planner：任务分解器 —— 把「目标 + 证据」拆成下游节点的任务清单。

同一个拆解模式，不同的阶段参数：
  plan()          子问题拆解：目标 → 子问题骨架（搜索归属 + 分析单元 + 报告结构）
  plan_analysis() analyze 任务清单：目标 + 骨架 + 研究发现 → analyze 要做什么分析

所有规划共用一套 prompt 骨架（_decompose）：阶段 + 任务 + 证据 + 不变约束 + schema。
planner 只做规划，不做搜索、不做分析；规划的质量决定调研的天花板。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from . import config
from .llm import LLMClient

if TYPE_CHECKING:
    from .researcher import Note  # 仅类型标注；运行时避免循环 import


# ============================================================
# 数据结构
# ============================================================

@dataclass
class PlanQuery:
    """一条研究计划项：子问题 + 对应搜索词。"""
    question: str   # 子问题（问句）：这条搜索要回答什么
    q: str          # 具体搜索词：对象 + 场景/用途 + 时间限定，直接能拿去 Tavily 搜
    domains: list[str] = field(default_factory=list)  # 建议权威域名（可空，用于白名单优先）


@dataclass
class ResearchPlan:
    """Planner 的输出：研究主题 + 子问题清单。"""
    topic: str
    questions: list[PlanQuery] = field(default_factory=list)


@dataclass
class AnalysisTask:
    """一条 analyze 任务：对哪些发现做什么分析、得到什么。"""
    question: str        # 针对的子问题（原样引用骨架里的）
    analysis_goal: str   # 要得到什么分析（回答用户目标的哪个方面）
    analysis_type: str   # 对比 / 归纳 / 评估 / 趋势 / 证据评估
    evidence: list[str]  # 该任务使用的发现所属搜索词
    output: str          # 产出形式：结论段 / 对比表 / 洞察段


# ============================================================
# Planner
# ============================================================

class Planner:
    """规划中枢：把目标 + 证据拆成下游节点的任务清单（任务分解器）。"""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    # ---- 共享 prompt 骨架 ----

    _SHARED_RULES = """\
1. 具体实体（产品名 / 基准名 / 模型名 / 版本号）只能来自上面的调研目标或检索发现，
   禁止用你自己的知识举例、禁止预设模型记忆里的名字
2. 发现型问题写成能力缺口，命名交给检索去发现
3. 严格以 JSON 输出，不要任何解释，不要多余字段"""

    def _decompose(
        self, *, stage: str, task_desc: str,
        evidence: str, output_schema: str, extra_rules: str = "",
    ) -> str:
        """拼装统一规划 prompt：阶段 + 任务 + 证据 + 不变约束 + 阶段约束 + schema。

        多次规划只换阶段参数，共享规则一字不动 —— 防止阶段混淆和上下文漂移。
        """
        return f"""\
你是深度调研的规划师。当前阶段：{stage}。

【本次任务】
{task_desc}

【可见证据】
{evidence}

【不变约束】
{self._SHARED_RULES}
{extra_rules}

【输出】
{output_schema}
""".strip()

    # ---- 规划 1：子问题拆解 ----

    def plan(self, goal: str) -> ResearchPlan:
        """把调研目标拆成子问题骨架（搜索归属 + 分析单元 + 报告结构）。"""
        prompt = self._decompose(
            stage="子问题拆解",
            task_desc=f"""\
把下面的调研目标拆成研究计划，让执行者去联网搜索。

先拆 {config.MIN_PLAN_QUESTIONS}~{config.MAX_PLAN_QUESTIONS} 个子问题：每个是目标的一个
可回答切面，用问句表述，例如 "Milvus 和 Qdrant 在千万级向量规模下谁写入性能更好？"
每个子问题配一个具体搜索词 q：对象 + 场景/用途 + 时间限定，直接能拿去搜索，
例如 "Milvus vs Qdrant benchmark 写入性能 千万向量 2025 2026"
子问题覆盖目标的所有关键面。
domains 可选：每个子问题建议 1~3 个该领域的权威域名（官方文档站 / 官方榜单页 /
官方 repo 托管域，如 "milvus.io"），不确定或目标没提实体就留空 []——
留空时静态权威表（arxiv / github / 官方机构）会自动兜底，不用怕""",
            evidence=f"调研目标：{goal}\n（检索尚未开始，无检索发现）",
            output_schema='''\
{"topic": "研究主题一句话总结",
 "questions": [
   {"question": "子问题（问句）", "q": "具体搜索词", "domains": ["建议权威域名"]}
 ]}''',
        )
        resp = self.llm.chat(prompt, hint="planner_plan")
        data = _try_parse_json(resp)
        questions_data = data.get("questions", []) if isinstance(data, dict) else []
        questions = [
            PlanQuery(
                question=item.get("question", ""),
                q=item.get("q", ""),
                domains=_parse_domains(item.get("domains")),
            )
            for item in questions_data
            if isinstance(item, dict) and item.get("q")
        ]
        return ResearchPlan(
            topic=data.get("topic", goal),
            questions=questions,
        )

    # ---- 规划 2：analyze 任务清单 ----

    def plan_analysis(
        self, goal: str, plan: ResearchPlan, notes: list["Note"],
    ) -> list[AnalysisTask]:
        """基于研究发现规划 analyze 任务清单：对每部分发现做什么分析、得到什么。

        notes 按子问题（target_q）分组渲染为证据；自由补充的发现单独列出。
        每个任务都必须由发现支撑 —— 发现不足的子问题规划为"评估证据薄弱"，
        不硬出结论。
        """
        by_q: dict[str, list] = {}
        for n in notes:
            by_q.setdefault(n.target_q or n.query, []).append(n)

        evidence_lines = [f"调研目标：{goal}", "", "子问题骨架："]
        for i, pq in enumerate(plan.questions, 1):
            evidence_lines.append(f"{i}. {pq.question or pq.q}（搜索词：{pq.q}）")
        evidence_lines += ["", "研究发现（按子问题分组）："]
        def _fmt_facts(ns: list) -> list[str]:
            out = []
            for n in ns:
                out.append(f"  - {n.fact}（来源 {len(n.sources)} 条）")
                for s in n.snippets:  # 完整发现：含原始摘要，供规划分析角度
                    out.append(f"    · 摘要：{s}")
            return out

        for pq in plan.questions:
            facts = by_q.get(pq.q, [])
            if facts:
                evidence_lines.append(f"- 子问题 {pq.q}：")
                evidence_lines += _fmt_facts(facts)
            else:
                evidence_lines.append(f"- 子问题 {pq.q}：（无发现 —— 证据薄弱）")
        extra = [
            (q, ns) for q, ns in by_q.items()
            if q not in {pq.q for pq in plan.questions}
        ]
        if extra:
            evidence_lines += ["", "自由补充搜索的发现（不属于任何子问题）："]
            for q, ns in extra:
                evidence_lines.append(f"- 搜索 {q}：")
                evidence_lines += _fmt_facts(ns)
        evidence = "\n".join(evidence_lines)

        prompt = self._decompose(
            stage="规划分析任务（analyze 的前置规划）",
            task_desc="""\
研究已检索完毕，发现如上。基于调研目标 + 研究发现，规划 analyze 要执行的分析任务清单：
对每部分研究发现，要做什么分析（analysis_type）、要得到什么结论/洞察（analysis_goal），
从而回答用户目标。

每个任务针对一个子问题（question 原样引用骨架）；可规划 1~2 个
跨子问题的综合分析任务（对比联系、整体判断），这组任务是"有洞察的报告"的来源。""",
            evidence=evidence,
            output_schema='''\
{"analysis_tasks": [
  {"question": "针对的子问题（原样引用）",
   "analysis_goal": "要得到什么分析（回答用户目标的哪个方面）",
   "analysis_type": "对比/归纳/评估/趋势/证据评估 之一",
   "evidence": ["该任务使用的发现所属搜索词"],
   "output": "产出形式：结论段 / 对比表 / 洞察段"}
 ]}''',
            extra_rules="""\
4. 每个分析任务必须由发现支撑：发现里没有的方向不要规划"得出结论"，
   证据不足的子问题规划为"评估证据薄弱 / 标注不确定性"
5. 任务清单覆盖用户目标的所有关键面；跨子问题的综合任务必须有真实的
   可联系证据，不要为凑洞察硬编
6. evidence 字段填该任务使用的发现所属搜索词，必须来自上面"可见证据"里出现过的""",
        )
        resp = self.llm.chat(prompt, hint="planner_analysis")
        data = _try_parse_json(resp)
        raw_tasks = data.get("analysis_tasks") if isinstance(data, dict) else data  # 顶层数组容错
        tasks: list[AnalysisTask] = []
        for item in raw_tasks or []:
            if not isinstance(item, dict):
                continue
            if not any(item.get(k) for k in ("question", "analysis_goal", "analysis_type")):
                continue  # 三字段全空才丢弃，避免字段缺失误杀
            tasks.append(AnalysisTask(
                question=item.get("question", ""),
                analysis_goal=item.get("analysis_goal", ""),
                analysis_type=item.get("analysis_type", ""),
                evidence=_parse_list(item.get("evidence")),
                output=item.get("output", ""),
            ))
        if not tasks:
            # 解析失败/无任务：暴露原始响应，方便排查 prompt 或模型输出问题
            print(f"[Planner] ⚠️ plan_analysis 未解析出任务，LLM 原始响应：\n{resp!r}")
        return tasks


# ============================================================
# 工具函数
# ============================================================

def _parse_domains(raw) -> list[str]:
    """容错解析 domains 字段：接受 list 或逗号分隔字符串。"""
    if isinstance(raw, list):
        return [str(d).strip().lower() for d in raw if str(d).strip()]
    if isinstance(raw, str):
        return [d.strip().lower() for d in raw.split(",") if d.strip()]
    return []


def _parse_list(raw) -> list[str]:
    """容错解析字符串列表字段（evidence 等）：接受 list 或逗号分隔字符串。"""
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    if isinstance(raw, str):
        return [x.strip() for x in raw.split(",") if x.strip()]
    return []


def _try_parse_json(text: str) -> dict:
    """容错解析 JSON：先全文解析，再找第一个 { ... } 块。"""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass
    return {}
