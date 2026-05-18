#!/usr/bin/env python3
"""Example run-script placeholder for Android keycode operations.

RodSki mobile mode should use standard case actions. Complex platform
operations can be represented as explicit run scripts under fun/.
"""
from __future__ import annotations

import json
import sys


def main() -> int:
    keycode = sys.argv[1] if len(sys.argv) > 1 else ""
    if not keycode:
        print(json.dumps({"status": "error", "message": "missing keycode"}))
        return 2

    print(
        json.dumps(
            {
                "status": "skipped",
                "operation": "android_keycode",
                "keycode": keycode,
                "reason": "placeholder until RodSki mobile driver exposes device session context",
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
