# Agent评测框架的现状、方法与能力缺口研究

> 调研目标：Agent评测框架

## 研究计划
1. 当前主流的Agent评测框架有哪些，它们各自的核心评测维度和方法是什么？
   - 搜索词：`Agent evaluation framework benchmark survey 2025 2026`
2. Agent评测框架在评测复杂任务（如多步推理、工具调用、长程规划）时存在哪些已知的能力缺口或局限性？
   - 搜索词：`Agent evaluation limitations gaps complex tasks tool use planning 2025`
3. 针对Agent评测，业界是否有公认的基准测试集或排行榜，其更新频率和覆盖场景如何？
   - 搜索词：`Agent benchmark leaderboard 2025 2026 update coverage`
4. Agent评测框架如何评估Agent的鲁棒性、安全性和对抗性攻击下的表现？
   - 搜索词：`Agent evaluation robustness safety adversarial attacks benchmark 2025`
5. 在真实业务或生产环境中，Agent评测框架如何落地，是否有从离线评测到在线评测的实践案例或方法论？
   - 搜索词：`Agent evaluation production online offline practice case study 2025`
6. Agent评测框架的未来发展趋势是什么，例如自适应评测、自动化生成评测任务或跨模态评测？
   - 搜索词：`Agent evaluation future trends adaptive automated generation cross-modal 2026`

## analyze 大纲
> planner 基于研究发现（fact + 来源 + 摘要）规划的分析任务清单
1. **[归纳]** 当前主流的Agent评测框架有哪些，它们各自的核心评测维度和方法是什么？（搜索词：Agent evaluation framework benchmark survey 2025 2026）
   - 目标：梳理当前主流Agent评测框架的类别（如动态环境、静态评估、工具调用、多智能体编排等），并归纳其核心评测维度（如任务完成率、工具选择准确率、鲁棒性）与方法（如状态检查、LLM-as-judge、轨迹分析）。
   - 证据：Agent evaluation framework benchmark survey 2025 2026
   - 产出：结论段：按评测环境（动态/静态）、评测对象（Web、工具、多智能体）和评测方法（状态检查、LLM评判）对主流框架进行分类，并列出代表性基准（如WebArena、Mind2Web、MCP-Bench、PerspectiveGap）及其核心维度。
2. **[归纳]** Agent评测框架在评测复杂任务（如多步推理、工具调用、长程规划）时存在哪些已知的能力缺口或局限性？（搜索词：Agent evaluation limitations gaps complex tasks tool use planning 2025）
   - 目标：识别现有评测框架在复杂任务场景下的具体能力缺口，包括任务粒度、稳定性、难度感知和真实场景覆盖度。
   - 证据：Agent evaluation limitations gaps complex tasks tool use planning 2025
   - 产出：结论段：总结现有基准（如MCPAgentBench、GeoAgentBench）在评测复杂任务时暴露的共性问题，如依赖远程服务导致可复现性差、任务分类粒度粗、缺乏对多步工具调用差异的感知，以及现有通用API基准（ToolBench、API-Bank）在特定领域（如空间分析）的适配不足。
3. **[对比]** 针对Agent评测，业界是否有公认的基准测试集或排行榜，其更新频率和覆盖场景如何？（搜索词：Agent benchmark leaderboard 2025 2026 update coverage）
   - 目标：评估当前主流排行榜（如Sierra、Morph、CodeSOTA、Galileo、Vellum）的公认度、更新频率、覆盖场景及排名稳定性，揭示排行榜对比中的关键陷阱（如pass@k差异）。
   - 证据：Agent benchmark leaderboard 2025 2026 update coverage
   - 产出：对比表：列出各排行榜（Sierra、Morph、CodeSOTA、Galileo、Vellum）的更新日期、覆盖基准（如τ-bench、Terminal-Bench、SWE-bench）、覆盖场景（编码、终端、企业场景）及当前领先模型。结论段：指出排行榜排名随评估次数（pass@k）变化而逆转的现象，说明单次评估的局限性。
4. **[归纳]** Agent评测框架如何评估Agent的鲁棒性、安全性和对抗性攻击下的表现？（搜索词：Agent evaluation robustness safety adversarial attacks benchmark 2025）
   - 目标：归纳当前安全评测基准（如NRT-Bench、TEE-RedBench、MCP-SafetyBench、GuardianAgentBench）的评测方法（如红队攻击、轨迹级评估、ARIA框架）和主要发现（如大模型更易受攻击、安全与效用权衡）。
   - 证据：Agent evaluation robustness safety adversarial attacks benchmark 2025
   - 产出：结论段：总结安全评测从孤立响应向交互轨迹演进的趋势，列举不同基准的攻击模式（如提示注入、工具投毒、多智能体串谋）和核心发现（如攻击成功率范围、安全-效用权衡指标ERS），并指出当前评测对搜索智能体等特定场景覆盖不足。
5. **[归纳]** 在真实业务或生产环境中，Agent评测框架如何落地，是否有从离线评测到在线评测的实践案例或方法论？（搜索词：Agent evaluation production online offline practice case study 2025）
   - 目标：提炼生产环境中离线与在线评测的闭环实践方法论，包括发布门禁、流量采样、监控指标和失败反馈机制。
   - 证据：Agent evaluation production online offline practice case study 2025
   - 产出：结论段：归纳Lyzr、Braintrust、Maxim、Datadog等平台/指南的共性实践，形成“离线把关发布、在线监控行为、失败自动回流”的闭环方法论，并列出关键监控指标（如准确性、成本、包含率、用户满意度）。
6. **[趋势]** Agent评测框架的未来发展趋势是什么，例如自适应评测、自动化生成评测任务或跨模态评测？（搜索词：Agent evaluation future trends adaptive automated generation cross-modal 2026）
   - 目标：识别未来评测趋势的具体方向，包括自适应评估（Agent-as-a-Judge）、自动化任务生成、跨模态评测及主动学习，并评估其成熟度。
   - 证据：Agent evaluation future trends adaptive automated generation cross-modal 2026
   - 产出：趋势段：基于Agent-as-a-Judge综述、MM-tau-p²、Nexus Architect等证据，阐述自适应评估（动态合成标准）、跨模态评测（视觉生成、材料科学）和自动化工作流生成等趋势，并指出这些方向仍处于早期探索阶段。
7. **[对比]** 跨子问题综合分析：Agent评测框架的现状、缺口与未来方向之间存在怎样的内在联系？
   - 目标：整合各子问题发现，形成对Agent评测领域“现状-缺口-趋势”的整体判断，揭示评测演进的内在逻辑（如从静态到动态、从单次到多次、从能力到安全）。
   - 证据：Agent evaluation framework benchmark survey 2025 2026, Agent evaluation limitations gaps complex tasks tool use planning 2025, Agent benchmark leaderboard 2025 2026 update coverage, Agent evaluation robustness safety adversarial attacks benchmark 2025, Agent evaluation production online offline practice case study 2025, Agent evaluation future trends adaptive automated generation cross-modal 2026
   - 产出：洞察段：论证评测演进的三条主线——(1) 从单次静态评估（pass@1）向多次动态评估（pass@k）转变，以应对任务复杂性和排名不稳定；(2) 从能力导向向安全与鲁棒性并重转变，安全评测从孤立响应走向交互轨迹；(3) 从人工构造用例向自动化、自适应生成转变，以解决可扩展性和覆盖度问题。同时指出生产环境中的闭环实践（离线-在线）是连接前沿研究与实际落地的重要桥梁。
8. **[证据评估]** 跨子问题综合分析：当前Agent评测体系在覆盖用户目标（Agent评测框架）时，哪些方面证据充分，哪些方面证据薄弱或存在不确定性？
   - 目标：对六个子问题的证据充分性进行整体评估，明确哪些结论可靠、哪些仍需更多证据，为后续深入分析提供优先级。
   - 证据：Agent evaluation framework benchmark survey 2025 2026, Agent evaluation limitations gaps complex tasks tool use planning 2025, Agent benchmark leaderboard 2025 2026 update coverage, Agent evaluation robustness safety adversarial attacks benchmark 2025, Agent evaluation production online offline practice case study 2025, Agent evaluation future trends adaptive automated generation cross-modal 2026
   - 产出：证据评估段：指出证据充分的方面——主流框架分类（子问题1）、排行榜更新与排名不稳定性（子问题3）、安全评测的演进方向（子问题4）、生产环境闭环方法论（子问题5）。证据薄弱的方面——复杂任务评测缺口（子问题2）多为特定领域（MCP、地理空间）的案例，缺乏通用性结论；未来趋势（子问题6）多为论文提案或早期框架，缺乏大规模实证。标注不确定性：排行榜数据时间跨度大（2025-2026），部分基准（如Sierra、Morph）的公认度需进一步验证。

