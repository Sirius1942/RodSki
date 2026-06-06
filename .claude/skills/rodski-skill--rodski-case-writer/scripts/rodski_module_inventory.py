#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import urllib.parse
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


DEFAULT_REPO = Path.home() / "TestCase"
MODEL_REQUIRED_ACTIONS = {"type", "verify", "send", "DB", "check"}
SKIP_DIR_PARTS = {".git", "node_modules", "__pycache__", "result", "recordings", "screenshots"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="汇总 RodSki 模块的 case/model/data/plan 三元结构和常见缺口。"
    )
    parser.add_argument("--module", required=True, help="RodSki 模块目录。")
    parser.add_argument("--repo", default=str(DEFAULT_REPO), help="RodSki 用例仓库根目录。")
    parser.add_argument("--limit", type=int, default=12, help="每类问题最多输出的示例数量。")
    parser.add_argument("--json", action="store_true", help="输出 JSON。")
    return parser.parse_args()


def should_skip(path: Path) -> bool:
    return bool(set(path.parts) & SKIP_DIR_PARTS)


def xml_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*.xml") if not should_skip(path))


def rel(path: Path, base: Path) -> str:
    try:
        return str(path.resolve().relative_to(base.resolve()))
    except ValueError:
        return str(path)


def parse_xml(path: Path) -> ET.Element | None:
    try:
        return ET.parse(path).getroot()
    except ET.ParseError:
        return None


def inspect_cases(module: Path, repo: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "files": [],
        "case_count": 0,
        "scenario_count": 0,
        "step_count": 0,
        "action_counts": Counter(),
        "model_refs": Counter(),
        "data_refs": [],
        "global_refs": Counter(),
        "parse_errors": [],
        "step_wait_values": Counter(),
    }
    for path in xml_files(module / "case"):
        text = path.read_text(encoding="utf-8", errors="replace")
        root = parse_xml(path)
        if root is None:
            result["parse_errors"].append(rel(path, repo))
            continue
        result["files"].append(rel(path, repo))
        if root.get("step_wait"):
            result["step_wait_values"][root.get("step_wait")] += 1
        for global_ref in re.findall(r"GlobalValue\.[A-Za-z0-9_.-]+", text):
            result["global_refs"][global_ref] += 1
        for case in root.findall(".//case"):
            result["case_count"] += 1
            result["scenario_count"] += len(case.findall(".//scenario"))
        for step in root.findall(".//test_step"):
            action = step.get("action", "")
            model = step.get("model", "")
            data = step.get("data", "")
            result["step_count"] += 1
            if action:
                result["action_counts"][action] += 1
            if model:
                result["model_refs"][model] += 1
            if model and data:
                result["data_refs"].append(
                    {
                        "file": rel(path, repo),
                        "action": action,
                        "model": model,
                        "data": data,
                    }
                )
    return result


def inspect_models(module: Path, repo: Path) -> dict[str, Any]:
    models: dict[str, set[str]] = defaultdict(set)
    files: list[str] = []
    parse_errors: list[str] = []
    location_count = 0
    element_count = 0
    for path in xml_files(module / "model"):
        root = parse_xml(path)
        if root is None:
            parse_errors.append(rel(path, repo))
            continue
        files.append(rel(path, repo))
        for model in root.findall(".//model"):
            model_name = model.get("name")
            if not model_name:
                continue
            for element in model.findall(".//element"):
                name = element.get("name")
                if name:
                    models[model_name].add(name)
                    element_count += 1
                location_count += len(element.findall("location"))
    return {
        "files": files,
        "parse_errors": parse_errors,
        "model_count": len(models),
        "element_count": element_count,
        "location_count": location_count,
        "models": {name: sorted(elements) for name, elements in sorted(models.items())},
    }


