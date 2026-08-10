"""全局配置：预算、阈值、LLM 供应商。

所有数字都可以根据实际效果调，这里给的是合理的默认值。
"""

# --- 调研预算 ---
MAX_REACT_STEPS = 8          # Researcher ReAct 循环最多几步（think→act→observe 算一步）
MAX_RESULTS_PER_SEARCH = 5   # 每次 Tavily 搜索取多少条结果

# --- Planner 计划约束 ---
MIN_PLAN_QUESTIONS = 3       # 最少拆几个搜索问题
MAX_PLAN_QUESTIONS = 6       # 最多拆几个

# --- 澄清约束 ---
MAX_CLARIFY_QUESTIONS = 3    # 规划前最多问几个澄清问题

# --- 信源分层（检索后处理：相关性交给 Tavily，权威性我们打分） ---
# 静态通用权威域名（主题无关）；主题相关的权威域名由 planner 按子问题动态建议
TIER1_DOMAINS = {
    "arxiv.org", "github.com", "paperswithcode.com", "huggingface.co",
    "wikipedia.org",
}
TIER1_TLDS = {".gov", ".edu", ".gov.cn", ".edu.cn"}   # 政府 / 学术机构域名直接视为权威
FARM_DOMAINS = {                     # 已知转载农场（域名只能粗筛；原创/转载由 observe 判内容）
    "csdn.net", "blog.csdn.net", "juejin.cn",
    "baijiahao.baidu.com", "toutiao.com", "sohu.com",
}
FRESHNESS_DAYS = 365                 # Tavily 时效过滤：只返回最近 N 天（0=今天，-1=关闭）

# --- LLM 相关 ---
# 单一真源：用 LLM_PROVIDER 决定走哪一套配置，避免 OPENAI_* / DEEPSEEK_* 同时存在打架。
# 可选值："deepseek" / "openai"
LLM_PROVIDER = "deepseek"
LLM_TEMPERATURE = 0.2        # 调研类任务要低温度，减少幻觉

# DeepSeek（OpenAI 兼容协议）
# 这里只放"环境变量名"，真正的 key 通过 `export DEEPSEEK_API_KEY=xxx` 提供。
DEEPSEEK_API_KEY_ENV = "DEEPSEEK_API_KEY"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"   # V3 对外的对话模型；如用 V4 可改为 "deepseek-v4-flash"

# OpenAI（备用）
OPENAI_API_KEY_ENV = "OPENAI_API_KEY"
OPENAI_BASE_URL = "https://api.openai.com/v1"
OPENAI_MODEL = "gpt-4o-mini"
