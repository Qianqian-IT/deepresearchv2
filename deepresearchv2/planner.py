"""Planner：把用户调研目标拆成 Researcher 的研究计划。

输入一个 goal，输出结构化 ResearchPlan（主题 + 搜索问题清单）。
只做规划，不做搜索；规划的质量决定调研的天花板。
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
    """规划中枢：一次 plan() 出研究计划。"""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def plan(self, goal: str) -> ResearchPlan:
        prompt = f"""
你是深度调研的规划师。把下面的调研目标拆成研究计划，让执行者去联网搜索。

调研目标：{goal}

请严格以 JSON 输出，不要任何解释。JSON 格式：
{{
  "topic": "研究主题一句话总结",
  "questions": [
    {{"question": "子问题（问句）", "q": "具体搜索词", "domains": ["建议权威域名"]}}
  ]
}}

要求：
1. 先拆 {config.MIN_PLAN_QUESTIONS}~{config.MAX_PLAN_QUESTIONS} 个子问题：每个是目标的一个
   可回答切面，用问句表述，例如 "Milvus 和 Qdrant 在千万级向量规模下谁写入性能更好？"
2. 每个子问题配一个具体搜索词 q：对象 + 场景/用途 + 时间限定，直接能拿去搜索，
   例如 "Milvus vs Qdrant benchmark 写入性能 千万向量 2025 2026"
3. 子问题覆盖目标的所有关键面
4. 实体约束（最重要）：子问题和搜索词里的具体实体（产品名 / 基准名 / 模型名 / 版本号）
   只能来自调研目标原文，目标没提到的实体一律不要预设——不要用你自己的知识举例。
   发现型问题（"有哪些 X"、"谁更好"）就写成能力缺口，命名交给检索去发现：
   搜出来的名字会在后续轮次深入，不需要你先知道。
   反例："agent 评测有哪些基准（如 GAIA、AgentBench、SWE-bench）？" ← 预设了模型记忆
   正例："当前 agent 评测有哪些主流基准测试集？各自侧重什么能力？"
   搜索词同理：用"领域类别 + 场景 + 时间"构造，如 "agent evaluation benchmark 主流 最新 2026"，
   不把目标外的具体名字放进搜索词
5. domains 可选：每个子问题建议 1~3 个该领域的权威域名（官方文档站 / 官方榜单页 /
   官方 repo 托管域，如 "milvus.io"），不确定或目标没提实体就留空 []——
   留空时静态权威表（arxiv / github / 官方机构）会自动兜底，不用怕
""".strip()
        resp = self.llm.chat(prompt, hint="planner_plan")
        data = _try_parse_json(resp)
        questions = [
            PlanQuery(
                question=item.get("question", ""),
                q=item.get("q", ""),
                domains=_parse_domains(item.get("domains")),
            )
            for item in data.get("questions", [])
            if item.get("q")
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
