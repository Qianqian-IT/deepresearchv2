"""Clarifier：规划前的需求澄清。

一句话调研目标往往缺关键信息（场景/规模约束、对比维度、决策用途、时间范围），
Planner 只能猜。Clarifier 在规划前先向用户补齐这些影响调研方向的信息：

  analyze → LLM 判断目标的信息缺口，产出最多 3 个澄清问题（空 = 目标已明确，跳过）
  enrich  → 交互收集答案，把 Q&A 拼回 goal 作为规划上下文

交互在 CLI 层完成（不在 LangGraph 图里）：图保持纯计算，不挂交互节点。
"""

from __future__ import annotations

import json

from . import config
from .llm import LLMClient


class Clarifier:
    """需求澄清：在规划前补齐影响调研方向的关键信息。"""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def analyze(self, goal: str) -> list[dict]:
        """LLM 判断目标的信息缺口，返回澄清问题列表（[{question, why}]，可空）。"""
        prompt = f"""
你是调研需求澄清助手。下面是一句调研目标，请判断信息是否足够支撑高质量调研。

调研目标：{goal}

请严格以 JSON 输出，不要任何解释：
- 目标信息已足够明确（场景/规模约束、对比维度、决策用途、时间范围等已齐）：输出 []
- 否则输出要问用户的问题列表：
[{{"question": "要问的问题", "why": "为什么影响调研方向（一句话）"}}]

要求：
1. 问题要具体、可直接回答，不要问"还有什么补充"这种开放问题
2. 只问真正影响调研方向的：场景/规模约束、对比维度、决策用途、时间范围
3. 目标里已写明的信息不要重复问
4. 最多 {config.MAX_CLARIFY_QUESTIONS} 个，宁可少问，不要凑数
""".strip()
        resp = self.llm.chat(prompt, hint="clarify_questions")
        return _parse_questions(resp)[: config.MAX_CLARIFY_QUESTIONS]

    def enrich(self, goal: str, questions: list[dict], input_fn=input) -> str:
        """交互收集答案，返回拼上【补充说明】的 goal；无答案则原样返回。"""
        answers: list[tuple[str, str]] = []
        for q in questions:
            why = f"（{q['why']}）" if q.get("why") else ""
            try:
                ans = input_fn(f"   · {q['question']}{why}\n     > ").strip()
            except (EOFError, KeyboardInterrupt):
                ans = ""   # 非交互环境（管道/CI）：跳过，不阻塞
            if ans:
                answers.append((q["question"], ans))
        if not answers:
            return goal
        lines = "\n".join(f"- {qq} → {aa}" for qq, aa in answers)
        return f"{goal}\n\n【补充说明】\n{lines}"


def _parse_questions(text: str) -> list[dict]:
    """容错解析澄清问题：接受数组或 {"questions": [...]} 两种形态。"""
    text = text.strip()
    data = None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("["), text.rfind("]")
        if start >= 0 and end > start:
            try:
                data = json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                data = None
    if isinstance(data, dict) and isinstance(data.get("questions"), list):
        data = data["questions"]
    if not isinstance(data, list):
        return []
    out: list[dict] = []
    for item in data:
        if isinstance(item, dict) and item.get("question"):
            out.append({"question": str(item["question"]), "why": str(item.get("why", ""))})
    return out
