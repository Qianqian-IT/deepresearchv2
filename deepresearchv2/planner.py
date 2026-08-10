"""Planner：任务分解器 —— 把调研目标拆成子问题搜索骨架。

plan()  目标 → 子问题骨架（搜索归属 + 分析单元 + 报告结构）
planner 只做规划，不做搜索、不做分析；规划的质量决定调研的天花板。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from . import config
from .llm import LLMClient


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
