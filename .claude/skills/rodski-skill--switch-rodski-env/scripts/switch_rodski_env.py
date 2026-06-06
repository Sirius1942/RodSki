#!/usr/bin/env python3
import argparse
import difflib
import json
import re
import shutil
import sqlite3
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape


SENSITIVE_RE = re.compile(r"password|passwd|token|cookie|secret|session|authorization|username", re.I)
STALE_ENV_RE = re.compile(r"(ec-hwbeta|hwbeta|f2b-beta)", re.I)
URL_RE = re.compile(r"https?://[^\s\"'<>]+")
DB_HOST_RE = re.compile(r"[\w.-]*(?:mysql\.rds\.[\w.-]+|(?:market-)?rds\.[\w.-]+)[\w.-]*", re.I)
TEXT_EXTS = {".py", ".env", ".properties", ".yaml", ".yml", ".json", ".ini", ".conf", ".txt"}
TEXT_SKIP_NAMES = {"package-lock.json", "package.json", "README.md"}
CASE_ASSET_DIRS = {"case", "data", "model", "fun"}
OS_JUNK_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}
DEFAULT_OLD_ROOT = Path.home() / "beta_old/000 case_old"
DEFAULT_NEW_ROOT = Path.home() / "ci_new/000 case_new"
SKIP_DIRS = {
    "result",
    "results",
    "recordings",
    "screenshots",
    "node_modules",
    "dist",
    "build",
    ".git",
    ".vscode",
    "000 report_old",
    "000 report_new",
    "__pycache__",
}


def mask(key, value, artifact=None):
    if value is None:
        return None
    if artifact == "text":
        return value
    if SENSITIVE_RE.search(str(key)):
        return "<masked>" if value else ""
    return value


def module_from_path(root, path):
    rel = path.relative_to(root)
    parts = rel.parts
    if "data" in parts:
        idx = parts.index("data")
        return str(Path(*parts[:idx])) if idx else "."
    if "model" in parts:
        idx = parts.index("model")
        return str(Path(*parts[:idx])) if idx else "."
    if "fun" in parts:
        idx = parts.index("fun")
        return str(Path(*parts[:idx])) if idx else "."
    return str(rel.parent)


def is_db_key(key):
    key = key.lower()
    return key.endswith(".host") or key.endswith("_host") or ".host" in key or "mysql" in key or "database.host" in key


def is_env_like(key, value):
    text = str(value or "")
    if SENSITIVE_RE.search(str(key)):
        return False
    return bool(URL_RE.search(text) or DB_HOST_RE.search(text) or is_db_key(str(key)))


def value_kind(key, value):
    text = str(value or "")
    if URL_RE.search(text):
        return "url"
    if DB_HOST_RE.search(text) or is_db_key(str(key)):
        return "db"
    return "other"


def stale_env_like(value):
    return bool(STALE_ENV_RE.search(str(value or "")))


def should_skip_path(path):
    return any(part in SKIP_DIRS for part in path.parts)


def iter_globalvalue_files(root):
    return sorted(p for p in root.rglob("data/globalvalue.xml") if p.is_file() and not should_skip_path(p))


def iter_model_files(root):
    return sorted(p for p in root.rglob("model/model.xml") if p.is_file() and not should_skip_path(p))


def iter_sqlite_files(root):
    return sorted(p for p in root.rglob("data/data.sqlite") if p.is_file() and not should_skip_path(p))


def iter_text_files(root, broad=False):
    files = []
    for path in root.rglob("*"):
        if not path.is_file() or should_skip_path(path):
            continue
        rel_parts = path.relative_to(root).parts
        in_fun = "fun" in rel_parts
        is_env_file = path.name == ".env"
        if not broad and not (in_fun or is_env_file):
            continue
        if path.name in TEXT_SKIP_NAMES:
            continue
        if path.suffix in TEXT_EXTS or is_env_file:
            files.append(path)
    return sorted(files)


def iter_case_asset_files(root, assets):
    files = []
    for path in root.rglob("*"):
        if not path.is_file() or should_skip_path(path):
            continue
        if path.name in OS_JUNK_NAMES:
            continue
        rel = path.relative_to(root)
        if case_asset_kind(root, rel, assets):
            files.append(path)
    return sorted(files)


def read_xml(path):
    return ET.parse(path).getroot()


