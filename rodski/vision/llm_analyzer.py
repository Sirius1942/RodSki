"""
LLM Analyzer — 多模态 LLM 语义识别层

支持 Claude / OpenAI GPT-4V / Qwen-VL，通过 vision_config.yaml 中的
``llm.provider`` 字段区分。
API Key 优先级：环境变量 VISION_LLM_API_KEY > llm.api_key_env 指定的变量 > ~/.claude/ 配置。
"""

from __future__ import annotations

import base64
import json
import logging
import os
import pathlib
from typing import Any

logger = logging.getLogger(__name__)

# 默认配置（当 yaml 文件不可用时的兜底值）
_DEFAULT_LLM_CONFIG: dict[str, Any] = {
    "provider": "claude",
    "model": "claude-opus-4-6",
    "base_url": "",
    "api_key_env": "ANTHROPIC_API_KEY",
    "timeout": 10,
    "max_tokens": 1024,
}

_CONFIG_PATH = (
    pathlib.Path(__file__).parent.parent  # rodski/
    / "config"
    / "vision_config.yaml"
)

def _load_llm_config(config: dict | None, global_vars: dict | None = None) -> dict[str, Any]:
    """合并配置：外部传入 > 全局变量 > yaml 文件 > 默认值。"""
    base = dict(_DEFAULT_LLM_CONFIG)
    if _CONFIG_PATH.exists():
        try:
            import yaml  # optional dependency
            with _CONFIG_PATH.open(encoding="utf-8") as fh:
                raw = yaml.safe_load(fh) or {}
            base.update(raw.get("llm", {}))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to load vision_config.yaml: %s", exc)

    # 从全局变量读取 OpenAI 配置
    if global_vars:
        if global_vars.get("VisionConfig.OPENAI_BASE_URL") or global_vars.get("OPENAI_BASE_URL"):
            base["base_url"] = global_vars.get("VisionConfig.OPENAI_BASE_URL") or global_vars.get("OPENAI_BASE_URL")
        if global_vars.get("VisionConfig.OPENAI_MODEL") or global_vars.get("OPENAI_MODEL"):
            base["model"] = global_vars.get("VisionConfig.OPENAI_MODEL") or global_vars.get("OPENAI_MODEL")
            base["provider"] = "openai"  # 自动切换到 openai provider

    if config:
        base.update(config)
    return base


def _resolve_api_key(cfg: dict[str, Any], global_vars: dict | None = None) -> str | None:
    """按优先级解析 API Key。"""
    # 0. 从全局变量读取（最高优先级）
    if global_vars:
        # 支持 ANTHROPIC_API_KEY 和 OPENAI_API_KEY
        key = (global_vars.get("VisionConfig.ANTHROPIC_API_KEY") or
               global_vars.get("VisionConfig.OPENAI_API_KEY") or
               global_vars.get("ANTHROPIC_API_KEY") or
               global_vars.get("OPENAI_API_KEY"))
        if key:
            return key
    # 1. 专属覆盖环境变量
    key = os.environ.get("VISION_LLM_API_KEY")
    if key:
        return key
    # 2. yaml 中指定的环境变量或标准环境变量
    env_name = cfg.get("api_key_env", "ANTHROPIC_API_KEY")
    key = os.environ.get(env_name)
    if key:
        return key
    # 2b. OpenAI 标准环境变量
    if cfg.get("provider") in ("openai", "qwen"):
        key = os.environ.get("OPENAI_API_KEY")
        if key:
            return key
    # 3. ~/.claude/ 配置（仅 Claude provider）
    if cfg.get("provider", "claude") == "claude":
        claude_cfg = pathlib.Path.home() / ".claude" / ".credentials.json"
        if claude_cfg.exists():
            try:
                data = json.loads(claude_cfg.read_text(encoding="utf-8"))
                key = data.get("api_key") or data.get("ANTHROPIC_API_KEY")
                if key:
                    return key
            except Exception:  # noqa: BLE001
                pass
    return None


# ---------------------------------------------------------------------------
# Provider-specific call helpers
# ---------------------------------------------------------------------------

def _encode_image(path: str) -> tuple[str, str]:
    """Base64-encode an image file; return (base64_data, media_type)."""
    suffix = pathlib.Path(path).suffix.lower()
    media_map = {".png": "image/png", ".jpg": "image/jpeg",
                 ".jpeg": "image/jpeg", ".webp": "image/webp",
                 ".gif": "image/gif"}
    media_type = media_map.get(suffix, "image/png")
    with open(path, "rb") as fh:
        data = base64.standard_b64encode(fh.read()).decode()
    return data, media_type


def _build_prompt(elements: list[dict]) -> str:
    """构建发送给 LLM 的文字 prompt。"""
    element_summary = json.dumps(
        [{"index": i, "content": e.get("content", ""),
          "type": e.get("type", "")} for i, e in enumerate(elements)],
        ensure_ascii=False,
    )
    return (
        "你是一个 UI 元素语义分析助手。"
        "以下是从截图中识别出的 UI 元素列表（JSON 格式），"
        "请为每个元素生成一个简洁的中文语义标签（semantic_label），"
        "描述该元素的功能或用途。\n\n"
        f"元素列表：\n{element_summary}\n\n"
        "请严格以如下 JSON 数组格式返回，不要有任何多余内容：\n"
        '[{"index": 0, "semantic_label": "..."}，...]'
    )


