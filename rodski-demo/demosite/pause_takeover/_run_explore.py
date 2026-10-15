#!/usr/bin/env python3
"""单条探索步骤 runner：走真实 CLI（`rodski explore-step`）在共享浏览器上执行一步。

由 run_demo.py 以子进程方式调用。刻意不复用框架内部 API，而是驱动**真实的 CLI
入口**——扮演「外部 Agent 手里只有 rodski 命令」这一真实场景：

    python3 _run_explore.py --session take1 --action type --model NavMenu --data N001

`--cdp` 由本脚本固定注入（共享浏览器端点见 CDP_ENDPOINT），因此调用方只需给出
探索动作本身。stdout 原样透传 CLI 的 JSON 结果；退出码 = CLI 退出码。
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent.parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

MODULE = Path(__file__).resolve().parent
CDP_ENDPOINT = ":9333"


def main() -> int:
    from rodski.rodski_cli import main as cli_main

    sys.argv = [
        "rodski", "explore-step",
        "--module", str(MODULE),
        "--cdp", CDP_ENDPOINT,
        *sys.argv[1:],
    ]
    return cli_main()


if __name__ == "__main__":
    raise SystemExit(main())
