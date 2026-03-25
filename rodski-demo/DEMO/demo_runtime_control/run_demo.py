#!/usr/bin/env python3
"""演示：RuntimeCommandQueue 在步骤边界插入额外 wait（与《核心设计约束》§8 一致）"""
from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

# rodski 包路径：…/RodSki/rodski
_REPO = Path(__file__).resolve().parent.parent.parent.parent
_RODSKI = _REPO / "rodski"
if str(_RODSKI) not in sys.path:
    sys.path.insert(0, str(_RODSKI))

from core.runtime_control import RuntimeCommandQueue  # noqa: E402
from core.ski_executor import SKIExecutor  # noqa: E402
from drivers.playwright_driver import PlaywrightDriver  # noqa: E402


def main() -> int:
    module_dir = Path(__file__).resolve().parent
    case_path = module_dir / "case" / "runtime_case.xml"

    rq = RuntimeCommandQueue()

    def create_driver() -> PlaywrightDriver:
        return PlaywrightDriver(headless=True, browser="chromium")

    driver = create_driver()
    try:
        ex = SKIExecutor(
            str(case_path),
            driver,
            driver_factory=lambda: create_driver(),
            module_dir=str(module_dir),
            runtime_control=rq,
        )

        def inject() -> None:
            # 须在执行器就绪后再启动线程，避免 insert 早于第一条固定步入队
            # 约 0.5s 后入队：此时 navigate 通常已结束，正在执行固定 wait 1s（见 §8.7 边界排队）
            time.sleep(0.5)
            rq.insert(
                [
                    {"action": "wait", "model": "", "data": "0.2"},
                ]
            )

        threading.Thread(target=inject, daemon=True).start()

        results = ex.execute_all_cases()
        ex.close()
    finally:
        try:
            driver.close()
        except Exception:
            pass

    ok = all(r.get("status", "").upper() in ("PASS", "SKIP") for r in results)
    print("\n预期：日志中「用例」阶段出现 3 条步骤（navigate → wait 1s → 插入的 wait 0.2s）")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
