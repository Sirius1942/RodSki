#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import sqlite3
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


ALLOWED_ACTIONS = {
    "close",
    "type",
    "verify",
    "wait",
    "navigate",
    "launch",
    "assert",
    "upload_file",
    "clear",
    "get_text",
    "get",
    "evaluate",
    "send",
    "set",
    "DB",
    "run",
    "check",
    "screenshot",
}

BANNED_ACTIONS = {
    "open": "使用 navigate，不要使用 open。",
    "http_get": "使用 send 加 verify，不要使用 HTTP 专用 action。",
    "http_post": "使用 send 加 verify，不要使用 HTTP 专用 action。",
    "assert_json": "使用 verify 对响应 model/table 做验证。",
    "assert_status": "使用 verify 对响应 model/table 做验证。",
    "click": "将 UI 原子操作放入由 type 执行的数据行。",
    "double_click": "将 UI 原子操作放入由 type 执行的数据行。",
    "right_click": "将 UI 原子操作放入由 type 执行的数据行。",
    "hover": "将 UI 原子操作放入由 type 执行的数据行。",
    "select": "将 UI 原子操作放入由 type 执行的数据行。",
    "key_press": "将 UI 原子操作放入由 type 执行的数据行。",
    "drag": "将 UI 原子操作放入由 type 执行的数据行。",
    "scroll": "将 UI 原子操作放入由 type 执行的数据行。",
}

MODEL_REQUIRED_ACTIONS = {"type", "verify", "send", "DB", "check"}
# component_type / execute 的兜底集合。权威清单以 `rodski capabilities` 的
# component_types / execute_values 为准；仅当当前 CLI 未暴露 capabilities 时才退回这里。
FALLBACK_COMPONENT_TYPES = {"界面", "接口", "数据库"}
FALLBACK_EXECUTE_VALUES = {"是", "否"}

# 定位器类型的兜底集合。权威清单以 `rodski capabilities` 的 locator_types 为准；
# 仅当当前 CLI 未暴露 capabilities 时才退回到这里。
FALLBACK_LOCATOR_TYPES = {
    "id",
    "class",
    "css",
    "xpath",
    "text",
    "tag",
    "name",
    "static",
    "field",
    "vision",
    "ocr",
    "vision_bbox",
    "vision_image",
}
SKIP_PARTS = {".git", "myenv", "node_modules", "__pycache__", "result", ".vscode", ".idea"}
WAIT_LONG_THRESHOLD_SECONDS = 5.0
DEFAULT_GLOBAL_RODSKI = Path("/opt/homebrew/bin/rodski")
DEFAULT_LONG_TERM_RODSKI = Path.home() / ".local/share/rodski/venv/bin/rodski"


@dataclass
class Issue:
    severity: str
    path: str
    message: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="用于检查 RodSki case/model/data XML 常见幻觉的静态 guard。"
    )
    parser.add_argument(
        "--repo",
        default=".",
        help="RodSki 测试仓库根目录。",
    )
    parser.add_argument(
        "--target",
        action="append",
        help="要扫描的改动文件或模块目录。可重复。默认扫描 repo。",
    )
    parser.add_argument(
        "--rodski-bin",
        default="",
        help="用于报告版本的 RodSki CLI 路径。默认从目标 repo 和 PATH 自动检测。",
    )
    parser.add_argument("--json", action="store_true", help="输出 JSON。")
    return parser.parse_args()


def should_skip(path: Path) -> bool:
    parts = set(path.parts)
    if parts & SKIP_PARTS:
        return True
    return any("源码" in part for part in path.parts)


def is_rodski_xml(path: Path) -> bool:
    if path.suffix.lower() != ".xml" or should_skip(path):
        return False
    parts = set(path.parts)
    if {"case", "model", "data", "plan"} & parts:
        return True
    return path.name in {"globalvalue.xml", "model.xml"}


def collect_xml_files(targets: list[Path]) -> list[Path]:
    files: list[Path] = []
    for target in targets:
        if target.is_file():
            if is_rodski_xml(target):
                files.append(target)
            continue
        if target.is_dir():
            files.extend(path for path in target.rglob("*.xml") if is_rodski_xml(path))
            continue
        files.append(target)
    return sorted(dict.fromkeys(files))


def rel(path: Path, repo: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo.resolve()))
    except ValueError:
        return str(path)


def add(issues: list[Issue], severity: str, path: Path, repo: Path, message: str) -> None:
    issues.append(Issue(severity, rel(path, repo), message))