def xml_value_for_raw(value):
    return xml_escape(value, {'"': "&quot;"})


def parse_globalvalue_entries(root, path):
    module = module_from_path(root, path)
    xml_root = read_xml(path)
    entries = []
    for group in xml_root.findall(".//group"):
        group_name = group.attrib.get("name", "")
        for var in group.findall("./var"):
            var_name = var.attrib.get("name", "")
            value = var.attrib.get("value", "")
            key = f"{group_name}.{var_name}"
            if not is_env_like(key, value):
                continue
            entries.append(
                {
                    "artifact": "globalvalue",
                    "module": module,
                    "file": str(path),
                    "key": key,
                    "kind": value_kind(key, value),
                    "value": value,
                    "raw_value": xml_value_for_raw(value),
                    "replace_mode": "xml-attribute",
                    "selector": f"globalvalue:{module}::{key}",
                }
            )
    return entries


def parse_model_entries(root, path):
    module = module_from_path(root, path)
    xml_root = read_xml(path)
    entries = []
    for model in xml_root.findall(".//model"):
        model_name = model.attrib.get("name", "")
        for element in model.findall("./element"):
            element_name = element.attrib.get("name", "")
            for idx, loc in enumerate(element.findall("./location"), 1):
                value = (loc.text or "").strip()
                key = f"{model_name}.{element_name}.location[{idx}]"
                if not is_env_like(key, value):
                    continue
                entries.append(
                    {
                        "artifact": "model",
                        "module": module,
                        "file": str(path),
                        "key": key,
                        "kind": value_kind(key, value),
                        "value": value,
                        "raw_value": xml_value_for_raw(value),
                        "replace_mode": "xml-text",
                        "selector": f"model:{module}::{key}",
                    }
                )
    return entries


def parse_sqlite_entries(root, path):
    module = module_from_path(root, path)
    entries = []
    try:
        con = sqlite3.connect(str(path))
        con.row_factory = sqlite3.Row
        query = """
            SELECT table_name, data_id, field_name, field_value
            FROM rs_field
            ORDER BY table_name, data_id, field_name
        """
        for row in con.execute(query):
            key = f"{row['table_name']}/{row['data_id']}/{row['field_name']}"
            value = row["field_value"]
            if not is_env_like(key, value):
                continue
            entries.append(
                {
                    "artifact": "sqlite",
                    "module": module,
                    "file": str(path),
                    "key": key,
                    "kind": value_kind(key, value),
                    "value": value,
                    "selector": f"sqlite:{module}::{key}",
                    "table_name": row["table_name"],
                    "data_id": row["data_id"],
                    "field_name": row["field_name"],
                }
            )
        con.close()
    except sqlite3.Error as exc:
        entries.append(
            {
                "artifact": "sqlite",
                "module": module,
                "file": str(path),
                "key": "<sqlite-error>",
                "kind": "error",
                "value": str(exc),
                "selector": f"sqlite:{module}::<sqlite-error>",
            }
        )
    return entries


def parse_text_entries(root, path):
    module = module_from_path(root, path)
    entries = []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return entries
    for lineno, line in enumerate(text.splitlines(), 1):
        matches = list(URL_RE.finditer(line)) + list(DB_HOST_RE.finditer(line))
        for idx, match in enumerate(matches, 1):
            value = match.group(0)
            key = f"{path.relative_to(root)}:{lineno}:{idx}"
            entries.append(
                {
                    "artifact": "text",
                    "module": module,
                    "file": str(path),
                    "key": key,
                    "kind": value_kind(key, value),
                    "value": value,
                    "selector": f"text:{module}::{key}",
                    "line": lineno,
                }
            )
    return entries


def collect(root, scopes, broad_text=False):
    rows = []
    if "globalvalue" in scopes:
        for path in iter_globalvalue_files(root):
            rows.extend(parse_globalvalue_entries(root, path))
    if "model" in scopes:
        for path in iter_model_files(root):
            rows.extend(parse_model_entries(root, path))
    if "sqlite" in scopes:
        for path in iter_sqlite_files(root):
            rows.extend(parse_sqlite_entries(root, path))
    if "text" in scopes:
        for path in iter_text_files(root, broad=broad_text):
            rows.extend(parse_text_entries(root, path))
    for row in rows:
        row["masked_value"] = mask(row["key"], row["value"], row["artifact"])
        row["stale_env_like"] = stale_env_like(row["value"])
    return rows


