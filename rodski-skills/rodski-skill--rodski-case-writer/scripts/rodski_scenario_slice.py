#!/usr/bin/env python3
"""从单 case 判定表 XML 中按 scenario 切片。

大型判定表（如 UI 平台促销活动单用例判定表，300KB+、几十个 <scenario>）整文件读入会
吃光上下文。本脚本只做两件事：
  list  —— 列出所有 scenario 的 id/title/group/tag、行范围和字节数，不打印正文；
  show  —— 按 id 打印单个或多个 scenario 的原文，并给出精确行范围，便于定位编辑。

只读脚本，不修改任何文件。行范围为 1 基、闭区间，可直接用于按行读取或定位 Edit。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET


SCENARIO_OPEN = re.compile(r"<scenario\b")
SCENARIO_CLOSE = re.compile(r"</scenario\s*>")
ATTR = re.compile(r"([A-Za-z_][\w:-]*)\s*=\s*(['\"])(.*?)\2", re.S)


@dataclass
class Scenario:
    scenario_id: str
    title: str
    group: str
    tag: str
    start_line: int  # 1-based, inclusive
    end_line: int    # 1-based, inclusive
    byte_size: int = field(default=0)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.scenario_id,
            "title": self.title,
            "group": self.group,
            "tag": self.tag,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "line_count": self.end_line - self.start_line + 1,
            "byte_size": self.byte_size,
        }


def parse_attrs(open_head: str) -> dict[str, str]:
    """从 <scenario ...> 起始标签文本里抽属性。只取第一个标签（到首个 '>'）的属性。"""
    head = open_head.split(">", 1)[0]
    return {m.group(1): m.group(3) for m in ATTR.finditer(head)}


def find_scenarios(lines: list[str]) -> list[Scenario]:
    """按行扫描定位每个 <scenario>…</scenario> 的边界。

    判定表里一行一个 <scenario 起始、独立的 </scenario> 结束（已对本仓库实际文件验证）。
    起始标签属性可能跨行，故向后拼接若干行再抽属性。
    """
    scenarios: list[Scenario] = []
    open_idx: int | None = None
    open_attrs: dict[str, str] = {}
    for i, line in enumerate(lines):
        if open_idx is None and SCENARIO_OPEN.search(line):
            open_idx = i
            joined = "\n".join(lines[i : i + 6])
            open_attrs = parse_attrs(joined[joined.index("<scenario") :])
        if open_idx is not None and SCENARIO_CLOSE.search(line):
            body = "\n".join(lines[open_idx : i + 1])
            scenarios.append(
                Scenario(
                    scenario_id=open_attrs.get("id", ""),
                    title=open_attrs.get("title", ""),
                    group=open_attrs.get("group", ""),
                    tag=open_attrs.get("tag", ""),
                    start_line=open_idx + 1,
                    end_line=i + 1,
                    byte_size=len(body.encode("utf-8")),
                )
            )
            open_idx = None
            open_attrs = {}
    return scenarios


def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


def validate_well_formed(path: Path) -> str | None:
    """尽力整体解析一次；失败只告警，不阻断（切片仍按行边界进行）。"""
    try:
        ET.parse(path)
    except ET.ParseError as exc:
        return f"整文件 XML 解析告警（不影响按行切片）：{exc}"
    return None


def cmd_list(args: argparse.Namespace) -> int:
    path = Path(args.case).expanduser().resolve()
    if not path.exists():
        print(f"ERROR: 找不到文件：{path}", file=sys.stderr)
        return 1
    lines = read_lines(path)
    scenarios = find_scenarios(lines)
    warn = validate_well_formed(path)
    if args.json:
        print(
            json.dumps(
                {
                    "case": str(path),
                    "total_lines": len(lines),
                    "scenario_count": len(scenarios),
                    "warning": warn,
                    "scenarios": [s.to_dict() for s in scenarios],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    print(f"# 文件：{path}")
    print(f"# 总行数：{len(lines)}  scenario 数：{len(scenarios)}")
    if warn:
        print(f"# ⚠️ {warn}")
    print(f"# {'id':<10} {'行范围':>13}  {'字节':>8}  group / title")
    for s in scenarios:
        rng = f"{s.start_line}-{s.end_line}"
        print(f"  {s.scenario_id:<10} {rng:>13}  {s.byte_size:>8}  {s.group}  {s.title}")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    path = Path(args.case).expanduser().resolve()
    if not path.exists():
        print(f"ERROR: 找不到文件：{path}", file=sys.stderr)
        return 1
    lines = read_lines(path)
    scenarios = find_scenarios(lines)
    wanted = {sid.strip() for sid in args.id}
    by_id = {s.scenario_id: s for s in scenarios}
    missing = [sid for sid in wanted if sid not in by_id]
    if missing:
        available = ", ".join(s.scenario_id for s in scenarios)
        print(f"ERROR: 未找到 scenario id: {', '.join(missing)}", file=sys.stderr)
        print(f"可用 id：{available}", file=sys.stderr)
        return 1
    selected = [s for s in scenarios if s.scenario_id in wanted]
    if args.json:
        print(
            json.dumps(
                {
                    "case": str(path),
                    "scenarios": [
                        {**s.to_dict(), "text": "\n".join(lines[s.start_line - 1 : s.end_line])}
                        for s in selected
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    for s in selected:
        print(f"# scenario {s.scenario_id}  行 {s.start_line}-{s.end_line}  ({s.byte_size} 字节)")
        print(f"# title: {s.title}")
        print("\n".join(lines[s.start_line - 1 : s.end_line]))
        print()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="按 scenario 切片大型单 case 判定表 XML，避免整文件读入。只读，不改文件。"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="列出所有 scenario 的 id/行范围/字节数，不打印正文。")
    p_list.add_argument("case", help="判定表 case XML 路径。")
    p_list.add_argument("--json", action="store_true", help="输出 JSON。")
    p_list.set_defaults(func=cmd_list)

    p_show = sub.add_parser("show", help="按 id 打印单个或多个 scenario 原文与行范围。")
    p_show.add_argument("case", help="判定表 case XML 路径。")
    p_show.add_argument("--id", required=True, nargs="+", help="一个或多个 scenario id，如 PC_001。")
    p_show.add_argument("--json", action="store_true", help="输出 JSON（含正文）。")
    p_show.set_defaults(func=cmd_show)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
