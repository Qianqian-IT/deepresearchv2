# deepresearchv2

轻量级深度调研 agent：LangGraph 编排 Planner + Researcher，联网检索 + 筛选 + 报告。

## 架构

```
planner → think → act（Tavily 搜索）→ observe（筛选）→ 回 think
                ↘ 收工（FINISH，或预算用尽）→ 生成 Markdown 报告
```

- **planner**：把调研目标拆成 3~6 个子问题 + 搜索词（实体约束：只允许目标原文提到的实体，不预设模型记忆）
- **think**：看全部子问题 + 已接受的发现，决定本轮搜什么（`SEARCH | 子问题序号 | 词`）或收工（`FINISH`）；图里有机械闸门兜底——子问题还没发现不许收工、步数上限强制收工
- **act**：Tavily 搜索，带权威域名白名单（优先一手/权威信源）和 `days` 新鲜度过滤；空结果自动降级不限域名
- **observe**：筛选器——有价值的保留（引用原文、带来源），没价值的丢弃；每次 observe 的完整记录落盘，一条不丢

## 快速开始

```bash
pip install -r deepresearchv2/requirements.txt

export DEEPSEEK_API_KEY=sk-xxx   # 或 OPENAI_API_KEY，并在 deepresearchv2/config.py 切 LLM_PROVIDER
export TAVILY_API_KEY=tvly-xxx   # 联网搜索

python3 deepresearchv2/main.py "调研目标" --save out.md
```

常用参数：

| 参数 | 作用 |
| --- | --- |
| `--quiet` | 关闭过程日志 |
| `--no-clarify` | 跳过规划前的需求澄清 |
| `--save out.md` | 把结论 + 来源存成 Markdown |

## 产出报告结构

研究计划 → 调研结论（按搜索分组，带来源链接）→ 观察记录（逐次不丢）→ 子问题覆盖情况（✅/❌）→ 未覆盖缺口 → 全部检索结果（带信源分层标签）→ 统计。

信源分三层：一手/权威 / 原创/普通 / 转载农场，报告里逐条标注，observe 优先保留权威来源。

示例报告见 [`deepresearchv2/demo_report.md`](deepresearchv2/demo_report.md)。
