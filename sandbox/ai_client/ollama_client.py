"""Lightweight synchronous client for Ollama's ``POST /api/generate`` endpoint.

Provides ``ask_ollama(prompt, model)`` — a single-call helper that sends a
prompt to a local Ollama server and returns the generated text.

Usage::

    from ai_client.ollama_client import ask_ollama
    reply = ask_ollama("你好")
"""

from __future__ import annotations

import json
import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_OLLAMA_BASE_URL: str = "http://localhost:11434"
_GENERATE_ENDPOINT: str = f"{_OLLAMA_BASE_URL}/api/generate"
_DEFAULT_MODEL: str = "qwen2:7b"
_REQUEST_TIMEOUT: int = 30  # seconds


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def ask_ollama(prompt: str, model: str = _DEFAULT_MODEL) -> str:
    """Send *prompt* to a local Ollama instance and return the generated text.

    Args:
        prompt: The user / system prompt string to send.
        model: Ollama model name (default ``"qwen2:7b"``).

    Returns:
        The model's response text.  Returns an empty string when the server
        is unreachable, the request times out, the response is empty, or an
        unexpected error occurs.  Callers should treat an empty return as a
        signal to use fallback rules.
    """
    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }

    try:
        resp = requests.post(
            _GENERATE_ENDPOINT,
            json=payload,
            timeout=_REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
    except requests.exceptions.ConnectionError:
        logger.error(
            "无法连接到 Ollama 服务 (%s)。请确认 Ollama 已启动：ollama serve",
            _OLLAMA_BASE_URL,
        )
        return ""
    except requests.exceptions.Timeout:
        logger.warning("Ollama 请求超时（%d 秒），模型 %s 可能响应过慢，将使用兜底规则。", _REQUEST_TIMEOUT, model)
        return ""
    except requests.exceptions.RequestException as exc:
        logger.error("Ollama 请求失败: %s", exc)
        return ""

    try:
        data: dict[str, Any] = resp.json()
    except json.JSONDecodeError as exc:
        logger.error("Ollama 返回了非 JSON 响应: %s", exc)
        return ""

    response_text: str = data.get("response", "")
    if not response_text:
        logger.warning("Ollama 返回了空响应（model=%s）。", model)

    return response_text


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    test_prompt = "你好，请用一句话介绍你自己。"
    print(f"→ 发送 prompt: {test_prompt!r}")
    result = ask_ollama(test_prompt)

    if result:
        print(f"← Ollama 响应:\n{result}")
    else:
        print("← 未收到响应。如果 Ollama 未运行，请先执行: ollama serve")
        print("  （可切换到 Mock 模式测试：将 OLLAMA_MOCK=true 加入环境变量。）")
