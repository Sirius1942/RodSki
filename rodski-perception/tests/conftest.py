"""共享 pytest 配置。"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Tuple

import pytest


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def pytest_collection_modifyitems(config, items):
    """在 ollama 不可达时自动 skip @requires_ollama 测试。"""
    if os.getenv("RUN_OLLAMA_TESTS") == "1":
        return  # 强制运行

    try:
        import requests
        r = requests.get("http://localhost:11434/api/tags", timeout=1)
        ollama_ok = r.status_code == 200
    except Exception:
        ollama_ok = False

    if ollama_ok:
        return

    skip_marker = pytest.mark.skip(
        reason="ollama not reachable; skipping @requires_ollama tests"
    )
    for item in items:
        if "requires_ollama" in item.keywords:
            item.add_marker(skip_marker)


@pytest.fixture
def tiny_png(tmp_path) -> Path:
    """生成一个 100x100 的小 PNG，避免依赖外部素材。"""
    from PIL import Image

    p = tmp_path / "tiny.png"
    Image.new("RGB", (100, 100), color=(200, 200, 200)).save(p)
    return p


@pytest.fixture
def login_screenshot() -> Path:
    """返回 demo_perception 提供的真实截图（仅当存在时；集成测试用）。"""
    # 相对 tests/ → rodski-perception/ → rodski/
    candidates = [
        FIXTURES_DIR / "login_screen.png",
        Path(__file__).parents[2]
        / "rodski-demo" / "DEMO" / "demo_perception" / "assets" / "_sources"
        / "login_screen.png",
    ]
    for c in candidates:
        if c.exists():
            return c
    pytest.skip("login_screen.png fixture not available")


@pytest.fixture
def fake_ollama_chat_payload() -> dict:
    """模拟 Qwen3-VL 单目标定位的 ollama chat 响应。"""
    return {
        "model": "qwen3-vl:2b",
        "message": {
            "role": "assistant",
            "content": '[{"bbox_2d": [100, 200, 300, 250], "label": "login button"}]',
        },
        "done": True,
    }


@pytest.fixture
def fake_ollama_tags_payload() -> dict:
    return {
        "models": [
            {"name": "qwen3-vl:2b"},
            {"name": "qwen3-vl:8b"},
            {"name": "llama3:8b"},
        ]
    }
