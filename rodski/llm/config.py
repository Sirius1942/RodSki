"""LLM 配置加载模块"""
import os
import logging
import pathlib
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG = {
    "provider": "claude",
    "providers": {
        "claude": {
            "model": "claude-opus-4-6",
            "base_url": "",
            "api_key_env": "ANTHROPIC_API_KEY",
            "timeout": 10,
            "max_tokens": 1024,
        },
        "openai": {
            "model": "gpt-4o",
            "base_url": "https://api.openai.com/v1",
            "api_key_env": "OPENAI_API_KEY",
            "timeout": 10,
            "max_tokens": 2000,
        },
    },
    "capabilities": {},
}

_CONFIG_PATH = pathlib.Path(__file__).parent.parent / "config" / "llm_config.yaml"


def load_config(config: dict = None, global_vars: dict = None) -> dict[str, Any]:
    """加载配置，优先级：外部传入 > 全局变量 > yaml > 默认值"""
    import copy
    result = copy.deepcopy(_DEFAULT_CONFIG)

    # 加载 yaml
    if _CONFIG_PATH.exists():
        try:
            import yaml
            with _CONFIG_PATH.open(encoding="utf-8") as f:
                yaml_config = yaml.safe_load(f) or {}
            _merge_dict(result, yaml_config)
        except Exception as e:
            logger.warning(f"Failed to load llm_config.yaml: {e}")

    # 全局变量（向后兼容）
    if global_vars:
        _apply_global_vars(result, global_vars)

    # 外部传入
    if config:
        _merge_dict(result, config)

    return result


def _merge_dict(base: dict, update: dict):
    """递归合并字典"""
    for key, value in update.items():
        if isinstance(value, dict) and key in base and isinstance(base[key], dict):
            _merge_dict(base[key], value)
        else:
            base[key] = value


def _apply_global_vars(config: dict, global_vars: dict):
    """应用全局变量（向后兼容 vision_config）"""
    if global_vars.get("VisionConfig.OPENAI_BASE_URL"):
        config["providers"]["openai"]["base_url"] = global_vars["VisionConfig.OPENAI_BASE_URL"]
    if global_vars.get("VisionConfig.OPENAI_MODEL"):
        config["providers"]["openai"]["model"] = global_vars["VisionConfig.OPENAI_MODEL"]
        config["provider"] = "openai"


def resolve_api_key(provider_config: dict) -> str:
    """解析 API key，优先级：VISION_LLM_API_KEY > 指定环境变量 > 默认环境变量"""
    # 优先使用 VISION_LLM_API_KEY
    api_key = os.getenv("VISION_LLM_API_KEY")
    if api_key:
        return api_key

    # 使用配置指定的环境变量
    api_key_env = provider_config.get("api_key_env")
    if api_key_env:
        api_key = os.getenv(api_key_env)
        if api_key:
            return api_key

    # Claude 特殊处理：尝试 ~/.claude/.credentials.json
    if api_key_env == "ANTHROPIC_API_KEY":
        try:
            import json
            cred_file = pathlib.Path.home() / ".claude" / ".credentials.json"
            if cred_file.exists():
                with cred_file.open() as f:
                    creds = json.load(f)
                    return creds.get("api_key", "")
        except Exception:
            pass

    return ""
