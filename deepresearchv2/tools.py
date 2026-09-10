"""基础工具：Tavily 搜索 + 信源分层。

分层原理：搜索引擎只保证"相关性"，不保证"权威/新鲜"。所以搜索照常全量返回，
检索后我们做纯确定性的后处理 —— 按域名打信源分级 → 稳定排序（Tier1 提到前面，
同层保持 Tavily 原序，不丢结果）→ 标签随结果透传给 observe 做引用权衡。
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from urllib.parse import urlparse

from . import config

TIER_LABEL = {1: "一手/权威", 2: "原创/普通", 3: "转载农场"}


def _registered_host(url: str) -> str:
    """取注册域：去掉协议 / 路径 / www. 前缀。"""
    try:
        host = urlparse(url if "://" in url else "http://" + url).netloc.lower()
    except ValueError:
        return ""
    return host.removeprefix("www.")


def tier_for_url(url: str, topic_domains: set[str] | None = None) -> int:
    """信源分级：1 一手/权威，2 原创/普通，3 转载农场。

    匹配顺序：主题权威域名（planner 建议）→ 静态通用权威表 / .gov .edu → 农场表
    → 默认 2（未知域名不误杀）。纯域名匹配，零成本。
    """
    host = _registered_host(url)
    if not host:
        return 2
    tables = [
        ((topic_domains or set()) | config.TIER1_DOMAINS, 1),
        (config.FARM_DOMAINS, 3),
    ]
    for domains, tier in tables:
        if any(host == d or host.endswith("." + d) for d in domains):
            return tier
    if any(host.endswith(tld) for tld in config.TIER1_TLDS):
        return 1
    return 2


@dataclass
class SearchResult:
    """单条检索结果。"""
    title: str
    url: str
    snippet: str
    query_origin: str = ""   # 由哪条搜索得到，用于结果归类
    source_tier: int = 2     # 信源分级：1 一手/权威，2 原创/普通，3 转载农场


class SearchTool:
    """对外搜索的统一入口，内部走 Tavily。

    密钥只来自「显式传入」或「环境变量」，**没有内置兜底 key**：
    服务层由租户 BYOK 显式传入，CLI 场景由用户 export 环境变量。
    """

    def __init__(self, tavily_api_key: str | None = None):
        self.key = tavily_api_key or os.environ.get(config.TAVILY_API_KEY_ENV, "")
        if not self.key:
            raise RuntimeError(
                f"缺少 {config.TAVILY_API_KEY_ENV}。"
                "服务层请通过租户 BYOK 配置注入；CLI 请先 `export TAVILY_API_KEY=tvly-xxx` 再启动。"
            )

    def search(
        self,
        query: str,
        *,
        max_results: int = config.MAX_RESULTS_PER_SEARCH,
        include_domains: list[str] | None = None,
        days: int = config.FRESHNESS_DAYS,
        topic_domains: set[str] | None = None,
    ) -> list[SearchResult]:
        """Tavily 搜索 → 信源打分 → 稳定排序。

        include_domains: 权威域名白名单（优先限定，graph 层负责空结果降级重搜）
        days:           时效过滤，只返回最近 N 天（-1/0 关闭）
        topic_domains:  planner 建议的权威域名，给结果打信源分级用
        """
        try:
            from tavily import TavilyClient
        except ImportError as e:
            raise RuntimeError("需要安装 tavily：pip install tavily-python") from e

        params: dict = {
            "query": query,
            "search_depth": "basic",
            "max_results": max_results,
            "include_answer": False,
        }
        if include_domains:
            params["include_domains"] = include_domains
        if days and days > 0:
            params["days"] = days

        client = TavilyClient(api_key=self.key)
        last_err: Exception | None = None
        resp = None
        for attempt in range(config.SEARCH_MAX_RETRIES):
            try:
                resp = client.search(**params)
                break
            except Exception as e:   # noqa: BLE001 - 网络/限流统一重试
                last_err = e
                if attempt < config.SEARCH_MAX_RETRIES - 1:
                    time.sleep(config.LLM_RETRY_BACKOFF ** attempt)
        if resp is None:
            raise RuntimeError(
                f"Tavily 搜索失败（{query!r}，已重试 {config.SEARCH_MAX_RETRIES} 次）："
                f"{type(last_err).__name__}: {last_err}"
            ) from last_err

        results = [
            SearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=item.get("content", ""),
                query_origin=query,
            )
            for item in resp.get("results", [])
        ]
        for r in results:
            r.source_tier = tier_for_url(r.url, topic_domains)
        results.sort(key=lambda r: r.source_tier)   # 稳定排序：权威提前，同层保持原序，不丢结果
        return results
