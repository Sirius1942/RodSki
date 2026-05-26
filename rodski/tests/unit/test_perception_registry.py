"""PerceptionRegistry + PerceptionBackend 抽象接口单元测试 (iter-54b T6)

覆盖目标（来自 ``.pb/iterations/iteration-54b/tasks.md`` T6 + 验收 §7）:

  1. 无任何 backend 时 ``discover()`` 返回空字典，
     ``get_backend()`` 抛 ``PerceptionUnavailableError``（含安装指引）
  2. ``register()`` 注入 mock backend 后 ``get_backend()`` 返回 mock
  3. 多 backend 时 ``perception_backend`` 配置 / 环境变量正确选择
  4. ``vision_image`` / ``ocr`` 在无 perception 环境下仍能工作
     （证明它们不进 Registry）
  5. **stub backend 通过 entry_points 注册后被 Registry 发现**
     （契约稳定性证明 —— 第三方扩展无需改 rodski）

不依赖外部网络或 ollama。
"""
from __future__ import annotations

import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from rodski.vision.perception_interface import (
    DEFAULT_CAPABILITIES,
    LocatorHint,
    PerceptionBackend,
    PerceptionResult,
    PerceptionUnavailableError,
)
from rodski.vision.registry import (
    DEFAULT_FALLBACK_ORDER,
    ENTRY_POINT_GROUP,
    PerceptionRegistry,
)


# ═══════════════════════════════════════════════════════════════
# 工具 backend 类
# ═══════════════════════════════════════════════════════════════


class StubBackend(PerceptionBackend):
    """测试用 backend：返回预设 bbox，可控可用性。"""

    name = "stub"
    capabilities = {"locate"}

    def __init__(self, available=True, **kwargs):
        self.available = available
        self.locate_calls = []
        self.init_kwargs = kwargs

    def is_available(self):
        return self.available

    def locate(self, image_path, description, element_type=None):
        self.locate_calls.append((image_path, description, element_type))
        return PerceptionResult(
            bbox=(10, 20, 30, 40),
            coordinates=(20, 30),
            target_description=description,
            confidence=0.88,
        )


class LocalLikeBackend(StubBackend):
    name = "local"


class RemoteLikeBackend(StubBackend):
    name = "remote"


class AlwaysUnavailableBackend(PerceptionBackend):
    name = "broken"
    capabilities = set()

    def __init__(self, **kwargs):
        pass

    def is_available(self):
        return False

    def locate(self, image_path, description, element_type=None):
        raise AssertionError("should not be called when unavailable")


# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════


@pytest.fixture(autouse=True)
def reset_registry():
    """每个测试前后重置 Registry 缓存。"""
    PerceptionRegistry.reset()
    yield
    PerceptionRegistry.reset()


@pytest.fixture
def clean_env(monkeypatch):
    """清理 perception 相关环境变量，避免外部环境干扰测试。"""
    for key in ("RODSKI_PERCEPTION_BACKEND", "RODSKI_PERCEPTION_MODEL",
                "OLLAMA_HOST", "RODSKI_PERCEPTION_SERVER"):
        monkeypatch.delenv(key, raising=False)


# ═══════════════════════════════════════════════════════════════
# §1. discover() 与 get_backend() 在无 backend 时的行为
# ═══════════════════════════════════════════════════════════════


