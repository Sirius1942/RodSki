#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path


DEFAULT_REPO = Path.home() / "TestCase"
DEFAULT_GUIDE = DEFAULT_REPO / "TEST_CASE_WRITING_GUIDE.md"

MODE_PATTERNS: dict[str, list[str]] = {
    "core": [
        r"^## 1\.",
        r"^## 2\.",
        r"^### 3\.[1256]\b",
        r"^## 4\.",
        r"^## 5\.",
        r"^## 6\.",
        r"^## 7\.",
        r"^## 附录：关键字速查清单",
    ],
    "ui": [
        r"^### 3\.[1-6]\b",
        r"^## 4\.",
        r"^### 5\.3\b",
        r"^### 5\.4\b",
        r"^### 6\.4\b",
        r"^### 7\.[36]\b",
        r"^### 8\.1\b",
        r"^### 8\.2\b",
        r"^### 8\.5\b",
        r"^### 8\.6\b",
        r"^## .*视觉定位器",
        r"^### Q[1237]:",
        r"^### A\. UI",
    ],
    "api": [
        r"^### 3\.[156]\b",
        r"^### 4\.[126]\b",
        r"^### 5\.[134]\b",
        r"^### 7\.[1-6]\b",
        r"^### 8\.2\b",
        r"^#### 接口测试",
        r"^### 8\.3\b",
        r"^### B\. 接口关键字",
    ],
    "db": [
        r"^### 3\.[156]\b",
        r"^### 4\.[126]\b",
        r"^### 5\.[135]\b",
        r"^### 6\.5\b",
        r"^### 8\.4\b",
        r"^### Q4:",
        r"^### C\. 数据与高级关键字",
    ],
    "data": [
        r"^## 5\.",
        r"^## 6\.",
        r"^## 7\.",
        r"^### Q[2456]:",
        r"^### C\. 数据与高级关键字",
    ],
    "plan": [
        r"^### 3\.4\b",
        r"^## .*测试计划",
        r"^## .*固定与动态测试步骤",
    ],
    "long-flow": [
        r"^### 3\.3\b",
        r"^### 3\.4\b",
        r"^### 5\.4\b",
        r"^## 7\.",
        r"^### 8\.2\b",
        r"^### 8\.5\b",
        r"^### 8\.6\b",
        r"^## .*测试计划",
    ],
    "debug": [
        r"^### 3\.6\b",
        r"^### 4\.3\b",
        r"^### 4\.5\b",
        r"^### 4\.6\b",
        r"^### 5\.3\b",
        r"^### 5\.4\b",
        r"^## 7\.",
        r"^## 8\. 关键字手册",
        r"^## 附录：常见问题",
        r"^## 附录：测试结果 XML",
    ],
    "desktop": [
        r"^### 8\.5\b",
        r"^## .*视觉定位器",
        r"^## .*桌面端自动化",
    ],
}


# 勘误覆盖：guide 是只读参考，部分章节已被当前 CLI/源码淘汰。
# key 是匹配标题行的正则，value 是抽到该章节时追加的提示。
# 以本机实测的 references/ 笔记和当前 CLI/源码为准，不要照抄被勘误的章节。
ERRATA: list[tuple[str, str]] = [
    (
        r"^## 11\. .*视觉定位器",
        "§11 视觉定位器：guide 描述的 OmniParser 服务 + vision_config.yaml 配置方式在 "
        "RodSki v7.1.0 已删除。以 references/vision-locators.md 和当前 CLI/源码为准。",
    ),
    (
        r"^### 11\.4 ",
        "§11.4 配置要求：vision_config.yaml / omniparser 段已被淘汰，本机不存在该文件，"
        "加载时会被直接丢弃。不要照抄此节，见 references/vision-locators.md。",
    ),
    (
        r"^#### 4\.3\.2 .*视觉定位器",
        "视觉定位器现状以 references/vision-locators.md 为准；guide §11.4 的 OmniParser "
        "配置已过时。",
    ),
]


@dataclass(frozen=True)
class Heading:
    line_index: int
    level: int
    text: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="从 TEST_CASE_WRITING_GUIDE.md 打印与任务相关的切片。"
    )
    parser.add_argument("--repo", default=str(DEFAULT_REPO), help="RodSki 用例仓库根目录。")
    parser.add_argument("--guide", default="", help="显式指定 guide 路径。")
    parser.add_argument(
        "--mode",
        choices=sorted(MODE_PATTERNS),
        default="core",
        help="要打印的 guide 切片。",
    )
    parser.add_argument("--list", action="store_true", help="列出可用模式后退出。")
    parser.add_argument("--json", action="store_true", help="输出 JSON 元数据和文本。")
    return parser.parse_args()