def parse_scopes(value):
    scopes = {item.strip() for item in value.split(",") if item.strip()}
    allowed = {"globalvalue", "model", "sqlite", "text"}
    unknown = scopes - allowed
    if unknown:
        raise argparse.ArgumentTypeError(f"unknown scope(s): {', '.join(sorted(unknown))}")
    return scopes


def parse_assets(value):
    assets = {item.strip() for item in value.split(",") if item.strip()}
    unknown = assets - CASE_ASSET_DIRS
    if unknown:
        raise argparse.ArgumentTypeError(f"unknown asset dir(s): {', '.join(sorted(unknown))}")
    return assets


def write_json(path, payload):
    if path:
        Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))


def validate_root(path, label):
    root = Path(path).resolve()
    if not root.exists() or not root.is_dir():
        raise SystemExit(f"{label} does not exist or is not a directory: {root}")
    return root


def load_map(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("map must be a JSON object")
    mapping = {
        "value_replacements": data.get("value_replacements", {}),
        "key_replacements": data.get("key_replacements", {}),
        "regex_replacements": data.get("regex_replacements", []),
    }
    for name in ("value_replacements", "key_replacements"):
        if not isinstance(mapping[name], dict):
            raise SystemExit(f"{name} must be an object")
    if not isinstance(mapping["regex_replacements"], list):
        raise SystemExit("regex_replacements must be a list")
    for item in mapping["regex_replacements"]:
        if not isinstance(item, dict) or "pattern" not in item or "replacement" not in item:
            raise SystemExit("each regex replacement must contain pattern and replacement")
        re.compile(item["pattern"])
    return mapping


def replacement_for(entry, mapping):
    module = entry["module"]
    key = entry["key"]
    value = entry["value"]
    selectors = [
        entry.get("selector"),
        f"{module}::{key}",
        key,
    ]
    for selector in selectors:
        if selector in mapping["key_replacements"]:
            return mapping["key_replacements"][selector], "key"
    if value in mapping["value_replacements"]:
        return mapping["value_replacements"][value], "value"
    new_value = value
    changed = False
    for item in mapping["regex_replacements"]:
        candidate = re.sub(item["pattern"], item["replacement"], new_value)
        if candidate != new_value:
            new_value = candidate
            changed = True
    if changed:
        return new_value, "regex"
    return value, None


def diff_text(old, new, label):
    return "\n".join(
        difflib.unified_diff(
            old.splitlines(),
            new.splitlines(),
            fromfile=f"{label}:before",
            tofile=f"{label}:after",
            lineterm="",
        )
    )


def backup_file(path, target_root, backup_dir):
    if not backup_dir:
        return None
    backup_dir = Path(backup_dir).resolve()
    rel = path.resolve().relative_to(target_root)
    dest = backup_dir / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)
    return str(dest)


def plan_xml_text_changes(root, mapping, scopes):
    plans = []
    entries = []
    if "globalvalue" in scopes:
        for path in iter_globalvalue_files(root):
            entries.extend(parse_globalvalue_entries(root, path))
    if "model" in scopes:
        for path in iter_model_files(root):
            entries.extend(parse_model_entries(root, path))
    by_file = {}
    for entry in entries:
        new_value, source = replacement_for(entry, mapping)
        if source and new_value != entry["value"]:
            by_file.setdefault(Path(entry["file"]), []).append((entry, new_value, source))
    for path, changes in sorted(by_file.items()):
        old_text = path.read_text(encoding="utf-8")
        new_text = old_text
        file_changes = []
        for entry, new_value, source in changes:
            changed_text = replace_xml_value(new_text, entry, new_value)
            if changed_text == new_text:
                file_changes.append({**change_record(entry, new_value, source), "error": "raw value not found"})
                continue
            new_text = changed_text
            file_changes.append(change_record(entry, new_value, source))
        plans.append({"file": path, "kind": "text-file", "old": old_text, "new": new_text, "changes": file_changes})
    return plans


