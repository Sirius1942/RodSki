#!/usr/bin/env python3
"""RodSki 用例完成前的一条龙校验。

按固定顺序串起四步，省去每次手敲：
  1. rodski --version / capabilities  —— 锚定 live 关键字/定位器事实
  2. rodski_case_guard.py             —— 静态幻觉 + 跨文件引用 guard
  3. rodski data validate <module>    —— 数据层完整性
  4. rodski run <case|module> --dry-run --output-format json

任一步失败即整体失败（exit 1），并指出首个失败步骤；只读，不写任何文件。
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_REPO = Path.home() / "TestCase"
DEFAULT_GLOBAL_RODSKI = Path("/opt/homebrew/bin/rodski")
DEFAULT_LONG_TERM_RODSKI = Path.home() / ".local/share/rodski/venv/bin/rodski"
GUARD = Path(__file__).resolve().with_name("rodski_case_guard.py")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="RodSki 用例完成前的一条龙校验。")
    parser.add_argument("module", help="要校验的模块目录（含 case/model/data）。")
    parser.add_argument("--repo", default=str(DEFAULT_REPO), help="RodSki 用例仓库根目录。")
    parser.add_argument(
        "--rodski-bin", default="", help="RodSki CLI 路径。默认自动检测（全局优先）。"
    )
    parser.add_argument(
        "--run-target",
        default="",
        help="dry-run 的目标（单个 case 文件或 case/ 目录）。默认用 <module>/case。",
    )
    parser.add_argument("--json", action="store_true", help="输出 JSON。")
    return parser.parse_args()


def resolve_rodski_bin(repo: Path, explicit: str) -> Path:
    if explicit:
        return Path(explicit).expanduser()
    candidates = [DEFAULT_GLOBAL_RODSKI, DEFAULT_LONG_TERM_RODSKI]
    path_rodski = shutil.which("rodski")
    if path_rodski:
        candidates.append(Path(path_rodski))
    candidates.extend(
        repo / name / "bin" / "rodski" for name in ("myenv", ".venv", "venv")
    )
    for candidate in dict.fromkeys(candidates):
        if candidate.exists():
            return candidate
    return candidates[0]


def rodski_has_subcommand(rodski_bin: Path, name: str) -> bool:
    """顶层 --help 是否列出该子命令。与 rodski skill 纪律一致：
    只有当前 CLI 暴露 capabilities 时才调用它，不对老 CLI 盲调。"""
    if not rodski_bin.exists():
        return False
    try:
        result = subprocess.run(
            [str(rodski_bin), "--help"],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except Exception:
        return False
    help_text = f"{result.stdout}\n{result.stderr}"
    return result.returncode == 0 and re.search(rf"\b{re.escape(name)}\b", help_text) is not None


def run_step(name: str, cmd: list[str], timeout: int) -> dict[str, object]:
    try:
        result = subprocess.run(
            cmd, check=False, capture_output=True, text=True, timeout=timeout
        )
    except Exception as exc:  # pragma: no cover - defensive CLI wrapper
        return {"name": name, "cmd": cmd, "ok": False, "error": str(exc)}
    return {
        "name": name,
        "cmd": cmd,
        "ok": result.returncode == 0,
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def step_failure_detail(step: dict[str, object]) -> str:
    """提取失败步骤的可读首行。guard 输出 JSON，改抽其中的 FAIL 文案。"""
    if step.get("error"):
        return str(step["error"])
    if step["name"] == "guard":
        try:
            data = json.loads(str(step.get("stdout") or ""))
        except json.JSONDecodeError:
            data = None
        if isinstance(data, dict):
            fails = [
                f"{i.get('path')}: {i.get('message')}"
                for i in data.get("issues", [])
                if isinstance(i, dict) and i.get("severity") == "FAIL"
            ]
            if fails:
                head = "；".join(fails[:3])
                more = f"（共 {len(fails)} 处 FAIL）" if len(fails) > 3 else ""
                return head + more
    detail = step.get("stderr") or step.get("stdout") or ""
    return str(detail).splitlines()[0] if detail else ""


def main() -> int:
    args = parse_args()
    repo = Path(args.repo).expanduser().resolve()
    module = Path(args.module).expanduser()
    if not module.is_absolute():
        module = (repo / module).resolve()
    rodski_bin = resolve_rodski_bin(repo, args.rodski_bin)
    run_target = (
        Path(args.run_target).expanduser() if args.run_target else module / "case"
    )

    steps: list[dict[str, object]] = []
    fatal: list[str] = []
    if not module.is_dir():
        fatal.append(f"模块目录不存在：{module}")
    if not rodski_bin.exists():
        fatal.append(f"未找到 RodSki CLI：{rodski_bin}")

    if not fatal:
        steps.append(
            run_step("version", [str(rodski_bin), "--version"], timeout=20)
        )
        if rodski_has_subcommand(rodski_bin, "capabilities"):
            steps.append(
                run_step("capabilities", [str(rodski_bin), "capabilities"], timeout=20)
            )
        else:
            steps.append(
                {
                    "name": "capabilities",
                    "cmd": [str(rodski_bin), "capabilities"],
                    "ok": True,
                    "skipped": "当前 RodSki CLI 顶层 --help 未列出 capabilities 子命令；跳过（信息性步骤，不阻断）。",
                }
            )
        steps.append(
            run_step(
                "guard",
                [
                    sys.executable,
                    str(GUARD),
                    "--repo",
                    str(repo),
                    "--target",
                    str(module),
                    "--json",
                ],
                timeout=120,
            )
        )
        steps.append(
            run_step(
                "data_validate",
                [str(rodski_bin), "data", "validate", str(module)],
                timeout=120,
            )
        )
        steps.append(
            run_step(
                "dry_run",
                [
                    str(rodski_bin),
                    "run",
                    str(run_target),
                    "--dry-run",
                    "--output-format",
                    "json",
                ],
                timeout=300,
            )
        )

    # capabilities/version 失败不阻断（信息性），核心门禁是 guard/validate/dry_run。
    gate_steps = {"guard", "data_validate", "dry_run"}
    failed = [s["name"] for s in steps if s["name"] in gate_steps and not s["ok"]]
    first_failure = failed[0] if failed else None
    ok = not fatal and not failed

    output = {
        "module": str(module),
        "rodski_bin": str(rodski_bin),
        "run_target": str(run_target),
        "ok": ok,
        "fatal": fatal,
        "first_failure": first_failure,
        "failed_steps": failed,
        "steps": steps,
    }

    if args.json:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(f"模块：{module}")
        print(f"RodSki：{rodski_bin}")
        for msg in fatal:
            print(f"  [FATAL] {msg}")
        for step in steps:
            mark = "OK" if step["ok"] else "FAIL"
            gate = "" if step["name"] in gate_steps else "（信息）"
            print(f"  [{mark}] {step['name']}{gate}")
            if step.get("skipped"):
                print(f"        {step['skipped']}")
            elif not step["ok"]:
                detail = step_failure_detail(step)
                if detail:
                    print(f"        {detail[:300]}")
        if ok:
            print("预检通过：guard + data validate + dry-run 全部通过。")
        elif first_failure:
            print(f"预检失败：首个失败步骤 = {first_failure}。")
        else:
            print("预检失败。")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
