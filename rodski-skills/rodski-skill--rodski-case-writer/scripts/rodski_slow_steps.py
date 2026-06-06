#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_THRESHOLD_SECONDS = 5.0
TIMESTAMP_RE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),(\d{3})")
STEP_MARKER_RE = re.compile(r"\[\s*(\d+)\s*\]\s*([A-Za-z_][\w-]*)?")
KEYWORD_RE = re.compile(r"执行关键字:\s*([A-Za-z_][\w-]*)(?:\((.*?)\))?")
NUMBER_SECONDS_RE = re.compile(r"(?<!\d)(\d+(?:\.\d+)?)\s*(?:s|秒|seconds?)", re.I)
MODEL_ELEMENT_RE = re.compile(r"\b([A-Za-z_][\w-]*)\.([A-Za-z_][\w-]*)\b")
MODEL_ARG_RE = re.compile(r"\bmodel=([A-Za-z_][\w-]*)")
DATA_ARG_RE = re.compile(r"\bdata=([A-Za-z_][\w-]*)")
XPATH_RE = re.compile(r"xpath|//|\.//", re.I)
QUERY_SELECTOR_RE = re.compile(r"querySelector|query_selector|document\.querySelector", re.I)
FALLBACK_RE = re.compile(r"fallback|备用|兜底|降级|下一个定位器|尝试.*定位器", re.I)
LOCATOR_RE = re.compile(r"定位器|locator|selector|SKI302|所有定位器均失败", re.I)
READY_RE = re.compile(r"必填|校验.*(?:完成|失败|结果)|未完成|保存失败|落表|入表|回填|主表|已添加|添加成功", re.I)


@dataclass
class StepTiming:
    index: int
    action: str = ""
    model: str = ""
    data: str = ""
    label: str = ""
    start: datetime | None = None
    end: datetime | None = None
    explicit_duration: float | None = None
    lines: list[str] = field(default_factory=list)
    locator_failure: bool = False
    retry: bool = False
    wait_seconds: float | None = None
    xpath_fallback: bool = False
    query_selector: bool = False
    ready_state_gap: bool = False
    signals: set[str] = field(default_factory=set)

    @property
    def duration(self) -> float | None:
        if self.explicit_duration is not None:
            return self.explicit_duration
        if self.start is not None and self.end is not None and self.end >= self.start:
            return (self.end - self.start).total_seconds()
        return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="从结果目录分析 RodSki 慢步骤。"
    )
    parser.add_argument("--result-dir", required=True, help="RodSki 结果目录。")
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD_SECONDS,
        help="步骤被报告为慢步骤的最小时长（秒）。",
    )
    parser.add_argument("--limit", type=int, default=30, help="最多打印的慢步骤数量。")
    parser.add_argument("--json", action="store_true", help="输出 JSON。")
    return parser.parse_args()


def parse_timestamp(line: str) -> datetime | None:
    match = TIMESTAMP_RE.match(line)
    if not match:
        return None
    return datetime.strptime(f"{match.group(1)}.{match.group(2)}", "%Y-%m-%d %H:%M:%S.%f")


def parse_seconds(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value)
    match = NUMBER_SECONDS_RE.search(text)
    if match:
        return float(match.group(1))
    try:
        return float(text)
    except ValueError:
        return None


def read_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return None