def replace_xml_value(text, entry, new_value):
    old_raw = entry["raw_value"]
    new_raw = xml_value_for_raw(new_value)
    if entry.get("replace_mode") == "xml-attribute":
        for quote in ('"', "'"):
            needle = f"value={quote}{old_raw}{quote}"
            repl = f"value={quote}{new_raw}{quote}"
            if needle in text:
                return text.replace(needle, repl, 1)
    if entry.get("replace_mode") == "xml-text":
        needle = f">{old_raw}<"
        repl = f">{new_raw}<"
        if needle in text:
            return text.replace(needle, repl, 1)
    if old_raw in text:
        return text.replace(old_raw, new_raw, 1)
    return text


def plan_text_file_changes(root, mapping, broad_text=False):
    plans = []
    env_repls = {
        old: new
        for old, new in mapping["value_replacements"].items()
        if is_env_like("<map-value>", old) or is_env_like("<map-value>", new)
    }
    regex_items = mapping["regex_replacements"]
    for path in iter_text_files(root, broad=broad_text):
        old_text = path.read_text(encoding="utf-8")
        new_text = old_text
        file_changes = []
        for old, new in env_repls.items():
            if old in new_text:
                new_text = new_text.replace(old, new)
                file_changes.append(
                    {
                        "artifact": "text",
                        "module": module_from_path(root, path),
                        "file": str(path),
                        "key": "<raw-text>",
                        "source": "value",
                        "old": mask("<raw-text>", old, "text"),
                        "new": mask("<raw-text>", new, "text"),
                    }
                )
        for item in regex_items:
            candidate = re.sub(item["pattern"], item["replacement"], new_text)
            if candidate != new_text:
                new_text = candidate
                file_changes.append(
                    {
                        "artifact": "text",
                        "module": module_from_path(root, path),
                        "file": str(path),
                        "key": "<raw-text>",
                        "source": "regex",
                        "old": item["pattern"],
                        "new": item["replacement"],
                    }
                )
        if new_text != old_text:
            plans.append({"file": path, "kind": "text-file", "old": old_text, "new": new_text, "changes": file_changes})
    return plans


def plan_sqlite_changes(root, mapping, scopes):
    if "sqlite" not in scopes:
        return []
    plans = []
    for path in iter_sqlite_files(root):
        changes = []
        for entry in parse_sqlite_entries(root, path):
            if entry["kind"] == "error":
                continue
            new_value, source = replacement_for(entry, mapping)
            if source and new_value != entry["value"]:
                changes.append((entry, new_value, source))
        if changes:
            plans.append({"file": path, "kind": "sqlite", "changes": changes})
    return plans


def change_record(entry, new_value, source):
    return {
        "artifact": entry["artifact"],
        "module": entry["module"],
        "file": entry["file"],
        "key": entry["key"],
        "selector": entry.get("selector"),
        "kind": entry["kind"],
        "source": source,
        "old": mask(entry["key"], entry["value"], entry["artifact"]),
        "new": mask(entry["key"], new_value, entry["artifact"]),
    }


def cmd_audit(args):
    root = validate_root(args.root, "root")
    rows = collect(root, args.scopes, args.broad_text)
    payload = {
        "root": str(root),
        "scopes": sorted(args.scopes),
        "count": len(rows),
        "items": [{k: v for k, v in row.items() if k not in {"value", "raw_value"}} for row in rows],
    }
    write_json(args.out, payload)
    return 0


def cmd_compare(args):
    old_root = validate_root(args.old_root, "old-root")
    new_root = validate_root(args.new_root, "new-root")
    old_rows = {(r["artifact"], r["module"], r["key"]): r for r in collect(old_root, args.scopes, args.broad_text)}
    new_rows = {(r["artifact"], r["module"], r["key"]): r for r in collect(new_root, args.scopes, args.broad_text)}
    changed = []
    unchanged_env = []
    missing = []
    added = []
    stale_new = []
    for key in sorted(set(old_rows) | set(new_rows)):
        old = old_rows.get(key)
        new = new_rows.get(key)
        if old is None:
            added.append(public_entry(new))
            continue
        if new is None:
            missing.append(public_entry(old))
            continue
        if old["value"] != new["value"]:
            changed.append(
                {
                    "artifact": key[0],
                    "module": key[1],
                    "key": key[2],
                    "kind": new["kind"],
                    "old": mask(key[2], old["value"], old["artifact"]),
                    "new": mask(key[2], new["value"], new["artifact"]),
                }
            )
        else:
            item = {
                "artifact": key[0],
                "module": key[1],
                "key": key[2],
                "kind": new["kind"],
                "value": mask(key[2], new["value"], new["artifact"]),
            }
            unchanged_env.append(item)
            if new["stale_env_like"]:
                stale_new.append(item)
    payload = {
        "old_root": str(old_root),
        "new_root": str(new_root),
        "scopes": sorted(args.scopes),
        "summary": {
            "changed": len(changed),
            "unchanged_env": len(unchanged_env),
            "stale_new": len(stale_new),
            "missing": len(missing),
            "added": len(added),
        },
        "changed": changed,
        "unchanged_env": unchanged_env,
        "stale_new": stale_new,
        "missing": missing,
        "added": added,
    }
    write_json(args.out, payload)
    if args.markdown:
        write_markdown_compare(Path(args.markdown), payload)
    return 0