def read_guide(args: argparse.Namespace) -> tuple[Path, list[str]]:
    guide = Path(args.guide).expanduser() if args.guide else Path(args.repo).expanduser() / "TEST_CASE_WRITING_GUIDE.md"
    guide = guide.resolve()
    if not guide.exists():
        raise FileNotFoundError(f"guide 未找到：{guide}")
    return guide, guide.read_text(encoding="utf-8", errors="replace").splitlines()


def collect_headings(lines: list[str]) -> list[Heading]:
    headings: list[Heading] = []
    for index, line in enumerate(lines):
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if match:
            headings.append(Heading(index, len(match.group(1)), line.strip()))
    return headings


def heading_range(headings: list[Heading], index: int, line_count: int) -> tuple[int, int]:
    heading = headings[index]
    end = line_count
    for later in headings[index + 1 :]:
        if later.level <= heading.level:
            end = later.line_index
            break
    return heading.line_index, end


def merge_ranges(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    if not ranges:
        return []
    ranges = sorted((start, end) for start, end in ranges if start < end)
    merged = [ranges[0]]
    for start, end in ranges[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end + 1:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


def selected_ranges(lines: list[str], headings: list[Heading], mode: str) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    first_section = next(
        (heading.line_index for heading in headings if heading.text.startswith("## 1.")),
        min(30, len(lines)),
    )
    ranges.append((0, first_section))

    patterns = [re.compile(pattern) for pattern in MODE_PATTERNS[mode]]
    for index, heading in enumerate(headings):
        if any(pattern.search(heading.text) for pattern in patterns):
            ranges.append(heading_range(headings, index, len(lines)))
    return merge_ranges(ranges)


def unmatched_patterns(headings: list[Heading], mode: str) -> list[str]:
    """返回该 mode 中在当前 guide 标题里 0 命中的 pattern 原文。

    guide 是只读参考且 MODE_PATTERNS 写死了章节号；一旦 guide 被重新编号、
    章节号漂移，对应 pattern 会静默落空，切片只剩 header。把落空的 pattern
    暴露出来，让 guide 版本漂移可见，而不是静默返回错误内容。
    """
    raw_patterns = MODE_PATTERNS[mode]
    heading_texts = [heading.text for heading in headings]
    missing: list[str] = []
    for raw in raw_patterns:
        compiled = re.compile(raw)
        if not any(compiled.search(text) for text in heading_texts):
            missing.append(raw)
    return missing


def render(lines: list[str], ranges: list[tuple[int, int]]) -> str:
    chunks: list[str] = []
    for start, end in ranges:
        chunks.extend(lines[start:end])
        chunks.append("")
    return "\n".join(chunks).rstrip() + "\n"


def applicable_errata(lines: list[str], ranges: list[tuple[int, int]]) -> list[str]:
    """返回当前切片范围内命中勘误的提示，去重后保持声明顺序。"""
    patterns = [(re.compile(pattern), note) for pattern, note in ERRATA]
    notes: list[str] = []
    for start, end in ranges:
        for line in lines[start:end]:
            for compiled, note in patterns:
                if compiled.search(line.strip()) and note not in notes:
                    notes.append(note)
    return notes


def main() -> int:
    args = parse_args()
    if args.list:
        for mode in sorted(MODE_PATTERNS):
            print(mode)
        return 0

    try:
        guide, lines = read_guide(args)
    except OSError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    headings = collect_headings(lines)
    ranges = selected_ranges(lines, headings, args.mode)
    text = render(lines, ranges)
    errata = applicable_errata(lines, ranges)
    missing_patterns = unmatched_patterns(headings, args.mode)

    if args.json:
        print(
            json.dumps(
                {
                    "guide": str(guide),
                    "mode": args.mode,
                    "source_line_count": len(lines),
                    "selected_line_count": sum(end - start for start, end in ranges),
                    "ranges": [{"start": start + 1, "end": end} for start, end in ranges],
                    "errata": errata,
                    "unmatched_patterns": missing_patterns,
                    "text": text,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if missing_patterns:
        print(
            f"WARN: mode={args.mode} 有 {len(missing_patterns)}/{len(MODE_PATTERNS[args.mode])} "
            "个章节匹配落空，guide 可能已重新编号；切片可能不完整。落空 pattern："
            + ", ".join(missing_patterns),
            file=sys.stderr,
        )

    print(f"# Guide 切片：{args.mode}")
    print(f"# 来源：{guide}")
    print(f"# 行数：从 {len(lines)} 行中选择 {sum(end - start for start, end in ranges)} 行")
    if errata:
        print("#")
        print("# ⚠️ 勘误（guide 为只读参考，以下章节已被当前 CLI/源码淘汰）：")
        for note in errata:
            print(f"#   - {note}")
    print()
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