def parse_xml(path: Path, repo: Path, issues: list[Issue]) -> ET.Element | None:
    if not path.exists():
        add(issues, "FAIL", path, repo, "目标不存在。")
        return None
    try:
        return ET.parse(path).getroot()
    except ET.ParseError as exc:
        add(issues, "FAIL", path, repo, f"XML 解析错误：{exc}。")
        return None


def check_case_xml(
    root: ET.Element,
    path: Path,
    repo: Path,
    issues: list[Issue],
    allowed_actions: set[str],
    compat_actions: set[str],
    component_types: set[str],
    execute_values: set[str],
) -> None:
    for case in root.findall("case"):
        case_id = case.get("id", "<missing id>")
        for attr in ("id", "title", "execute"):
            if not case.get(attr):
                add(issues, "FAIL", path, repo, f"case {case_id}: 缺少 @{attr}。")
        execute = case.get("execute")
        if execute and execute not in execute_values:
            add(issues, "FAIL", path, repo, f"case {case_id}: execute 必须是 {' 或 '.join(sorted(execute_values))}。")
        component_type = case.get("component_type")
        if component_type and component_type not in component_types:
            add(
                issues,
                "FAIL",
                path,
                repo,
                f"case {case_id}: component_type 必须是 {'、'.join(sorted(component_types))}。",
            )
        test_cases = case.findall("test_case")
        if len(test_cases) != 1:
            add(issues, "FAIL", path, repo, f"case {case_id}: 必须恰好有一个 test_case。")
        elif not list(test_cases[0]):
            add(issues, "FAIL", path, repo, f"case {case_id}: test_case 为空。")
        if len(case.findall("pre_process")) > 1:
            add(issues, "FAIL", path, repo, f"case {case_id}: 存在多个 pre_process 容器。")
        if len(case.findall("post_process")) > 1:
            add(issues, "FAIL", path, repo, f"case {case_id}: 存在多个 post_process 容器。")
        check_wait_usage(case, case_id, path, repo, issues)
        for scenario in case.findall(".//scenario"):
            if scenario.get("id") is None:
                add(issues, "FAIL", path, repo, f"case {case_id}: scenario 缺少 @id。")
            parent_is_test_case = any(scenario in list(tc) for tc in test_cases)
            if not parent_is_test_case:
                add(issues, "FAIL", path, repo, f"case {case_id}: scenario 必须位于 test_case 内。")

    for step in root.findall(".//test_step"):
        action = step.get("action", "")
        data = step.get("data", "")
        model = step.get("model", "")
        if not action:
            add(issues, "FAIL", path, repo, "test_step 缺少 @action。")
            continue
        if action in BANNED_ACTIONS:
            # 安全阀：BANNED_ACTIONS 是硬编码的常见幻觉/旧式关键字清单，但权威清单以
            # rodski capabilities 为准。若某 banned 词出现在 live allowed_actions
            # （capabilities/xsd）里，说明当前 RodSki 真的把它当合法 action，降级为 WARN
            # 并提示风格约定，而不是硬 FAIL，避免与 capabilities 冲突时静默误判。
            if action in allowed_actions:
                add(
                    issues,
                    "WARN",
                    path,
                    repo,
                    f"action={action}: 当前 capabilities 列为合法 action，但风格约定仍建议——"
                    f"{BANNED_ACTIONS[action]}",
                )
            else:
                add(issues, "FAIL", path, repo, f"action={action}: {BANNED_ACTIONS[action]}")
        elif action not in allowed_actions:
            add(issues, "FAIL", path, repo, f"action={action}: 不在 TEST_CASE_WRITING_GUIDE action 列表中。")
        elif action in compat_actions:
            # capabilities 把这些归入 compat_keywords：当前 CLI 仍接受，但属于兼容/将淘汰
            # 关键字。放行不报 FAIL，但提示改用新写法，避免静默沉淀旧关键字。
            add(
                issues,
                "WARN",
                path,
                repo,
                f"action={action}: 当前 capabilities 列为兼容关键字（compat_keywords），仍受支持但建议改用新写法。",
            )
        if action in MODEL_REQUIRED_ACTIONS and not model:
            add(issues, "WARN", path, repo, f"action={action}: 通常需要 @model。")
        if action in MODEL_REQUIRED_ACTIONS and looks_like_model_data_ref(data):
            add(
                issues,
                "WARN",
                path,
                repo,
                f"data={data}: 只使用 DataID；带点号引用保留给 GlobalValue.Group.Var。",
            )


