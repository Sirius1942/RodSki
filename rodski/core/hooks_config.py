"""hooks.json 配置加载（v8.2.0 Hooks 机制外部命令 hook）

配置文件格式（JSON）::

    {
      "on_run_start": [{"command": ["python3", "check.py"], "timeout": 10}],
      "on_case_failure": [{"command": ["./notify.sh"]}],
      "on_run_end": [...],
      "on_session_start": [...]
    }

查找顺序：优先 `module_dir/hooks.json`（项目内），不存在则 `~/.rodski/hooks.json`
（全局）。项目内配置存在时**完全覆盖**全局配置，不做按事件合并（MVP 简化语义）。
两者都不存在时静默返回 `{}`（多数用户不配置外部 hook，属正常情况）。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .exceptions import InvalidConfigError

_GLOBAL_HOOKS_PATH = Path.home() / ".rodski" / "hooks.json"


def _validate_hook_specs(config: Dict[str, Any], source: Path) -> None:
    """校验每个事件下的 hook 规格：必须是列表，每项必须含非空字符串数组 command。"""
    for event, specs in config.items():
        if not isinstance(specs, list):
            raise InvalidConfigError(
                f"hooks.json 格式错误（{source}）：事件 '{event}' 的值必须是数组"
            )
        for spec in specs:
            if not isinstance(spec, dict):
                raise InvalidConfigError(
                    f"hooks.json 格式错误（{source}）：事件 '{event}' 下的每一项必须是对象"
                )
            command = spec.get("command")
            if (
                not isinstance(command, list)
                or not command
                or not all(isinstance(c, str) and c for c in command)
            ):
                raise InvalidConfigError(
                    f"hooks.json 格式错误（{source}）：事件 '{event}' 的 command 必须是"
                    f"非空字符串数组，避免 shell 字符串被误用（当前值: {command!r}）"
                )


def load_hooks_config(module_dir: Path) -> Dict[str, List[Dict[str, Any]]]:
    """加载外部命令 hook 配置。

    Args:
        module_dir: 测试模块目录（用于定位项目内 hooks.json）

    Returns:
        {事件名: [hook_spec, ...]}；两处配置均不存在时返回 {}

    Raises:
        InvalidConfigError: 配置文件存在但格式不合法（command 非字符串数组等）
    """
    project_path = Path(module_dir) / "hooks.json"
    if project_path.exists():
        try:
            config = json.loads(project_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise InvalidConfigError(f"hooks.json 解析失败（{project_path}）: {e}")
        if not isinstance(config, dict):
            raise InvalidConfigError(f"hooks.json 格式错误（{project_path}）：根节点必须是对象")
        _validate_hook_specs(config, project_path)
        return config

    if _GLOBAL_HOOKS_PATH.exists():
        try:
            config = json.loads(_GLOBAL_HOOKS_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise InvalidConfigError(f"hooks.json 解析失败（{_GLOBAL_HOOKS_PATH}）: {e}")
        if not isinstance(config, dict):
            raise InvalidConfigError(
                f"hooks.json 格式错误（{_GLOBAL_HOOKS_PATH}）：根节点必须是对象"
            )
        _validate_hook_specs(config, _GLOBAL_HOOKS_PATH)
        return config

    return {}
