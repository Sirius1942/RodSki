"""集成测试 — CLI 通过 subprocess 调用真实 ollama。"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


pytestmark = pytest.mark.requires_ollama


class TestCliReal:
    def test_models_lists_qwen_vl(self):
        r = subprocess.run(
            [sys.executable, "-m", "rodski_perception.cli", "models", "--output", "json"],
            capture_output=True, text=True, timeout=15,
        )
        assert r.returncode == 0, f"stderr={r.stderr}"
        data = json.loads(r.stdout)
        assert any("qwen3-vl" in m for m in data["models"])

    def test_locate_single_real(self, login_screenshot):
        r = subprocess.run(
            [
                sys.executable, "-m", "rodski_perception.cli",
                "locate",
                "--image", str(login_screenshot),
                "--prompt", "login button",
                "--element-type", "button",
                "--output", "json",
            ],
            capture_output=True, text=True, timeout=120,
        )
        assert r.returncode == 0, f"stderr={r.stderr}"
        data = json.loads(r.stdout)
        assert data["target_description"] == "login button"
        assert data["bbox"] is not None
        assert data["coordinates"] is not None
        assert data["latency_ms"] > 0
        print(f"\nbbox={data['bbox']}  center={data['coordinates']}  latency={data['latency_ms']}ms")

    def test_locate_many_real(self, login_screenshot):
        r = subprocess.run(
            [
                sys.executable, "-m", "rodski_perception.cli",
                "locate",
                "--image", str(login_screenshot),
                "--prompt", "username input",
                "--prompt", "password input",
                "--prompt", "login button",
                "--output", "json",
            ],
            capture_output=True, text=True, timeout=180,
        )
        assert r.returncode == 0, f"stderr={r.stderr}"
        data = json.loads(r.stdout)
        assert len(data["results"]) == 3
        found = sum(1 for x in data["results"] if x.get("bbox"))
        assert found >= 2
