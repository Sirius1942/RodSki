#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


FAIL_VALUES = {"fail", "failed", "failure", "error", "exception", "失败"}
LOG_PATTERNS = ("ERROR", "FAIL", "FAILED", "SKI302", "SKI313", "Traceback", "Exception")
# 用词边界匹配，避免 "0 ERRORS"、"FAILSAFE" 这类子串误命中。
# FAIL 与 FAILED 都保留：\bFAIL\b 不会匹配 FAILED，需各自列出。
LOG_PATTERN_RE = re.compile(r"\b(?:" + "|".join(LOG_PATTERNS) + r")\b")
OK_VALUES = {"ok", "pass", "passed", "success", "成功", "通过"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="将 RodSki 结果目录汇总为首个失败和修复提示。"
    )
    parser.add_argument("--result-dir", required=True, help="RodSki 结果目录。")
    parser.add_argument("--log-bytes", type=int, default=2_000_000, help="从 execution.log 尾部读取的字节数。")
    parser.add_argument("--limit", type=int, default=20, help="最多打印的证据行/条目数量。")
    parser.add_argument("--json", action="store_true", help="输出 JSON。")
    return parser.parse_args()


def read_tail(path: Path, max_bytes: int) -> str:
    size = path.stat().st_size
    with path.open("rb") as handle:
        if size > max_bytes:
            handle.seek(-max_bytes, 2)
        data = handle.read()
    return data.decode("utf-8", errors="replace")


