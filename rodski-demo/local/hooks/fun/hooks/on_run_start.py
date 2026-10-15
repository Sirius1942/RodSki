#!/usr/bin/env python3
"""External on_run_start hook used by the self-contained demo module.

The default mode is deny so the external-hook failure is visible without
additional setup.  The demo runner sets ``RODSKI_DEMO_HOOK_MODE=allow`` only
for the separate built-in compliance ``--force-compliance`` demonstration.
"""
from __future__ import annotations

import json
import os
import sys


def main() -> int:
    try:
        context = json.load(sys.stdin)
    except (json.JSONDecodeError, TypeError):
        context = {}

    mode = os.environ.get("RODSKI_DEMO_HOOK_MODE", "deny").strip().lower()
    if mode != "allow":
        print(
            json.dumps(
                {
                    "reason": "demo external policy denied on_run_start",
                    "event": context.get("event", "on_run_start"),
                },
                ensure_ascii=False,
            )
        )
        return 2

    print(
        json.dumps(
            {"detail": "demo external policy allowed on_run_start"},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