def check_wait_usage(
    case: ET.Element,
    case_id: str,
    path: Path,
    repo: Path,
    issues: list[Issue],
) -> None:
    wait_steps = [
        step for step in case.findall(".//test_step") if step.get("action") == "wait"
    ]
    if wait_steps:
        add(
            issues,
            "WARN",
            path,
            repo,
            f"case {case_id}: 包含 {len(wait_steps)} 个显式 wait 步骤；应尽量减少固定等待，优先通过 verify、稳定定位器或框架 wait/retry 表达可观察就绪。",
        )

    for step in wait_steps:
        data = (step.get("data") or "").strip()
        if not data:
            add(
                issues,
                "WARN",
                path,
                repo,
                f"case {case_id}: wait 步骤缺少 @data 时长。",
            )
            continue
        try:
            seconds = float(data)
        except ValueError:
            continue
        if seconds > WAIT_LONG_THRESHOLD_SECONDS:
            add(
                issues,
                "WARN",
                path,
                repo,
                f"case {case_id}: wait data={data!r} 超过 {WAIT_LONG_THRESHOLD_SECONDS:g}s；检查是否可用基于条件的步骤替代。",
            )

    for container in case.iter():
        children = list(container)
        for index, child in enumerate(children[1:], start=1):
            previous = children[index - 1]
            if (
                previous.tag == "test_step"
                and child.tag == "test_step"
                and previous.get("action") == "wait"
                and child.get("action") == "wait"
            ):
                add(
                    issues,
                    "WARN",
                    path,
                    repo,
                    f"case {case_id}: {element_label(container)} 中存在连续 wait 步骤；合并它们或用可观察条件替代。",
                )
                break


def element_label(element: ET.Element) -> str:
    if element.tag == "scenario":
        return f"scenario {element.get('id') or element.get('title') or '<missing id>'}"
    return element.tag


def looks_like_model_data_ref(value: str) -> bool:
    if not value or value.startswith("GlobalValue."):
        return False
    if "${" in value:
        return False
    if re.search(r"\.(py|png|jpg|jpeg|gif|json|xml|sqlite|db|csv|xlsx?)$", value, re.I):
        return False
    return bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_-]*", value))


def check_model_xml(
    root: ET.Element,
    path: Path,
    repo: Path,
    issues: list[Issue],
    allowed_locator_types: set[str],
) -> None:
    for model in root.findall("model"):
        model_name = model.get("name", "<missing model name>")
        if not model.get("name"):
            add(issues, "FAIL", path, repo, "model 缺少 @name。")
        for element in model.findall("element"):
            element_name = element.get("name", "<missing element name>")
            if not element.get("name"):
                add(issues, "FAIL", path, repo, f"model {model_name}: element 缺少 @name。")
            if "locator" in element.attrib:
                add(
                    issues,
                    "FAIL",
                    path,
                    repo,
                    f"model {model_name}.{element_name}: 不允许使用旧式 locator 属性。",
                )
            if element.get("value") is not None:
                add(
                    issues,
                    "FAIL",
                    path,
                    repo,
                    f"model {model_name}.{element_name}: 不允许使用旧式 element @value；请使用 <location type=\"...\">value</location>。",
                )
            element_type = element.get("type")
            if element_type and element.find("location") is None:
                if element_type in allowed_locator_types or element_type == "locator":
                    add(
                        issues,
                        "FAIL",
                        path,
                        repo,
                        f"model {model_name}.{element_name}: 旧式 element type={element_type!r}；locator type 应放在 <location type=\"...\"> 上。",
                    )
            locations = element.findall("location")
            if not locations:
                add(
                    issues,
                    "FAIL",
                    path,
                    repo,
                    f"model {model_name}.{element_name}: 缺少 location 子节点。",
                )
            for location in locations:
                loc_type = location.get("type")
                if not loc_type:
                    add(
                        issues,
                        "FAIL",
                        path,
                        repo,
                        f"model {model_name}.{element_name}: location 缺少 @type。",
                    )
                elif loc_type not in allowed_locator_types and loc_type != "locator":
                    add(
                        issues,
                        "FAIL",
                        path,
                        repo,
                        f"model {model_name}.{element_name}: location type={loc_type!r} 不在受支持的定位器类型内"
                        f"（以 rodski capabilities 的 locator_types 为准：{', '.join(sorted(allowed_locator_types))}）。",
                    )
                if loc_type == "locator" or "value" in location.attrib:
                    add(
                        issues,
                        "FAIL",
                        path,
                        repo,
                        f"model {model_name}.{element_name}: 请使用 <location type=\"...\">value</location>。",
                    )


