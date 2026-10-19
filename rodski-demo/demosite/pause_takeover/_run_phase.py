#!/usr/bin/env python3
"""单 phase 子进程 runner：CDP 附加共享浏览器执行一个 phase case。

由 run_demo.py 以子进程方式调用（每次独立 Python 进程 / 独立 Playwright 事件循环），
避免同一线程内嵌套 sync_playwright 冲突。usage:
    python3 _run_phase.py part1_login.xml   # 或 part2_continue.xml
退出码：0=该 case PASS；1=FAIL/异常。共享浏览器由调用方保活，本进程仅断连。
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent.parent.parent
_RODSKI = _REPO / "rodski"
if str(_RODSKI) not in sys.path:
    sys.path.insert(0, str(_RODSKI))

MODULE = Path(__file__).resolve().parent
CDP_ENDPOINT = "http://127.0.0.1:9333"

from core.config_manager import ConfigManager  # noqa: E402
from core.ski_executor import SKIExecutor  # noqa: E402
from drivers.playwright_driver import PlaywrightDriver  # noqa: E402


def build_config() -> ConfigManager:
    cfg = ConfigManager(config_path=str(MODULE / "no_such_config.json"))
    cfg.config["recording"]["enabled"] = False
    cfg.config["auto_screenshot_on_failure"] = False
    cfg.config["auto_screenshot_on_step"] = False
    return cfg


def build_driver() -> PlaywrightDriver:
    return PlaywrightDriver(cdp_endpoint=CDP_ENDPOINT)


def _expected_case_id(case_file: Path) -> str:
    """从 case XML 读取首个 <case> 的 id 属性（每 phase 文件恰一个 case）。"""
    import xml.etree.ElementTree as ET
    root = ET.parse(MODULE / "case" / case_file.name).getroot()
    return (root.find("case").get("id") or "") if root.find("case") is not None else ""


def main() -> int:
    case_file = Path(sys.argv[1])
    expected_id = _expected_case_id(case_file)
    ex = None
    try:
        ex = SKIExecutor(
            str(MODULE / "case" / case_file.name),
            build_driver(),
            config=build_config(),
            driver_factory=build_driver,
            module_dir=str(MODULE),
        )
        results = ex.execute_all_cases()
        by_case = {r.get("case_id"): r for r in results}
        res = by_case.get(expected_id) or (results[0] if results else {})
        st = res.get("status", "MISSING")
        err = res.get("error", "")
        print(f"[phase:{case_file.stem}] {res.get('case_id')}: {st}"
              + (f"  ({err})" if err else ""))
        return 0 if st == "PASS" else 1
    finally:
        if ex is not None:
            try:
                ex.close()
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
