"""示例入口：python3 deepresearchv2/main.py "调研目标"

需要的环境变量（缺哪个就会在启动时直接报错）：
  export DEEPSEEK_API_KEY=sk-xxx     # 或 OPENAI_API_KEY，并在 config.LLM_PROVIDER 切换
  export TAVILY_API_KEY=tvly-xxx     # 用于联网搜索

常用参数：
  python3 deepresearchv2/main.py "调研目标"              # 基本用法
  python3 deepresearchv2/main.py "调研目标" --quiet      # 关闭过程日志
  python3 deepresearchv2/main.py "调研目标" --save out.md  # 把结论+来源存成 Markdown
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import textwrap
from dataclasses import asdict

# 保证从仓库任意目录 `python3 deepresearchv2/main.py` 都能 import 到包
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from deepresearchv2 import (
    Clarifier, LLMClient, SearchTool, build_research_graph, initial_state,
)
from deepresearchv2.planner import AnalysisTask, Planner
from deepresearchv2.tools import TIER_LABEL


def main() -> int:
    parser = argparse.ArgumentParser(description="DeepResearch v2 调研助手（LangGraph: Planner + Researcher）")
    parser.add_argument("query", nargs="?", help="调研目标。不配则用示例。")
    parser.add_argument("--quiet", action="store_true", help="关闭过程日志")
    parser.add_argument("--no-clarify", action="store_true", help="跳过规划前的需求澄清")
    parser.add_argument("--save", type=str, default="", help="把结论+来源存成 Markdown 文件")
    args = parser.parse_args()

    default_goal = (
        "调研 2026 年主流向量数据库（Milvus / Qdrant / Weaviate / pgvector）的技术选型，"
        "从性能、生态、运维成本三个角度对比，用于给千万级向量规模的 RAG 应用做选型。"
    )
    goal = args.query or default_goal

    print()
    print("=" * 70)
    print("🔍 DeepResearch v2（LangGraph: Planner + Researcher）")
    print("=" * 70)
    print(f"🎯 调研目标：\n{textwrap.fill(goal, width=68, subsequent_indent='     ')}")
    print()

    llm = LLMClient()

    # Step 0: 需求澄清 —— 目标信息缺口多就交互补齐，再进图
    if not args.no_clarify:
        clarifier = Clarifier(llm)
        questions = clarifier.analyze(goal)
        if not questions:
            print("（目标信息已足够明确，跳过澄清）")
        else:
            print("❓ 调研前先澄清几个问题（直接回车跳过）：")
            goal = clarifier.enrich(goal, questions)
            print()

    # 组装并编译调研图，一次 invoke 跑完全流程
    app = build_research_graph(
        llm, SearchTool(), verbose=not args.quiet,
    )
    final = app.invoke(initial_state(goal))

    # 研究计划（plan 是图里 planner 节点的产物）
    plan = final["plan"]
    print(f"📋 研究计划（主题：{plan.topic}）")
    for i, q in enumerate(plan.questions, 1):
        print(f"   {i}. 子问题: {q.question}  q={q.q!r}")

    # analyze 大纲：planner 读完整发现（fact + 来源 + 摘要）规划 analyze 的任务清单
    # （analyze 节点未实现，先把规划结果展示出来，并随报告落盘）
    analysis_tasks = Planner(llm).plan_analysis(goal, plan, final["notes"])
    final["analysis_tasks"] = analysis_tasks  # 渲染进报告，--save 的文件里也有记录
    print()
    print("📋 analyze 大纲（规划的分析任务）：")
    print(render_analysis_plan(analysis_tasks))

    # 产出：渲染成 Markdown（结论 + 对应来源）
    report_md = render_report(final)
    print()
    print(report_md)
    print()
    print("=" * 70)
    print(
        f"📊 统计：ReAct {final['steps']} 步 ｜ 搜索 {final['searches']} 次 ｜ "
        f"结果 {len(final['all_results'])} 条 ｜ 发现 {len(final['notes'])} 条"
    )
    if final["gaps"]:
        print("⚠️ 预算内未完全覆盖的缺口：")
        for g in final["gaps"]:
            print(f"   · {g.get('question')} ｜ 还缺: {g.get('why')}")

    # 保存 Markdown
    if args.save:
        with open(args.save, "w", encoding="utf-8") as f:
            f.write(report_md)
        print(f"💾 Markdown 报告已保存到：{args.save}")

        # 同时保存原始 observations（每次搜索 + 筛选保留的 Note），
        # 与报告同目录：out.md → out.observations.json，方便二次处理
        obs_path = args.save.rsplit(".", 1)[0] + ".observations.json"
        with open(obs_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "goal": final["goal"],
                    "plan": {
                        "topic": plan.topic,
                        "questions": [
                            {
                                "question": pq.question,
                                "q": pq.q,
                                "domains": pq.domains,
                            }
                            for pq in plan.questions
                        ],
                    },
                    "observations": [
                        {
                            "query": obs["query"],
                            "notes": [asdict(n) for n in obs["notes"]],
                        }
                        for obs in final["observations"]
                    ],
                    "searches": final["searches"],
                    "steps": final["steps"],
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
        print(f"💾 原始 observations 已保存到：{obs_path}")

    return 0


def render_analysis_plan(tasks: list[AnalysisTask]) -> str:
    """把 analyze 任务清单渲染成可读文本。"""
    lines: list[str] = []
    for i, t in enumerate(tasks, 1):
        lines.append(f"{i}. [{t.analysis_type or '分析'}] {t.question or t.analysis_goal}")
        if t.analysis_goal:
            lines.append(f"   目标：{t.analysis_goal}")
        if t.evidence:
            lines.append(f"   证据：{', '.join(t.evidence)}")
        if t.output:
            lines.append(f"   产出：{t.output}")
    return "\n".join(lines) or "（planner 没有规划出分析任务）"


def render_report(final: dict) -> str:
    """把最终 state 渲染成 Markdown。

    结构：主题 → 研究计划（子问题+搜索词）→ 调研结论（按 query 分组，
    每条结论带来源链接）→ 观察记录（每次 observe 的完整记录，按执行顺序）
    → 子问题覆盖情况（每个子问题搜了几次、发现几条、有无缺口）
    → 未覆盖缺口 → 全部检索结果 → 统计。
    """
    plan = final["plan"]
    url_title = {r.url: r.title for r in final["all_results"]}

    lines = [f"# {plan.topic}", ""]
    lines.append(f"> 调研目标：{final['goal'].strip()}")
    lines.append("")
    lines.append("## 研究计划")
    for i, q in enumerate(plan.questions, 1):
        lines.append(f"{i}. {q.question}")
        lines.append(f"   - 搜索词：`{q.q}`")
    lines.append("")

    # analyze 大纲：planner 基于发现规划的分析任务清单（有才渲染）
    tasks = final.get("analysis_tasks") or []
    if tasks:
        lines.append("## analyze 大纲")
        lines.append("> planner 基于研究发现（fact + 来源 + 摘要）规划的分析任务清单")
        for i, t in enumerate(tasks, 1):
            lines.append(f"{i}. **[{t.analysis_type or '分析'}]** {t.question or t.analysis_goal}")
            if t.analysis_goal:
                lines.append(f"   - 目标：{t.analysis_goal}")
            if t.evidence:
                lines.append(f"   - 证据：{', '.join(t.evidence)}")
            if t.output:
                lines.append(f"   - 产出：{t.output}")
        lines.append("")

    lines.append("## 调研结论")
    notes_by_query: dict[str, list] = {}
    for n in final["notes"]:
        notes_by_query.setdefault(n.query, []).append(n)
    seen: set[str] = set()
    for r in final["all_results"]:
        q = r.query_origin
        if q in seen:
            continue
        seen.add(q)
        lines.append(f"### 搜索：{q}")
        for n in notes_by_query.get(q, []):
            lines.append(f"- **结论**：{n.fact}")
            for url in n.sources:
                lines.append(f"  - 来源：[{url_title.get(url, url)}]({url})")
        if q not in notes_by_query:
            lines.append("- （本次搜索无相关发现）")
        lines.append("")

    # 观察记录：每次 observe 的完整记录，按执行顺序，一条不丢
    lines.append("## 观察记录")
    lines.append("> Researcher 每次 observe 的完整记录（结论 + 来源，按执行顺序，一条不丢）")
    for i, obs in enumerate(final.get("observations", []), 1):
        lines.append(f"### 第 {i} 次搜索：{obs.get('query')}")
        obs_notes = obs.get("notes") or []
        if not obs_notes:
            lines.append("- （该次搜索未归纳出发现）")
        for n in obs_notes:
            lines.append(f"- **发现**：{n.fact}")
            for url in n.sources:
                lines.append(f"  - 来源：[{url_title.get(url, url)}]({url})")
        lines.append("")

    # 每个子问题的搜索/发现/覆盖情况：直接搜索 = 完全按计划词搜的次数；
    # think 自由发挥的补充搜索词无法可靠归属到单一子问题，计入统计里的"补充"。
    lines.append("## 子问题覆盖情况")
    for i, pq in enumerate(plan.questions, 1):
        direct = sum(1 for q in final["done_queries"] if q == pq.q)
        # 归属用 think 声明服务的子问题 target_q：think 自由补充的词也能计入它服务的子问题
        found = sum(1 for n in final["notes"] if n.target_q == pq.q)
        gap = any(g.get("question") == pq.question for g in final["gaps"])
        status = "❌ 缺口" if gap else "✅ 已覆盖"
        lines.append(f"{i}. {pq.question}")
        lines.append(
            f"   - 搜索词：`{pq.q}` ｜ 直接搜索 {direct} 次 ｜ 发现 {found} 条 ｜ {status}"
        )
    lines.append("")

    if final["gaps"]:
        lines.append("## 未覆盖缺口")
        for g in final["gaps"]:
            lines.append(f"- **{g.get('question')}**：还缺 {g.get('why')}")
        lines.append("")

    lines.append("## 全部检索结果")
    seen_results: set[str] = set()
    for r in final["all_results"]:
        if r.url in seen_results:
            continue
        seen_results.add(r.url)
        snippet = (r.snippet or "").replace("\n", " ")
        lines.append(f"- **{r.title}**")
        lines.append(f"  - URL：{r.url}")
        lines.append(f"  - 搜索词：{r.query_origin}")
        lines.append(f"  - 信源：{TIER_LABEL.get(r.source_tier, '未知')}")
        lines.append(f"  - 摘要：{snippet}")
    lines.append("")

    lines.append("## 统计")
    lines.append(
        f"ReAct {final['steps']} 步 ｜ 搜索 {final['searches']} 次 ｜ "
        f"结果 {len(final['all_results'])} 条 ｜ 发现 {len(final['notes'])} 条"
    )
    direct_total = sum(
        1 for pq in plan.questions for q in final["done_queries"] if q == pq.q
    )
    lines.append(
        f"计划词直接命中 {direct_total} 次 ｜ "
        f"think 自由补充 {len(final['done_queries']) - direct_total} 次"
    )
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
