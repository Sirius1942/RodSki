"""外部命令 hook 执行器（v8.2.0 Hooks 机制）

协议：context 以 JSON 经 stdin 传给外部命令；exit code 语义：
  0   → 继续下一个 hook（全部通过才 allow）
  2   → 立即 deny，短路后续 hook
  其他 → warning 记录但不阻断，继续下一个

`command` 必须以数组形式传给 `subprocess.run`（不经过 shell），避免命令注入。
"""
from __future__ import annotations

import json
import logging
import subprocess
from typing import Any, Dict, List

from .exceptions import HookDeniedError, HookTimeoutError
from .keyword_engine import HookDecision

logger = logging.getLogger("rodski")


def run_external_hook(
    event: str,
    context: Dict[str, Any],
    hook_specs: List[Dict[str, Any]],
) -> HookDecision:
    """按 hook_specs 数组顺序调用外部命令，返回汇总裁决。

    Args:
        event: 事件名（用于日志与超时异常）
        context: 传给外部命令 stdin 的上下文（会被 json.dumps）
        hook_specs: [{"command": [...], "timeout": 10}, ...]

    Returns:
        HookDecision(allow=True) 表示全部 hook 通过；
        HookDecision(allow=False, reason=...) 表示某个 hook 返回 deny 或超时
    """
    event_context = dict(context)
    event_context["event"] = event
    payload = json.dumps(event_context, ensure_ascii=False)

    for spec in hook_specs:
        command = spec.get("command")
        timeout = spec.get("timeout", 10)

        try:
            proc = subprocess.run(
                command,
                input=payload,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            timeout_error = HookTimeoutError(event=event, timeout=timeout)
            logger.warning(
                "外部命令 hook 超时: command=%s, error=%s",
                command,
                timeout_error,
            )
            # 超时按 deny 处理：视为该 hook 返回 deny，短路后续 hook
            return HookDecision(
                allow=False,
                reason=str(timeout_error),
            )
        except (OSError, ValueError) as e:
            # 命令本身不可执行（如二进制不存在）：记录 warning，不阻断（对齐非零退出码语义）
            logger.warning(f"外部命令 hook 执行失败: event={event}, command={command}, error={e}")
            continue

        _log_hook_output(event, command, proc.stdout)

        if proc.returncode == 0:
            continue
        if proc.returncode == 2:
            reason = _extract_reason(proc.stdout) or f"外部命令 hook 拒绝: {' '.join(command)}"
            denied_error = HookDeniedError(event=event, reason=reason)
            logger.error(
                "外部命令 hook 拒绝: command=%s, error=%s",
                command,
                denied_error,
            )
            return HookDecision(allow=False, reason=str(denied_error))

        # 其他非零退出码：warning 记录但不阻断，继续下一个
        logger.warning(
            f"外部命令 hook 返回非零退出码（非 deny 语义）: event={event}, "
            f"command={command}, exit_code={proc.returncode}"
        )

    return HookDecision(allow=True)


def _extract_reason(stdout: str) -> str:
    """尝试从 stdout 解析 JSON 获取 reason/detail 字段，否则返回原始文本。"""
    if not stdout:
        return ""
    try:
        parsed = json.loads(stdout)
        if isinstance(parsed, dict):
            return str(parsed.get("reason") or parsed.get("detail") or stdout.strip())
    except (json.JSONDecodeError, ValueError):
        pass
    return stdout.strip()


def _log_hook_output(event: str, command: List[str], stdout: str) -> None:
    if not stdout:
        return
    try:
        parsed = json.loads(stdout)
        logger.debug(f"外部命令 hook 输出（结构化）: event={event}, command={command}, output={parsed}")
    except (json.JSONDecodeError, ValueError):
        logger.debug(f"外部命令 hook 输出（文本）: event={event}, command={command}, output={stdout.strip()}")