def walk_dicts(value: Any, path: str = "$") -> list[tuple[str, dict[str, Any]]]:
    found: list[tuple[str, dict[str, Any]]] = []
    if isinstance(value, dict):
        found.append((path, value))
        for key, item in value.items():
            found.extend(walk_dicts(item, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(walk_dicts(item, f"{path}[{index}]"))
    return found


def looks_failed(record: dict[str, Any]) -> bool:
    for key in ("status", "result", "state", "outcome"):
        value = str(record.get(key, "")).strip().lower()
        if value in FAIL_VALUES or "fail" in value or "error" in value:
            return True
    message = str(record.get("message", "") or record.get("error", "")).lower()
    return bool(re.search(r'\bfail(ed|ure)?\b|\berror\b|\bexception\b', message))


def looks_ok(record: dict[str, Any]) -> bool:
    for key in ("status", "result", "state", "outcome"):
        value = str(record.get(key, "")).strip().lower()
        if value in OK_VALUES:
            return True
    return False


def parse_seconds(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value)
    match = re.search(r"(?<!\d)(\d+(?:\.\d+)?)\s*(?:s|秒|seconds?)", text, re.I)
    if match:
        return float(match.group(1))
    try:
        return float(text)
    except ValueError:
        return None


def step_index(record: dict[str, Any]) -> int | None:
    for key in ("index", "step", "step_index", "step_no"):
        value = record.get(key)
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


def step_duration(record: dict[str, Any]) -> float | None:
    for key in ("duration", "elapsed", "elapsed_seconds", "execution_time", "total_time"):
        seconds = parse_seconds(record.get(key))
        if seconds is not None:
            return seconds
    return None


def is_step_record(record: dict[str, Any]) -> bool:
    return "action" in record and step_index(record) is not None


def compact_record(record: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "case",
        "case_id",
        "scenario",
        "scenario_id",
        "step",
        "step_index",
        "index",
        "action",
        "keyword",
        "model",
        "data",
        "status",
        "result",
        "message",
        "error",
        "screenshot",
        "recording",
        "duration",
        "elapsed",
    ]
    compact = {key: record[key] for key in keys if key in record and record[key] not in (None, "")}
    if compact:
        return compact
    return {key: record[key] for key in list(record)[:10]}


def compact_step(path_expr: str, record: dict[str, Any]) -> dict[str, Any]:
    compact = {"json_path": path_expr, **compact_record(record)}
    duration = step_duration(record)
    if duration is not None:
        compact["duration_seconds"] = duration
    return compact


def summarize_steps(data: Any) -> dict[str, Any]:
    step_records = [
        (path_expr, record)
        for path_expr, record in walk_dicts(data)
        if is_step_record(record)
    ]
    step_records.sort(key=lambda item: step_index(item[1]) or 0)
    failed_positions = [
        index for index, (_, record) in enumerate(step_records) if looks_failed(record)
    ]
    first_failed_index = failed_positions[0] if failed_positions else None
    first_failed = (
        compact_step(*step_records[first_failed_index])
        if first_failed_index is not None
        else {}
    )
    last_ok = {}
    if first_failed_index is not None:
        for path_expr, record in reversed(step_records[:first_failed_index]):
            if looks_ok(record):
                last_ok = compact_step(path_expr, record)
                break

    durations = [
        (step_duration(record), path_expr, record)
        for path_expr, record in step_records
        if step_duration(record) is not None
    ]
    slowest = {}
    if durations:
        seconds, path_expr, record = max(durations, key=lambda item: item[0] or 0)
        slowest = compact_step(path_expr, record)
        slowest["duration_seconds"] = seconds
    return {
        "step_count": len(step_records),
        "last_ok_before_failure": last_ok,
        "next_failed_step": first_failed,
        "slowest_step": slowest,
    }


def parse_summary(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False}
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"exists": True, "error": str(exc)}
    failed = [(path_expr, record) for path_expr, record in walk_dicts(data) if looks_failed(record)]
    first = {"json_path": failed[0][0], **compact_record(failed[0][1])} if failed else {}
    step_summary = summarize_steps(data)
    return {
        "exists": True,
        "top_level_keys": list(data) if isinstance(data, dict) else [],
        "failed_count": len(failed),
        "first_failed": first,
        **step_summary,
    }


def text_of(element: ET.Element) -> str:
    return " ".join(part.strip() for part in element.itertext() if part and part.strip())


def parse_result_xml(path: Path, limit: int) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False}
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        return {"exists": True, "error": str(exc)}

    failed_nodes: list[dict[str, Any]] = []
    path_hints: list[str] = []
    for element in root.iter():
        attrs = {key: value for key, value in element.attrib.items()}
        values = " ".join(str(value).lower() for value in attrs.values())
        tag = element.tag.lower()
        body = text_of(element)
        if any(token in values for token in ("fail", "error", "exception")) or any(token in tag for token in ("fail", "error")):
            failed_nodes.append({"tag": element.tag, "attrs": attrs, "text": body[:300]})
        for value in list(attrs.values()) + ([body] if body else []):
            for match in re.findall(r"[\w./\\-]*(?:screenshot|failure|recording)[\w./\\-]*\.(?:png|jpg|jpeg|webm|mp4)", value, re.I):
                path_hints.append(match)
    return {
        "exists": True,
        "root": root.tag,
        "failed_count": len(failed_nodes),
        "first_failed": failed_nodes[0] if failed_nodes else {},
        "path_hints": path_hints[:limit],
    }


def parse_log(path: Path, max_bytes: int, limit: int) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False}
    text = read_tail(path, max_bytes)
    lines = text.splitlines()
    matches = [
        {"line_tail_index": index + 1, "text": line[-1000:]}
        for index, line in enumerate(lines)
        if LOG_PATTERN_RE.search(line)
    ]
    slow: list[dict[str, Any]] = []
    for index, line in enumerate(lines):
        if not any(keyword in line.lower() for keyword in ("耗时", "duration", "elapsed", "took", "cost", "seconds", "秒")):
            continue
        numbers = [float(match) for match in re.findall(r"(?<!\d)(\d+(?:\.\d+)?)\s*(?:s|秒|seconds?)", line, re.I)]
        if any(value >= 5 for value in numbers):
            slow.append({"line_tail_index": index + 1, "text": line[-1000:]})
    return {
        "exists": True,
        "tail_line_count": len(lines),
        "evidence": matches[-limit:],
        "slow_hints": slow[-limit:],
    }