class TestEmptyRegistry:

    def test_discover_returns_empty_dict_when_no_entry_points(self, clean_env):
        """无任何 backend 注册 → discover() 返回 {}。"""
        # 用 patch 直接让 entry_points 看不到任何 group 数据
        with patch("rodski.vision.registry.entry_points") as ep:
            ep.return_value = []
            backends = PerceptionRegistry.discover()
        assert backends == {}

    def test_get_backend_raises_unavailable_with_install_hint(self, clean_env):
        """无 backend → PerceptionUnavailableError 含 pip / ollama 指引。"""
        with patch("rodski.vision.registry.entry_points") as ep:
            ep.return_value = []
            with pytest.raises(PerceptionUnavailableError) as exc_info:
                PerceptionRegistry.get_backend()
        msg = str(exc_info.value)
        assert "pip install rodski[perception]" in msg
        assert "ollama pull" in msg

    def test_discover_handles_entry_points_exception(self, clean_env):
        """entry_points 调用抛错时不应让 discover 崩溃，应返回 {}。"""
        with patch(
            "rodski.vision.registry.entry_points",
            
            side_effect=RuntimeError("boom"),
        ):
            backends = PerceptionRegistry.discover()
        assert backends == {}

    def test_single_backend_load_failure_isolated(self, clean_env):
        """单个 entry_point 加载失败不影响其他 entry_point。"""
        good_ep = SimpleNamespace(name="local", load=lambda: LocalLikeBackend)
        bad_ep = SimpleNamespace(
            name="broken",
            load=MagicMock(side_effect=ImportError("missing dep")),
        )
        with patch(
            "rodski.vision.registry.entry_points",
            
            return_value=[good_ep, bad_ep],
        ):
            backends = PerceptionRegistry.discover()
        assert "local" in backends
        assert "broken" not in backends

    def test_non_backend_class_filtered_out(self, clean_env):
        """entry_point 指向非 PerceptionBackend 子类时跳过。"""
        ep = SimpleNamespace(name="bogus", load=lambda: str)
        with patch(
            "rodski.vision.registry.entry_points",
            
            return_value=[ep],
        ):
            backends = PerceptionRegistry.discover()
        assert "bogus" not in backends


# ═══════════════════════════════════════════════════════════════
# §2. register() 测试 hook
# ═══════════════════════════════════════════════════════════════


class TestRegisterHook:

    def test_register_then_get_returns_instance(self, clean_env):
        PerceptionRegistry.register("stub", StubBackend)
        backend = PerceptionRegistry.get_backend({"perception_backend": "stub"})
        assert isinstance(backend, StubBackend)
        assert backend.name == "stub"

    def test_register_rejects_non_backend_class(self):
        with pytest.raises(TypeError):
            PerceptionRegistry.register("bad", str)

    def test_register_visible_via_list_backends(self, clean_env):
        PerceptionRegistry.register("alpha", StubBackend)
        PerceptionRegistry.register("beta", LocalLikeBackend)
        assert "alpha" in PerceptionRegistry.list_backends()
        assert "beta" in PerceptionRegistry.list_backends()

    def test_reset_clears_registrations(self, clean_env):
        PerceptionRegistry.register("stub", StubBackend)
        assert "stub" in PerceptionRegistry.discover()
        PerceptionRegistry.reset()
        with patch(
            "rodski.vision.registry.entry_points",
            
            return_value=[],
        ):
            assert PerceptionRegistry.discover() == {}


# ═══════════════════════════════════════════════════════════════
# §3. 多 backend 选择策略
# ═══════════════════════════════════════════════════════════════


