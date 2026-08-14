"""hooks.json 配置加载测试（v8.2.0 Hooks 机制）"""
import json
from pathlib import Path

import pytest

from core.hooks_config import load_hooks_config
from core.exceptions import InvalidConfigError


def test_no_config_returns_empty_dict(tmp_path):
    assert load_hooks_config(tmp_path) == {}


def test_project_config_loaded(tmp_path):
    (tmp_path / "hooks.json").write_text(
        json.dumps({"on_run_start": [{"command": ["python3", "check.py"], "timeout": 5}]}),
        encoding="utf-8",
    )
    config = load_hooks_config(tmp_path)
    assert config["on_run_start"][0]["command"] == ["python3", "check.py"]


def test_project_config_overrides_global(tmp_path, monkeypatch):
    global_dir = tmp_path / "global_home"
    global_dir.mkdir()
    global_hooks_path = global_dir / ".rodski" / "hooks.json"
    global_hooks_path.parent.mkdir(parents=True)
    global_hooks_path.write_text(
        json.dumps({"on_run_end": [{"command": ["echo", "global"]}]}), encoding="utf-8"
    )
    monkeypatch.setattr("core.hooks_config._GLOBAL_HOOKS_PATH", global_hooks_path)

    module_dir = tmp_path / "module"
    module_dir.mkdir()
    (module_dir / "hooks.json").write_text(
        json.dumps({"on_run_start": [{"command": ["echo", "project"]}]}), encoding="utf-8"
    )

    config = load_hooks_config(module_dir)
    # 项目内配置完全覆盖全局，不做合并
    assert "on_run_end" not in config
    assert config["on_run_start"][0]["command"] == ["echo", "project"]


def test_global_config_used_when_no_project_config(tmp_path, monkeypatch):
    global_hooks_path = tmp_path / ".rodski" / "hooks.json"
    global_hooks_path.parent.mkdir(parents=True)
    global_hooks_path.write_text(
        json.dumps({"on_run_end": [{"command": ["echo", "global"]}]}), encoding="utf-8"
    )
    monkeypatch.setattr("core.hooks_config._GLOBAL_HOOKS_PATH", global_hooks_path)

    module_dir = tmp_path / "module"
    module_dir.mkdir()
    config = load_hooks_config(module_dir)
    assert config["on_run_end"][0]["command"] == ["echo", "global"]


def test_command_not_array_raises(tmp_path):
    (tmp_path / "hooks.json").write_text(
        json.dumps({"on_run_start": [{"command": "not-an-array"}]}), encoding="utf-8"
    )
    with pytest.raises(InvalidConfigError):
        load_hooks_config(tmp_path)


def test_command_empty_array_raises(tmp_path):
    (tmp_path / "hooks.json").write_text(
        json.dumps({"on_run_start": [{"command": []}]}), encoding="utf-8"
    )
    with pytest.raises(InvalidConfigError):
        load_hooks_config(tmp_path)


def test_command_non_string_elements_raises(tmp_path):
    (tmp_path / "hooks.json").write_text(
        json.dumps({"on_run_start": [{"command": ["python3", 123]}]}), encoding="utf-8"
    )
    with pytest.raises(InvalidConfigError):
        load_hooks_config(tmp_path)


def test_malformed_json_raises(tmp_path):
    (tmp_path / "hooks.json").write_text("{not valid json", encoding="utf-8")
    with pytest.raises(InvalidConfigError):
        load_hooks_config(tmp_path)


def test_root_not_object_raises(tmp_path):
    (tmp_path / "hooks.json").write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    with pytest.raises(InvalidConfigError):
        load_hooks_config(tmp_path)