def list_media(result_dir: Path, limit: int) -> dict[str, list[str]]:
    screenshots = sorted(
        [path for path in result_dir.rglob("*") if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg"}],
        key=lambda path: path.stat().st_mtime,
    )
    recordings = sorted(
        [path for path in result_dir.rglob("*") if path.is_file() and path.suffix.lower() in {".webm", ".mp4"}],
        key=lambda path: path.stat().st_mtime,
    )
    failure_screenshots = [
        str(path)
        for path in screenshots
        if re.search(r"fail|failure|error|失败", path.name, re.I)
    ]
    return {
        "failure_screenshots": failure_screenshots[-limit:],
        "latest_screenshots": [str(path) for path in screenshots[-limit:]],
        "recordings": [str(path) for path in recordings[-limit:]],
    }


def infer_edit_surface(summary: dict[str, Any], result_xml: dict[str, Any], log: dict[str, Any]) -> list[str]:
    focus = summary.get("next_failed_step") or summary.get("first_failed")
    if not focus and summary.get("slowest_step"):
        slowest = summary["slowest_step"]
        action = slowest.get("action", "")
        label = ".".join(part for part in (slowest.get("model", ""), slowest.get("data", "")) if part)
        return [f"性能：检查最慢的 PASS 步骤 action={action} {label}".strip()]

    evidence = json.dumps([focus or {}, result_xml], ensure_ascii=False).lower()
    if log.get("evidence"):
        evidence += "\n" + "\n".join(item["text"].lower() for item in log["evidence"][-5:])
    hints: list[str] = []
    if "verify" in evidence:
        hints.append("verify 失败：先检查 data/data.sqlite 期望行，再检查 model 定位器/取值提取。")
    if "type" in evidence or "click" in evidence or "locator" in evidence:
        hints.append("UI action/定位失败：检查 model/model.xml 定位器优先级和匹配的数据行动作值。")
    if "send" in evidence or "api" in evidence or "http" in evidence:
        hints.append("API 失败：检查接口模型字段、请求数据行和 _verify 表。")
    if "db" in evidence or "database" in evidence or "sql" in evidence:
        hints.append("DB 失败：检查数据库模型、查询数据行和 data/globalvalue.xml 连接。")
    if "schema" in evidence or "xsd" in evidence or "parse" in evidence:
        hints.append("schema/解析失败：修改业务数据前先检查 case/model XML 结构。")
    if not hints:
        hints.append("未推断出具体编辑面；将首个失败步骤映射回 case -> data.sqlite -> model.xml。")
    return hints


def infer_action_advice(summary: dict[str, Any], result_xml: dict[str, Any], log: dict[str, Any]) -> list[str]:
    focus = summary.get("next_failed_step") or summary.get("first_failed") or summary.get("slowest_step") or {}
    action = str(focus.get("action") or focus.get("keyword") or "").strip()
    evidence = json.dumps([focus, result_xml, log.get("evidence", [])[-3:]], ensure_ascii=False)
    if not action:
        keyword = re.search(r"keyword:\s*([A-Za-z_][\w-]*)", evidence)
        if keyword:
            action = keyword.group(1)
    if not action:
        quoted = re.search(r"关键字\s*'([^']+)'", evidence)
        if quoted:
            action = quoted.group(1)

    advice: list[str] = []
    if action == "verify":
        advice.append("verify：优先核查 data.sqlite 的 _verify 表期望值，再核查 model.xml 的取值 locator。")
    elif action == "type":
        advice.append("type：优先核查 data.sqlite 对应 data row 的动作值，再核查 model.xml locator 与优先级。")
    elif action == "send":
        advice.append("send：优先核查接口 model 字段、请求 data row、以及对应 _verify 表。")
    elif action == "DB":
        advice.append("DB：优先核查 database model、查询 data row、以及 data/globalvalue.xml 连接配置。")
    elif action:
        advice.append(f"{action}：先从 case step 映射到 data.sqlite，再核查 model.xml 或关键字参数。")

    if "SKI302" in evidence or "locator" in evidence.lower() or "定位器" in evidence:
        advice.append("定位失败：优先调整 locator priority，删除无效 fallback，避免用 wait 掩盖定位问题。")
    if "SKI313" in evidence or "重试" in evidence or "retry" in evidence.lower():
        advice.append("重试失败：先确认最新截图页面状态，再只修复首个真实失败点。")
    if not advice:
        advice.append("未识别到具体 action：按 case -> data.sqlite -> model.xml 顺序映射首个失败步骤。")
    return advice


def render(report: dict[str, Any], limit: int) -> str:
    lines: list[str] = []
    lines.append(f"结果目录：{report['result_dir']}")
    summary = report["execution_summary"]
    result_xml = report["result_xml"]
    log = report["execution_log"]
    media = report["media"]

    lines.append("")
    lines.append("首个失败：")
    if summary.get("first_failed"):
        lines.append(f"- execution_summary.json: {summary['first_failed']}")
    elif result_xml.get("first_failed"):
        lines.append(f"- result.xml: {result_xml['first_failed']}")
    else:
        lines.append("- 未找到结构化失败")

    if summary.get("last_ok_before_failure") or summary.get("next_failed_step"):
        lines.append("")
        lines.append("执行汇总焦点：")
        if summary.get("last_ok_before_failure"):
            lines.append(f"- 最后通过：{summary['last_ok_before_failure']}")
        if summary.get("next_failed_step"):
            lines.append(f"- 下一失败：{summary['next_failed_step']}")

    if not summary.get("next_failed_step") and summary.get("slowest_step"):
        lines.append("")
        lines.append("最慢步骤：")
        lines.append(f"- {summary['slowest_step']}")

    if result_xml.get("path_hints"):
        lines.append("")
        lines.append("Result XML 路径：")
        for item in result_xml["path_hints"][:limit]:
            lines.append(f"- {item}")

    if log.get("evidence"):
        lines.append("")
        lines.append("日志证据：")
        for item in log["evidence"][-limit:]:
            lines.append(f"- 尾部第 {item['line_tail_index']} 行：{item['text']}")

    if log.get("slow_hints"):
        lines.append("")
        lines.append("慢步骤线索：")
        for item in log["slow_hints"][-limit:]:
            lines.append(f"- 尾部第 {item['line_tail_index']} 行：{item['text']}")

    if media["failure_screenshots"] or media["latest_screenshots"]:
        lines.append("")
        lines.append("截图：")
        for item in media["failure_screenshots"][-limit:]:
            lines.append(f"- 失败：{item}")
        for item in media["latest_screenshots"][-min(5, limit) :]:
            lines.append(f"- 最新：{item}")

    if media["recordings"]:
        lines.append("")
        lines.append("录像：")
        for item in media["recordings"][-limit:]:
            lines.append(f"- {item}")

    lines.append("")
    lines.append("可能编辑面：")
    for hint in report["likely_edit_surface"]:
        lines.append(f"- {hint}")
    lines.append("")
    lines.append("Action 建议：")
    for hint in report["action_advice"]:
        lines.append(f"- {hint}")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    result_dir = Path(args.result_dir).expanduser().resolve()
    if not result_dir.exists() or not result_dir.is_dir():
        print(f"ERROR: 未找到结果目录：{result_dir}", file=sys.stderr)
        return 1

    summary = parse_summary(result_dir / "execution_summary.json")
    result_xml = parse_result_xml(result_dir / "result.xml", args.limit)
    log = parse_log(result_dir / "execution.log", args.log_bytes, args.limit)
    media = list_media(result_dir, args.limit)
    report = {
        "result_dir": str(result_dir),
        "execution_summary": summary,
        "result_xml": result_xml,
        "execution_log": log,
        "media": media,
        "likely_edit_surface": infer_edit_surface(summary, result_xml, log),
        "action_advice": infer_action_advice(summary, result_xml, log),
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render(report, args.limit), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