class TestBackendSelection:

    def test_explicit_perception_backend_config(self, clean_env):
        PerceptionRegistry.register("local", LocalLikeBackend)
        PerceptionRegistry.register("remote", RemoteLikeBackend)
        backend = PerceptionRegistry.get_backend(
            {"perception_backend": "remote"}
        )
        assert isinstance(backend, RemoteLikeBackend)

    def test_unknown_backend_name_raises_unavailable(self, clean_env):
        PerceptionRegistry.register("local", LocalLikeBackend)
        with pytest.raises(PerceptionUnavailableError) as exc_info:
            PerceptionRegistry.get_backend(
                {"perception_backend": "no_such"}
            )
        assert "no_such" in str(exc_info.value)

    def test_env_var_overrides_default(self, clean_env, monkeypatch):
        PerceptionRegistry.register("local", LocalLikeBackend)
        PerceptionRegistry.register("remote", RemoteLikeBackend)
        monkeypatch.setenv("RODSKI_PERCEPTION_BACKEND", "remote")
        backend = PerceptionRegistry.get_backend()
        assert isinstance(backend, RemoteLikeBackend)

    def test_config_takes_precedence_over_env(self, clean_env, monkeypatch):
        PerceptionRegistry.register("local", LocalLikeBackend)
        PerceptionRegistry.register("remote", RemoteLikeBackend)
        monkeypatch.setenv("RODSKI_PERCEPTION_BACKEND", "remote")
        backend = PerceptionRegistry.get_backend(
            {"perception_backend": "local"}
        )
        assert isinstance(backend, LocalLikeBackend)

    def test_auto_fallback_picks_local_first(self, clean_env):
        """无配置 → 按 DEFAULT_FALLBACK_ORDER 选 local 优先。"""
        PerceptionRegistry.register("remote", RemoteLikeBackend)
        PerceptionRegistry.register("local", LocalLikeBackend)
        backend = PerceptionRegistry.get_backend()
        assert isinstance(backend, LocalLikeBackend)
        assert DEFAULT_FALLBACK_ORDER[0] == "local"

    def test_unavailable_backend_falls_back(self, clean_env):
        """local 注册但 is_available=False → 自动尝试 remote。"""

        class BrokenLocal(LocalLikeBackend):
            def is_available(self):
                return False

        PerceptionRegistry.register("local", BrokenLocal)
        PerceptionRegistry.register("remote", RemoteLikeBackend)
        backend = PerceptionRegistry.get_backend()
        assert isinstance(backend, RemoteLikeBackend)

    def test_all_unavailable_raises_with_diag(self, clean_env):
        PerceptionRegistry.register("local", AlwaysUnavailableBackend)
        PerceptionRegistry.register("remote", AlwaysUnavailableBackend)
        with pytest.raises(PerceptionUnavailableError) as exc_info:
            PerceptionRegistry.get_backend()
        msg = str(exc_info.value)
        assert "is_available() == False" in msg
        assert "local" in msg or "remote" in msg

    def test_explicit_backend_must_be_available(self, clean_env):
        """显式指定的 backend 不可用时应当抛错，而不是静默回退。"""
        PerceptionRegistry.register("local", LocalLikeBackend)
        PerceptionRegistry.register("remote", AlwaysUnavailableBackend)
        with pytest.raises(PerceptionUnavailableError):
            PerceptionRegistry.get_backend(
                {"perception_backend": "remote"}
            )

    def test_extra_config_passed_to_backend_init(self, clean_env):
        PerceptionRegistry.register("stub", StubBackend)
        backend = PerceptionRegistry.get_backend({
            "perception_backend": "stub",
            "perception_model": "qwen3-vl:2b",
            "ollama_host": "http://localhost:11434",
        })
        # StubBackend 接受 **kwargs，应当看到这些 init_kwargs
        assert backend.init_kwargs["perception_model"] == "qwen3-vl:2b"
        assert backend.init_kwargs["ollama_host"] == "http://localhost:11434"
        # perception_backend 是 Registry 自身的选择 key，不应透传
        assert "perception_backend" not in backend.init_kwargs


# ═══════════════════════════════════════════════════════════════
# §4. vision_image / ocr 在无 perception 环境下仍可用
# ═══════════════════════════════════════════════════════════════