## 调研结论
### 搜索：Agent evaluation framework benchmark survey 2025 2026
- **结论**：A Survey on Evaluation of LLM-based Agents（arXiv:2503.16416）为ACL Findings论文，综述LLM智能体评估，指出WebArena是动态环境Web智能体领先基准，截至2026年4月19日顶级性能已更新
  - 来源：[A Survey on Evaluation of LLM-based Agents - arXiv](https://arxiv.org/html/2503.16416v2)
- **结论**：GitHub仓库Asaf-Yehudai/LLM-Agent-Evaluation-Survey收录HAL Holistic Agent Leaderboard 2025、PerspectiveGap多智能体编排提示基准（arXiv 2026）、Online-Mind2Web（arXiv 2025）、BrowseComp等智能体评估基准
  - 来源：[Asaf-Yehudai/LLM-Agent-Evaluation-Survey](https://github.com/Asaf-Yehudai/LLM-Agent-Evaluation-Survey)
- **结论**：arXiv:2602.18998评估10个前沿语言模型（含Qwen3-235B、DeepSeek-R1、Qwen3-Next）的通用LLM智能体测试时扩展（Test-Time Scaling）表现
  - 来源：[Benchmark Test-Time Scaling of General LLM Agents - arXiv](https://arxiv.org/html/2602.18998v1)
- **结论**：A Survey on Agent-as-a-Judge（arXiv:2601.05111）综述智能体作为评判者的评估范式，该范式支持高自主性、运行中动态合成评估标准并更新记忆，开启自适应评估新方向
  - 来源：[A Survey on Agent-as-a-Judge - arXiv](https://arxiv.org/html/2601.05111v1)

### 搜索：Agent evaluation limitations gaps complex tasks tool use planning 2025
- **结论**：MCPAgentBench是评估LLM智能体MCP工具使用的真实世界任务基准，覆盖MCP工具调用场景
  - 来源：[MCPAgentBench: A Real-world Task Benchmark for Evaluating LLM Agent MCP Tool Use](https://arxiv.org/html/2512.24565)
- **结论**：GeoAgentBench是面向空间分析工具增强智能体的动态执行基准，对比ToolBench、API-Bank等通用API调用基准
  - 来源：[GeoAgentBench: A Dynamic Execution Benchmark for Tool-Augmented Agents in Spatial Analysis](https://arxiv.org/html/2604.13888)

### 搜索：Agent benchmark leaderboard 2025 2026 update coverage
- **结论**：AgentAtlas论文指出τ-bench证明单次成功评估不足，2026年5月Sierra榜单上Claude Opus 4.5 pass1得分0.70领先，但Qwen3.5-397B-A17B在pass4以0.56反超，排名随尝试次数k增加而逆转
  - 来源：[AgentAtlas: Beyond Outcome Leaderboards for LLM Agents](https://arxiv.org/html/2605.20530v1)
- **结论**：Morph 2026年6月榜单显示，Terminal-Bench 2.1上GPT-5.6 Sol以89.5%领先，Claude Opus 5以89.1%紧随其后
  - 来源：[Best AI Coding Agents (June 2026): Scored Leaderboard - Morph](https://www.morphllm.com/best-ai-coding-agents-2026)
- **结论**：CodeSOTA LLM基准榜单（2026年5月26日更新）追踪7个基准、130个模型，覆盖编码、数学、推理和智能体领域
  - 来源：[LLM Benchmark Leaderboard 2026: Coding, Math, Reasoning and Agents | CodeSOTA | CodeSOTA](https://www.codesota.com/llm)
- **结论**：Galileo发布Agent Leaderboard v2，用跨五个行业的真实企业场景、多轮对话和复杂决策测试智能体，2025年7月17日公布关键结果
  - 来源：[Launching Agent Leaderboard v2: The Enterprise-Grade Benchmark ...](https://galileo.ai/blog/agent-leaderboard-v2)
- **结论**：Vellum 2026年LLM榜单显示，SWE Bench智能体编码任务中GPT-5.6 Sol以96.2%居首，Claude Mythos 5以95.5%次之
  - 来源：[LLM Leaderboard 2026 - Vellum](https://www.vellum.ai/llm-leaderboard)

### 搜索：LLM agent red teaming robustness safety benchmark methodology 2025 2026
- **结论**：NRT-Bench基准评估LLM操作员智能体在多轮红队攻击下的安全控制室场景表现，关注交互轨迹而非孤立响应
  - 来源：[NRT-Bench: Benchmarking Multi-Turn Red-Teaming of LLM Operator Agents in Safety-Critical Control Rooms](https://arxiv.org/html/2606.20408v3)
- **结论**：TEE-RedBench提出面向可信执行环境的红队基准方法，测试Sophia和Cai等LLM在策略滥用探针下的提示失败可迁移性
  - 来源：[Red-Teaming Claude Opus and ChatGPT-based Security Advisors for Trusted Execution Environments](https://arxiv.org/html/2602.19450v1)
- **结论**：SafeSearch对LLM搜索智能体开展系统红队研究，指出现有评估依赖人工构造测试用例
  - 来源：[SafeSearch: Automated Red-Teaming of LLM-Based Search Agents](https://arxiv.org/html/2509.23694v5)
- **结论**：CNFinBench评估LLM在金融场景的能力、合规与安全维度，FinJailbreak聚焦金融对抗提示，覆盖市场操纵、内幕交易、监管规避等违规类型
  - 来源：[Risk-Adjusted Harm Scoring for Automated Red Teaming for LLMs in Financial Services](https://arxiv.org/html/2603.10807v1)

### 搜索：enterprise LLM agent evaluation deployment methodology offline-to-online transition lessons learned 2025 2026
- **结论**：Lyzr 2026企业指南建议将在线与离线评估作为单一闭环运行，离线评估把关发布、在线评估监控实时行为，成熟LLM团队两者并行
  - 来源：[Online vs Offline Evaluation in AI: 2026 Enterprise Guide](https://www.lyzr.ai/blog/online-vs-offline-ai-evaluation)
- **结论**：Lyzr指南强调生产环境失败捕获应自动化，每个生产故障都是评估数据来源
  - 来源：[Online vs Offline Evaluation in AI: 2026 Enterprise Guide](https://www.lyzr.ai/blog/online-vs-offline-ai-evaluation)
- **结论**：Neontri 2026企业AI智能体部署指南指出，Langfuse、Phoenix（Arize）等LLMOps平台提供追踪、成本跟踪和质量评估，支撑生产部署的监控与学习
  - 来源：[Enterprise AI Agents: 2026 Strategy & Deployment Guide](https://neontri.com/blog/enterprise-ai-agents)
- **结论**：Teneo企业级LLM智能体构建指南建议先在受控环境向小规模用户群部署，监控准确性、每次交互LLM调用成本及包含率
  - 来源：[How to Build Enterprise-Grade LLM Agents in 2026: A Techn...](https://www.teneo.ai/blog/what-are-llm-agents-and-how-to-build-them-for-your-enterprise)
- **结论**：LangChain《State of Agent Engineering》报告显示，相当比例受访者尚未在LLM聊天或编码辅助之外使用智能体，agentic应用仍处早期阶段
  - 来源：[State of Agent Engineering](https://www.langchain.com/state-of-agent-engineering)
- **结论**：LangChain报告基于公开调查汇总，反映2025-2026年企业智能体工程实践现状
  - 来源：[State of Agent Engineering](https://www.langchain.com/state-of-agent-engineering)

### 搜索：Agent evaluation robustness safety adversarial attacks benchmark 2025
- **结论**：Nöther等2025年研究测试多智能体系统对对抗诱导危害的鲁棒性，覆盖17类危害类别，核心数据集含188个有害行为示例，测试5个智能体系统
  - 来源：[Taxonomy and Consistency Analysis of Safety Benchmarks for AI Agents](https://arxiv.org/html/2605.16282v1)
- **结论**：OS-Harm基准衡量计算机使用智能体的安全性，Yang等2025年实证研究提示词技术可有效缓解对抗输入
  - 来源：[OS-Harm: A Benchmark for Measuring Safety of Computer Use Agents](https://arxiv.org/html/2506.14866v1)
- **结论**：MCP-SafetyBench基于MCP-Universe构建，系统评估LLM智能体对MCP攻击的鲁棒性，任务反映真实场景和多轮推理
  - 来源：[MCP-SafetyBench: A Benchmark for Safety Evaluation of Large Language Models with Real-World MCP Servers](https://arxiv.org/html/2512.15163v2)
- **结论**：TAMAS采用ARIA框架评估多智能体LLM系统对抗风险，ARIA-1为立即拒绝（安全），ARIA-2为延迟拒绝
  - 来源：[TAMAS: Benchmarking Adversarial Risks in Multi-Agent LLM Systems](https://arxiv.org/html/2511.05269)
- **结论**：GuardianAgentBench对Claude Opus 4.5、GPT-5.2 Pro、GPT-OSS-120B、Gemini-3-Pro等六个前沿模型施加五种对抗攻击模式，测试不同失败模式
  - 来源：[GuardianAgentBench: Where Agents Fail and How to Guard Them](https://arxiv.org/html/2607.20982v1)

### 搜索：Agent evaluation future trends adaptive automated generation cross-modal 2026
- **结论**：Multicrossmodal Automated Agent面向材料科学跨模态数据整合，未来计划引入主动学习和多模态Transformer扩展
  - 来源：[Multicrossmodal Automated Agent for Integrating Diverse Materials Science Data](https://arxiv.org/html/2505.15132v1)
- **结论**：MM-tau-p²提出双控制设置下人物自适应提示方法，用于鲁棒多模态智能体评估
  - 来源：[[2603.09643] MM-tau-p$^2$: Persona-Adaptive Prompting for Robust Multi-Modal Agent Evaluation in Dual-Control Settings](https://arxiv.org/abs/2603.09643)
- **结论**：Nexus Architect通过自动化工作流生成实现自适应多智能体推理，已对前沿LRM全面基准测试
  - 来源：[[PDF] Adaptive Multi-Agent Reasoning via Automated Workflow Generation](https://arxiv.org/pdf/2507.14393)
- **结论**：Nexus Architect论文提出自适应多智能体推理方法，包含自动化工作流生成与基准测试
  - 来源：[[PDF] Adaptive Multi-Agent Reasoning via Automated Workflow Generation](https://www.arxiv.org/pdf/2507.14393)
- **结论**：基于LLM和多智能体协作的移动智能助手自动多模态评估框架，利用LLM生成类人判断
  - 来源：[An Automated Multi-modal Evaluation Framework for Mobile Intelligent Assistants Based on Large Language Models and Multi-Agent Collaboration](https://arxiv.org/html/2508.09507v2)

### 搜索：Agent evaluation production online offline practice case study 2025
- **结论**：Braintrust平台同时支持开发期离线评估（针对精选测试集捕获回归）和生产流量异步在线评估
  - 来源：[Top 5 platforms for agent evals in 2025 - Articles - Braintrust](https://www.braintrust.dev/articles/top-5-platforms-agent-evals-2025)
- **结论**：Maxim平台支持采样生产会话进行在线评估、设置回归告警、分布式追踪定位根因，并将失败案例沉淀为离线数据集
  - 来源：[Top Agent Evaluation Tools in 2025: Best Platforms for Reliable Enterprise Evals](https://www.getmaxim.ai/articles/top-agent-evaluation-tools-in-2025-best-platforms-for-reliable-enterprise-evals)
- **结论**：Datadog提出离线评估作为开发期单元测试方法，在发布前用已知测试用例验证变更
  - 来源：[Offline evaluation for AI agents: Best practices | Datadog](https://www.datadoghq.com/blog/offline-llm-evaluations)
- **结论**：Cleanlab指出MIT 2025年调查发现合规密集型后台职能常隐藏ROI，合规用例在受监管行业开始增多
  - 来源：[AI Agents in Production 2025: Enterprise Trends and Best Practices | Cleanlab](https://cleanlab.ai/ai-agents-in-production-2025)

## 观察记录
> Researcher 每次 observe 的完整记录（结论 + 来源，按执行顺序，一条不丢）
### 第 1 次搜索：Agent evaluation framework benchmark survey 2025 2026
- **发现**：A Survey on Evaluation of LLM-based Agents（arXiv:2503.16416）为ACL Findings论文，综述LLM智能体评估，指出WebArena是动态环境Web智能体领先基准，截至2026年4月19日顶级性能已更新
  - 来源：[A Survey on Evaluation of LLM-based Agents - arXiv](https://arxiv.org/html/2503.16416v2)
- **发现**：GitHub仓库Asaf-Yehudai/LLM-Agent-Evaluation-Survey收录HAL Holistic Agent Leaderboard 2025、PerspectiveGap多智能体编排提示基准（arXiv 2026）、Online-Mind2Web（arXiv 2025）、BrowseComp等智能体评估基准
  - 来源：[Asaf-Yehudai/LLM-Agent-Evaluation-Survey](https://github.com/Asaf-Yehudai/LLM-Agent-Evaluation-Survey)
- **发现**：arXiv:2602.18998评估10个前沿语言模型（含Qwen3-235B、DeepSeek-R1、Qwen3-Next）的通用LLM智能体测试时扩展（Test-Time Scaling）表现
  - 来源：[Benchmark Test-Time Scaling of General LLM Agents - arXiv](https://arxiv.org/html/2602.18998v1)
- **发现**：A Survey on Agent-as-a-Judge（arXiv:2601.05111）综述智能体作为评判者的评估范式，该范式支持高自主性、运行中动态合成评估标准并更新记忆，开启自适应评估新方向
  - 来源：[A Survey on Agent-as-a-Judge - arXiv](https://arxiv.org/html/2601.05111v1)

### 第 2 次搜索：Agent evaluation limitations gaps complex tasks tool use planning 2025
- **发现**：MCPAgentBench是评估LLM智能体MCP工具使用的真实世界任务基准，覆盖MCP工具调用场景
  - 来源：[MCPAgentBench: A Real-world Task Benchmark for Evaluating LLM Agent MCP Tool Use](https://arxiv.org/html/2512.24565)
- **发现**：GeoAgentBench是面向空间分析工具增强智能体的动态执行基准，对比ToolBench、API-Bank等通用API调用基准
  - 来源：[GeoAgentBench: A Dynamic Execution Benchmark for Tool-Augmented Agents in Spatial Analysis](https://arxiv.org/html/2604.13888)

### 第 3 次搜索：Agent benchmark leaderboard 2025 2026 update coverage
- **发现**：AgentAtlas论文指出τ-bench证明单次成功评估不足，2026年5月Sierra榜单上Claude Opus 4.5 pass1得分0.70领先，但Qwen3.5-397B-A17B在pass4以0.56反超，排名随尝试次数k增加而逆转
  - 来源：[AgentAtlas: Beyond Outcome Leaderboards for LLM Agents](https://arxiv.org/html/2605.20530v1)
- **发现**：Morph 2026年6月榜单显示，Terminal-Bench 2.1上GPT-5.6 Sol以89.5%领先，Claude Opus 5以89.1%紧随其后
  - 来源：[Best AI Coding Agents (June 2026): Scored Leaderboard - Morph](https://www.morphllm.com/best-ai-coding-agents-2026)
- **发现**：CodeSOTA LLM基准榜单（2026年5月26日更新）追踪7个基准、130个模型，覆盖编码、数学、推理和智能体领域
  - 来源：[LLM Benchmark Leaderboard 2026: Coding, Math, Reasoning and Agents | CodeSOTA | CodeSOTA](https://www.codesota.com/llm)
- **发现**：Galileo发布Agent Leaderboard v2，用跨五个行业的真实企业场景、多轮对话和复杂决策测试智能体，2025年7月17日公布关键结果
  - 来源：[Launching Agent Leaderboard v2: The Enterprise-Grade Benchmark ...](https://galileo.ai/blog/agent-leaderboard-v2)
- **发现**：Vellum 2026年LLM榜单显示，SWE Bench智能体编码任务中GPT-5.6 Sol以96.2%居首，Claude Mythos 5以95.5%次之
  - 来源：[LLM Leaderboard 2026 - Vellum](https://www.vellum.ai/llm-leaderboard)

### 第 4 次搜索：LLM agent red teaming robustness safety benchmark methodology 2025 2026
- **发现**：NRT-Bench基准评估LLM操作员智能体在多轮红队攻击下的安全控制室场景表现，关注交互轨迹而非孤立响应
  - 来源：[NRT-Bench: Benchmarking Multi-Turn Red-Teaming of LLM Operator Agents in Safety-Critical Control Rooms](https://arxiv.org/html/2606.20408v3)
- **发现**：TEE-RedBench提出面向可信执行环境的红队基准方法，测试Sophia和Cai等LLM在策略滥用探针下的提示失败可迁移性
  - 来源：[Red-Teaming Claude Opus and ChatGPT-based Security Advisors for Trusted Execution Environments](https://arxiv.org/html/2602.19450v1)
- **发现**：SafeSearch对LLM搜索智能体开展系统红队研究，指出现有评估依赖人工构造测试用例
  - 来源：[SafeSearch: Automated Red-Teaming of LLM-Based Search Agents](https://arxiv.org/html/2509.23694v5)
- **发现**：CNFinBench评估LLM在金融场景的能力、合规与安全维度，FinJailbreak聚焦金融对抗提示，覆盖市场操纵、内幕交易、监管规避等违规类型
  - 来源：[Risk-Adjusted Harm Scoring for Automated Red Teaming for LLMs in Financial Services](https://arxiv.org/html/2603.10807v1)

### 第 5 次搜索：enterprise LLM agent evaluation deployment methodology offline-to-online transition lessons learned 2025 2026
- **发现**：Lyzr 2026企业指南建议将在线与离线评估作为单一闭环运行，离线评估把关发布、在线评估监控实时行为，成熟LLM团队两者并行
  - 来源：[Online vs Offline Evaluation in AI: 2026 Enterprise Guide](https://www.lyzr.ai/blog/online-vs-offline-ai-evaluation)
- **发现**：Lyzr指南强调生产环境失败捕获应自动化，每个生产故障都是评估数据来源
  - 来源：[Online vs Offline Evaluation in AI: 2026 Enterprise Guide](https://www.lyzr.ai/blog/online-vs-offline-ai-evaluation)
- **发现**：Neontri 2026企业AI智能体部署指南指出，Langfuse、Phoenix（Arize）等LLMOps平台提供追踪、成本跟踪和质量评估，支撑生产部署的监控与学习
  - 来源：[Enterprise AI Agents: 2026 Strategy & Deployment Guide](https://neontri.com/blog/enterprise-ai-agents)
- **发现**：Teneo企业级LLM智能体构建指南建议先在受控环境向小规模用户群部署，监控准确性、每次交互LLM调用成本及包含率
  - 来源：[How to Build Enterprise-Grade LLM Agents in 2026: A Techn...](https://www.teneo.ai/blog/what-are-llm-agents-and-how-to-build-them-for-your-enterprise)
- **发现**：LangChain《State of Agent Engineering》报告显示，相当比例受访者尚未在LLM聊天或编码辅助之外使用智能体，agentic应用仍处早期阶段
  - 来源：[State of Agent Engineering](https://www.langchain.com/state-of-agent-engineering)
- **发现**：LangChain报告基于公开调查汇总，反映2025-2026年企业智能体工程实践现状
  - 来源：[State of Agent Engineering](https://www.langchain.com/state-of-agent-engineering)

### 第 6 次搜索：Agent evaluation robustness safety adversarial attacks benchmark 2025
- **发现**：Nöther等2025年研究测试多智能体系统对对抗诱导危害的鲁棒性，覆盖17类危害类别，核心数据集含188个有害行为示例，测试5个智能体系统
  - 来源：[Taxonomy and Consistency Analysis of Safety Benchmarks for AI Agents](https://arxiv.org/html/2605.16282v1)
- **发现**：OS-Harm基准衡量计算机使用智能体的安全性，Yang等2025年实证研究提示词技术可有效缓解对抗输入
  - 来源：[OS-Harm: A Benchmark for Measuring Safety of Computer Use Agents](https://arxiv.org/html/2506.14866v1)
- **发现**：MCP-SafetyBench基于MCP-Universe构建，系统评估LLM智能体对MCP攻击的鲁棒性，任务反映真实场景和多轮推理
  - 来源：[MCP-SafetyBench: A Benchmark for Safety Evaluation of Large Language Models with Real-World MCP Servers](https://arxiv.org/html/2512.15163v2)
- **发现**：TAMAS采用ARIA框架评估多智能体LLM系统对抗风险，ARIA-1为立即拒绝（安全），ARIA-2为延迟拒绝
  - 来源：[TAMAS: Benchmarking Adversarial Risks in Multi-Agent LLM Systems](https://arxiv.org/html/2511.05269)
- **发现**：GuardianAgentBench对Claude Opus 4.5、GPT-5.2 Pro、GPT-OSS-120B、Gemini-3-Pro等六个前沿模型施加五种对抗攻击模式，测试不同失败模式
  - 来源：[GuardianAgentBench: Where Agents Fail and How to Guard Them](https://arxiv.org/html/2607.20982v1)

### 第 7 次搜索：Agent evaluation future trends adaptive automated generation cross-modal 2026
- **发现**：Multicrossmodal Automated Agent面向材料科学跨模态数据整合，未来计划引入主动学习和多模态Transformer扩展
  - 来源：[Multicrossmodal Automated Agent for Integrating Diverse Materials Science Data](https://arxiv.org/html/2505.15132v1)
- **发现**：MM-tau-p²提出双控制设置下人物自适应提示方法，用于鲁棒多模态智能体评估
  - 来源：[[2603.09643] MM-tau-p$^2$: Persona-Adaptive Prompting for Robust Multi-Modal Agent Evaluation in Dual-Control Settings](https://arxiv.org/abs/2603.09643)
- **发现**：Nexus Architect通过自动化工作流生成实现自适应多智能体推理，已对前沿LRM全面基准测试
  - 来源：[[PDF] Adaptive Multi-Agent Reasoning via Automated Workflow Generation](https://arxiv.org/pdf/2507.14393)
- **发现**：Nexus Architect论文提出自适应多智能体推理方法，包含自动化工作流生成与基准测试
  - 来源：[[PDF] Adaptive Multi-Agent Reasoning via Automated Workflow Generation](https://www.arxiv.org/pdf/2507.14393)
- **发现**：基于LLM和多智能体协作的移动智能助手自动多模态评估框架，利用LLM生成类人判断
  - 来源：[An Automated Multi-modal Evaluation Framework for Mobile Intelligent Assistants Based on Large Language Models and Multi-Agent Collaboration](https://arxiv.org/html/2508.09507v2)

### 第 8 次搜索：Agent evaluation production online offline practice case study 2025
- **发现**：Braintrust平台同时支持开发期离线评估（针对精选测试集捕获回归）和生产流量异步在线评估
  - 来源：[Top 5 platforms for agent evals in 2025 - Articles - Braintrust](https://www.braintrust.dev/articles/top-5-platforms-agent-evals-2025)
- **发现**：Maxim平台支持采样生产会话进行在线评估、设置回归告警、分布式追踪定位根因，并将失败案例沉淀为离线数据集
  - 来源：[Top Agent Evaluation Tools in 2025: Best Platforms for Reliable Enterprise Evals](https://www.getmaxim.ai/articles/top-agent-evaluation-tools-in-2025-best-platforms-for-reliable-enterprise-evals)
- **发现**：Datadog提出离线评估作为开发期单元测试方法，在发布前用已知测试用例验证变更
  - 来源：[Offline evaluation for AI agents: Best practices | Datadog](https://www.datadoghq.com/blog/offline-llm-evaluations)
- **发现**：Cleanlab指出MIT 2025年调查发现合规密集型后台职能常隐藏ROI，合规用例在受监管行业开始增多
  - 来源：[AI Agents in Production 2025: Enterprise Trends and Best Practices | Cleanlab](https://cleanlab.ai/ai-agents-in-production-2025)

## 子问题覆盖情况
1. 当前主流的Agent评测框架有哪些，它们各自的核心评测维度和方法是什么？
   - 搜索词：`Agent evaluation framework benchmark survey 2025 2026` ｜ 直接搜索 1 次 ｜ 发现 4 条 ｜ ✅ 已覆盖
2. Agent评测框架在评测复杂任务（如多步推理、工具调用、长程规划）时存在哪些已知的能力缺口或局限性？
   - 搜索词：`Agent evaluation limitations gaps complex tasks tool use planning 2025` ｜ 直接搜索 1 次 ｜ 发现 2 条 ｜ ✅ 已覆盖
3. 针对Agent评测，业界是否有公认的基准测试集或排行榜，其更新频率和覆盖场景如何？
   - 搜索词：`Agent benchmark leaderboard 2025 2026 update coverage` ｜ 直接搜索 1 次 ｜ 发现 5 条 ｜ ✅ 已覆盖
4. Agent评测框架如何评估Agent的鲁棒性、安全性和对抗性攻击下的表现？
   - 搜索词：`Agent evaluation robustness safety adversarial attacks benchmark 2025` ｜ 直接搜索 1 次 ｜ 发现 9 条 ｜ ✅ 已覆盖
5. 在真实业务或生产环境中，Agent评测框架如何落地，是否有从离线评测到在线评测的实践案例或方法论？
   - 搜索词：`Agent evaluation production online offline practice case study 2025` ｜ 直接搜索 1 次 ｜ 发现 10 条 ｜ ✅ 已覆盖
6. Agent评测框架的未来发展趋势是什么，例如自适应评测、自动化生成评测任务或跨模态评测？
   - 搜索词：`Agent evaluation future trends adaptive automated generation cross-modal 2026` ｜ 直接搜索 1 次 ｜ 发现 5 条 ｜ ✅ 已覆盖

## 全部检索结果
- **A Survey on Evaluation of LLM-based Agents - arXiv**
  - URL：https://arxiv.org/html/2503.16416v2
  - 搜索词：Agent evaluation framework benchmark survey 2025 2026
  - 信源：一手/权威
  - 摘要：### E.1 Web Agents  The choice of benchmark in this domain depends heavily on the environment’s dynamicity and the agent’s modality.  Dynamic Interaction: WebArena remains the leading option for agents operating in dynamic environments. We note that as of April 19, 2026, top performance has reached 74.3%, based on a submission from February 2026, suggesting there is still room for improvement.  Static Evaluation: For offline evaluation using cached traces, Mind2Web remains the standard. [...] To better reflect real-world scenarios, recent evaluations have become increasingly agentic Patil et al. (2025b: from tool use to agentic evaluation of large language models")), requiring longer interactions and scaling the number of domains and tools by sourcing them from real MCP servers Anthropic (Nov 2024). Two current frontier benchmarks, Scale’s MCP Atlas Bandi et al. (2026) and Tool-Decathlon Li et al. (2026), further push in this direction. Despite significant model advancements, these [...] Yet, this approach does not support the same agent harness evaluation across any benchmark environment. Harbor and Exgentic aim to solve that by providing frameworks with a unified protocol for general agent assessment Harbor Framework Team (2026); Bandel et al. (2026a). These represent the first steps toward holistic, standardized, cross-environment agent evaluation Lacoste et al. (2026).
- **Asaf-Yehudai/LLM-Agent-Evaluation-Survey**
  - URL：https://github.com/Asaf-Yehudai/LLM-Agent-Evaluation-Survey
  - 搜索词：Agent evaluation framework benchmark survey 2025 2026
  - 信源：一手/权威
  - 摘要：HAL: Holistic Agent Leaderboard, HAL leaderboard 2025 (  PerspectiveGap: A Benchmark for Multi-Agent Orchestration Prompting, arXiv 2026 ( [...] Online-Mind2Web:An Illusion of Progress? Assessing the Current State of Web Agents, arXiv 2025 (  BrowseComp: A Simple Yet Challenging Benchmark for Browsing Agents, arXiv 2025 (  Mind2Web 2: Evaluating Agentic Search with Agent-as-a-Judge, arXiv 2025 (  ClawBench: Can AI Agents Complete Everyday Online Tasks?, arXiv 2026 ( ( ( [...] AgentHarm: A Benchmark for Measuring Harmfulness of LLM Agents, ICLR 2025 (  ST-WebAgentBench: A Benchmark for Evaluating Safety and Trustworthiness in Web Agents, ICLR 2025 (  Multi-Agent Risks from Advanced AI, arXiv 2025 (  Evaluating Cultural and Social Awareness of LLM Web Agents, NAACL-findings 2025 (  Breaking ReAct Agents: Foot-in-the-Door Attack Will Get You In, NAACL 2025 (  ## ➕ Adding a Benchmark / Paper
- **Benchmark Test-Time Scaling of General LLM Agents - arXiv**
  - URL：https://arxiv.org/html/2602.18998v1
  - 搜索词：Agent evaluation framework benchmark survey 2025 2026
  - 信源：一手/权威
  - 摘要：Our evaluation covers a total of ten frontier language models. Among open-source models, we include several high-performing systems such as Qwen3-235B (Yang et al., 2025) and DeepSeek-R1 (Guo et al., 2025), as well as more recent models with novel attention mechanisms, including Qwen3-Next (Qwen Team, Alibaba Inc., 2025) and DeepSeek-v3.2 (Liu et al., 2025). For proprietary models, we consider both efficiency-oriented variants (e.g., Gemini 2.5 Flash (Comanici et al., 2025)) and models [...] For the tool-use domain, we include tasks from Tau2-Bench(Barres et al., 2025) and MCP-Bench(Wang et al., 2025b), both of which provide extensive tool suites for evaluating a model’s ability to understand, select, and invoke the appropriate tool to solve a problem. Tau2-Bench focuses on customer-service scenarios, where the model acts as a customer-support agent responding to simulated user queries using a set of synthetic tools tailored to the scenario. MCP-Bench, in contrast, offers a [...] Our attention analysis is conducted on inference trajectories collected from General AgentBench. For each benchmark domain, we randomly sample 25 trajectories generated by the model under analysis. Because attention patterns depend strongly on the specific text region being examined, we follow the framework of Jin et al. (2025) to extract reasoning-behavior sentences from each trajectory. These sentences correspond to critical decision-making steps, where the model actively reasons over
- **A Survey on Agent-as-a-Judge - arXiv**
  - URL：https://arxiv.org/html/2601.05111v1
  - 搜索词：Agent evaluation framework benchmark survey 2025 2026
  - 信源：一手/权威
  - 摘要：represents the cutting edge of the field, characterized by high autonomy and the ability to refine internal components during operation—synthesizing evaluation rubrics on-the-fly [wadhwa2025EvalAgents] and updating memory with lessons learned. This paradigm opens new frontiers for adaptive evaluation systems, though challenges remain in ensuring stability during self-modification [gao2025self-evolving-agent-survey].  ## 3 Methodologies [...] Conversely, Evaluation Agent [zhang2025EvaluationAgent] introduces dynamic multi-round planning, where agents adjust strategies based on intermediate feedback. This system further optimizes efficiency through autonomous termination, allowing the agent to self-monitor information gain and proactively halt execution once sufficient evidence is gathered. [...] In the multimodal and vision domain, Agent-as-a-Judge shifts from static scoring to interactive inspection. For visual generation, CIGEval [wang-etal-2025-unified] orchestrates specialized tools to probe control adherence and subject consistency, while Evaluation Agent [zhang2025EvaluationAgent] runs multi-round checks to provide user-tailored, explainable analyses.
- **[2503.16416] Survey on Evaluation of LLM-based Agents - arXiv**
  - URL：https://arxiv.org/abs/2503.16416
  - 搜索词：Agent evaluation framework benchmark survey 2025 2026
  - 信源：一手/权威
  - 摘要：archive  # Computer Science > Artificial Intelligence  # Title:Survey on Evaluation of LLM-based Agents  |  |  |  --- | | Comments: | ACL Findings | | Subjects: | Artificial Intelligence (cs.AI); Computation and Language (cs.CL); Machine Learning (cs.LG) | | Cite as: | arXiv:2503.16416 [cs.AI] | |  | (or  arXiv:2503.16416v2 [cs.AI] for this version) | |  |  Focus to learn more  arXiv-issued DOI via DataCite |  ## Submission history  ## Access Paper:  license icon  ### Current browse context: [...] ### References & Citations  ## BibTeX formatted citation  ### Bookmark  BibSonomy Reddit  # Bibliographic and Citation Tools  # Code, Data and Media Associated with this Article  # Demos  # Recommenders and Search Tools  # arXivLabs: experimental projects with community collaborators  arXivLabs is a framework that allows collaborators to develop and share new arXiv features directly on our website. [...] Both individuals and organizations that work with arXivLabs have embraced and accepted our values of openness, community, excellence, and user data privacy. arXiv is committed to these values and only works with partners that adhere to them.  Have an idea for a project that will add value for arXiv's community? Learn more about arXivLabs.  Simons Foundation Simons Foundation International Schmidt Sciences
- **MCPAgentBench: A Real-world Task Benchmark for Evaluating LLM Agent MCP Tool Use**
  - URL：https://arxiv.org/html/2512.24565
  - 搜索词：Agent evaluation limitations gaps complex tasks tool use planning 2025
  - 信源：一手/权威
  - 摘要：threats, and future research directions")); Ehtesham et al. (2025, agent communication protocol (acp), agent-to-agent protocol (a2a), and agent network protocol (anp)")); Lumer et al. (2025) currently represents a crucial exploration aimed at unifying the interaction modality between Agents and external tools, defining a standard format for tool invocation. Agent utilization of MCP tools becomes a key approach for solving complex, real-world tasks. Consequently, establishing a comprehensive [...] However, existing MCP capability assessment benchmarks Luo et al. (2025); Gao et al. (2025); Fan et al. (2025) suffer from several significant limitations. Firstly, a stability and dependency issue exists, as current benchmarks often rely on real, remote MCP servers, where service stability and availability heavily impact the reproducibility of testing results. Secondly, these benchmarks exhibit insufficient difficulty awareness, performing only simple task categorization and lacking granular [...] differences in handling complex, multi-step tool invocations. All code is open-source at Github (2025).
- **MCPAgentBench: A Real-world Task Benchmark for Evaluating LLM Agent MCP Tool Use**
  - URL：https://arxiv.org/html/2512.24565v2
  - 搜索词：Agent evaluation limitations gaps complex tasks tool use planning 2025
  - 信源：一手/权威
  - 摘要：threats, and future research directions")); Ehtesham et al. (2025, agent communication protocol (acp), agent-to-agent protocol (a2a), and agent network protocol (anp)")); Lumer et al. (2025) currently represents a crucial exploration aimed at unifying the interaction modality between Agents and external tools, defining a standard format for tool invocation. Agent utilization of MCP tools becomes a key approach for solving complex, real-world tasks. Consequently, establishing a comprehensive [...] However, existing MCP capability assessment benchmarks Luo et al. (2025); Gao et al. (2025); Fan et al. (2025) suffer from several significant limitations. Firstly, a stability and dependency issue exists, as current benchmarks often rely on real, remote MCP servers, where service stability and availability heavily impact the reproducibility of testing results. Secondly, these benchmarks exhibit insufficient difficulty awareness, performing only simple task categorization and lacking granular [...] differences in handling complex, multi-step tool invocations. All code is open-source at Github (2025).
- **MCPAgentBench: A Real-world Task Benchmark for Evaluating LLM Agent MCP Tool Use**
  - URL：https://arxiv.org/html/2512.24565v3
  - 搜索词：Agent evaluation limitations gaps complex tasks tool use planning 2025
  - 信源：一手/权威
  - 摘要：threats, and future research directions")); Ehtesham et al. (2025, agent communication protocol (acp), agent-to-agent protocol (a2a), and agent network protocol (anp)")); Lumer et al. (2025) currently represents a crucial exploration aimed at unifying the interaction modality between Agents and external tools, defining a standard format for tool invocation. Agent utilization of MCP tools becomes a key approach for solving complex, real-world tasks. Consequently, establishing a comprehensive [...] However, existing MCP capability assessment benchmarks Luo et al. (2025); Gao et al. (2025); Fan et al. (2025) suffer from several significant limitations. Firstly, a stability and dependency issue exists, as current benchmarks often rely on real, remote MCP servers, where service stability and availability heavily impact the reproducibility of testing results. Secondly, these benchmarks exhibit insufficient difficulty awareness, performing only simple task categorization and lacking granular [...] differences in handling complex, multi-step tool invocations. All code is open-source at Github (2025).
- **GeoAgentBench: A Dynamic Execution Benchmark for Tool-Augmented Agents in Spatial Analysis**
  - URL：https://arxiv.org/html/2604.13888
  - 搜索词：Agent evaluation limitations gaps complex tasks tool use planning 2025
  - 信源：一手/权威
  - 摘要：academic community have yielded several relevant evaluation benchmarks—such as ToolBench(Qin et al., 2024) and API-Bank (Li et al., 2023) for general-domain API invocation, alongside GeoAnalystBench (Zhang et al., 2025), GeoBenchX (Krechetova and Kochedykov, 2025), and GeoPlan-Bench (Li et al., 2025b) tailored for geospatial tasks—these existing baselines still exhibit significant limitations when assessing authentic, complex spatial analysis workflows (as summarized in Table 1). [...] The construction of the task set began with a rigorous screening of GeoAnalystBench (Zhang et al., 2025). We evaluated its 50 cases and excluded 10 tasks that relied on closed-source data or proprietary ArcGIS formats, ensuring compatibility with open geospatial computing ecosystems. However, a deeper analysis revealed that the remaining 40 cases could not be directly utilized for autonomous tool orchestration due to two critical limitations: (1) Coarse Logical Granularity: The original [...] remains weak (Akinboyewa et al., 2025). This further underscores the urgent need for systematic evaluation of the comprehensive capability boundaries of agents in complex geospatial scenarios.
- **GeoAgentBench: A Dynamic Execution Benchmark for Tool-Augmented Agents in Spatial Analysis**
  - URL：https://arxiv.org/html/2604.13888v1
  - 搜索词：Agent evaluation limitations gaps complex tasks tool use planning 2025
  - 信源：一手/权威
  - 摘要：academic community have yielded several relevant evaluation benchmarks—such as ToolBench(Qin et al., 2024) and API-Bank (Li et al., 2023) for general-domain API invocation, alongside GeoAnalystBench (Zhang et al., 2025), GeoBenchX (Krechetova and Kochedykov, 2025), and GeoPlan-Bench (Li et al., 2025b) tailored for geospatial tasks—these existing baselines still exhibit significant limitations when assessing authentic, complex spatial analysis workflows (as summarized in Table 1). [...] The construction of the task set began with a rigorous screening of GeoAnalystBench (Zhang et al., 2025). We evaluated its 50 cases and excluded 10 tasks that relied on closed-source data or proprietary ArcGIS formats, ensuring compatibility with open geospatial computing ecosystems. However, a deeper analysis revealed that the remaining 40 cases could not be directly utilized for autonomous tool orchestration due to two critical limitations: (1) Coarse Logical Granularity: The original [...] remains weak (Akinboyewa et al., 2025). This further underscores the urgent need for systematic evaluation of the comprehensive capability boundaries of agents in complex geospatial scenarios.
- **AgentAtlas: Beyond Outcome Leaderboards for LLM Agents**
  - URL：https://arxiv.org/html/2605.20530v1
  - 搜索词：Agent benchmark leaderboard 2025 2026 update coverage
  - 信源：一手/权威
  - 摘要：τ\tau-bench is the strongest external evidence that single-shot success is insufficient (Fig. 2). On the May-2026 Sierra Overall leaderboard, Claude Opus 4.5 wins pass1 (0.70) but Qwen3.5-397B-A17B wins pass4 (0.56) — rank-3 becomes rank-1 as kk grows because Qwen has the flattest decay curve (−-12 pp vs. ≈\approx−-18 pp). Even the strongest 2026 system loses ≈\approx25 pp between pass1 and pass4 on Retail (Qwen 0.84 →\to 0.60). The one controlled pair on the leaderboard — GPT-5.2 with [...] still trails clean utility by ≈\approx11 pp (AgentDojo team, 2025; Debenedetti et al., 2024); AgentRx localizes critical failure steps in failed trajectories (Microsoft Research, 2026); ATBench evaluates long-horizon trajectory safety (Li et al., 2026); and MCP security benchmarks reveal new tool-poisoning and prompt-injection surfaces (Yang et al., 2025; MCPTox authors, 2025). Anthropic’s computer-use work and the broader Claude Code ecosystem have made agentic coding and GUI interaction a [...] insufficient and scaffold-sensitive. Newer benchmark families instead expose the evaluation gaps this taxonomy is designed to map: τ\tau-bench reports passk decay and the frontier-model crown flips between k=1k{=}1 and k=4k{=}4 on the 2026 Sierra Overall leaderboard — Opus 4.5 wins pass1 (0.70), Qwen3.5 wins pass4 (0.56) (tau-bench team, 2026; Yao et al., 2024); AgentDojo shows targeted prompt-injection ASR fell from 56.3% on GPT-4-0125 to 7.3% on Claude 3.7 Sonnet while utility-under-attack
- **Best AI Coding Agents (June 2026): Scored Leaderboard - Morph**
  - URL：https://www.morphllm.com/best-ai-coding-agents-2026
  - 搜索词：Agent benchmark leaderboard 2025 2026 update coverage
  - 信源：原创/普通
  - 摘要：The best AI coding agent in August 2026 depends on the benchmark that matches your work. On Terminal-Bench 2.1, GPT-5.6 Sol at xhigh effort leads at 89.5% and Claude Opus 5 at max effort follows at 89.1%, so the two default models of the two most-used agents are within half a point of each other. Codex has defaulted to GPT-5.6 Sol since GPT-5.6 went generally available on July 9, 2026; Claude Code has defaulted to Opus 5 since July 24. On SWE-bench Verified, Fable 5 leads at 95.0% and Opus 4.8 [...] ## The Benchmarks, Explained  Three benchmarks separate the agents. SWE-bench Verified measures whether a model resolves a real GitHub issue in Python (human-validated, 500 tasks). SWE-bench Pro is the harder, contamination-resistant set on larger commercial-style codebases. Terminal-Bench v2 (the 2.1 leaderboard) measures whether an agent completes a terminal-driven task end to end, scoring the agent-plus-model pair, not the model alone. [...] Updated August 2, 2026 (post-GPT-5.6, post-Opus-5). Coding agents scored on SWE-bench Verified, SWE-bench Pro, and Terminal-Bench v2, with $/task and pricing. GPT-5.6 Sol leads Terminal-Bench 2.1 at 89.5%; Claude Opus 5 is 89.1%. Fable 5 is available again.  Best AI Coding Agents (August 2026): The Scored Leaderboard, Updated After GPT-5.6 and Opus 5
- **LLM Benchmark Leaderboard 2026: Coding, Math, Reasoning and Agents | CodeSOTA | CodeSOTA**
  - URL：https://www.codesota.com/llm
  - 搜索词：Agent benchmark leaderboard 2025 2026 update coverage
  - 信源：原创/普通
  - 摘要：Results :   304  Page updated :   May 26, 2026  Tracked shortlist · dated evidence  Copper cells mark benchmark leaders [...] Codesota · Large Language ModelsThe frontier leaderboard, dated & sourcedSnapshot page updated: 2026-05-26  Tracked registry · 7 benchmarks · 130 models · per-benchmark timestamps below  # Large language models, measured honestly.  Frontier model performance across knowledge, reasoning, math, code, and sustained tool-use — every score dated, every source linked, every benchmark described in its own words. No vendor spin, no collapsed averages. [...] Gemini 3.1 Pro  Coding· verified 2026-05-26LiveCodeBench (classic)  93.5%53 models  DeepSeek-V4-Pro Max  Coding· verified 2026-04-24Tau2-Bench  89.7%19 models  GLM-5  Agentic & Tools· verified 2026-05-12MMLU (legacy saturated sanity check)  92.9%63 models  o3  Legacy Sanity Check· verified 2026-05-18  Fig 3 · Tracked leader per benchmark with count of recorded submissions and latest benchmark timestamp. Click any tile to scroll to its full leaderboard below.  § 03 · Caveat
- **Launching Agent Leaderboard v2: The Enterprise-Grade Benchmark ...**
  - URL：https://galileo.ai/blog/agent-leaderboard-v2
  - 搜索词：Agent benchmark leaderboard 2025 2026 update coverage
  - 信源：原创/普通
  - 摘要：That’s precisely the problem Agent Leaderboard v2 is built to solve. Rather than simply testing whether an agent can call the right tools, we put AIs through real enterprise scenarios spanning five industries with multi-turn dialogues and complex decision-making.  Key Results as of July 17, 2025:  GPT-4.1 leads with an average Action Completion (AC) score of 62% across all domains.  Gemini-2.5-flash excels at tool selection (94% TSQ) but struggles with task completion (38% AC). [...] That’s precisely the problem Agent Leaderboard v2 is built to solve. Rather than simply testing whether an agent can call the right tools, we put AIs through real enterprise scenarios spanning five industries with multi-turn dialogues and complex decision-making.  Key Results as of July 17, 2025:  GPT-4.1 leads with an average Action Completion (AC) score of 62% across all domains.  Gemini-2.5-flash excels at tool selection (94% TSQ) but struggles with task completion (38% AC). [...] That’s precisely the problem Agent Leaderboard v2 is built to solve. Rather than simply testing whether an agent can call the right tools, we put AIs through real enterprise scenarios spanning five industries with multi-turn dialogues and complex decision-making.  Key Results as of July 17, 2025:  GPT-4.1 leads with an average Action Completion (AC) score of 62% across all domains.  Gemini-2.5-flash excels at tool selection (94% TSQ) but struggles with task completion (38% AC).
- **LLM Leaderboard 2026 - Vellum**
  - URL：https://www.vellum.ai/llm-leaderboard
  - 搜索词：Agent benchmark leaderboard 2025 2026 update coverage
  - 信源：原创/普通
  - 摘要：Image 2896.2  GPT-5.6 Sol  Image 2995.5  Claude Mythos 5  Image 3095  Claude Fable 5  Image 3193  GPT-5.6 Luna  Image 3288.6  Claude Opus 4.8  Best in Agentic Coding (SWE Bench) | Model | Score |  --- | | GPT-5.6 Sol | 96.2% | | Claude Mythos 5 | 95.5% | | Claude Fable 5 | 95% | | GPT-5.6 Luna | 93% | | Claude Opus 4.8 | 88.6% |  New ### Best for Work Automations (AutoBench)  30%23%15%8%0%  Image 3326  Claude Opus 5  Image 3418.1  GPT-5.6 Sol  Image 3517.4  Claude Fable 5  Image 3615.5 [...] vs  Image 69  |  | Image 70Claude Opus 5 | Image 71Claude Mythos 5 |  ---  | Context size | 1,000,000 | 1,000,000 | | Cutoff date | May 2026 | Jan 2026 | | I/O cost | $5 / $25 | $10 / $50 | | Max output | 128,000 | 128,000 | | Latency  - | | Speed  - |  Best Overall (HLE)  Claude Opus 5  64.7  Claude Mythos 5  64.5  Best in Terminal Use (Terminal-Bench 2.1)  Claude Opus 5-  Claude Mythos 5  88  Best in Agentic Coding (SWE-Bench)  Claude Opus 5-  Claude Mythos 5  95.5 [...] ## Top models per tasks  ### Best in Reasoning (GPQA Diamond)  100%95%91%86%81%  Image 2396.2  Claude Sonnet 5  Image 2495.4  Claude 3 Opus  Image 2594.6  GPT-5.6 Sol  Image 2694.3  Gemini 3.1 Pro  Image 2794.2  Claude Opus 4.7  Best in Reasoning (GPQA Diamond) | Model | Score |  --- | | Claude Sonnet 5 | 96.2% | | Claude 3 Opus | 95.4% | | GPT-5.6 Sol | 94.6% | | Gemini 3.1 Pro | 94.3% | | Claude Opus 4.7 | 94.2% |  ### Best in Agentic Coding (SWE Bench)  100%94%88%82%77%  Image 2896.2
- **Risk-Adjusted Harm Scoring for Automated Red Teaming for LLMs in Financial Services**
  - URL：https://arxiv.org/html/2603.10807v1
  - 搜索词：LLM agent red teaming robustness safety benchmark methodology 2025 2026
  - 信源：一手/权威
  - 摘要：CNFinBench (Ding et al., 2025) evaluates LLMs across capability, compliance, and safety dimensions in realistic financial scenarios, while FinJailbreak (Li, 2026) focuses on adversarial prompting in finance, covering violation types including market manipulation, insider trading, regulatory evasion, and data privacy breaches. [...] Recent finance-oriented benchmarks begin to address this gap by introducing domain-aware categorizations. Cheng et al. (2025) reveal significant deficiencies in current safety alignment even when evaluated on a dedicated financial benchmark, and introduce FINBench to systematically assess regulatory risk concealment in multi-turn interactions.
- **NRT-Bench: Benchmarking Multi-Turn Red-Teaming of LLM Operator Agents in Safety-Critical Control Rooms**
  - URL：https://arxiv.org/html/2606.20408v3
  - 搜索词：LLM agent red teaming robustness safety benchmark methodology 2025 2026
  - 信源：一手/权威
  - 摘要：Agent safety evaluation has moved from isolated responses to interactive trajectories (Andriushchenko et al., 2025; Zhang et al., 2024; Kuntz et al., 2025; Yuan et al., 2024; Vijayvargiya et al., 2026). Closest to us, AgentDojo scores prompt-injection robustness via formal state-checking utility functions rather than an LLM judge (Debenedetti et al., 2024); we adopt the same attack-resistant criterion but ground it in a physical signal. A parallel literature shows that a single injected message [...] injected message can cascade through inter-agent communication (He et al., 2025; Xie et al., 2026), yet these works measure abstract harms (task failure, data leakage) and rarely model sustained adaptive pressure against a role-structured operator team; defences against such multi-agent attacks remain nascent (Miao et al., 2025). [...] LLMs are increasingly proposed for nuclear and industrial decision support (Lee and others, 2025; Xian et al., 2024; Almeldein and others, 2025; Lee, 2025), and ICS-focused benchmarks evaluate their cyber-advisory knowledge (Bhusal et al., 2024; Keppler et al., 2026). This work establishes the appetite for—and risk of—deployment near critical infrastructure, but measures capability or knowledge in isolation, not the adversarial robustness of an operator team driven toward a physically unsafe
- **[PDF] NRT-Bench: Benchmarking Multi-Turn Red-Teaming of LLM ... - arXiv**
  - URL：https://arxiv.org/pdf/2606.20408
  - 搜索词：LLM agent red teaming robustness safety benchmark methodology 2025 2026
  - 信源：一手/权威
  - 摘要：Rui Miao, Yixin Liu, Yili Wang, Xu Shen, Yue Tan, Yiwei Dai, Shirui Pan, and Xin Wang. 2025. BlindGuard: Safeguarding LLM-based Multi-Agent Systems under H. Lee et al Unknown Attacks. arXiv preprint arXiv:2508.08127.  OpenAI. 2026. Introducing GPT-5.4 mini and nano.  introducing-gpt-5-4-mini-and-nano/. Released March 17, 2026; system card addendum.  Qwen Team. 2026. Qwen3.5: Accelerating Productivity with Native Multimodal Agents. [...] Google DeepMind. 2026. Gemma 4 Technical Report. Technical Report. Google DeepMind.   Pengfei He, Yupin Lin, Shen Dong, Han Xu, Yue Xing, and Hui Liu. 2025. Red-Teaming LLM Multi-Agent Systems via Communication Attacks. arXiv preprint arXiv:2502.14847.  Gustav Keppler, Moritz Gstür, and Veit Hagenmeyer. 2026. CritBench: A Frame-work for Evaluating Cybersecurity Capabilities of Large Language Models in IEC 61850 Digital Substation Environments. arXiv preprint arXiv:2604.06019. [...] Mark Russinovich, Ahmed Salem, and Ronen Eldan. 2025. Great, Now Write an Article About That: The Crescendo Multi-Turn LLM Jailbreak Attack. In 34th USENIX Security Symposium (USENIX Security). USENIX Association, Seattle, WA, USA, 2421–2440.  Jialin Song, Xiaodong Liu, Weiwei Yang, Wuyang Chen, Mingqian Feng, Xuekai Zhu, and Jianfeng Gao. 2026. MultiBreak: A Scalable and Diverse Multi-turn Jailbreak Benchmark for Evaluating LLM Safety. arXiv preprint arXiv:2605.01687.
- **Red-Teaming Claude Opus and ChatGPT-based Security Advisors for Trusted Execution Environments**
  - URL：https://arxiv.org/html/2602.19450v1
  - 搜索词：LLM agent red teaming robustness safety benchmark methodology 2025 2026
  - 信源：一手/权威
  - 摘要：Motivated by this view, we propose TEE-RedBench 111, a TEE-grounded benchmark methodology designed around high-precision relevant questions and policy-bound misuse probes, and we focus on the transferability of prompt-induced failures between two of the most prevalently deployed LLMs (Sophia and Cai, 2026): ChatGPT-5.2 and Claude Opus-4.6. Rather than ranking TEEs, we study how assistants reason about TEEs, how errors cluster, and how to build secure workflows that remain robust even when [...] TEE-RedBench is a benchmarking methodology for evaluating general-purpose LLM assistants as TEE security decision aids. It combines (i) a TEE-grounded prompt framework that targets architecturally consequential reasoning, (ii) paraphrase and multi-turn stress tests that expose brittle failure modes, and (iii) a dual-track rubric that separates technical correctness from safety behavior (described in Tables 2 and 1). [...] We design a red-teaming methodology for evaluating prevalently used LLM (ChatGPT-5.2 and Claude Opus-4.6) as TEE security decision aids, focusing on SGX and TrustZone and on the transferability of prompt-induced failures. Our benchmark, TEE-RedBench, couples a TEE-grounded prompt taxonomy (Table 2) with a dual-track rubric (Table 1) that disentangles technical quality from safety behavior and supports conservative, worst-case risk accounting. We notice that many failures are not purely
- **SafeSearch: Automated Red-Teaming of LLM-Based Search Agents**
  - URL：https://arxiv.org/html/2509.23694v5
  - 搜索词：LLM agent red teaming robustness safety benchmark methodology 2025 2026
  - 信源：一手/权威
  - 摘要：To answer this question, we undertake a systematic red-teaming study to identify, measure, and begin to mitigate failures in search agent safety. This is non-trivial: (1) Existing evaluations (Wei et al., 2025; Wong et al., 2026) for search agents rely on human effort to craft test cases, which is labor-intensive and hard to scale. (2) Testing by crafting risk-inducing queries (Luo et al., 2025; Ou et al., 2025) can be cost-inefficient and offer limited risk coverage. [...] Agent safety benchmarks. Existing agent safety evaluations rarely cover threats to search agents or tools in depth (Ruan et al., 2024; Zhang et al., 2025b: formalizing and benchmarking attacks and defenses in LLM-based agents"); Andriushchenko et al., 2025), and when they do, the focus is often restricted to narrow threats like indirect prompt injection (Zhan et al., 2024; Liao et al., 2025). As a result, these benchmarks provide only partial coverage of the risks faced by search agents.
- **Online vs Offline Evaluation in AI: 2026 Enterprise Guide**
  - URL：https://www.lyzr.ai/blog/online-vs-offline-ai-evaluation
  - 搜索词：enterprise LLM agent evaluation deployment methodology offline-to-online transition lessons learned 2025 2026
  - 信源：原创/普通
  - 摘要：## Best Practices for Continuous Improvement  Run both evaluation modes as a single loop, not two separate programs owned by two separate teams. Offline gates releases, online watches live behavior, most mature LLM teams in 2026 run both.  Make failure capture automatic. Every production failure a monitoring system catches should have a path back into the offline test set, or the same failure will resurface after the next model update. [...] 1. New model or major prompt change → Offline first, always. No exceptions, regardless of how confident the team is. 2. Passed offline, safety-critical domain (healthcare, finance, legal) → Human evaluation pass, then shadow deployment before any user exposure. 3. Passed offline, lower-stakes domain (internal tools, recommendations) → Shadow deployment optional; move to a small A/B test (1-5% of traffic) directly. [...] A B2B sales research agent. Offline benchmarks confirm the agent retrieves accurate company data and drafts outreach that passes a rubric-based LLM-as-judge check for tone and factuality. Online, the real test is whether reps actually use the drafts without heavy editing, a signal no offline dataset can produce, because it depends entirely on how a specific sales team behaves under time pressure inside a complex B2B sales process. Lyzr’s Agent Control Plane structures exactly this kind of
- **Enterprise AI Agents: 2026 Strategy & Deployment Guide**
  - URL：https://neontri.com/blog/enterprise-ai-agents
  - 搜索词：enterprise LLM agent evaluation deployment methodology offline-to-online transition lessons learned 2025 2026
  - 信源：原创/普通
  - 摘要：To support and monitor this learning process, LLMOps platforms such as Langfuse, Phoenix (Arize), and cloud-native observability modules provide tracing, cost tracking, and quality evaluation, ensuring responsible and reliable production deployment. [...] This includes model updates, prompt drift management, monitoring and alerting, security patching, and continuous evaluation. LLMOps tooling adds cost but is essential to catch quality degradation before it becomes a business problem. [...] Enterprise AI agents operate as layered systems, in which each component plays a distinct role in translating goals into outcomes. The IDEAL architecture stack captures this structure across five critical layers: Intelligence (LLM foundation), Decision (reasoning and planning), Execution (tools and APIs), Action (orchestration), and Learned (memory and observability). Together, these layers define how agents reason, plan, interact with other systems, orchestrate workflows, and continuously
- **How to Build Enterprise-Grade LLM Agents in 2026: A Techn...**
  - URL：https://www.teneo.ai/blog/what-are-llm-agents-and-how-to-build-them-for-your-enterprise
  - 搜索词：enterprise LLM agent evaluation deployment methodology offline-to-online transition lessons learned 2025 2026
  - 信源：原创/普通
  - 摘要：Deploy your agent in a controlled environment, starting with a small group of users. Monitor its performance closely:   Accuracy: Is it correctly understanding intent and providing correct information?  Cost: How many LLM calls is it making per interaction? Are costs within budget?  Containment Rate: What percentage of requests is it handling without human escalation?  User Satisfaction: Are users finding the agent helpful? [...] Orchestration is Key: The most critical component for success is an LLM Orchestration Platform. This layer acts as the central nervous system, managing the agent’s logic, state, tool use, and security, while remaining independent of the underlying LLM.  A 5-Step Framework: This guide provides a practical, 5-step framework for building an enterprise-grade LLM agent, covering everything from use case definition to deployment and monitoring. [...] For each action your agent needs to perform, you must create a secure tool. This involves creating a dedicated, secure API endpoint that the agent can call. Crucially, never expose your internal databases or systems directly to the agent. The orchestration layer should be the only system authorized to invoke these tools, based on its defined logic.  #### Step 5: Deploy, Monitor, and Iterate
- **State of Agent Engineering**
  - URL：https://www.langchain.com/state-of-agent-engineering
  - 搜索词：enterprise LLM agent evaluation deployment methodology offline-to-online transition lessons learned 2025 2026
  - 信源：原创/普通
  - 摘要：A meaningful minority also noted that they don’t yet use agents beyond LLM chat or coding assistance, underscoring that while agent usage is widespread, broader “agentic everything” is still in its early innings.  ## Methodology  The insights from this report were aggregated from a public survey that we ran for 2 weeks from Nov 18th-Dec 2nd, 2025. We received 1340 responses. Here’s some demographic data:  Top 5 industries:     Technology (63% of respondents) [...] today.  12 June, 2026  Introduction  Insights  Methodology  Share   now have agents running in production environments, with another 30.4% actively developing agents with concrete plans to deploy them.  This marks clear growth from last year’s survey, where 51% reported having agents in production. Organizations are moving past the proof-of-concept stage into production — the question for most organizations is no longer “if” they will ship agents but “how” and “when”.  Image 11
- **Medium**
  - URL：https://medium.com/@vikramlingam/ai-agents-evolve-into-sophisticated-architectures-for-2026-enterprise-deployment-c334efbad1ab
  - 搜索词：enterprise LLM agent evaluation deployment methodology offline-to-online transition lessons learned 2025 2026
  - 信源：原创/普通
  - 摘要：to integrate into enterprise environments. Enterprises stand to gain from agents that manage multi-step workflows without constant human oversight. This evolution promises operational shifts in 2026 as companies deploy agents for tasks once requiring full teams. [...] In March 2026, arXiv researchers published HiMAC, a hierarchical macro-micro learning framework designed specifically for long-horizon LLM agents tackling complex sequential tasks. This work builds on a surge of agent-focused papers that shift focus from raw model scaling to structured architectures capable of real-world execution. Reading through these developments, I see a clear. AI agents no longer linger as theoretical ideas. They emerge as deployable systems ready to integrate into
- **Taxonomy and Consistency Analysis of Safety Benchmarks for AI Agents**
  - URL：https://arxiv.org/html/2605.16282v1
  - 搜索词：Agent evaluation robustness safety adversarial attacks benchmark 2025
  - 信源：一手/权威
  - 摘要：(Nöther et al., 2025) [R5] benchmarks the robustness of multi-agent systems to adversarially-induced harms, where a compromised insider agent manipulates others into executing harmful actions across 17 harm categories. The core dataset contains 188 harmful action examples tested across 5 agentic system implementations and 8 LLMs. All tested models are vulnerable, with attack success rates ranging from 3% (Qwen3 in debate settings) to 53% (Llama-3.1-8B). Larger models are often more vulnerable [...] (Kavathekar et al., 2025) [R5] benchmarks adversarial risks specific to multi-agent LLM systems with 300 adversarial instances across 5 high-stakes scenarios (healthcare, legal, finance, education, news) using 211 tools. It evaluates 6 attack types—including colluding agents, single-agent compromise, and impersonation—across 10 backbone LLMs in AutoGen and CrewAI configurations. The benchmark introduces the Effective Robustness Score (ERS) metric to quantify the safety–utility tradeoff, finding [...] significant after multiple-comparison correction (AgentDojo: τb=−0.53\tau\_{b}{=}{-}0.53, raw p=0.016p{=}0.016). This suggests that adversarial robustness and autonomous alignment are distinct risk dimensions that the current benchmark landscape evaluates unevenly. The bias has a temporal dimension: the agent-internal evaluation cluster (RepliBench, AgentMisalignment, PropensityBench, Scheming Propensity, Shutdown Resistance) appears only in 2025–2026, so non-adversarial evaluation is
- **OS-Harm: A Benchmark for Measuring Safety of Computer Use Agents**
  - URL：https://arxiv.org/html/2506.14866v1
  - 搜索词：Agent evaluation robustness safety adversarial attacks benchmark 2025
  - 信源：一手/权威
  - 摘要：Defenses for LLM agents. Improving the robustness of LLM agents against adversarial inputs is critical for their widespread adoption. To this end, Yang et al. (2025) conduct an empirical study on in-context defense strategies, demonstrating the effectiveness of prompting techniques in mitigating prompt injection (or context deception in their terminology) attacks. [...] Similarly, Yuan et al. (2024) present R-Judge, a benchmark designed to assess LLMs’ accuracy in recognizing safety risks within agent execution traces. Agent Security Bench (Zhang et al., 2024a) formalizes and benchmarks a wide spectrum of attacks and defenses for generic LLM agents across 10 scenarios that use over 400 different tools. More relevant to the computer use setting, Wu et al. (2025) dissect the adversarial robustness of multimodal LLM agents, revealing vulnerabilities to [...] Li et al. (2025) show that browser agents are vulnerable to simple prompt injection attacks. Some attacks like adversarial pop-ups (Zhang et al., 2024b) achieve high success rate and are trivial to implement.
- **MCP-SafetyBench: A Benchmark for Safety Evaluation of Large Language Models with Real-World MCP Servers**
  - URL：https://arxiv.org/html/2512.15163v2
  - 搜索词：Agent evaluation robustness safety adversarial attacks benchmark 2025
  - 信源：一手/权威
  - 摘要：In this paper, we present MCP-SafetyBench, a comprehensive benchmark designed to systematically evaluate the robustness of LLM Agents against MCP attacks. Built on the MCP-Universe benchmark (Luo et al., 2025), MCP-SafetyBench provides tasks that reflect realistic scenarios and multi-turn reasoning workflows, filling critical gaps in existing evaluations. [...] MCIP-bench (Jing et al., 2025) builds a taxonomy-driven dataset from function-calling corpora, and MCP-AttackBench (Xing et al., 2025) scales adversarial testing with 70k+ attack samples. MCPSecBench (Yang et al., 2025b) provides a benchmark covering seventeen representative attacks across user, host, transport, and server layers. [...] Attack Vectors in MCP. While MCP extends agent capability, it also creates new security exposures (Guo et al., 2025). Invariant Labs (Beurer-Kellner and Fischer, 2025) introduced Tool Poisoning Attacks, where malicious metadata or instructions inside tool descriptions manipulate agent behavior. They further proposed Shadowing Attacks, in which malicious servers override trusted tools, and MCP Rug Pulls, where benign tools are later updated with harmful logic.
- **TAMAS: Benchmarking Adversarial Risks in Multi-Agent LLM Systems**
  - URL：https://arxiv.org/html/2511.05269
  - 搜索词：Agent evaluation robustness safety adversarial attacks benchmark 2025
  - 信源：一手/权威
  - 摘要：To assess robustness, we adopt the Agent Risk Assessment (ARIA) framework (Tur et al., 2025), which categorizes system responses into four outcomes: ARIA-1 represents immediate refusal, indicating safe behavior; ARIA-2 denotes delayed refusal, where the system hesitates before rejecting the task; ARIA-3 reflects an intent to complete the task but a failure to do so; and ARIA-4 indicates a successful attack, representing unsafe behavior. Due to the semantic complexity of the logs, we adopt an [...] Despite significant progress in improving the collaboration and usability of multi-agent systems, their security and robustness remain largely under-explored (Hammond et al., 2025). The inclusion of multiple interacting agents introduces additional components in the system, thereby increasing the attack surface as shown in Figure 1. This increased complexity makes multi-agent setups more susceptible to diverse adversarial attacks, which can compromise the system integrity and lead to severe [...] agent safety in the context of generating and executing malicious code. Agent Security Bench (ASB) (Zhang et al., 2025: formalizing and benchmarking attacks and defenses in llm-based agents")) expands the scope to include multiple attacks and defenses, but remains limited to a single-agent setup, leaving the complexities of multi-agent interactions largely unexplored. Single-agent benchmarks evaluate isolated prompt injection or code execution risks. However, they cannot capture emergent risks
- **GuardianAgentBench: Where Agents Fail and How to Guard Them**
  - URL：https://arxiv.org/html/2607.20982v1
  - 搜索词：Agent evaluation robustness safety adversarial attacks benchmark 2025
  - 信源：一手/权威
  - 摘要：and evaluation criteria, and is further subjected to five adversarial attack modes targeting distinct failure patterns. We benchmark six frontier models—Claude Opus 4.5 (Anthropic, 2025a), GPT-5.2 Pro (OpenAI, 2025a), GPT-OSS-120B (OpenAI, 2025b), Gemini-3-Pro (Gemini Team, Google DeepMind, 2025), DeepSeek-V3.2 (DeepSeek-AI, 2025), and Qwen3-Max (Yang et al., 2025)—and find that even the strongest configuration achieves only 74.8 overall accuracy, confirming substantial room for improvement.
- **Multicrossmodal Automated Agent for Integrating Diverse Materials Science Data**
  - URL：https://arxiv.org/html/2505.15132v1
  - 搜索词：Agent evaluation future trends adaptive automated generation cross-modal 2026
  - 信源：一手/权威
  - 摘要：tailored to cross-modal understanding in materials science. Future work involves incorporating active learning (e.g., agent-driven data requests), scaling the system for larger datasets, and integrating advanced multimodal transformers. Ultimately, such AI agents can transform the growing volume of materials data into actionable knowledge, accelerating innovation in materials discovery and development. [...] features and property trends across multiple data sources, an important step toward AI-driven “digital researchers.” Our comparison with domain-specific models shows that while specialized tools remain essential, a multicrossmodal method provides holistic problem-solving capabilities previously unattainable. We also discussed evaluation strategies focusing on retrieval, accuracy, alignment, and human judgment to capture integration quality, anticipating the rise of new benchmarks tailored to [...] | Evaluation Metric | Our Agent | MultiMat | AtomAgents | GPT-4.5 |  ---  ---  | Cross-modal Retrieval Accuracy (Recall@K) | 85% | 80% | 82% | 78% | | Task-Specific Performance (Image Captioning Accuracy) | 85% | 83% | 84% | 80% | | Modality Alignment (Cosine Similarity) | 0.82 | 0.78 | 0.80 | 0.75 | | Integrated Answer Coverage (improvement) | +35% | +25% | +28% | +20% |
- **[2603.09643] MM-tau-p$^2$: Persona-Adaptive Prompting for Robust Multi-Modal Agent Evaluation in Dual-Control Settings**
  - URL：https://arxiv.org/abs/2603.09643
  - 搜索词：Agent evaluation future trends adaptive automated generation cross-modal 2026
  - 信源：一手/权威
  - 摘要：|  |  Focus to learn more  arXiv-issued DOI via DataCite | [...] Both individuals and organizations that work with arXivLabs have embraced and accepted our values of openness, community, excellence, and user data privacy. arXiv is committed to these values and only works with partners that adhere to them.  Have an idea for a project that will add value for arXiv's community? Learn more about arXivLabs.  Simons Foundation Simons Foundation International Schmidt Sciences [...] archive  # Computer Science > Emerging Technologies  # Title:MM-tau-p$^2$: Persona-Adaptive Prompting for Robust Multi-Modal Agent Evaluation in Dual-Control Settings
- **[PDF] Adaptive Multi-Agent Reasoning via Automated Workflow Generation**
  - URL：https://arxiv.org/pdf/2507.14393
  - 搜索词：Agent evaluation future trends adaptive automated generation cross-modal 2026
  - 信源：一手/权威
  - 摘要：our empirical evaluation, including a comprehensive benchmarking of Nexus Architect against state-of-the-art LRMs. Finally, Section 5 summarizes our key findings and discusses open challenges and future research directions.
- **[PDF] Adaptive Multi-Agent Reasoning via Automated Workflow Generation**
  - URL：https://www.arxiv.org/pdf/2507.14393
  - 搜索词：Agent evaluation future trends adaptive automated generation cross-modal 2026
  - 信源：一手/权威
  - 摘要：our empirical evaluation, including a comprehensive benchmarking of Nexus Architect against state-of-the-art LRMs. Finally, Section 5 summarizes our key findings and discusses open challenges and future research directions.
- **An Automated Multi-modal Evaluation Framework for Mobile Intelligent Assistants Based on Large Language Models and Multi-Agent Collaboration**
  - URL：https://arxiv.org/html/2508.09507v2
  - 搜索词：Agent evaluation future trends adaptive automated generation cross-modal 2026
  - 信源：一手/权威
  - 摘要：Recent advances in Large Language Models (LLMs) have demonstrated remarkable capabilities in understanding context, reasoning about complex scenarios, and generating human-like judgments across diverse domains (Zhang et al., 2025). These developments suggest that LLM-based evaluation systems could potentially bridge the gap between manual assessment quality and automated scalability. Multi-agent frameworks have emerged as promising approaches for addressing evaluation complexity, as [...] Inter-annotator agreement presents persistent challenges, particularly when assessing subjective dimensions such as naturalness and user satisfaction (Levi et al., 2025). The multi-modal nature of modern AI assistants introduces additional complexity that traditional evaluation frameworks struggle to address, lacking unified frameworks for assessing cross-modal consistency and temporal alignment. Traditional metrics derived from machine translation research prove inadequate for capturing [...] Recent developments in multi-agent systems show promising potential for addressing conversational AI evaluation complexity. The IntellAgent framework employs strategy-driven graph modeling with realistic event generation and interactive user-agent simulation (Levi et al., 2025). The HiMATE hierarchical framework constructs agent systems based on multi-dimensional quality metrics with inter-agent self-reflection mechanisms that significantly reduce systematic hallucination problems (Zhang et
- **Top 5 platforms for agent evals in 2025 - Articles - Braintrust**
  - URL：https://www.braintrust.dev/articles/top-5-platforms-agent-evals-2025
  - 搜索词：Agent evaluation production online offline practice case study 2025
  - 信源：原创/普通
  - 摘要：Online and offline evaluation  Braintrust supports both development-time experimentation and production monitoring. Offline evals run against curated test datasets during development, catching regressions before deployment. Online evaluation scores production traffic asynchronously, enabling teams to monitor quality at scale with configurable sampling rates.  python [...] Offline evaluation runs during development against test datasets, while online evaluation scores production traffic asynchronously. Braintrust supports both modes with the same scorer library and configurable sampling rates.  What are the best alternatives to Galileo AI? [...] Online and offline evaluation with configurable sampling for production monitoring  Deep tracing with span-level visibility and session replay  Pre-built scorer library for common patterns when needed  Brainstore purpose-built database for searching and analyzing AI interactions at scale  SOC 2 compliance with enterprise security, RBAC, and self-hosting options
- **Top Agent Evaluation Tools in 2025: Best Platforms for Reliable Enterprise Evals**
  - URL：https://www.getmaxim.ai/articles/top-agent-evaluation-tools-in-2025-best-platforms-for-reliable-enterprise-evals
  - 搜索词：Agent evaluation production online offline practice case study 2025
  - 信源：原创/普通
  - 摘要：### Observe   Sample production agent sessions for online evals; set alerts on regressions.  Instrument distributed tracing for model and tool spans (OTel) to surface root causes.  Mine failures into datasets for targeted offline re-runs and fine-tuning.  A strong platform lets teams move fluidly across layers: ship an agent, observe issues, mine logs into datasets, run targeted offline evals, fix, redeploy, and validate improvements in production. [...] Offline evals run on curated datasets before release to quantify quality, safety, latency, and cost in controlled conditions. Online evals sample real production traffic and apply evaluators continuously to detect regressions and trigger alerts.  ### How Much Production Traffic Should Be Sampled For Online Evals? [...] CI/CD tip: Gate deployment if any core evaluator drops more than 2 percentage points versus baseline or if p95 latency exceeds the SLO.  ### 5. Observe In Production And Run Online Evals  Instrument distributed tracing with spans for model calls and tool invocations. Sample 5 to 10 percent of sessions for online evaluations.
- **AI Agents in Production 2025: Enterprise Trends and Best Practices | Cleanlab**
  - URL：https://cleanlab.ai/ai-agents-in-production-2025
  - 搜索词：Agent evaluation production online offline practice case study 2025
  - 信源：原创/普通
  - 摘要：> MIT’s State of AI in Business 2025 found that hidden ROI often emerges in back-office and compliance-heavy functions. Our data shows compliance use cases are less common overall, but beginning to appear more frequently in regulated industries where oversight is a priority.  Chart comparing percent usage for AI agent use cases  ## Evaluation stays in-house, but gaps remain [...] ### 2. Invest early in reliability layers  Weak observability and immature guardrails are the most common pain points in production. Enterprises cannot scale agents without trust, and trust comes from visibility. Prioritizing evaluation, monitoring, and safeguards is the foundation for closing what MIT calls the “learning gap.”  ### 3. Build human governance into how agents operate [...] This report is based on a survey of 95 professionals across industries and company sizes. Participation was limited to leaders already operating AI agents in production with live user interactions. Respondents were screened carefully to ensure their agents were not in pilot or proof-of-concept stages but were actively deployed in workflows handling thousands of real interactions. The result is a focused view into the practices and challenges of the small minority of organizations that have
- **Offline evaluation for AI agents: Best practices | Datadog**
  - URL：https://www.datadoghq.com/blog/offline-llm-evaluations
  - 搜索词：Agent evaluation production online offline practice case study 2025
  - 信源：原创/普通
  - 摘要：Offline evaluation presents a way to unit test your AI agent in development, validating new changes against known test cases before shipping them to production. In this guide, we’ll discuss best practices for offline evaluations to help you deliver improvements for your AI agents faster and with more confidence.  To follow along, download our example application “Contract Redliner”.  ## Why offline evaluation matters [...] Offline evaluation is critical for making your agent development workflows efficient, scalable, and less incident-prone. By measuring application performance in preproduction with offline evaluations, you can prevent regressions from reaching users. [...] With a limited ability to validate changes before they reach customers, your agent is exposed to a higher potential for churn and lost revenue. Offline evaluation, where you maintain test data and run experiments within your local environment before pushing changes, is a portable and effective way to benchmark and iterate AI agents more efficiently and reliably.
- **AI Agent Evaluation Crash Course: Evaluate & Improve AI Agents for Production 🚀**
  - URL：https://www.youtube.com/watch?v=rwxcoEglXA4
  - 搜索词：Agent evaluation production online offline practice case study 2025
  - 信源：原创/普通
  - 摘要：it will give you two kinds of response and it will tell which response is good. You are selecting let's say uh let's say you are selecting uh response number one. So it is taking a feedback for you. It is trying to evaluate whether this agent is correctly working fine or not. So this is called online evaluation. After deployment your agents you continuously takes the feedback from the human and you improve the let's say agents. Okay. So that's why uh in production we have to apply offline [...] are the things we have to apply. And in online evaluation guys, you will deploy your application. And you will evaluate your real agent behavior after deployment. Example, production traces, user feedback, task success, latency, okay, percentile, tool failure rate, safety uh incidents, okay, hallucination reports, etc. That means if you are using charge GPT guys, still you will see that charge GPT will ask some feedback. Let's say sometimes whenever you ask giving any prompt, it will give you [...] want to give you uh because in industry in production what engineer does actually they perform two kinds of evaluation. One is the offline and another is the online versus evaluation. Okay. In offline evaluation guys, we have to apply whatever we have learned so far. That means the five criteria. Okay. The five criteria we have learned we can apply. Okay. That means the uh tool selections, correct answer. Okay. Then uh that uh trajectory, safety and uh lat uh latency. Okay. These are the things

## 统计
ReAct 9 步 ｜ 搜索 8 次 ｜ 结果 40 条 ｜ 发现 35 条
计划词直接命中 6 次 ｜ think 自由补充 2 次