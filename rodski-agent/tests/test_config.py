"""AgentConfig 配置加载器单元测试。

测试 src/rodski_agent/common/config.py 中 AgentConfig 及各 Section 数据类的行为。
覆盖：默认值加载、YAML 文件加载、环境变量覆盖、类型强制转换、字段校验。
所有文件系统操作通过 pytest tmp_path 隔离；环境变量通过 monkeypatch 注入。
"""
from __future__ import annotations

import os

import pytest
import yaml

from rodski_agent.common.config import (
    AgentConfig,
    DesignConfig,
    ExecutionConfig,
    LLMConfig,
    OmniParserConfig,
    OutputConfig,
    RodskiConfig,
    _coerce,
)


class TestDefaultConfig:
    """AgentConfig —— 默认值加载（无配置文件时）"""

    def test_load_无配置文件返回默认值(self, monkeypatch, tmp_path):
        """AgentConfig.load() 在无配置文件环境下应使用内置默认值。"""
        # 清除可能存在的环境变量，并切换到无配置文件的目录
        monkeypatch.delenv("RODSKI_AGENT_CONFIG", raising=False)
        monkeypatch.chdir(tmp_path)
        cfg = AgentConfig.load()
        assert isinstance(cfg, AgentConfig)

    def test_rodski_section_默认值(self, monkeypatch, tmp_path):
        """rodski section 默认值应符合设计约束文档中的记录。"""
        monkeypatch.delenv("RODSKI_AGENT_CONFIG", raising=False)
        monkeypatch.chdir(tmp_path)
        cfg = AgentConfig.load()
        assert cfg.rodski.cli_path == "python rodski/ski_run.py"
        assert cfg.rodski.default_browser == "chromium"
        assert cfg.rodski.headless is True

    def test_design_section_默认值(self, monkeypatch, tmp_path):
        """design section 默认值应与源码 DesignConfig 一致。"""
        monkeypatch.delenv("RODSKI_AGENT_CONFIG", raising=False)
        monkeypatch.chdir(tmp_path)
        cfg = AgentConfig.load()
        assert cfg.design.max_scenarios == 10
        assert cfg.design.max_fix_attempts == 3

    def test_execution_section_默认值(self, monkeypatch, tmp_path):
        """execution section 默认值应与源码 ExecutionConfig 一致。"""
        monkeypatch.delenv("RODSKI_AGENT_CONFIG", raising=False)
        monkeypatch.chdir(tmp_path)
        cfg = AgentConfig.load()
        assert cfg.execution.max_retry == 3
        assert cfg.execution.screenshot_on_fail is True
        assert cfg.execution.diagnosis_enabled is True

    def test_output_section_默认值(self, monkeypatch, tmp_path):
        """output section 默认值应与源码 OutputConfig 一致。"""
        monkeypatch.delenv("RODSKI_AGENT_CONFIG", raising=False)
        monkeypatch.chdir(tmp_path)
        cfg = AgentConfig.load()
        assert cfg.output.format == "human"
        assert cfg.output.verbose is False

    def test_llm_section_类型正确(self, monkeypatch, tmp_path):
        """llm section 应返回 LLMConfig 实例。"""
        monkeypatch.delenv("RODSKI_AGENT_CONFIG", raising=False)
        monkeypatch.chdir(tmp_path)
        cfg = AgentConfig.load()
        assert isinstance(cfg.llm, LLMConfig)

    def test_omniparser_section_类型正确(self, monkeypatch, tmp_path):
        """omniparser section 应返回 OmniParserConfig 实例。"""
        monkeypatch.delenv("RODSKI_AGENT_CONFIG", raising=False)
        monkeypatch.chdir(tmp_path)
        cfg = AgentConfig.load()
        assert isinstance(cfg.omniparser, OmniParserConfig)


class TestYamlFileLoading:
    """AgentConfig —— 指定 YAML 文件加载"""

    def test_load_指定路径成功加载(self, tmp_config):
        """AgentConfig.load(path) 应成功从指定 YAML 文件加载配置。"""
        cfg = AgentConfig.load(path=tmp_config)
        assert isinstance(cfg, AgentConfig)

    def test_load_yaml文件覆盖默认值(self, tmp_config):
        """YAML 文件中的值应覆盖内置默认值。"""
        cfg = AgentConfig.load(path=tmp_config)
        # tmp_config fixture 写入了 max_scenarios=5
        assert cfg.design.max_scenarios == 5
        assert cfg.design.max_fix_attempts == 2

    def test_load_yaml文件execution字段(self, tmp_config):
        """YAML 文件中的 execution 字段应被正确解析。"""
        cfg = AgentConfig.load(path=tmp_config)
        assert cfg.execution.max_retry == 1
        assert cfg.execution.screenshot_on_fail is False

    def test_load_yaml文件output字段(self, tmp_config):
        """YAML 文件中的 output 字段应被正确解析。"""
        cfg = AgentConfig.load(path=tmp_config)
        assert cfg.output.format == "json"
        assert cfg.output.verbose is True

    def test_load_不存在的路径抛出FileNotFoundError(self, tmp_path):
        """指定不存在的配置文件路径时应抛出 FileNotFoundError。"""
        non_existent = tmp_path / "no_such_file.yaml"
        with pytest.raises(FileNotFoundError):
            AgentConfig.load(path=non_existent)

    def test_load_空yaml文件使用默认值(self, tmp_path, monkeypatch):
        """空 YAML 文件（safe_load 返回 None）时应回退到默认值。"""
        empty_file = tmp_path / "agent_config.yaml"
        empty_file.write_text("", encoding="utf-8")
        monkeypatch.delenv("RODSKI_AGENT_CONFIG", raising=False)
        cfg = AgentConfig.load(path=empty_file)
        # 空文件应回退到默认值
        assert cfg.design.max_scenarios == 10

    def test_load_部分字段yaml只覆盖指定字段(self, tmp_path, monkeypatch):
        """YAML 文件中只写部分字段时，未写的字段应保持默认值。"""
        monkeypatch.delenv("RODSKI_AGENT_CONFIG", raising=False)
        partial = tmp_path / "partial.yaml"
        partial.write_text(yaml.dump({"design": {"max_scenarios": 7}}), encoding="utf-8")
        cfg = AgentConfig.load(path=partial)
        assert cfg.design.max_scenarios == 7
        # 未指定的字段保持默认
        assert cfg.design.max_fix_attempts == 3