class TestNonPerceptionLocatorsIndependent:
    """vision_image / vision_bbox / ocr 不走 Registry，证明它们正交。"""

    def test_image_template_matcher_independent_of_registry(self, tmp_path):
        """vision_image 直接走 ImageTemplateMatcher，与 Registry 状态无关。"""
        from rodski.vision.image_matcher import ImageTemplateMatcher

        # Registry 完全空
        with patch(
            "rodski.vision.registry.entry_points",
            return_value=[],
        ):
            assert PerceptionRegistry.discover() == {}

            # 构造一张有可识别图案的截图：黑底中央放一个白色方块
            # 模板就是这个白色方块本身，必然命中
            import cv2
            import numpy as np
            screen = np.zeros((200, 200, 3), dtype=np.uint8)
            screen[80:120, 80:120] = 255  # 中央白色方块
            template = screen[80:120, 80:120].copy()

            screen_path = tmp_path / "screen.png"
            template_path = tmp_path / "template.png"
            cv2.imwrite(str(screen_path), screen)
            cv2.imwrite(str(template_path), template)

            matcher = ImageTemplateMatcher(threshold=0.5)
            bbox = matcher.locate(str(screen_path), str(template_path))
            assert bbox is not None  # 模板等于截图中的一部分，必命中

    def test_bbox_locator_independent_of_registry(self):
        from rodski.vision.bbox_locator import BBoxLocator
        with patch(
            "rodski.vision.registry.entry_points",
            
            return_value=[],
        ):
            assert PerceptionRegistry.discover() == {}
            bbox = BBoxLocator().locate("100,200,300,400")
            assert bbox == (100, 200, 300, 400)

    def test_vision_locator_dispatches_without_backend(self, tmp_path):
        """VisionLocator.locate('vision_bbox', ...) 不调 Registry。"""
        from rodski.vision.locator import VisionLocator
        with patch(
            "rodski.vision.registry.entry_points",
            
            return_value=[],
        ):
            loc = VisionLocator()
            bbox = loc.locate("vision_bbox", "1,2,3,4", None)
            assert bbox == (1, 2, 3, 4)

    def test_ocr_provider_injection_does_not_touch_registry(self):
        """OCRLocator 用注入的 provider 干活，无需 Registry。"""
        from rodski.vision.ocr_locator import OCRLocator
        provider = MagicMock()
        provider.parse.return_value = [
            {"type": "text", "content": "Hi", "bbox": [0.1, 0.1, 0.2, 0.2]}
        ]
        with patch(
            "rodski.vision.registry.entry_points",
            
            return_value=[],
        ):
            ocr = OCRLocator(provider=provider)
            # 截图任意，关键是不进 Registry
            with patch.object(OCRLocator, "_get_image_size",
                              return_value=(1000, 1000)):
                with patch.object(OCRLocator, "_prepare_screenshot",
                                  return_value=("/tmp/x.png", False)):
                    elems = ocr.get_all_text_elements("/tmp/x.png")
        assert len(elems) == 1
        provider.parse.assert_called_once()


# ═══════════════════════════════════════════════════════════════
# §5. 契约稳定性证明：第三方 backend 通过 entry_points 注册
# ═══════════════════════════════════════════════════════════════


class TestEntryPointContractStability:
    """**接口契约稳定性证明**：第三方 backend 仅通过 ``pyproject.toml``
    的 entry_points 注册（rodski 源码无需修改），即可被 Registry 发现并使用。

    模拟方式：通过 patch ``rodski.vision.registry.entry_points`` 返回
    一个仿真的 EntryPoint 对象列表（``name`` + ``load()``），等价于真实
    的 ``importlib.metadata.entry_points(group="rodski.perception_backends")``
    返回结果。
    """

    def test_third_party_backend_discovered_via_entry_point(self, clean_env):
        """模拟一个外部包 `external_perception` 注册了 backend。"""

        class ThirdPartyBackend(PerceptionBackend):
            name = "external"
            capabilities = {"locate"}

            def __init__(self, **kwargs):
                pass

            def is_available(self):
                return True

            def locate(self, image_path, description, element_type=None):
                return PerceptionResult(
                    bbox=(1, 2, 3, 4),
                    coordinates=(2, 3),
                    target_description=description,
                )

        # 模拟一个第三方包注册的 entry_point
        fake_ep = SimpleNamespace(
            name="external",
            load=lambda: ThirdPartyBackend,
        )

        with patch(
            "rodski.vision.registry.entry_points",
            
            return_value=[fake_ep],
        ):
            backends = PerceptionRegistry.discover()
            assert "external" in backends
            assert backends["external"] is ThirdPartyBackend

            # 显式选中
            backend = PerceptionRegistry.get_backend(
                {"perception_backend": "external"}
            )
            assert isinstance(backend, ThirdPartyBackend)

            # 调用契约接口
            result = backend.locate("/tmp/x.png", "login")
            assert result.bbox == (1, 2, 3, 4)
            assert result.target_description == "login"

    def test_entry_point_group_name_is_stable(self):
        """entry_point group 名称是契约的一部分，不应随意改动。"""
        assert ENTRY_POINT_GROUP == "rodski.perception_backends"

    def test_default_fallback_order_is_stable(self):
        """fallback 顺序约定：local 优先于 remote。"""
        assert DEFAULT_FALLBACK_ORDER[0] == "local"
        assert "remote" in DEFAULT_FALLBACK_ORDER


