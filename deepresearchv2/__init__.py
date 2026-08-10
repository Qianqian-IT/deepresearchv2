"""deepresearchv2 包入口：Planner + Researcher 两 Agent 的最小闭环（LangGraph 编排）。

设计原则：
- 只有两个 agent，不引入意图闸口 / 报告写手等机制
- Planner 出研究计划，Researcher 用 ReAct（think→act→observe）循环执行 Tavily 搜索
- 产出 = 检索回来的 SearchResult + Researcher 归纳的 Note，没有报告节点
"""

from .clarify import Clarifier
from .graph import build_research_graph, initial_state
from .llm import LLMClient
from .planner import Planner, PlanQuery, ResearchPlan
from .researcher import Note, Researcher
from .tools import SearchResult, SearchTool

__all__ = [
    "Clarifier",
    "LLMClient",
    "Planner",
    "PlanQuery",
    "ResearchPlan",
    "Researcher",
    "Note",
    "SearchTool",
    "SearchResult",
    "build_research_graph",
    "initial_state",
]
