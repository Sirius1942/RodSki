#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_RODSKI = "/opt/homebrew/bin/rodski"


@dataclass
class StepRecord:
    global_index: int
    phase: str
    case_id: str
    case_title: str
    scenario_id: str
    scenario_title: str
    scenario_step_no: int | None
    action: str
    model: str
    data: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="围绕长流程步骤建议并可选生成窄范围 RodSki debug plan。"
    )
    parser.add_argument("--module", required=True, help="RodSki 模块目录。")
    parser.add_argument("--case", required=True, help="Case XML 路径、文件名或 case id。")
    parser.add_argument("--around-step", type=int, required=True, help="目标全局步骤编号。")
    parser.add_argument("--rodski", default=DEFAULT_RODSKI, help="RodSki CLI 路径。")
    parser.add_argument("--step-mode", choices=["all", "from", "only"], default="from")
    parser.add_argument("--prepare", choices=["auto", "case", "none"], default="auto")
    parser.add_argument("--cleanup", choices=["是", "否"], default="否")
    parser.add_argument("--no-write-plan", action="store_true", help="只打印建议的 plan，不写入。")
    parser.add_argument("--json", action="store_true", help="输出 JSON。")
    return parser.parse_args()


def sanitize(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_")
    return text[:80] or "debug"


def find_case_file(module: Path, case_arg: str) -> Path:
    candidate = Path(case_arg).expanduser()
    if candidate.exists():
        return candidate.resolve()
    case_dir = module / "case"
    by_name = case_dir / case_arg
    if by_name.exists():
        return by_name.resolve()
    if not case_arg.endswith(".xml"):
        by_xml = case_dir / f"{case_arg}.xml"
        if by_xml.exists():
            return by_xml.resolve()

    matches: list[Path] = []
    for path in sorted(case_dir.rglob("*.xml")):
        if path.name == case_arg or path.stem == case_arg:
            matches.append(path)
            continue
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError:
            continue
        for case in root.findall(".//case"):
            if case.get("id") == case_arg:
                matches.append(path)
                break
    if len(matches) == 1:
        return matches[0].resolve()
    if not matches:
        raise FileNotFoundError(f"未找到 case：{case_arg}")
    raise RuntimeError(f"case 参数不唯一：{case_arg}；匹配={matches}")


def add_step(
    records: list[StepRecord],
    *,
    phase: str,
    case_id: str,
    case_title: str,
    scenario_id: str = "",
    scenario_title: str = "",
    scenario_step_no: int | None = None,
    step: ET.Element,
) -> None:
    records.append(
        StepRecord(
            global_index=len(records) + 1,
            phase=phase,
            case_id=case_id,
            case_title=case_title,
            scenario_id=scenario_id,
            scenario_title=scenario_title,
            scenario_step_no=scenario_step_no,
            action=step.get("action") or "",
            model=step.get("model") or "",
            data=step.get("data") or "",
        )
    )


def parse_steps(case_file: Path) -> list[StepRecord]:
    root = ET.parse(case_file).getroot()
    records: list[StepRecord] = []
    for case in root.findall(".//case"):
        case_id = case.get("id") or case_file.stem
        case_title = case.get("title") or ""
        for step in case.findall("./pre_process/test_step"):
            add_step(records, phase="pre_process", case_id=case_id, case_title=case_title, step=step)
        test_case = case.find("./test_case")
        if test_case is not None:
            for child in list(test_case):
                if child.tag == "test_step":
                    add_step(records, phase="test_case", case_id=case_id, case_title=case_title, step=child)
                elif child.tag == "scenario":
                    scenario_id = child.get("id") or ""
                    scenario_title = child.get("title") or ""
                    for index, step in enumerate(child.findall("./test_step"), start=1):
                        add_step(
                            records,
                            phase="scenario",
                            case_id=case_id,
                            case_title=case_title,
                            scenario_id=scenario_id,
                            scenario_title=scenario_title,
                            scenario_step_no=index,
                            step=step,
                        )
        for step in case.findall("./post_process/test_step"):
            add_step(records, phase="post_process", case_id=case_id, case_title=case_title, step=step)
    return records


def step_label(step: StepRecord) -> str:
    if step.model and step.data:
        return f"{step.model}.{step.data}"
    if step.model:
        return step.model
    if step.data:
        return step.data
    return "-"


def choose_target(records: list[StepRecord], around_step: int) -> StepRecord:
    if not records:
        raise RuntimeError("case 中没有 test_step")
    for record in records:
        if record.global_index == around_step:
            return record
    return min(records, key=lambda record: abs(record.global_index - around_step))


def checkpoint_before(records: list[StepRecord], target: StepRecord) -> str:
    prior = [record for record in records if record.global_index < target.global_index]
    for record in reversed(prior):
        if record.action == "verify":
            return f"step {record.global_index} verify {step_label(record)}"
        if record.action == "navigate":
            return f"step {record.global_index} navigate {step_label(record)}"
    return "case 开始 / pre_process"


def checkpoint_after(records: list[StepRecord], target: StepRecord) -> str:
    if target.action == "verify":
        return f"step {target.global_index} verify {step_label(target)}"
    same_scope = [
        record
        for record in records
        if record.global_index > target.global_index
        and record.case_id == target.case_id
        and record.scenario_id == target.scenario_id
    ]
    for record in same_scope:
        if record.action == "verify":
            return f"step {record.global_index} verify {step_label(record)}"
    return f"step {target.global_index} {target.action} {step_label(target)}"


def related_model_data(records: list[StepRecord], target: StepRecord) -> list[str]:
    related: list[str] = []
    for record in records:
        if abs(record.global_index - target.global_index) > 2:
            continue
        if not record.model:
            continue
        label = step_label(record)
        if label != "-" and label not in related:
            related.append(label)
    if target.model and step_label(target) not in related and step_label(target) != "-":
        related.append(step_label(target))
    return related


def plan_supported(rodski: str) -> bool:
    try:
        result = subprocess.run(
            [rodski, "plan", "debug-step", "--help"],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def create_debug_plan(
    *,
    module: Path,
    rodski: str,
    plan_id: str,
    target: StepRecord,
    step_mode: str,
    prepare: str,
    cleanup: str,
) -> tuple[bool, str]:
    if not target.scenario_id or target.scenario_step_no is None:
        return False, "未生成 plan：目标步骤不在 scenario 内；RodSki step_debug 需要 scenario。"
    if not plan_supported(rodski):
        return False, "未生成 plan：当前 RodSki CLI 未暴露 plan debug-step。"
    command = [
        rodski,
        "plan",
        "debug-step",
        plan_id,
        "--case",
        target.case_id,
        "--scenario",
        target.scenario_id,
        "--step",
        str(target.scenario_step_no),
        "--step-mode",
        step_mode,
        "--prepare",
        prepare,
        "--cleanup",
        cleanup,
    ]
    result = subprocess.run(
        command,
        cwd=str(module),
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        message = (result.stderr or result.stdout).strip()
        return False, f"plan 生成失败：{message}"
    return True, (result.stdout or "").strip()


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    module = Path(args.module).expanduser().resolve()
    if not module.exists() or not module.is_dir():
        raise FileNotFoundError(f"未找到模块：{module}")
    case_file = find_case_file(module, args.case)
    records = parse_steps(case_file)
    target = choose_target(records, args.around_step)
    plan_id = f"debug_{sanitize(target.case_id)}_{sanitize(target.scenario_id or 'case')}_step{target.scenario_step_no or target.global_index}"
    created = False
    plan_message = "已通过 --no-write-plan 跳过 plan 生成"
    if not args.no_write_plan:
        created, plan_message = create_debug_plan(
            module=module,
            rodski=args.rodski,
            plan_id=plan_id,
            target=target,
            step_mode=args.step_mode,
            prepare=args.prepare,
            cleanup=args.cleanup,
        )
    plan_path = module / "plan" / f"{plan_id}.xml"
    return {
        "module": str(module),
        "case_file": str(case_file),
        "case_id": target.case_id,
        "scenario": target.scenario_id,
        "scenario_title": target.scenario_title,
        "target_step": {
            "global_index": target.global_index,
            "scenario_step_no": target.scenario_step_no,
            "action": target.action,
            "model": target.model,
            "data": target.data,
            "label": step_label(target),
        },
        "start_checkpoint": checkpoint_before(records, target),
        "target_checkpoint": checkpoint_after(records, target),
        "related_model_data": related_model_data(records, target),
        "plan": {
            "id": plan_id,
            "created": created,
            "path": str(plan_path) if created or plan_path.exists() else "",
            "message": plan_message,
            "run_command": f"{args.rodski} run @{plan_id} --debug",
        },
    }


def render_text(report: dict[str, Any]) -> str:
    lines = ["建议的窄范围运行："]
    lines.append(f"scenario: {report['scenario'] or '-'}")
    lines.append(f"起始 checkpoint: {report['start_checkpoint']}")
    lines.append(f"目标 checkpoint: {report['target_checkpoint']}")
    lines.append("相关 model/data:")
    for item in report["related_model_data"]:
        lines.append(item)
    lines.append("")
    lines.append("Debug plan:")
    if report["plan"]["created"]:
        lines.append(f"已创建: {report['plan']['path']}")
        lines.append(f"运行: {report['plan']['run_command']}")
    else:
        lines.append(report["plan"]["message"])
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    try:
        report = build_report(args)
    except (OSError, RuntimeError, ET.ParseError, subprocess.TimeoutExpired) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_text(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