def walk_dicts(value: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(value, dict):
        found.append(value)
        for item in value.values():
            found.extend(walk_dicts(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(walk_dicts(item))
    return found


def parse_kv_args(args_text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for part in re.split(r",\s*", args_text or ""):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def label_for(step: StepTiming) -> str:
    if step.label:
        return step.label
    if step.model and step.data:
        return f"{step.model}.{step.data}"
    if step.model:
        return step.model
    if step.data:
        return step.data
    return "-"


def reason_for(step: StepTiming, threshold: float) -> str | None:
    duration = step.duration
    if step.action == "wait" and step.wait_seconds is not None:
        return f"固定等待 {format_seconds(step.wait_seconds)}"
    if step.query_selector and step.xpath_fallback:
        return f"XPath fallback 进入 querySelector {format_seconds(duration)}"
    if step.query_selector:
        return f"querySelector fallback {format_seconds(duration)}"
    if step.xpath_fallback:
        return f"XPath fallback {format_seconds(duration)}"
    if step.locator_failure:
        return f"定位器 fallback {format_seconds(duration)}"
    if step.retry:
        return f"重试 {format_seconds(duration)}"
    if step.ready_state_gap:
        return f"业务状态未就绪 {format_seconds(duration)}"
    if duration is not None and duration >= threshold:
        return f"慢步骤 {format_seconds(duration)}"
    return None


def sorted_signals(step: StepTiming) -> list[str]:
    signals = set(step.signals)
    if step.locator_failure:
        signals.add("locator")
    if step.retry:
        signals.add("retry")
    if step.xpath_fallback:
        signals.add("xpath_fallback")
    if step.query_selector:
        signals.add("querySelector")
    if step.ready_state_gap:
        signals.add("ready_state_gap")
    if step.action == "wait" and step.wait_seconds is not None:
        signals.add("fixed_wait")
    return sorted(signals)


def edit_target_for(step: StepTiming) -> str:
    if step.label and "." in step.label:
        return f"model/model.xml::{step.label}"
    if step.model and step.data and step.action in {"type", "verify", "get", "clear", "upload_file"}:
        return f"model/model.xml::{step.model} + data/data.sqlite::{step.model}.{step.data}"
    if step.model and step.action in {"type", "verify", "get", "clear", "upload_file"}:
        return f"model/model.xml::{step.model}"
    if step.action == "wait":
        return "case/*.xml wait step or data ready locator"
    return ""


def suggestion_for(step: StepTiming, threshold: float) -> str:
    if step.action == "wait" and step.wait_seconds is not None:
        return "用可观察状态替代固定等待，例如 ready element、状态 verify 或有界 evaluate poll。"
    if step.query_selector or step.xpath_fallback:
        return "先检查 model.xml 对应 element 的 locator 优先级，删除长期不命中的 XPath/JS 兜底，只保留已验证秒中的稳定定位器。"
    if step.locator_failure:
        return "收窄当前页面/弹窗/行/列范围；把稳定命中的 locator 放到 priority=1，无价值 fallback 直接删。"
    if step.ready_state_gap:
        return "确认按钮前补业务状态等待，例如校验完成行、回填文本或主表新增行，再执行提交/确定。"
    if step.retry:
        return "用失败截图判断元素是未渲染、重复、隐藏还是页面状态错误，再决定改 locator 或补状态等待。"
    duration = step.duration
    if duration is not None and duration >= threshold:
        return "查看该步骤附近日志和截图，优先排查慢 locator、固定等待和真实异步状态。"
    return ""


def format_seconds(value: float | None) -> str:
    if value is None:
        return "未知"
    if abs(value - round(value)) < 0.05:
        return f"{int(round(value))}s"
    return f"{value:.1f}s"


def parse_execution_summary(result_dir: Path) -> list[StepTiming]:
    data = read_json(result_dir / "execution_summary.json")
    if data is None:
        return []
    steps: list[StepTiming] = []
    for record in walk_dicts(data):
        if "action" not in record:
            continue
        index = record.get("index") or record.get("step") or record.get("step_index")
        try:
            step_index = int(index)
        except (TypeError, ValueError):
            continue
        duration = None
        for key in ("duration", "elapsed", "elapsed_seconds", "execution_time", "total_time"):
            duration = parse_seconds(record.get(key))
            if duration is not None:
                break
        step = StepTiming(
            index=step_index,
            action=str(record.get("action") or ""),
            model=str(record.get("model") or ""),
            data=str(record.get("data") or ""),
            explicit_duration=duration,
        )
        if step.action == "wait":
            step.wait_seconds = parse_seconds(step.data)
        text = json.dumps(record, ensure_ascii=False)
        collect_signals_from_text(step, text)
        step.locator_failure = step.locator_failure or bool(LOCATOR_RE.search(text))
        step.retry = bool(re.search(r"重试|retry|SKI313", text, re.I))
        element = re.search(r"元素\s*'([^']+)'", text)
        if element:
            step.label = element.group(1)
        steps.append(step)
    return steps


def collect_signals_from_text(step: StepTiming, text: str) -> None:
    if LOCATOR_RE.search(text):
        step.locator_failure = True
        step.signals.add("locator")
    if FALLBACK_RE.search(text):
        step.signals.add("fallback")
    if XPATH_RE.search(text) and (step.locator_failure or FALLBACK_RE.search(text)):
        step.xpath_fallback = True
        step.signals.add("xpath_fallback")
    if QUERY_SELECTOR_RE.search(text):
        step.query_selector = True
        step.signals.add("querySelector")
    if READY_RE.search(text):
        step.ready_state_gap = True
        step.signals.add("ready_state_gap")
    if re.search(r"重试|retry|SKI313", text, re.I):
        step.retry = True
        step.signals.add("retry")
    model = MODEL_ARG_RE.search(text)
    if model and not step.model:
        step.model = model.group(1)
    data = DATA_ARG_RE.search(text)
    if data and not step.data:
        step.data = data.group(1)
    model_element = MODEL_ELEMENT_RE.search(text)
    if model_element and not step.label:
        step.label = f"{model_element.group(1)}.{model_element.group(2)}"


def parse_execution_log(result_dir: Path) -> list[StepTiming]:
    path = result_dir / "execution.log"
    if not path.exists():
        return []
    steps: list[StepTiming] = []
    current: StepTiming | None = None

    def finish(end_time: datetime | None) -> None:
        nonlocal current
        if current is None:
            return
        if current.end is None and end_time is not None:
            current.end = end_time
        steps.append(current)
        current = None

    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        ts = parse_timestamp(line)
        marker = STEP_MARKER_RE.search(line)
        if marker and "DEBUG" in line:
            finish(ts)
            current = StepTiming(index=int(marker.group(1)), action=marker.group(2) or "", start=ts)
        if current is None:
            continue
        if ts is not None:
            current.end = ts
        current.lines.append(line)

        keyword = KEYWORD_RE.search(line)
        if keyword:
            current.action = keyword.group(1)
            kv = parse_kv_args(keyword.group(2) or "")
            current.model = kv.get("model", current.model).strip("-")
            current.data = kv.get("data", current.data)
            if current.action == "wait":
                current.wait_seconds = parse_seconds(current.data)

        element = re.search(r"元素\s*'([^']+)'", line)
        if element:
            current.label = element.group(1)
        collect_signals_from_text(current, line)
        if current.action == "wait" and current.wait_seconds is None:
            current.wait_seconds = parse_seconds(line)
    finish(None)
    return steps


def merge_steps(summary_steps: list[StepTiming], log_steps: list[StepTiming]) -> list[StepTiming]:
    # 用 (index, 第几次出现) 作 join key：多 scenario 下步骤号会跨场景重复
    # （[1][2]...[1][2]），单纯用 index 当 key 会让后一个 step 静默覆盖前一个、
    # 丢失慢步骤。对 log 与 summary 各自按出现次序编号，同序号的第 N 次出现彼此
    # 匹配做富集合并，其余步骤全部保留。
    def keyed(steps: list[StepTiming]) -> list[tuple[tuple[int, int], StepTiming]]:
        seen: Counter[int] = Counter()
        pairs: list[tuple[tuple[int, int], StepTiming]] = []
        for step in steps:
            seen[step.index] += 1
            pairs.append(((step.index, seen[step.index]), step))
        return pairs

    merged: dict[tuple[int, int], StepTiming] = {}
    for key, step in keyed(log_steps):
        merged[key] = step
    for key, step in keyed(summary_steps):
        if key not in merged:
            merged[key] = step
            continue
        target = merged[key]
        for attr in ("action", "model", "data", "label"):
            if not getattr(target, attr) and getattr(step, attr):
                setattr(target, attr, getattr(step, attr))
        if target.explicit_duration is None:
            target.explicit_duration = step.explicit_duration
        target.locator_failure = target.locator_failure or step.locator_failure
        target.retry = target.retry or step.retry
        target.xpath_fallback = target.xpath_fallback or step.xpath_fallback
        target.query_selector = target.query_selector or step.query_selector
        target.ready_state_gap = target.ready_state_gap or step.ready_state_gap
        target.signals.update(step.signals)
        if target.wait_seconds is None:
            target.wait_seconds = step.wait_seconds
    # 按执行序号、再按出现次序排序，保持稳定的时间线展示。
    return [merged[key] for key in sorted(merged)]


def build_report(result_dir: Path, threshold: float, limit: int) -> dict[str, Any]:
    steps = merge_steps(parse_execution_summary(result_dir), parse_execution_log(result_dir))
    slow: list[dict[str, Any]] = []
    for step in steps:
        reason = reason_for(step, threshold)
        duration = step.duration
        if reason is None:
            continue
        slow.append(
            {
                "index": step.index,
                "action": step.action or "-",
                "label": label_for(step),
                "duration": duration,
                "reason": reason,
                "model": step.model,
                "data": step.data,
                "signals": sorted_signals(step),
                "edit_target": edit_target_for(step),
                "suggestion": suggestion_for(step, threshold),
            }
        )
    slow.sort(key=lambda item: item["index"])
    return {
        "result_dir": str(result_dir),
        "threshold": threshold,
        "slow_steps": slow[:limit],
        "step_count": len(steps),
        "hints": [
            "优先调整 locator 优先级，把稳定命中的定位器放前面。",
            "删除已知长期超时且无价值的 fallback locator。",
            "将固定 wait 改为状态 verify、稳定 ready locator 或有返回值的 evaluate poll。",
            "拆分 debug plan 执行单段流程，避免全链路反复重跑。",
        ],
    }


def render_text(report: dict[str, Any]) -> str:
    lines = ["慢步骤："]
    if not report["slow_steps"]:
        lines.append(f"（未发现超过 {format_seconds(report['threshold'])} 的慢步骤）")
    for item in report["slow_steps"]:
        lines.append(f"step {item['index']} {item['action']} {item['label']}: {item['reason']}")
        if item.get("signals"):
            lines.append(f"  signals: {', '.join(item['signals'])}")
        if item.get("edit_target"):
            lines.append(f"  edit: {item['edit_target']}")
        if item.get("suggestion"):
            lines.append(f"  next: {item['suggestion']}")
    lines.append("")
    lines.append("优化提示：")
    for hint in report["hints"]:
        lines.append(f"- {hint}")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    result_dir = Path(args.result_dir).expanduser().resolve()
    if not result_dir.exists() or not result_dir.is_dir():
        print(f"ERROR: 未找到结果目录：{result_dir}", file=sys.stderr)
        return 1
    report = build_report(result_dir, args.threshold, args.limit)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_text(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
