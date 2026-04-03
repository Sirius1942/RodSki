"""测试 LLM 配置加载"""
import os
import pytest
from unittest.mock import patch
from rodski.llm.config import load_config, resolve_api_key


def test_load_default_config():
    """测试默认配置"""
    config = load_config()
    assert config["provider"] == "claude"
    assert "claude" in config["providers"]
    assert "openai" in config["providers"]


def test_load_config_with_override():
    """测试外部配置覆盖"""
    override = {"provider": "openai"}
    config = load_config(override)
    assert config["provider"] == "openai"


@patch.dict(os.environ, {"VISION_LLM_API_KEY": "test-key"})
def test_resolve_api_key_priority():
    """测试 API key 优先级"""
    provider_config = {"api_key_env": "ANTHROPIC_API_KEY"}
    api_key = resolve_api_key(provider_config)
    assert api_key == "test-key"


@patch.dict(os.environ, {"ANTHROPIC_API_KEY": "claude-key"})
def test_resolve_api_key_from_env():
    """测试从环境变量读取"""
    provider_config = {"api_key_env": "ANTHROPIC_API_KEY"}
    api_key = resolve_api_key(provider_config)
    assert api_key == "claude-key"
