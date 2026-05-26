"""单元测试 — LocalPerceptionBackend。"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from rodski_perception.agent import LocateResult
from rodski_perception.backend import LocalPerceptionBackend


class TestBasicAttributes:
    def test_name(self):
        assert LocalPerceptionBackend.name == "local"

    def test_capabilities(self):
        caps = LocalPerceptionBackend.capabilities
        assert "locate" in caps
        assert "locate_many" in caps


class TestInit:
    def test_default_model_and_host(self):
        b = LocalPerceptionBackend()
        # access internal — but documented
        assert b._model == "qwen3-vl:2b"
        assert b._ollama_host.startswith("http://")

    def test_accepts_perception_model_alias(self):
        b = LocalPerceptionBackend(perception_model="custom:1b")
        assert b._model == "custom:1b"

    def test_explicit_model_overrides_alias(self):
        b = LocalPerceptionBackend(model="A", perception_model="B")
        assert b._model == "A"

    def test_accepts_arbitrary_kwargs(self):
        # 不应抛 TypeError
        b = LocalPerceptionBackend(unknown_key="x", perception_backend="local")
        assert b.name == "local"

    def test_env_var_for_model(self, monkeypatch):
        monkeypatch.setenv("RODSKI_PERCEPTION_MODEL", "env-model:7b")
        b = LocalPerceptionBackend()
        assert b._model == "env-model:7b"

    def test_env_var_for_host(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_HOST", "http://remote:11434")
        b = LocalPerceptionBackend()
        assert b._ollama_host == "http://remote:11434"


class TestIsAvailable:
    def test_unreachable(self):
        b = LocalPerceptionBackend()
        # 注入 probe client
        probe = MagicMock()
        probe.is_reachable.return_value = False
        b._probe_client = probe
        assert b.is_available() is False

    def test_reachable_model_installed(self):
        b = LocalPerceptionBackend(model="qwen3-vl:2b")
        probe = MagicMock()
        probe.is_reachable.return_value = True
        probe.list_models.return_value = ["qwen3-vl:2b", "llama3:8b"]
        b._probe_client = probe
        assert b.is_available() is True

    def test_reachable_model_missing(self):
        b = LocalPerceptionBackend(model="not-installed:1b")
        probe = MagicMock()
        probe.is_reachable.return_value = True
        probe.list_models.return_value = ["qwen3-vl:2b"]
        b._probe_client = probe
        assert b.is_available() is False

    def test_bare_name_matches(self):
        """请求 ``qwen3-vl`` 时，已安装 ``qwen3-vl:2b`` 应算 OK。"""
        b = LocalPerceptionBackend(model="qwen3-vl")
        probe = MagicMock()
        probe.is_reachable.return_value = True
        probe.list_models.return_value = ["qwen3-vl:2b"]
        b._probe_client = probe
        assert b.is_available() is True


class TestLocate:
    def test_delegates_to_agent(self, tiny_png):
        b = LocalPerceptionBackend()
        agent = MagicMock()
        agent.locate.return_value = LocateResult(
            bbox=(10, 20, 30, 40),
            coordinates=(15, 25),
            target_description="x",
            label="lbl",
            confidence=0.9,
            image_size=(100, 100),
            latency_ms=42,
            model="qwen3-vl:2b",
        )
        b._agent = agent
        result = b.locate(str(tiny_png), "x")
        assert result is not None
        assert result.bbox == (10, 20, 30, 40)
        assert result.coordinates == (15, 25)
        assert result.target_description == "x"
        assert result.confidence == 0.9
        assert result.latency_ms == 42
        assert result.consensus_count == 0
        assert result.hint_results == {}

    def test_returns_none_when_agent_returns_none(self, tiny_png):
        b = LocalPerceptionBackend()
        agent = MagicMock()
        agent.locate.return_value = None
        b._agent = agent
        assert b.locate(str(tiny_png), "x") is None

    def test_passes_element_type(self, tiny_png):
        b = LocalPerceptionBackend()
        agent = MagicMock()
        agent.locate.return_value = None
        b._agent = agent
        b.locate(str(tiny_png), "submit", element_type="button")
        kwargs = agent.locate.call_args.kwargs
        assert kwargs["element_type"] == "button"


class TestLocateMany:
    def test_passes_through(self, tiny_png):
        b = LocalPerceptionBackend()
        agent = MagicMock()
        r1 = LocateResult(
            bbox=(0, 0, 100, 100),
            coordinates=(10, 10),
            target_description="a",
            image_size=(100, 100),
        )
        agent.locate_many.return_value = [r1, None]
        b._agent = agent

        results = b.locate_many(str(tiny_png), ["a", "b"])
        assert len(results) == 2
        assert results[0].target_description == "a"
        assert results[1] is None

    def test_element_types_length_mismatch_raises(self, tiny_png):
        b = LocalPerceptionBackend()
        b._agent = MagicMock()
        with pytest.raises(ValueError):
            b.locate_many(str(tiny_png), ["a", "b"], element_types=["button"])

    def test_merged_element_type(self, tiny_png):
        b = LocalPerceptionBackend()
        agent = MagicMock()
        agent.locate_many.return_value = []
        b._agent = agent
        b.locate_many(str(tiny_png), ["a", "b"], element_types=[None, "input"])
        # 取第一个非空 type
        assert agent.locate_many.call_args.kwargs["element_type"] == "input"


class TestEntryPointsRegistration:
    """验证 LocalPerceptionBackend 通过 entry_points 注册可被 rodski 发现。"""

    def test_class_subclasses_rodski_backend(self):
        """确认 LocalPerceptionBackend 是 rodski PerceptionBackend 的子类。"""
        try:
            from rodski.vision.perception_interface import PerceptionBackend
        except ImportError:
            pytest.skip("rodski not installed; cannot test entry_points integration")
        assert issubclass(LocalPerceptionBackend, PerceptionBackend)

    def test_registry_discovers_after_install(self):
        """rodski Registry 能通过 entry_points 找到 local backend。

        前置：``pip install -e ./rodski-perception``（在测试运行环境中）。
        """
        try:
            from rodski.vision.registry import PerceptionRegistry
        except ImportError:
            pytest.skip("rodski not installed")
        try:
            from importlib.metadata import entry_points
            eps = entry_points(group="rodski.perception_backends")
            names = [ep.name for ep in eps]
        except Exception:
            pytest.skip("entry_points API not available")
        if "local" not in names:
            pytest.skip(
                "rodski-perception not installed via pip; "
                "run `pip install -e ./rodski-perception` first"
            )
        PerceptionRegistry.reset()
        backends = PerceptionRegistry.discover()
        assert "local" in backends
        assert issubclass(backends["local"], LocalPerceptionBackend.__mro__[0])