def check_globalvalue_xml(root: ET.Element, path: Path, repo: Path, issues: list[Issue]) -> None:
    group_names: set[str] = set()
    for group in root.findall("group"):
        group_name = group.get("name", "")
        if not group_name:
            add(issues, "FAIL", path, repo, "globalvalue group 缺少 @name。")
            continue
        if group_name in group_names:
            add(issues, "FAIL", path, repo, f"globalvalue group 名称重复：{group_name}。")
        group_names.add(group_name)
        var_names: set[str] = set()
        vars_ = group.findall("var")
        if not vars_:
            add(issues, "FAIL", path, repo, f"group {group_name}: 必须至少包含一个 var。")
        for var in vars_:
            name = var.get("name", "")
            if not name or var.get("value") is None:
                add(issues, "FAIL", path, repo, f"group {group_name}: var 需要 name 和 value。")
            if name in var_names:
                add(issues, "FAIL", path, repo, f"group {group_name}: var 名称重复 {name}。")
            var_names.add(name)


def check_plan_xml(root: ET.Element, path: Path, repo: Path, issues: list[Issue], execute_values: set[str]) -> None:
    if not root.get("id"):
        add(issues, "FAIL", path, repo, "test_plan 缺少 @id。")
    for case in root.findall("case"):
        if not case.get("id"):
            add(issues, "FAIL", path, repo, "test_plan case 缺少 @id。")
        execute = case.get("execute")
        if execute and execute not in execute_values:
            add(issues, "FAIL", path, repo, f"test_plan case execute 必须是 {' 或 '.join(sorted(execute_values))}。")


def module_root_for(path: Path) -> Path | None:
    """从 case/model/data/plan 文件路径回推模块根目录。"""
    parts = path.parts
    for marker in ("case", "model", "data", "plan"):
        if marker in parts:
            idx = parts.index(marker)
            if idx > 0:
                return Path(*parts[:idx])
    return None


def collect_module_model_names(module: Path) -> set[str]:
    """模块下所有 <model name>，含无 element 子节点的 db_query/连接模型。"""
    names: set[str] = set()
    model_dir = module / "model"
    if not model_dir.is_dir():
        return names
    for path in sorted(model_dir.glob("*.xml")):
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError:
            continue
        for model in root.findall(".//model"):
            name = model.get("name")
            if name:
                names.add(name)
    return names


def collect_module_globalvalues(module: Path) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    gv = module / "data" / "globalvalue.xml"
    if not gv.exists():
        return pairs
    try:
        root = ET.parse(gv).getroot()
    except ET.ParseError:
        return pairs
    for group in root.findall("group"):
        gname = group.get("name")
        for var in group.findall("var"):
            vname = var.get("name")
            if gname and vname:
                pairs.add((gname, vname))
    return pairs


GLOBALVALUE_REF = re.compile(r"^GlobalValue\.([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)$")


def collect_module_datatables(module: Path) -> dict[str, dict[str, object]] | None:
    """读取 data.sqlite，返回 {table_name: {model_name, kind, rows:set}}。

    缺库或读失败返回 None（调用方据此跳过 DataID 校验，不误报）。
    """
    db = module / "data" / "data.sqlite"
    if not db.exists():
        return None
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    except sqlite3.Error:
        return None
    tables: dict[str, dict[str, object]] = {}
    try:
        cur = con.execute("SELECT table_name, model_name, table_kind FROM rs_datatable")
        for table_name, model_name, kind in cur.fetchall():
            tables[table_name] = {"model_name": model_name, "kind": kind, "rows": set()}
        cur = con.execute("SELECT table_name, data_id FROM rs_row")
        for table_name, data_id in cur.fetchall():
            entry = tables.get(table_name)
            if entry is not None:
                entry["rows"].add(data_id)  # type: ignore[union-attr]
    except sqlite3.Error:
        return None
    finally:
        con.close()
    return tables


def candidate_tables_for(action: str, model: str, tables: dict[str, dict[str, object]]) -> list[str]:
    """复刻 module_inventory 的解析：verify 偏好 <model>_verify，其余偏好 <model>。"""
    preferred = [f"{model}_verify", model] if action == "verify" else [model]
    found = [name for name in preferred if name in tables]
    if found:
        return found
    for table_name, table in tables.items():
        if action == "verify":
            if table_name == f"{model}_verify" or table.get("model_name") == f"{model}_verify":
                found.append(table_name)
        elif table.get("model_name") == model and table.get("kind") == "data":
            found.append(table_name)
    return found