def _call_claude(
    cfg: dict[str, Any],
    api_key: str,
    screenshot_path: str,
    elements: list[dict],
) -> list[dict]:
    """调用 Anthropic Claude 多模态 API。"""
    import anthropic  # 延迟导入，允许在无此库时导入本模块

    kwargs: dict[str, Any] = {"api_key": api_key}
    if cfg.get("base_url"):
        kwargs["base_url"] = cfg["base_url"]

    client = anthropic.Anthropic(**kwargs)
    img_data, media_type = _encode_image(screenshot_path)
    prompt_text = _build_prompt(elements)

    response = client.messages.create(
        model=cfg["model"],
        max_tokens=cfg["max_tokens"],
        timeout=cfg["timeout"],
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": img_data,
                        },
                    },
                    {"type": "text", "text": prompt_text},
                ],
            }
        ],
    )
    raw = response.content[0].text
    return json.loads(raw)


def _call_openai(
    cfg: dict[str, Any],
    api_key: str,
    screenshot_path: str,
    elements: list[dict],
) -> list[dict]:
    """调用 OpenAI GPT-4V API。"""
    import openai  # 延迟导入

    kwargs: dict[str, Any] = {"api_key": api_key}
    if cfg.get("base_url"):
        kwargs["base_url"] = cfg["base_url"]

    client = openai.OpenAI(**kwargs)
    img_data, media_type = _encode_image(screenshot_path)
    prompt_text = _build_prompt(elements)

    response = client.chat.completions.create(
        model=cfg["model"],
        max_tokens=cfg["max_tokens"],
        timeout=cfg["timeout"],
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type};base64,{img_data}"
                        },
                    },
                    {"type": "text", "text": prompt_text},
                ],
            }
        ],
    )
    raw = response.choices[0].message.content
    return json.loads(raw)


def _call_qwen(
    cfg: dict[str, Any],
    api_key: str,
    screenshot_path: str,
    elements: list[dict],
) -> list[dict]:
    """调用 Qwen-VL API（通过 openai 兼容接口）。"""
    import openai  # 延迟导入

    base_url = cfg.get("base_url") or "https://dashscope.aliyuncs.com/compatible-mode/v1"
    client = openai.OpenAI(api_key=api_key, base_url=base_url)
    img_data, media_type = _encode_image(screenshot_path)
    prompt_text = _build_prompt(elements)

    response = client.chat.completions.create(
        model=cfg["model"],
        max_tokens=cfg["max_tokens"],
        timeout=cfg["timeout"],
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type};base64,{img_data}"
                        },
                    },
                    {"type": "text", "text": prompt_text},
                ],
            }
        ],
    )
    raw = response.choices[0].message.content
    return json.loads(raw)


# ---------------------------------------------------------------------------
# Public class
# ---------------------------------------------------------------------------

class LLMAnalyzer:
    """多模态 LLM 客户端，为 OmniParser 元素列表附加语义标签。"""

    def __init__(self, config: dict | None = None, global_vars: dict | None = None) -> None:
        self._cfg = _load_llm_config(config, global_vars)
        self._global_vars = global_vars
        self._api_key = _resolve_api_key(self._cfg, global_vars)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(
        self,
        screenshot_path: str,
        elements: list[dict],
    ) -> list[dict]:
        """
        给每个 OmniParser 元素附加 ``semantic_label`` 字段。

        Parameters
        ----------
        screenshot_path:
            截图文件路径（PNG/JPEG/WebP）。
        elements:
            OmniParser 返回的 ``parsed_content_list``。

        Returns
        -------
        增强后的元素列表（in-place 修改后的副本），每个元素含
        ``semantic_label`` 字段。若 LLM 调用失败，则保留原始列表。
        """
        if not elements:
            return elements

        if not self._api_key:
            logger.warning(
                "No API key found for provider '%s'; skipping LLM analysis.",
                self._cfg.get("provider"),
            )
            return elements

        try:
            labels = self._call_llm(screenshot_path, elements)
            return self._merge_labels(elements, labels)
        except Exception as exc:  # noqa: BLE001
            logger.error("LLM analysis failed: %s", exc)
            return elements

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _call_llm(self, screenshot_path: str, elements: list[dict]) -> list[dict]:
        """根据 provider 分发到对应的调用实现。"""
        provider = self._cfg.get("provider", "claude").lower()
        dispatch = {
            "claude": _call_claude,
            "openai": _call_openai,
            "qwen": _call_qwen,
        }
        fn = dispatch.get(provider)
        if fn is None:
            raise ValueError(f"Unsupported LLM provider: {provider!r}")
        return fn(self._cfg, self._api_key, screenshot_path, elements)

    @staticmethod
    def _merge_labels(elements: list[dict], labels: list[dict]) -> list[dict]:
        """将 LLM 返回的语义标签合并回元素列表。"""
        label_map: dict[int, str] = {}
        for item in labels:
            idx = item.get("index")
            label = item.get("semantic_label", "")
            if idx is not None and label:
                label_map[idx] = label

        result = []
        for i, elem in enumerate(elements):
            enhanced = dict(elem)
            enhanced["semantic_label"] = label_map.get(i, elem.get("content", ""))
            result.append(enhanced)
        return result