def public_entry(row):
    return {k: v for k, v in row.items() if k not in {"value", "raw_value"}}


def looks_like_case_module(module_dir):
    return any(
        marker.exists()
        for marker in (
            module_dir / "case",
            module_dir / "model" / "model.xml",
            module_dir / "data" / "globalvalue.xml",
            module_dir / "data" / "data.sqlite",
        )
    )


def case_asset_kind(root, rel, assets=CASE_ASSET_DIRS):
    for idx, part in enumerate(rel.parts):
        if part in assets:
            module_dir = root / Path(*rel.parts[:idx]) if idx else root
            if not looks_like_case_module(module_dir):
                continue
            return part
    return ""


def run_sync_missing(old_root, new_root, assets, write):
    source_files = iter_case_asset_files(old_root, assets)
    missing = []
    existing = []
    blocked = []
    copied = []
    for src in source_files:
        rel = src.relative_to(old_root)
        dest = new_root / rel
        record = {
            "asset": case_asset_kind(old_root, rel, assets),
            "relative_path": str(rel),
            "source": str(src),
            "target": str(dest),
        }
        if dest.exists():
            existing.append(record)
            continue
        if dest.parent.exists() and not dest.parent.is_dir():
            blocked.append({**record, "error": "target parent exists and is not a directory"})
            continue
        missing.append(record)
        if write:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            copied.append(record)
    return {
        "summary": {
            "source_files": len(source_files),
            "existing": len(existing),
            "missing": len(missing),
            "blocked": len(blocked),
            "copied": len(copied),
        },
        "missing": missing,
        "blocked": blocked,
        "copied": copied,
    }


def cmd_sync_missing(args):
    old_root = validate_root(args.old_root, "old-root")
    new_root = validate_root(args.new_root, "new-root")
    result = run_sync_missing(old_root, new_root, args.assets, args.write)
    payload = {
        "old_root": str(old_root),
        "new_root": str(new_root),
        "assets": sorted(args.assets),
        "write": bool(args.write),
        "summary": result["summary"],
        "missing": result["missing"],
        "blocked": result["blocked"],
        "copied": result["copied"],
    }
    write_json(args.out, payload)
    return 1 if result["blocked"] else 0


def md_cell(value):
    text = str(value).replace("|", "\\|").replace("\n", "<br>")
    return text


