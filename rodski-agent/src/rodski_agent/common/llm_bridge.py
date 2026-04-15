"""LLM 桥接层 — 基于 langchain 的自建 LLM 客户端。

为 rodski-agent 提供 LLM 调用能力。按 agent_type (design/execution)
使用不同的模型配置。LLM 不可用时直接抛出 LLMError，不降级。

Python 3.9 兼容：使用 ``from __future__ import annotations`` 延迟求值。
"""

from __future__ import annotations

import base64
import logging
import os
from typing import Any, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from rodski_agent.common.errors import LLMError

logger = logging.getLogger(__name__)

# 缓存已创建的 ChatModel 实例
_model_cache: dict[str, Any] = {}


def _get_config() -> Any:
    """懒加载 AgentConfig。"""
    from rodski_agent.common.config import AgentConfig
    return AgentConfig.load()


def get_chat_model(agent_type: str = "design") -> Any:
    """获取指定 agent 类型的 ChatModel 实例。

    Parameters
    ----------
    agent_type:
        ``"design"`` 或 ``"execution"``，决定使用哪组 LLM 配置。

    Returns
    -------
    BaseChatModel
        langchain ChatModel 实例。

    Raises
    ------
    LLMError
        配置错误或 API key 缺失时抛出。
    """
    if agent_type in _model_cache:
        return _model_cache[agent_type]

    config = _get_config()
    llm_config = config.llm

    if agent_type == "execution":
        provider_config = llm_config.execution
    else:
        provider_config = llm_config.design

    # 获取 API key
    api_key = os.environ.get(provider_config.api_key_env, "")
    if not api_key:
        raise LLMError(
            f"API key not found: environment variable '{provider_config.api_key_env}' is not set",
            code="E_LLM_KEY_MISSING",
            suggestion=f"Set the {provider_config.api_key_env} environment variable",
        )

    provider = provider_config.provider.lower()

    try:
        if provider in ("claude", "anthropic"):
            from langchain_anthropic import ChatAnthropic

            kwargs: dict[str, Any] = {
                "model": provider_config.model,
                "api_key": api_key,
                "temperature": provider_config.temperature,
                "max_tokens": provider_config.max_tokens,
            }
            if provider_config.base_url:
                kwargs["base_url"] = provider_config.base_url
            model = ChatAnthropic(**kwargs)

        elif provider in ("openai", "gpt"):
            from langchain_openai import ChatOpenAI

            kwargs = {
                "model": provider_config.model,
                "api_key": api_key,
                "temperature": provider_config.temperature,
                "max_tokens": provider_config.max_tokens,
            }
            if provider_config.base_url:
                kwargs["base_url"] = provider_config.base_url
            model = ChatOpenAI(**kwargs)

        else:
            raise LLMError(
                f"Unsupported LLM provider: '{provider}'",
                code="E_LLM_PROVIDER",
                suggestion="Supported providers: claude, openai",
            )
    except LLMError:
        raise
    except Exception as exc:
        raise LLMError(
            f"Failed to initialize LLM client for {agent_type}: {exc}",
            code="E_LLM_INIT",
        ) from exc

    _model_cache[agent_type] = model
    return model


def reset_cache() -> None:
    """清空模型缓存（供测试使用）。"""
    _model_cache.clear()


# ============================================================
# 高级 API：文本调用
# ============================================================


def call_llm_text(prompt: str, agent_type: str = "design") -> str:
    """调用 LLM 纯文本 API。

    Parameters
    ----------
    prompt:
        完整的 prompt 文本。
    agent_type:
        ``"design"`` 或 ``"execution"``。

    Returns
    -------
    str
        LLM 返回的文本。

    Raises
    ------
    LLMError
        LLM 不可用或调用失败时抛出。
    """
    model = get_chat_model(agent_type)
    try:
        response = model.invoke([HumanMessage(content=prompt)])
        return response.content
    except Exception as exc:
        raise LLMError(
            f"LLM text call failed: {exc}",
            code="E_LLM_CALL",
        ) from exc


# ============================================================
# 高级 API：截图分析（Vision）
# ============================================================


def analyze_screenshot(
    image_path: str,
    question: str,
    agent_type: str = "design",
) -> dict:
    """调用 LLM Vision 能力分析截图。

    Parameters
    ----------
    image_path:
        截图文件路径。
    question:
        需要回答的问题。
    agent_type:
        使用哪组 LLM 配置。

    Returns
    -------
    dict
        ``{"answer": str, "confidence": float}``

    Raises
    ------
    LLMError
        LLM 不可用或调用失败时抛出。
    """
    model = get_chat_model(agent_type)

    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    # 构造多模态消息
    message = HumanMessage(
        content=[
            {"type": "text", "text": question},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{image_data}"},
            },
        ]
    )

    try:
        response = model.invoke([message])
        return {"answer": response.content, "confidence": 0.8}
    except Exception as exc:
        raise LLMError(
            f"Screenshot analysis failed: {exc}",
            code="E_LLM_VISION",
        ) from exc