def is_simple_data_id(value: str) -> bool:
    """裸 DataID：排除 GlobalValue、含 ${}/空格/斜杠/点号 的运行期变量与脚本参数。"""
    if not value or value.startswith("GlobalValue."):
        return False
    if "${" in value or " " in value or "/" in value or "." in value:
        return False
    return bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", value))


@dataclass
class ModuleRefs:
    """模块级 model/globalvalue/data 查找结果，按 module root 缓存，避免每个 case 重复读取。"""

    model_names: set[str]
    globalvalues: set[tuple[str, str]]
    tables: dict[str, dict[str, object]] | None


def load_module_refs(module: Path, cache: dict[Path, ModuleRefs]) -> ModuleRefs:
    cached = cache.get(module)
    if cached is not None:
        return cached
    refs = ModuleRefs(
        model_names=collect_module_model_names(module),
        globalvalues=collect_module_globalvalues(module),
        tables=collect_module_datatables(module),
    )
    cache[module] = refs
    return refs


def check_cross_references(
    case_path: Path,
    root: ET.Element,
    repo: Path,
    issues: list[Issue],
    module_cache: dict[Path, ModuleRefs],
) -> None:
    """case 内 @model / @data 是否能在同模块 model.xml、data.sqlite、globalvalue.xml 解析。

    GlobalValue.Group.Var 引用对所有 action 校验（navigate URL 是最常见用法）。
    model 与裸 DataID 仅对消费 model/data 的 action（type/verify/send/DB/check）校验；
    run/set/get/evaluate 等的 @model/@data 是脚本类别或运行期变量，跳过以免误报。
    """
    module = module_root_for(case_path)
    if module is None:
        return
    refs = load_module_refs(module, module_cache)
    model_names = refs.model_names
    globalvalues = refs.globalvalues
    tables = refs.tables

    for step in root.findall(".//test_step"):
        action = step.get("action", "")
        data = (step.get("data") or "").strip()

        # GlobalValue 引用：对所有 action 校验。
        gv = GLOBALVALUE_REF.match(data) if data else None
        if gv:
            if globalvalues and (gv.group(1), gv.group(2)) not in globalvalues:
                add(
                    issues,
                    "FAIL",
                    case_path,
                    repo,
                    f"data={data!r}：在模块 globalvalue.xml 中未找到该 GlobalValue.Group.Var。",
                )

        # model 与裸 DataID：仅对消费 model/data 的 action 校验。
        if action not in MODEL_REQUIRED_ACTIONS:
            continue
        model = (step.get("model") or "").strip()
        if model and model_names and model not in model_names:
            add(
                issues,
                "FAIL",
                case_path,
                repo,
                f"action={action} model={model!r}：在模块 model.xml 中未定义该 model。",
            )

        if not data or gv:
            continue
        if tables is None or not is_simple_data_id(data):
            continue
        # model 缺失时已单独报错，DataID 解析依赖 model→表映射，跳过避免重复噪音。
        if not model or (model_names and model not in model_names):
            continue
        candidates = candidate_tables_for(action, model, tables)
        if not candidates:
            add(
                issues,
                "FAIL",
                case_path,
                repo,
                f"action={action} model={model} data={data!r}：data.sqlite 中没有匹配的数据表。",
            )
        elif not any(data in tables[name]["rows"] for name in candidates):  # type: ignore[operator]
            add(
                issues,
                "FAIL",
                case_path,
                repo,
                f"action={action} model={model} data={data!r}："
                f"在 {', '.join(candidates)} 中未找到该 DataID。",
            )


def check_layout(targets: list[Path], repo: Path, issues: list[Issue]) -> None:
    module_roots: set[Path] = set()
    for target in targets:
        if target.is_file():
            parts = target.parts
            for marker in ("case", "model", "data", "plan"):
                if marker in parts:
                    idx = parts.index(marker)
                    module_roots.add(Path(*parts[:idx]))
        elif target.is_dir():
            if any((target / name).exists() for name in ("case", "model", "data", "plan")):
                module_roots.add(target)
    for module in module_roots:
        if should_skip(module):
            continue
        if (module / "data" / "data.xml").exists() or (module / "data" / "data_verify.xml").exists():
            add(issues, "FAIL", module, repo, "发现旧式 data.xml/data_verify.xml；请使用 data.sqlite。")
        if not (module / "data" / "data.sqlite").exists():
            add(issues, "WARN", module, repo, "该模块未找到 data/data.sqlite。")
        if not (module / "data" / "globalvalue.xml").exists():
            add(issues, "WARN", module, repo, "该模块未找到 data/globalvalue.xml。")