def write_markdown_compare(path, payload):
    lines = []
    lines.append("# RodSki 环境值对比")
    lines.append("")
    lines.append(f"- 旧目录：`{payload['old_root']}`")
    lines.append(f"- 新目录：`{payload['new_root']}`")
    lines.append(f"- 范围：`{','.join(payload['scopes'])}`")
    lines.append(f"- 实际变化：{payload['summary']['changed']} 项")
    lines.append(f"- 未变化环境项：{payload['summary']['unchanged_env']} 项")
    lines.append(f"- 新目录仍像旧 beta 环境的项：{payload['summary']['stale_new']} 项")
    lines.append("")
    lines.append("## 实际变化")
    lines.append("")
    write_table(lines, payload["changed"], ["artifact", "module", "key", "kind", "old", "new"])
    lines.append("")
    lines.append("## 应变未变或仍像旧环境")
    lines.append("")
    write_table(lines, payload["stale_new"] or payload["unchanged_env"], ["artifact", "module", "key", "kind", "value"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_table(lines, rows, columns):
    if not rows:
        lines.append("- 无。")
        return
    lines.append("| " + " | ".join(columns) + " |")
    lines.append("|" + "|".join("---" for _ in columns) + "|")
    for row in rows:
        lines.append("| " + " | ".join(md_cell(row.get(col, "")) for col in columns) + " |")


def build_map(old_root, new_root, scopes, broad_text=False):
    old_rows = {(r["artifact"], r["module"], r["key"]): r for r in collect(old_root, scopes, broad_text)}
    new_rows = {(r["artifact"], r["module"], r["key"]): r for r in collect(new_root, scopes, broad_text)}
    candidates = []
    for key in sorted(set(old_rows) & set(new_rows)):
        old = old_rows[key]
        new = new_rows[key]
        if old["value"] != new["value"]:
            candidates.append((old, new))
    by_old = {}
    for old, new in candidates:
        by_old.setdefault(old["value"], set()).add(new["value"])
    value_replacements = {}
    key_replacements = {}
    conflicts = []
    for old, new in candidates:
        new_values = by_old[old["value"]]
        if len(new_values) == 1:
            value_replacements[old["value"]] = next(iter(new_values))
        else:
            key_replacements[old["selector"]] = new["value"]
            conflicts.append(
                {
                    "old": mask(old["key"], old["value"], old["artifact"]),
                    "selector": old["selector"],
                    "new": mask(new["key"], new["value"], new["artifact"]),
                }
            )
    mapping = {
        "value_replacements": value_replacements,
        "key_replacements": key_replacements,
        "regex_replacements": [],
    }
    return mapping, conflicts


def cmd_extract_map(args):
    old_root = validate_root(args.old_root, "old-root")
    new_root = validate_root(args.new_root, "new-root")
    mapping, conflicts = build_map(old_root, new_root, args.scopes, args.broad_text)
    payload = {
        "old_root": str(old_root),
        "new_root": str(new_root),
        "scopes": sorted(args.scopes),
        "value_replacements": mapping["value_replacements"],
        "key_replacements": mapping["key_replacements"],
        "regex_replacements": mapping["regex_replacements"],
        "conflicts_resolved_as_key_replacements": conflicts,
    }
    write_json(args.out, payload)
    return 0


def run_apply(target_root, mapping, scopes, write, backup_dir=None, diff=False, broad_text=False):
    plans = []
    plans.extend(plan_xml_text_changes(target_root, mapping, scopes))
    if "text" in scopes:
        plans.extend(plan_text_file_changes(target_root, mapping, broad_text))
    sqlite_plans = plan_sqlite_changes(target_root, mapping, scopes)
    changes = []
    diffs = []
    backups = []
    for plan in plans:
        changes.extend(plan["changes"])
        if diff:
            d = diff_text(plan["old"], plan["new"], str(plan["file"]))
            if d:
                diffs.append(d)
        if write and plan["old"] != plan["new"]:
            backup = backup_file(plan["file"], target_root, backup_dir)
            if backup:
                backups.append(backup)
            plan["file"].write_text(plan["new"], encoding="utf-8")
    for plan in sqlite_plans:
        for entry, new_value, source in plan["changes"]:
            changes.append(change_record(entry, new_value, source))
        if write:
            backup = backup_file(plan["file"], target_root, backup_dir)
            if backup:
                backups.append(backup)
            con = sqlite3.connect(str(plan["file"]))
            for entry, new_value, _ in plan["changes"]:
                con.execute(
                    """
                    UPDATE rs_field
                    SET field_value = ?
                    WHERE table_name = ? AND data_id = ? AND field_name = ?
                    """,
                    (new_value, entry["table_name"], entry["data_id"], entry["field_name"]),
                )
            con.commit()
            con.close()
    return {"changes": changes, "diffs": diffs, "backups": backups}


def cmd_apply(args):
    target_root = validate_root(args.target_root, "target-root")
    mapping = load_map(args.map)
    result = run_apply(
        target_root,
        mapping,
        args.scopes,
        args.write,
        backup_dir=args.backup_dir,
        diff=args.diff,
        broad_text=args.broad_text,
    )
    payload = {
        "target_root": str(target_root),
        "scopes": sorted(args.scopes),
        "write": bool(args.write),
        "change_count": len(result["changes"]),
        "changes": result["changes"],
        "backups": result["backups"],
    }
    if args.diff:
        payload["diff"] = "\n".join(result["diffs"])
    write_json(args.out, payload)
    return 0


def summarize_changes(changes):
    distinct = {}
    by_file = {}
    by_source = {}
    for ch in changes:
        pair = (str(ch.get("old")), str(ch.get("new")))
        distinct[pair] = distinct.get(pair, 0) + 1
        f = ch.get("file", "")
        by_file[f] = by_file.get(f, 0) + 1
        src = ch.get("source", "")
        by_source[src] = by_source.get(src, 0) + 1
    distinct_value_changes = [
        {"old": old, "new": new, "count": count}
        for (old, new), count in sorted(distinct.items(), key=lambda kv: (-kv[1], kv[0]))
    ]
    files = [
        {"file": f, "count": count}
        for f, count in sorted(by_file.items(), key=lambda kv: (-kv[1], kv[0]))
    ]
    return {
        "change_count": len(changes),
        "distinct_value_changes": distinct_value_changes,
        "by_source": by_source,
        "by_file": files,
    }


def cmd_convert(args):
    old_root = validate_root(args.old_root, "old-root")
    new_root = validate_root(args.new_root, "new-root")
    if old_root == new_root:
        raise SystemExit("old-root and new-root must differ; new-root is the target and must never equal the read-only old-root")
    # 1. derive mapping from old/new (or load explicit map to skip extraction).
    #    Map derivation excludes 'text': text keys are positional (path:line:idx)
    #    and pair unreliably; structured artifacts give clean old->new pairs.
    map_scopes = {s for s in args.scopes if s != "text"} or {"globalvalue", "model", "sqlite"}
    if args.map:
        mapping = load_map(args.map)
        conflicts = []
    else:
        mapping, conflicts = build_map(old_root, new_root, map_scopes, args.broad_text)
    # 2. supplement new-root with missing case/data/model/fun from old-root
    sync = run_sync_missing(old_root, new_root, args.assets, args.write)
    # 3. apply URL/DB switch to new-root (target), including just-copied assets
    apply_result = run_apply(
        new_root,
        mapping,
        args.scopes,
        args.write,
        backup_dir=args.backup_dir,
        diff=args.diff,
        broad_text=args.broad_text,
    )
    payload = {
        "old_root": str(old_root),
        "new_root": str(new_root),
        "scopes": sorted(args.scopes),
        "write": bool(args.write),
        "map": {
            "source": "explicit" if args.map else "extracted",
            "map_scopes": sorted(map_scopes),
            "value_replacements": len(mapping["value_replacements"]),
            "key_replacements": len(mapping["key_replacements"]),
            "regex_replacements": len(mapping["regex_replacements"]),
            "conflicts": len(conflicts),
        },
        "sync": sync["summary"],
        "apply": summarize_changes(apply_result["changes"]),
        "sync_missing": sync["missing"],
        "sync_blocked": sync["blocked"],
        "map_conflicts": conflicts,
        "backups": apply_result["backups"],
    }
    if args.full:
        payload["apply"]["changes"] = apply_result["changes"]
    if args.diff:
        payload["diff"] = "\n".join(apply_result["diffs"])
    if args.map_out:
        write_json(args.map_out, {
            "old_root": str(old_root),
            "new_root": str(new_root),
            "scopes": sorted(args.scopes),
            "value_replacements": mapping["value_replacements"],
            "key_replacements": mapping["key_replacements"],
            "regex_replacements": mapping["regex_replacements"],
            "conflicts_resolved_as_key_replacements": conflicts,
        })
    write_json(args.out, payload)
    return 1 if sync["blocked"] else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Audit, compare, sync missing assets, extract maps, or switch RodSki environment URL/DB address values.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    audit = sub.add_parser("audit", help="list URL and DB-address values")
    audit.add_argument("--root", required=True)
    audit.add_argument("--scope", dest="scopes", type=parse_scopes, default=parse_scopes("globalvalue,model,sqlite,text"))
    audit.add_argument("--out")
    audit.add_argument("--broad-text", action="store_true", help="scan all supported text files; default text scope is limited to fun/ and .env")
    audit.set_defaults(func=cmd_audit)

    compare = sub.add_parser("compare", help="read-only compare between two RodSki case roots")
    compare.add_argument("--old-root", required=True)
    compare.add_argument("--new-root", required=True)
    compare.add_argument("--scope", dest="scopes", type=parse_scopes, default=parse_scopes("globalvalue,model,sqlite"))
    compare.add_argument("--out")
    compare.add_argument("--markdown")
    compare.add_argument("--broad-text", action="store_true", help="scan all supported text files; default text scope is limited to fun/ and .env")
    compare.set_defaults(func=cmd_compare)

    sync_missing = sub.add_parser("sync-missing", help="copy missing RodSki case/data/model/fun files from old root to new root without overwriting")
    sync_missing.add_argument("--old-root", default=str(DEFAULT_OLD_ROOT), help=f"read-only source root; default: {DEFAULT_OLD_ROOT}")
    sync_missing.add_argument("--new-root", default=str(DEFAULT_NEW_ROOT), help=f"target root to supplement; default: {DEFAULT_NEW_ROOT}")
    sync_missing.add_argument("--assets", type=parse_assets, default=parse_assets("case,data,model,fun"), help="comma-separated asset dirs to copy when missing")
    sync_missing.add_argument("--out")
    sync_missing.add_argument("--write", action="store_true", help="copy missing files; default is dry-run")
    sync_missing.set_defaults(func=cmd_sync_missing)

    extract_map = sub.add_parser("extract-map", help="read-only derive a replacement map from old/new roots")
    extract_map.add_argument("--old-root", required=True)
    extract_map.add_argument("--new-root", required=True)
    extract_map.add_argument("--scope", dest="scopes", type=parse_scopes, default=parse_scopes("globalvalue,model,sqlite"))
    extract_map.add_argument("--out")
    extract_map.add_argument("--broad-text", action="store_true", help="scan all supported text files; default text scope is limited to fun/ and .env")
    extract_map.set_defaults(func=cmd_extract_map)

    apply = sub.add_parser("apply", help="apply explicit environment mapping to a separate target root")
    apply.add_argument("--target-root", required=True, dest="target_root", help="target/new case root to change; old roots must never be passed here")
    apply.add_argument("--map", required=True)
    apply.add_argument("--scope", dest="scopes", type=parse_scopes, default=parse_scopes("globalvalue,model,sqlite,text"))
    apply.add_argument("--out")
    apply.add_argument("--write", action="store_true", help="write target files; default is dry-run")
    apply.add_argument("--backup-dir", help="copy changed target files here before writing")
    apply.add_argument("--diff", action="store_true", help="include unified text diffs for changed text/XML files")
    apply.add_argument("--broad-text", action="store_true", help="scan all supported text files; default text scope is limited to fun/ and .env")
    apply.set_defaults(func=cmd_apply)

    convert = sub.add_parser(
        "convert",
        help="one-shot: derive map (or use --map), sync missing assets, and switch URL/DB in one pass; default dry-run with compact summary",
    )
    convert.add_argument("--old-root", default=str(DEFAULT_OLD_ROOT), help=f"read-only source root; default: {DEFAULT_OLD_ROOT}")
    convert.add_argument("--new-root", default=str(DEFAULT_NEW_ROOT), help=f"target root to supplement and switch; default: {DEFAULT_NEW_ROOT}")
    convert.add_argument("--map", help="explicit mapping JSON; skips extract-map when provided")
    convert.add_argument("--assets", type=parse_assets, default=parse_assets("case,data,model,fun"), help="comma-separated asset dirs to copy when missing")
    convert.add_argument("--scope", dest="scopes", type=parse_scopes, default=parse_scopes("globalvalue,model,sqlite,text"))
    convert.add_argument("--out")
    convert.add_argument("--map-out", help="also write the derived/used mapping to this path")
    convert.add_argument("--write", action="store_true", help="copy missing files and write target changes; default is dry-run")
    convert.add_argument("--backup-dir", help="copy changed target files here before writing")
    convert.add_argument("--diff", action="store_true", help="include unified text diffs for changed text/XML files")
    convert.add_argument("--full", action="store_true", help="include per-change detail list in addition to the compact summary")
    convert.add_argument("--broad-text", action="store_true", help="scan all supported text files; default text scope is limited to fun/ and .env")
    convert.set_defaults(func=cmd_convert)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