class TestEnvVarOverrides:
    """AgentConfig —— 环境变量覆盖"""

    def test_env_覆盖二级字段(self, monkeypatch, tmp_path):
        """RODSKI_AGENT_DESIGN__MAX_SCENARIOS 应覆盖 design.max_scenarios。"""
        monkeypatch.delenv("RODSKI_AGENT_CONFIG", raising=False)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("RODSKI_AGENT_DESIGN__MAX_SCENARIOS", "99")
        cfg = AgentConfig.load()
        assert cfg.design.max_scenarios == 99

    def test_env_覆盖布尔值_true(self, monkeypatch, tmp_path):
        """RODSKI_AGENT_OUTPUT__VERBOSE=true 应被强制转换为 bool True。"""
        monkeypatch.delenv("RODSKI_AGENT_CONFIG", raising=False)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("RODSKI_AGENT_OUTPUT__VERBOSE", "true")
        cfg = AgentConfig.load()
        assert cfg.output.verbose is True

    def test_env_覆盖布尔值_false(self, monkeypatch, tmp_path):
        """RODSKI_AGENT_RODSKI__HEADLESS=false 应被强制转换为 bool False。"""
        monkeypatch.delenv("RODSKI_AGENT_CONFIG", raising=False)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("RODSKI_AGENT_RODSKI__HEADLESS", "false")
        cfg = AgentConfig.load()
        assert cfg.rodski.headless is False

    def test_env_优先级高于yaml文件(self, monkeypatch, tmp_config):
        """环境变量覆盖应优先于 YAML 文件中的值。"""
        monkeypatch.setenv("RODSKI_AGENT_DESIGN__MAX_SCENARIOS", "42")
        cfg = AgentConfig.load(path=tmp_config)
        # tmp_config 中 max_scenarios=5，环境变量应覆盖为 42
        assert cfg.design.max_scenarios == 42

    def test_env_config_路径变量(self, monkeypatch, tmp_config):
        """RODSKI_AGENT_CONFIG 环境变量应指向配置文件路径并被加载。"""
        monkeypatch.setenv("RODSKI_AGENT_CONFIG", str(tmp_config))
        # 不传 path 参数，通过环境变量自动发现
        cfg = AgentConfig.load()
        assert cfg.design.max_scenarios == 5


class TestToDict:
    """AgentConfig.to_dict() —— 序列化"""

    def test_to_dict_返回字典(self, monkeypatch, tmp_path):
        """to_dict() 应返回包含所有 section 的字典。"""
        monkeypatch.delenv("RODSKI_AGENT_CONFIG", raising=False)
        monkeypatch.chdir(tmp_path)
        cfg = AgentConfig.load()
        d = cfg.to_dict()
        assert isinstance(d, dict)
        assert "rodski" in d
        assert "llm" in d
        assert "design" in d
        assert "execution" in d
        assert "output" in d

    def test_to_dict_值类型正确(self, monkeypatch, tmp_path):
        """to_dict() 返回字典中的值类型应与源码一致。"""
        monkeypatch.delenv("RODSKI_AGENT_CONFIG", raising=False)
        monkeypatch.chdir(tmp_path)
        cfg = AgentConfig.load()
        d = cfg.to_dict()
        assert isinstance(d["design"]["max_scenarios"], int)
        assert isinstance(d["rodski"]["headless"], bool)


class TestCoercion:
    """_coerce() —— 环境变量类型强制转换"""

    def test_coerce_true字符串(self):
        """'true' 应被转换为 bool True。"""
        assert _coerce("true") is True

    def test_coerce_yes字符串(self):
        """'yes' 应被转换为 bool True。"""
        assert _coerce("yes") is True

    def test_coerce_1字符串(self):
        """'1' 应被转换为 bool True。"""
        assert _coerce("1") is True

    def test_coerce_false字符串(self):
        """'false' 应被转换为 bool False。"""
        assert _coerce("false") is False

    def test_coerce_no字符串(self):
        """'no' 应被转换为 bool False。"""
        assert _coerce("no") is False

    def test_coerce_0字符串(self):
        """'0' 应被转换为 bool False。"""
        assert _coerce("0") is False

    def test_coerce_整数字符串(self):
        """纯数字字符串应被转换为 int。"""
        assert _coerce("42") == 42
        assert isinstance(_coerce("42"), int)

    def test_coerce_浮点字符串(self):
        """浮点字符串应被转换为 float。"""
        result = _coerce("3.14")
        assert abs(result - 3.14) < 1e-9
        assert isinstance(result, float)

    def test_coerce_普通字符串(self):
        """普通字符串应保持原值。"""
        assert _coerce("chromium") == "chromium"

    def test_coerce_大写true(self):
        """'TRUE' 应被转换为 bool True（大小写不敏感）。"""
        assert _coerce("TRUE") is True
