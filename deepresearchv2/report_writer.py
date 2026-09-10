"""报告生成节点：消费 analyzer 的结构化分析结果，生成最终报告。

设计原则：
- 只读 state.analysis + state.goal + state.plan，不碰 notes / all_results
- 一次 LLM 调用生成完整 markdown 报告
- 报告结构：摘要 → 横向对比表 → 逐维度分析 → 最终建议 → 风险/缺失信息
"""

from __future__ import annotations

import json
from typing import Any

from .llm import LLMClient


_REPORT_SYSTEM_PROMPT = """你是一个专业的技术报告撰写助手。你的任务是根据已有的研究分析结果，
撰写一份结构清晰、可直接供技术决策者阅读的调研报告。

你必须遵循以下结构：

## 一、摘要（Executive Summary）
- 一句话概括调研目标和核心结论
- 给出明确的选型推荐（如果分析数据支持的话）

## 二、横向对比总表
- 用 markdown 表格形式，列出各候选方案在各维度的关键指标对比
- 表头：维度 | 候选A | 候选B | ... 
- 每个单元格要给出具体数据（有的话）或标记为"数据缺失"

## 三、逐维度详细分析
- 每个维度一个小节，包含：
  - 该维度为什么重要
  - 各候选方案的表现（引用具体数据）
  - 该维度的结论

## 四、矛盾点说明
- 如果分析中发现了来源之间的矛盾，说明矛盾内容和处理方式

## 五、最终选型建议
- 给出明确的推荐方案，说明推荐理由
- 如果有约束条件（如成本敏感 / 延迟敏感），给出条件分支建议

## 六、信息缺口与风险提示
- 列出分析中仍缺失的关键信息
- 说明这些缺失对决策信心度的影响

写作规范：
- 数据必须基于分析结果中的 direct_evidence，不得编造
- 当数据缺失时，诚实标注"数据缺失"而非猜测
- 使用中文撰写，措辞专业但不过度技术化
- 控制总长度在 2000-4000 字之间
"""


class ReportWriter:
    """报告生成器：单次 LLM 调用，从结构化分析生成 final report。"""

    def __init__(self, llm: LLMClient):
        self._llm = llm

    def write(
        self,
        goal: str,
        plan: dict[str, Any],
        analysis: dict[str, dict[str, Any]],
    ) -> str:
        """生成最终调研报告。

        Args:
            goal: 调研目标
            plan: 研究计划（含子问题描述）
            analysis: analyzer 产出的结构化分析，key 为搜索词，value 为 AnalysisResult

        Returns:
            完整的 markdown 报告字符串
        """
        if not analysis:
            return self._empty_report(goal)

        analysis_summary = self._flatten_analysis(analysis, plan)

        prompt = f"""{_REPORT_SYSTEM_PROMPT}

---
以下是调研的原始输入：

调研目标：{goal}

研究计划：{json.dumps(plan, ensure_ascii=False, indent=2)}

结构化分析结果：{json.dumps(analysis_summary, ensure_ascii=False, indent=2)}
---

请根据以上素材，生成最终调研报告（markdown 格式）。"""
        return self._llm.chat(prompt, hint="report-writing")

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------

    def _flatten_analysis(
        self,
        analysis: dict[str, dict[str, Any]],
        plan: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """将分析结果拍平为 prompt 友好的列表格式。

        每个子问题一个条目：
        - question: 子问题文本
        - merged_insights: 综合结论
        - direct_evidence: 直接证据
        - conflicts: 矛盾点
        - missing_info: 缺失信息
        - confidence: 信心度
        """
        items: list[dict[str, Any]] = []
        sub_qs = plan.get("sub_questions", [])

        for pq in sub_qs:
            # analyzer 用搜索词（q）做 key，优先用 q 匹配
            search_key = pq.get("q", pq.get("question", ""))
            result = analysis.get(search_key, {})
            if not result:
                # 回退：尝试用 question 文本匹配
                result = analysis.get(pq.get("question", ""), {})

            q_text = pq.get("question", "") or pq.get("q", "")
            items.append({
                "question": q_text,
                "merged_insights": result.get("merged_insights", []),
                "direct_evidence": result.get("direct_evidence", []),
                "inferred_analysis": result.get("inferred_analysis", []),
                "conflicts": result.get("conflicts", []),
                "missing_info": result.get("missing_info", []),
                "confidence": result.get("confidence", "unknown"),
            })

        return items

    def _empty_report(self, goal: str) -> str:
        return f"""# 调研报告：{goal}

## 一、摘要

本次调研未能获取到足够的有效信息，所有子问题的分析结果均为空。

建议：
1. 检查搜索关键词是否合理
2. 尝试使用更具体的查询重试
3. 扩展搜索时间范围或信源白名单

## 二、信息缺口

全部子问题均无有效分析结果。
"""
