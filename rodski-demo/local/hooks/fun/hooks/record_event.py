#!/usr/bin/env python3
"""F112 外部命令 hook：把事件名与 stdin 上下文追加写入 JSONL，供 run_acceptance_extra.py 断言。

用法（hooks.json）: {"command": ["python3", "fun/hooks/record_event.py", "<事件名>"]}
- 记录文件：环境变量 RODSKI_DEMO_HOOK_LOG（未设置则不记录）
- 退出码：环境变量 RODSKI_DEMO_HOOK_EXIT_<事件名>（默认 0；2 = deny，见 HOOKS_REFERENCE §3）
"""
from __future__ import annotations

import json
import os
import sys
import time


def main() -> int:
    event = sys.argv[1] if len(sys.argv) > 1 else "unknown"
    raw = sys.stdin.read()
    try:
        context = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        context = {"_raw": raw}
    log_path = os.environ.get("RODSKI_DEMO_HOOK_LOG")
    if log_path:
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"event": event, "t": time.time(), "context": context},
                                ensure_ascii=False, default=str) + "\n")
    code = int(os.environ.get(f"RODSKI_DEMO_HOOK_EXIT_{event}", "0") or 0)
    if code == 2:
        print(json.dumps({"reason": f"demo {event} hook denied"}, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