def guide_status(repo: Path) -> dict[str, str | bool]:
    guide = repo / "TEST_CASE_WRITING_GUIDE.md"
    status: dict[str, str | bool] = {"exists": guide.exists(), "path": str(guide)}
    if not guide.exists():
        return status
    text = guide.read_text(encoding="utf-8", errors="replace")
    version = re.search(r"\*\*版本\*\*:\s*([^\n]+)", text)
    date = re.search(r"\*\*日期\*\*:\s*([^\n]+)", text)
    if version:
        status["version"] = version.group(1).strip()
    if date:
        status["date"] = date.group(1).strip()
    return status


def rodski_version(rodski_bin: Path) -> dict[str, str | bool]:
    if not rodski_bin.exists():
        return {"exists": False, "path": str(rodski_bin)}
    try:
        result = subprocess.run(
            [str(rodski_bin), "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception as exc:  # pragma: no cover - defensive CLI wrapper
        return {"exists": True, "path": str(rodski_bin), "error": str(exc)}
    return {
        "exists": True,
        "path": str(rodski_bin),
        "returncode": str(result.returncode),
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def resolve_rodski_bin(repo: Path, explicit: str) -> Path:
    if explicit:
        return Path(explicit).expanduser()

    candidates = [
        DEFAULT_GLOBAL_RODSKI,
        DEFAULT_LONG_TERM_RODSKI,
    ]
    path_rodski = shutil.which("rodski")
    if path_rodski:
        candidates.append(Path(path_rodski))
    candidates.extend(
        [
            repo / "myenv" / "bin" / "rodski",
            repo / ".venv" / "bin" / "rodski",
            repo / "venv" / "bin" / "rodski",
        ]
    )

    for candidate in dict.fromkeys(candidates):
        if candidate.exists():
            return candidate
    return candidates[0]


def rodski_has_subcommand(rodski_bin: Path, name: str) -> bool:
    if not rodski_bin.exists():
        return False
    try:
        result = subprocess.run(
            [str(rodski_bin), "--help"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception:
        return False
    help_text = f"{result.stdout}\n{result.stderr}"
    return result.returncode == 0 and re.search(rf"\b{re.escape(name)}\b", help_text) is not None


def rodski_capabilities(rodski_bin: Path) -> dict[str, object]:
    if not rodski_bin.exists():
        return {"exists": False, "path": str(rodski_bin)}
    if not rodski_has_subcommand(rodski_bin, "capabilities"):
        return {
            "exists": False,
            "path": str(rodski_bin),
            "skipped": "当前 RodSki CLI 未暴露 capabilities 子命令；guard 将使用当前 case.xsd 或内置 fallback。",
        }
    try:
        result = subprocess.run(
            [str(rodski_bin), "capabilities"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception as exc:  # pragma: no cover - defensive CLI wrapper
        return {"exists": True, "path": str(rodski_bin), "error": str(exc)}
    output: dict[str, object] = {
        "exists": True,
        "path": str(rodski_bin),
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }
    if result.returncode == 0 and result.stdout.strip():
        try:
            parsed = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            output["error"] = f"capabilities JSON 无效：{exc}"
        else:
            output["parsed"] = parsed
    return output


def actions_from_capabilities(capabilities: dict[str, object]) -> set[str]:
    parsed = capabilities.get("parsed")
    if not isinstance(parsed, dict):
        return set()
    actions = parsed.get("supported_keywords", [])
    compat = parsed.get("compat_keywords", [])
    if not isinstance(actions, list) or not isinstance(compat, list):
        return set()
    result = {str(action) for action in actions + compat if action}
    return result


def compat_actions_from_capabilities(capabilities: dict[str, object]) -> set[str]:
    """从 capabilities 取 compat_keywords（兼容/将淘汰关键字）；缺失时返回空集合。"""
    parsed = capabilities.get("parsed")
    if not isinstance(parsed, dict):
        return set()
    compat = parsed.get("compat_keywords", [])
    if not isinstance(compat, list):
        return set()
    return {str(value) for value in compat if value}


def _string_list_from_capabilities(capabilities: dict[str, object], key: str) -> set[str]:
    parsed = capabilities.get("parsed")
    if not isinstance(parsed, dict):
        return set()
    values = parsed.get(key, [])
    if not isinstance(values, list):
        return set()
    return {str(value) for value in values if value}


def locator_types_from_capabilities(capabilities: dict[str, object]) -> set[str]:
    """从 capabilities 取权威 locator_types；缺失时返回空集合，由调用方回退。"""
    parsed = capabilities.get("parsed")
    if not isinstance(parsed, dict):
        return set()
    locator_types = parsed.get("locator_types", [])
    if not isinstance(locator_types, list):
        return set()
    return {str(value) for value in locator_types if value}


def rodski_python_from_bin(rodski_bin: Path) -> str | None:
    try:
        first_line = rodski_bin.read_text(encoding="utf-8", errors="replace").splitlines()[0]
    except (OSError, IndexError):
        return None
    if not first_line.startswith("#!"):
        return None
    python = first_line[2:].strip()
    try:
        parts = shlex.split(python)
    except ValueError:
        parts = [python]
    def looks_like_python(value: str) -> bool:
        return Path(value).name.startswith("python")

    if parts and Path(parts[0]).name == "env" and len(parts) > 1:
        if not looks_like_python(parts[1]):
            return None
        resolved = shutil.which(parts[1])
        return resolved
    if parts and not looks_like_python(parts[0]):
        return None
    if len(parts) > 1 and Path(parts[0]).exists():
        return parts[0]
    return python if python else None


def rodski_bin_candidates_for_xsd(rodski_bin: Path, repo: Path) -> list[Path]:
    candidates = [rodski_bin]
    env_bin = os.environ.get("RODSKI_BIN")
    if env_bin:
        candidates.append(Path(env_bin).expanduser())
    candidates.extend(
        [
            DEFAULT_LONG_TERM_RODSKI,
            repo / ".venv" / "bin" / "rodski",
            repo / "venv" / "bin" / "rodski",
            repo / "myenv" / "bin" / "rodski",
        ]
    )
    return [candidate for candidate in dict.fromkeys(candidates) if candidate.exists()]


def rodski_case_xsd(rodski_bin: Path, repo: Path) -> Path | None:
    python = None
    for candidate in rodski_bin_candidates_for_xsd(rodski_bin, repo):
        python = rodski_python_from_bin(candidate)
        if python:
            break
    if not python:
        return None
    try:
        result = subprocess.run(
            [
                python,
                "-c",
                (
                    "import pathlib\n"
                    "candidates=[]\n"
                    "try:\n"
                    "    import rodski\n"
                    "    candidates.append(pathlib.Path(rodski.__path__[0]) / 'schemas' / 'case.xsd')\n"
                    "except Exception:\n"
                    "    pass\n"
                    "try:\n"
                    "    import schemas\n"
                    "    candidates.append(pathlib.Path(schemas.__path__[0]) / 'case.xsd')\n"
                    "except Exception:\n"
                    "    pass\n"
                    "for candidate in candidates:\n"
                    "    if candidate.exists():\n"
                    "        print(candidate)\n"
                    "        raise SystemExit(0)\n"
                    "raise SystemExit(1)\n"
                ),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception:
        return None
    if result.returncode != 0:
        return None
    path = Path(result.stdout.strip())
    return path if path.exists() else None


def actions_from_case_xsd(case_xsd: Path | None) -> set[str]:
    if case_xsd is None or not case_xsd.exists():
        return set()
    text = case_xsd.read_text(encoding="utf-8", errors="replace")
    match = re.search(
        r"<xs:simpleType\s+name=\"ActionType\">(?P<body>.*?)</xs:simpleType>",
        text,
        re.S,
    )
    if not match:
        return set()
    return set(re.findall(r"<xs:enumeration\s+value=\"([^\"]+)\"", match.group("body")))


def merged_allowed_actions(
    capabilities: dict[str, object],
    case_xsd: Path | None,
    issues: list[Issue],
    repo: Path,
) -> set[str]:
    capabilities_actions = actions_from_capabilities(capabilities)
    xsd_actions = actions_from_case_xsd(case_xsd)
    if capabilities_actions and xsd_actions:
        only_capabilities = sorted(capabilities_actions - xsd_actions)
        only_xsd = sorted(xsd_actions - capabilities_actions)
        if only_capabilities:
            add(
                issues,
                "WARN",
                repo,
                repo,
                "capabilities 列出了当前 case.xsd 中不存在的 action："
                + ", ".join(only_capabilities)
                + "。使用前请通过 dry-run 确认。",
            )
        if only_xsd:
            add(
                issues,
                "WARN",
                repo,
                repo,
                "当前 case.xsd 列出了 capabilities 中不存在的 action："
                + ", ".join(only_xsd)
                + "。使用前请通过 guide/help 确认。",
            )
    merged = capabilities_actions | xsd_actions
    return merged or set(ALLOWED_ACTIONS)


def resolve_allowed_locator_types(capabilities: dict[str, object]) -> set[str]:
    """优先用 capabilities 的 locator_types；缺失时退回内置兜底集合。"""
    return locator_types_from_capabilities(capabilities) or set(FALLBACK_LOCATOR_TYPES)


def resolve_component_types(capabilities: dict[str, object]) -> set[str]:
    """优先用 capabilities 的 component_types；缺失时退回内置兜底集合。"""
    return _string_list_from_capabilities(capabilities, "component_types") or set(FALLBACK_COMPONENT_TYPES)


def resolve_execute_values(capabilities: dict[str, object]) -> set[str]:
    """优先用 capabilities 的 execute_values；缺失时退回内置兜底集合。"""
    return _string_list_from_capabilities(capabilities, "execute_values") or set(FALLBACK_EXECUTE_VALUES)


def main() -> int:
    args = parse_args()
    repo = Path(args.repo).expanduser().resolve()
    targets = [Path(target).expanduser() for target in (args.target or [str(repo)])]
    targets = [target if target.is_absolute() else (repo / target) for target in targets]

    issues: list[Issue] = []
    if not repo.exists():
        add(issues, "FAIL", repo, repo, "仓库根目录不存在。")

    guide = guide_status(repo)
    if not guide.get("exists"):
        add(issues, "FAIL", Path(str(guide["path"])), repo, "未找到 TEST_CASE_WRITING_GUIDE.md。")

    rodski_bin = resolve_rodski_bin(repo, args.rodski_bin)
    version = rodski_version(rodski_bin)
    capabilities = rodski_capabilities(rodski_bin)
    case_xsd = rodski_case_xsd(rodski_bin, repo)
    allowed_actions = merged_allowed_actions(capabilities, case_xsd, issues, repo)
    compat_actions = compat_actions_from_capabilities(capabilities)
    allowed_locator_types = resolve_allowed_locator_types(capabilities)
    component_types = resolve_component_types(capabilities)
    execute_values = resolve_execute_values(capabilities)

    check_layout(targets, repo, issues)
    files = collect_xml_files(targets)
    module_cache: dict[Path, ModuleRefs] = {}
    profile: Counter[str] = Counter()
    for path in files:
        root = parse_xml(path, repo, issues)
        if root is None:
            continue
        if root.tag == "cases":
            # 复用本次解析结果统计 action 分布，避免后续再 ET.parse 一遍。
            profile.update(step.get("action", "<missing>") for step in root.findall(".//test_step"))
            check_case_xml(root, path, repo, issues, allowed_actions, compat_actions, component_types, execute_values)
            check_cross_references(path, root, repo, issues, module_cache)
        elif root.tag == "models":
            check_model_xml(root, path, repo, issues, allowed_locator_types)
        elif root.tag == "globalvalue":
            check_globalvalue_xml(root, path, repo, issues)
        elif root.tag == "test_plan":
            check_plan_xml(root, path, repo, issues, execute_values)

    output = {
        "repo": str(repo),
        "guide": guide,
        "rodski": version,
        "capabilities": capabilities,
        "case_xsd": str(case_xsd) if case_xsd else "",
        "allowed_actions": sorted(allowed_actions),
        "compat_actions": sorted(compat_actions),
        "allowed_locator_types": sorted(allowed_locator_types),
        "component_types": sorted(component_types),
        "execute_values": sorted(execute_values),
        "scanned_xml_files": [rel(path, repo) for path in files],
        "action_profile": dict(profile.most_common()),
        "issues": [issue.__dict__ for issue in issues],
        "summary": {
            "fail": sum(1 for issue in issues if issue.severity == "FAIL"),
            "warn": sum(1 for issue in issues if issue.severity == "WARN"),
        },
    }

    if args.json:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(f"仓库：{output['repo']}")
        print(f"Guide：{guide.get('path')}")
        if guide.get("version") or guide.get("date"):
            print(f"Guide 版本：{guide.get('version', '?')} ({guide.get('date', '?')})")
        print(f"RodSki: {version.get('stdout') or version.get('error') or version.get('path')}")
        print(f"已扫描 XML 文件：{len(files)}")
        if profile:
            actions = ", ".join(f"{name}={count}" for name, count in profile.most_common(12))
            print(f"Action 分布：{actions}")
        if issues:
            print("问题：")
            for issue in issues:
                print(f"  [{issue.severity}] {issue.path}: {issue.message}")
        else:
            print("问题：无")
        print(f"汇总：FAIL={output['summary']['fail']} WARN={output['summary']['warn']}")

    return 1 if any(issue.severity == "FAIL" for issue in issues) else 0


if __name__ == "__main__":
    sys.exit(main())