# ═══════════════════════════════════════════════════════════════
# §6. PerceptionBackend 抽象接口契约
# ═══════════════════════════════════════════════════════════════


class TestPerceptionBackendContract:

    def test_cannot_instantiate_without_abstract_methods(self):
        """ABC 强制必须实现 is_available + locate。"""

        class Incomplete(PerceptionBackend):
            pass

        with pytest.raises(TypeError):
            Incomplete()  # type: ignore[abstract]

    def test_locate_many_default_implementation(self):
        """默认 locate_many 调多次 locate。"""
        backend = StubBackend()
        results = backend.locate_many(
            "/tmp/x.png", ["a", "b", "c"],
        )
        assert len(results) == 3
        assert all(r is not None for r in results)
        # 3 次 locate 调用
        assert len(backend.locate_calls) == 3

    def test_locate_many_element_types_alignment(self):
        backend = StubBackend()
        backend.locate_many(
            "/tmp/x.png",
            ["a", "b"],
            element_types=["button", "input"],
        )
        # type 应当传递给 locate
        types = [c[2] for c in backend.locate_calls]
        assert types == ["button", "input"]

    def test_locate_many_mismatched_types_raises(self):
        backend = StubBackend()
        with pytest.raises(ValueError):
            backend.locate_many(
                "/tmp/x.png", ["a", "b"], element_types=["button"]
            )

    def test_locate_fused_default_falls_back_to_vision_hint(self):
        """默认 locate_fused 找第一个 vision hint 转调 locate。"""
        backend = StubBackend()
        result = backend.locate_fused(
            "/tmp/x.png",
            hints=[
                LocatorHint(type="ocr", value="登录"),
                LocatorHint(type="vision", value="登录按钮"),
            ],
            element_type="button",
        )
        assert result is not None
        # 真正调用的是 vision hint
        assert backend.locate_calls[0][1] == "登录按钮"

    def test_locate_fused_returns_none_without_vision_hint(self):
        backend = StubBackend()
        result = backend.locate_fused(
            "/tmp/x.png",
            hints=[
                LocatorHint(type="ocr", value="登录"),
                LocatorHint(type="vision_image", value="login.png"),
            ],
        )
        assert result is None  # 54d 才实现真正的融合

    def test_perception_result_has_required_fields(self):
        r = PerceptionResult(
            bbox=(1, 2, 3, 4),
            coordinates=(2, 3),
            target_description="x",
        )
        assert r.confidence is None
        assert r.consensus_count == 0
        assert r.latency_ms == 0
        assert r.hint_results == {}

    def test_default_capabilities_strings(self):
        """常用 capability 字符串集合稳定。"""
        for cap in ("locate", "locate_many", "locate_fused", "parse"):
            assert cap in DEFAULT_CAPABILITIES


# ═══════════════════════════════════════════════════════════════
# §7. PerceptionUnavailableError 错误信息契约
# ═══════════════════════════════════════════════════════════════


class TestPerceptionUnavailableError:

    def test_default_message_has_install_hints(self):
        err = PerceptionUnavailableError()
        msg = str(err)
        assert "pip install rodski[perception]" in msg
        assert "ollama" in msg.lower()

    def test_custom_message(self):
        err = PerceptionUnavailableError("custom reason")
        assert "custom reason" in str(err)

    def test_is_runtime_error_subclass(self):
        """允许调用方按 RuntimeError 通用捕获（保留 ImportError 不抛的契约）。"""
        assert issubclass(PerceptionUnavailableError, RuntimeError)
        with pytest.raises(RuntimeError):
            raise PerceptionUnavailableError()
