"""LLM 调用封装。

设计原则：
- 统一入口 chat(prompt) -> str，上层不用关心底层供应商
- 密钥只来自「显式传入」或「环境变量」两处，**没有内置兜底 key**：
  服务层由租户 BYOK 显式传入（app/services/research_runner.py），
  CLI 场景由用户 export 环境变量。
- 不支持 mock：缺 key 时直接抛错，避免调试时和真实响应混淆
- 复用底层 client（长连接），并做超时 + 指数退避重试
"""

from __future__ import annotations

import os
import time

from . import config


class LLMClient:
    """极简 LLM 封装：一个 chat 方法，参数全走 prompt 里控制。

    按 `provider`（默认取 config.LLM_PROVIDER）选 deepseek / openai 二选一。
    密钥优先级：显式参数 > 环境变量。两者都没有则构造时直接报错。
    """

    def __init__(
        self,
        *,
        provider: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        self.provider = (provider or config.LLM_PROVIDER).lower()
        cfg = self._resolve_provider_config(self.provider, model, api_key, base_url)
        self.model = cfg["model"]
        self.api_key = cfg["api_key"]
        self.base_url = cfg["base_url"]

        if not self.api_key:
            env_name = (
                config.DEEPSEEK_API_KEY_ENV
                if self.provider == "deepseek"
                else config.OPENAI_API_KEY_ENV
            )
            raise RuntimeError(
                f"LLM provider '{self.provider}' 缺少 API key。"
                f"服务层请通过租户 BYOK 配置注入；CLI 请先 `export {env_name}=xxx` 再启动。"
            )

        # token 统计（累加器，跨多次 chat 调用）
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_calls = 0
        self.usage_calls: list[dict] = []
        self._client = None   # 惰性初始化的底层 client（复用长连接）

    @staticmethod
    def _resolve_provider_config(
        provider: str, model: str | None, api_key: str | None, base_url: str | None
    ) -> dict:
        """单一真源：按 provider 选一套默认值，显式参数优先于环境变量。

        注意：这里**不再**回退到 config 里写死的 key（已彻底移除），
        只回退到环境变量 —— 保证仓库里不可能藏着可用密钥。
        """
        if provider == "deepseek":
            return {
                "model": model or config.DEEPSEEK_MODEL,
                "api_key": api_key or os.environ.get(config.DEEPSEEK_API_KEY_ENV, ""),
                "base_url": base_url or config.DEEPSEEK_BASE_URL,
            }
        if provider == "openai":
            return {
                "model": model or config.OPENAI_MODEL,
                "api_key": api_key or os.environ.get(config.OPENAI_API_KEY_ENV, ""),
                "base_url": base_url or config.OPENAI_BASE_URL,
            }
        raise ValueError(
            f"未知的 LLM_PROVIDER={provider!r}，仅支持 'deepseek' / 'openai'"
        )

    # ------------------------------------------------------------------
    # 底层 client：复用连接 + 超时
    # ------------------------------------------------------------------

    def _get_client(self):
        """惰性构建并复用 OpenAI client（BYOK 的 key 只在内存里）。"""
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError as e:
                raise RuntimeError("需要安装 openai 包：pip install openai") from e
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=config.LLM_TIMEOUT_SECONDS,
                max_retries=0,   # 重试由本层统一控制（可观测、可退避）
            )
        return self._client

    def chat(self, prompt: str, *, hint: str = "generic") -> str:
        """发起一次对话。hint 用于日志 / 调试。内置超时与指数退避重试。"""
        client = self._get_client()
        last_err: Exception | None = None
        for attempt in range(config.LLM_MAX_RETRIES):
            try:
                resp = client.chat.completions.create(
                    model=self.model,
                    temperature=config.LLM_TEMPERATURE,
                    messages=[{"role": "user", "content": prompt}],
                )
                self._record_usage(hint, prompt, resp)
                return resp.choices[0].message.content
            except Exception as e:   # noqa: BLE001 - 网络/限流/超时统一重试
                last_err = e
                if attempt < config.LLM_MAX_RETRIES - 1:
                    time.sleep(config.LLM_RETRY_BACKOFF ** attempt)
        raise RuntimeError(
            f"LLM 调用失败（{hint}，已重试 {config.LLM_MAX_RETRIES} 次）："
            f"{type(last_err).__name__}: {last_err}"
        ) from last_err

    # ------------------------------------------------------------------
    # token 统计：每次调用记录 usage，供任务结束后落库 / CLI 打印
    # ------------------------------------------------------------------

    def _record_usage(self, hint: str, prompt: str, resp) -> None:
        """记录一次调用的 token 消耗。"""
        try:
            usage = resp.usage
            input_tokens = usage.prompt_tokens
            output_tokens = usage.completion_tokens
        except Exception:
            return  # 供应商没返回 usage 就不记

        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_calls += 1
        self.usage_calls.append({
            "hint": hint,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "prompt_chars": len(prompt),
        })

    def usage_summary(self) -> dict:
        """汇总 token 消耗：总输入 / 总输出 / 总调用数 / 每次调用明细。"""
        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "total_calls": self.total_calls,
            "per_call": self.usage_calls,
        }
