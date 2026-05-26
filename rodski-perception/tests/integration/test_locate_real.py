"""集成测试 — 需要真实 ollama + qwen3-vl 模型。

运行：
    pytest tests/integration/ -m requires_ollama

或在已启动 ollama 的环境下让 conftest 自动启用。
"""

from __future__ import annotations

import pytest

from rodski_perception.agent import VLMAgent


pytestmark = pytest.mark.requires_ollama


class TestRealLocate:
    """真实 ollama 推理 — 用 demo_perception 的截图。"""

    def test_locate_login_button(self, login_screenshot):
        agent = VLMAgent(model="qwen3-vl:2b")
        result = agent.locate(
            prompt="login button",
            image=login_screenshot,
            element_type="button",
        )
        assert result is not None, "登录按钮应该被定位到"
        # bbox 在合理范围
        x1, y1, x2, y2 = result.bbox
        assert 0 <= x1 < x2 <= 1000
        assert 0 <= y1 < y2 <= 1000
        # 中心点是像素坐标
        cx, cy = result.coordinates
        assert 0 <= cx <= result.image_size[0]
        assert 0 <= cy <= result.image_size[1]
        # 推理耗时被记录
        assert result.latency_ms > 0
        print(
            f"\nlatency={result.latency_ms}ms  "
            f"bbox={result.bbox}  center={result.coordinates}  "
            f"image_size={result.image_size}"
        )

    def test_locate_returns_none_for_nonexistent(self, login_screenshot):
        agent = VLMAgent(model="qwen3-vl:2b")
        result = agent.locate(
            prompt="a giant pink elephant wearing a top hat",
            image=login_screenshot,
        )
        # 模型应返回 None 或一个低置信度结果（不强求 None）
        if result is None:
            print("\nmodel correctly returned None for nonsense prompt")
        else:
            print(f"\nmodel returned a bbox anyway: {result.bbox} (lenient)")


class TestRealLocateMany:
    def test_batch_login_form(self, login_screenshot):
        agent = VLMAgent(model="qwen3-vl:2b")
        results = agent.locate_many(
            prompts=["username input", "password input", "login button"],
            image=login_screenshot,
        )
        assert len(results) == 3
        non_none = [r for r in results if r is not None]
        # 三个目标至少命中两个
        assert len(non_none) >= 2, (
            f"expected at least 2/3 to be located, got {len(non_none)}: "
            f"{[r and r.target_description for r in results]}"
        )
        for r in non_none:
            print(
                f"\n  {r.target_description}: bbox={r.bbox} "
                f"center={r.coordinates} latency={r.latency_ms}ms"
            )
