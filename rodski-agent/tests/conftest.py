"""rodski-agent 测试公共 fixtures。

提供：
  - cli_runner: Click CliRunner 实例，用于调用 CLI 命令
  - tmp_config: 写入临时目录的 YAML 配置文件路径
  - sample_project_dir: 带有 case/model/data 标准目录结构的临时目录
"""
from __future__ import annotations

import pytest
import yaml
from click.testing import CliRunner


@pytest.fixture
def cli_runner() -> CliRunner:
    """返回 Click CliRunner 实例，用于单元测试 CLI 命令。"""
    return CliRunner()


@pytest.fixture
def tmp_config(tmp_path):
    """在临时目录中创建一个最小化的 YAML 配置文件，返回其路径（pathlib.Path）。"""
    config_data = {
        "rodski": {
            "cli_path": "python rodski/ski_run.py",
            "default_browser": "chromium",
            "headless": True,
        },
        "llm": {
            "design": {
                "provider": "claude",
                "model": "claude-sonnet-4-20250514",
                "api_key_env": "ANTHROPIC_API_KEY",
                "temperature": 0.7,
                "max_tokens": 4096,
            },
            "execution": {
                "provider": "claude",
                "model": "claude-sonnet-4-20250514",
                "api_key_env": "ANTHROPIC_API_KEY",
                "temperature": 0.1,
                "max_tokens": 2048,
            },
        },
        "omniparser": {
            "url": "http://localhost:8000",
            "timeout": 30,
        },
        "design": {
            "max_scenarios": 5,
            "max_fix_attempts": 2,
        },
        "execution": {
            "max_retry": 1,
            "screenshot_on_fail": False,
        },
        "output": {
            "format": "json",
            "verbose": True,
        },
    }
    config_file = tmp_path / "agent_config.yaml"
    config_file.write_text(yaml.dump(config_data, allow_unicode=True), encoding="utf-8")
    return config_file


@pytest.fixture
def sample_project_dir(tmp_path):
    """创建标准的测试模块目录结构（case / model / data）并返回根目录路径。

    结构：
        <tmp>/
          case/
          model/
          data/
    """
    (tmp_path / "case").mkdir()
    (tmp_path / "model").mkdir()
    (tmp_path / "data").mkdir()
    return tmp_path