def inspect_data(module: Path) -> dict[str, Any]:
    db_path = module / "data" / "data.sqlite"
    result: dict[str, Any] = {
        "path": str(db_path),
        "exists": db_path.exists(),
        "tables": {},
        "table_count": 0,
        "row_count": 0,
        "field_count": 0,
        "kind_counts": Counter(),
        "error": "",
    }
    if not db_path.exists():
        return result
    try:
        conn = sqlite3.connect(f"file:{urllib.parse.quote(str(db_path), safe='/')}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
    except sqlite3.Error as exc:
        result["error"] = str(exc)
        return result
    try:
        tables = conn.execute(
            "select table_name, model_name, table_kind, row_mode from rs_datatable order by table_name"
        ).fetchall()
        for table in tables:
            table_name = table["table_name"]
            fields = [
                row["field_name"]
                for row in conn.execute(
                    "select field_name from rs_datatable_field where table_name=? order by field_order, field_name",
                    (table_name,),
                )
            ]
            rows = [
                row["data_id"]
                for row in conn.execute(
                    "select data_id from rs_row where table_name=? order by data_id",
                    (table_name,),
                )
            ]
            result["tables"][table_name] = {
                "model_name": table["model_name"],
                "kind": table["table_kind"],
                "row_mode": table["row_mode"],
                "fields": fields,
                "rows": rows,
            }
            result["kind_counts"][table["table_kind"]] += 1
            result["row_count"] += len(rows)
            result["field_count"] += len(fields)
        result["table_count"] = len(tables)
    except sqlite3.Error as exc:
        result["error"] = str(exc)
    finally:
        conn.close()
    return result


def inspect_plans(module: Path, repo: Path) -> dict[str, Any]:
    files = xml_files(module / "plan")
    return {"files": [rel(path, repo) for path in files], "count": len(files)}


def candidate_tables(action: str, model: str, tables: dict[str, Any]) -> list[str]:
    if action == "verify":
        preferred = [f"{model}_verify", model]
    else:
        preferred = [model]
    candidates = [name for name in preferred if name in tables]
    if candidates:
        return candidates
    for table_name, table in tables.items():
        if action == "verify":
            if table_name == f"{model}_verify" or table.get("model_name") == f"{model}_verify":
                candidates.append(table_name)
        elif table.get("model_name") == model and table.get("kind") == "data":
            candidates.append(table_name)
    return candidates


def is_simple_data_id(value: str) -> bool:
    """裸 DataID：排除 GlobalValue、含 ${}/空格/斜杠/点号 的运行期变量与脚本参数。

    与 rodski_case_guard.is_simple_data_id 保持一致，避免对 x.py、foo.bar 等
    带点号引用误报“缺少 data”。
    """
    if not value or value.startswith("GlobalValue."):
        return False
    if "${" in value or " " in value or "/" in value or "." in value:
        return False
    return bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", value))


def cross_check(cases: dict[str, Any], models: dict[str, Any], data: dict[str, Any], limit: int) -> dict[str, Any]:
    model_names = set(models["models"])
    tables: dict[str, Any] = data["tables"]
    missing_models = [
        {"model": model, "refs": count}
        for model, count in cases["model_refs"].items()
        if model not in model_names
    ][:limit]

    missing_data: list[dict[str, str]] = []
    for ref in cases["data_refs"]:
        action = ref["action"]
        model = ref["model"]
        data_id = ref["data"]
        if action not in MODEL_REQUIRED_ACTIONS or not is_simple_data_id(data_id):
            continue
        tables_for_ref = candidate_tables(action, model, tables)
        if not tables_for_ref:
            missing_data.append({**ref, "reason": "没有匹配的数据表"})
            continue
        if not any(data_id in tables[table]["rows"] for table in tables_for_ref):
            missing_data.append({**ref, "reason": f"在 {', '.join(tables_for_ref)} 中未找到 data id"})
        if len(missing_data) >= limit:
            break

    field_mismatches: list[dict[str, Any]] = []
    for table_name, table in tables.items():
        base_model = table_name[:-7] if table["kind"] == "verify" and table_name.endswith("_verify") else table["model_name"]
        if base_model.endswith("_verify"):
            base_model = base_model[:-7]
        if base_model not in model_names:
            continue
        model_fields = set(models["models"][base_model])
        data_fields = set(table["fields"])
        data_without_model = sorted(data_fields - model_fields)
        if data_without_model:
            field_mismatches.append(
                {
                    "table": table_name,
                    "model": base_model,
                    "data_fields_without_model_element": data_without_model[:limit],
                    "count": len(data_without_model),
                }
            )
        if len(field_mismatches) >= limit:
            break

    empty_verify_tables = [
        table_name
        for table_name, table in tables.items()
        if table["kind"] == "verify" and (not table["fields"] or not table["rows"])
    ][:limit]

    return {
        "missing_models": missing_models,
        "missing_data": missing_data,
        "field_mismatches": field_mismatches,
        "empty_verify_tables": empty_verify_tables,
    }


def to_jsonable(value: Any) -> Any:
    if isinstance(value, Counter):
        return dict(value)
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    return value


def render_text(report: dict[str, Any], limit: int) -> str:
    lines: list[str] = []
    module = report["module"]
    cases = report["cases"]
    models = report["models"]
    data = report["data"]
    plans = report["plans"]
    checks = report["checks"]

    lines.append(f"模块：{module}")
    lines.append(
        "Cases："
        f"{len(cases['files'])} 个文件，{cases['case_count']} 个 case，"
        f"{cases['scenario_count']} 个 scenario，{cases['step_count']} 个 step"
    )
    lines.append(f"Actions：{dict(cases['action_counts'])}")
    if cases["step_wait_values"]:
        lines.append(f"step_wait: {dict(cases['step_wait_values'])}")
    lines.append(
        f"Models：{len(models['files'])} 个文件，{models['model_count']} 个 model，"
        f"{models['element_count']} 个 element，{models['location_count']} 个 location"
    )
    lines.append(
        "Data："
        f"{data['table_count']} 张表，{data['row_count']} 行，"
        f"{data['field_count']} 个字段，kinds={dict(data['kind_counts'])}"
    )
    lines.append(f"Plans：{plans['count']} 个文件")
    if cases["global_refs"]:
        refs = ", ".join(name for name, _ in cases["global_refs"].most_common(limit))
        lines.append(f"GlobalValue 引用：{refs}")
    if cases["parse_errors"] or models["parse_errors"] or data["error"]:
        lines.append("")
        lines.append("解析/数据错误：")
        for path in cases["parse_errors"][:limit]:
            lines.append(f"- case XML 解析错误：{path}")
        for path in models["parse_errors"][:limit]:
            lines.append(f"- model XML 解析错误：{path}")
        if data["error"]:
            lines.append(f"- data.sqlite 错误：{data['error']}")

    lines.append("")
    lines.append("交叉引用检查：")
    if not any(checks.values()):
        lines.append("- 未发现明显交叉引用缺口")
    for item in checks["missing_models"][:limit]:
        lines.append(f"- 缺少 model：{item['model']}（{item['refs']} 次引用）")
    for item in checks["missing_data"][:limit]:
        lines.append(
            "- 缺少 data："
            f"{item['file']} action={item['action']} model={item['model']} "
            f"data={item['data']} ({item['reason']})"
        )
    for item in checks["field_mismatches"][:limit]:
        fields = ", ".join(item["data_fields_without_model_element"][:5])
        lines.append(
            "- data 字段缺少对应 model element："
            f"{item['table']} -> {item['model']}（{item['count']} 个字段；{fields}）"
        )
    for table_name in checks["empty_verify_tables"][:limit]:
        lines.append(f"- 空 verify 表：{table_name}")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    repo = Path(args.repo).expanduser().resolve()
    module = Path(args.module).expanduser().resolve()
    if not module.exists() or not module.is_dir():
        print(f"ERROR: 未找到模块目录：{module}", file=sys.stderr)
        return 1

    cases = inspect_cases(module, repo)
    models = inspect_models(module, repo)
    data = inspect_data(module)
    plans = inspect_plans(module, repo)
    checks = cross_check(cases, models, data, args.limit)
    report = {
        "module": str(module),
        "cases": cases,
        "models": models,
        "data": data,
        "plans": plans,
        "checks": checks,
    }

    if args.json:
        print(json.dumps(to_jsonable(report), ensure_ascii=False, indent=2))
    else:
        print(render_text(report, args.limit), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
