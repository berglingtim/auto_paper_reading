"""LLM 客户端抽象：兼容 DeepSeek / Kimi(Moonshot) / OpenAI 的 OpenAI 风格接口。

配置优先级：环境变量 > config.json > 默认值。
- 文本生成：默认 DeepSeek（deepseek-chat）
- 视觉理解：默认 Kimi（kimi-latest，支持图片输入）
"""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path

from openai import OpenAI

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config.json"

DEFAULTS = {
    "text": {
        "provider": "deepseek",
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
        "api_key_env": "DEEPSEEK_API_KEY",
    },
    "vision": {
        "provider": "kimi",
        "base_url": "https://api.moonshot.cn/v1",
        "model": "kimi-latest",
        "api_key_env": "MOONSHOT_API_KEY",
    },
}

_PROVIDERS = {
    "deepseek": "https://api.deepseek.com",
    "kimi": "https://api.moonshot.cn/v1",
    "moonshot": "https://api.moonshot.cn/v1",
    "openai": "https://api.openai.com/v1",
}

_MODELS = {
    "deepseek": "deepseek-chat",
    "kimi": "kimi-latest",
    "moonshot": "kimi-latest",
    "openai": "gpt-4o",
}

_KEY_ENVS = {
    "deepseek": "DEEPSEEK_API_KEY",
    "kimi": "MOONSHOT_API_KEY",
    "moonshot": "MOONSHOT_API_KEY",
    "openai": "OPENAI_API_KEY",
}


def _load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _resolve(section: str) -> dict:
    cfg = _load_config().get(section, {})
    provider = cfg.get("provider") or DEFAULTS[section]["provider"]
    base_url = (
        cfg.get("base_url")
        or os.environ.get("LLM_BASE_URL")
        or _PROVIDERS.get(provider, DEFAULTS[section]["base_url"])
    )
    model = cfg.get("model") or os.environ.get("LLM_MODEL") or _MODELS.get(provider, DEFAULTS[section]["model"])
    key_env = _KEY_ENVS.get(provider, DEFAULTS[section]["api_key_env"])
    api_key = cfg.get("api_key") or os.environ.get(key_env, "")
    return {"provider": provider, "base_url": base_url, "model": model, "api_key": api_key}


class LLMClient:
    """OpenAI 兼容的聊天客户端，支持文本与图片输入。"""

    def __init__(self, section: str = "text", timeout: int = 300):
        cfg = _resolve(section)
        if not cfg["api_key"]:
            raise RuntimeError(
                f"未配置 {cfg['provider']} 的 API key。请在 config.json 填入，"
                f"或设置环境变量 {_KEY_ENVS.get(cfg['provider'], '')}。"
            )
        self.model = cfg["model"]
        self._client = OpenAI(base_url=cfg["base_url"], api_key=cfg["api_key"], timeout=timeout)

    def chat(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        json_mode: bool = False,
        max_tokens: int | None = None,
    ) -> str:
        kwargs: dict = {"model": self.model, "messages": messages, "temperature": temperature}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        resp = self._client.chat.completions.create(**kwargs)
        return (resp.choices[0].message.content or "").strip()

    def chat_vision(self, user_text: str, image_paths: list[str | Path], temperature: float = 0.2) -> str:
        """发送文本 + 多张图片，返回模型回答。"""
        content: list[dict] = [{"type": "text", "text": user_text}]
        for p in image_paths:
            p = Path(p)
            ext = p.suffix.lstrip(".").lower()
            mime = "image/png" if ext == "png" else "image/jpeg"
            b64 = base64.b64encode(p.read_bytes()).decode()
            content.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})
        return self.chat([{"role": "user", "content": content}], temperature=temperature)
