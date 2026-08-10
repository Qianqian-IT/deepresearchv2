"""LLM 调用封装。

设计原则：
- 统一入口 chat(prompt) -> str，上层不用关心底层供应商
- 不支持 mock：缺 key 时直接抛错，避免调试时和真实响应混淆
"""

from __future__ import annotations

import os

from . import config


class LLMClient:
    """极简 LLM 封装：一个 chat 方法，参数全走 prompt 里控制。

    按 `config.LLM_PROVIDER` 选 deepseek / openai 二选一。
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
                f"请先 `export {env_name}=xxx` 再启动。"
            )

    @staticmethod
    def _resolve_provider_config(
        provider: str, model: str | None, api_key: str | None, base_url: str | None
    ) -> dict:
        """单一真源：按 provider 选一套配置，显式参数优先于环境变量。"""
        if provider == "deepseek":
            return {
                "model": model or config.DEEPSEEK_MODEL,
                "api_key": api_key or os.environ.get(config.DEEPSEEK_API_KEY_ENV) or config.DEEPSEEK_API_KEY,
                "base_url": base_url or config.DEEPSEEK_BASE_URL,
            }
        if provider == "openai":
            return {
                "model": model or config.OPENAI_MODEL,
                "api_key": api_key or os.environ.get(config.OPENAI_API_KEY_ENV) or config.OPENAI_API_KEY,
                "base_url": base_url or config.OPENAI_BASE_URL,
            }
        raise ValueError(
            f"未知的 LLM_PROVIDER={provider!r}，仅支持 'deepseek' / 'openai'"
        )

    def chat(self, prompt: str, *, hint: str = "generic") -> str:
        """发起一次对话。hint 用于日志 / 调试。"""
        try:
            from openai import OpenAI
        except ImportError as e:
            raise RuntimeError("需要安装 openai 包：pip install openai") from e

        client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        resp = client.chat.completions.create(
            model=self.model,
            temperature=config.LLM_TEMPERATURE,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content
