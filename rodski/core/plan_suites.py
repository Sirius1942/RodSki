"""测试套与分发清单（v11.11.0，CORE §7.9）。

一处实现，多处复用：

- ``select_plan``：计划 → 选择结果（带测试套归属）。执行器与编译共用。
- ``compile_plan``：计划 → 分发清单（``rodski plan compile --json``、``run --suite`` /
  ``--expect-digest`` 预检、``--workers`` 按套调度、设备队列按套入队）。

计划不写 ``<suite>`` 时视为隐式测试套 ``default``，执行行为与 v11.10 一致。
"""
from __future__ import annotations

import hashlib
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from .test_plan_selection import TestPlanSelection, apply_plan_selection, scope_plan_cases

MANIFEST_SCHEMA = "rodski.plan-manifest/1"
IMPLICIT_SUITE_ID = "default"
SUITE_EXECUTE_FALSE = "suite_execute_false"

# 归属优先级：显式 <case> 高于任何 <case_dir>；case_dir 按路径段数，越长越具体
_EXPLICIT_RANK = 10_000


class PlanSuiteError(ValueError):
    """计划测试套结构 / 编译错误（可能包含多条）。"""

    def __init__(self, errors: Sequence[str]):
        self.errors = list(errors)
        super().__init__("；".join(self.errors))


def has_suites(plan: Dict[str, Any]) -> bool:
    return bool(plan.get("suites"))


def check_plan_structure(plan: Dict[str, Any]) -> List[str]:
    """XSD 之外的结构约束（CORE §7.9.1）。"""
    errors: List[str] = []
    pid = plan.get("id", "")
    kind = plan.get("kind", "")
    suites = plan.get("suites") or []
    if kind != "suite":
        if suites:
            errors.append(f"计划 {pid}: <suite> 只能用于 kind=\"suite\" 的测试计划（当前 kind={kind!r}）")
        if plan.get("max_parallel") is not None:
            errors.append(f"计划 {pid}: max_parallel 只能用于 kind=\"suite\" 的测试计划（当前 kind={kind!r}）")
    if suites and plan.get("default_execute", "否") == "是":
        errors.append(f"计划 {pid}: default_execute=\"是\" 不能与 <suite> 同用（测试套划分必须显式）")
    seen: Set[str] = set()
    for suite in suites:
        sid = suite.get("id", "")
        if sid in seen:
            errors.append(f"计划 {pid}: 测试套 id 重复: {sid}")
        seen.add(sid)
    return errors


def _case_uid(case: Dict[str, Any]) -> str:
    case_file = case.get("case_file", "")
    case_id = case.get("case_id") or case.get("id") or ""
    return f"{case_file}::{case_id}" if case_file else case_id


def _dir_contains(dir_path: str, case_file: str) -> bool:
    dir_path = dir_path.strip().strip("/")
    if not dir_path:
        return True
    return case_file.startswith(dir_path + "/")


def assign_suites(plan: Dict[str, Any], cases: List[Dict[str, Any]]) -> Tuple[Dict[str, str], List[str]]:
    """用例 → 测试套归属（CORE §7.9.1-3）。返回 ({case_uid: suite_id}, errors)。

    显式 <case> > 更长的 <case_dir> > 更短的 <case_dir>；平级命中不同测试套报错。
    execute="否" 的 <case_dir> 不认领用例；execute="否" 的显式 <case> 仍认领（用例记为 SKIP）。
    """
    by_id: Dict[str, List[str]] = {}
    for case in cases:
        by_id.setdefault(case.get("case_id", ""), []).append(_case_uid(case))
    claims: Dict[str, Dict[str, int]] = {}   # uid -> {suite_id: best rank}

    def claim(uid: str, sid: str, rank: int) -> None:
        bucket = claims.setdefault(uid, {})
        bucket[sid] = max(rank, bucket.get(sid, -1))

    for suite in plan.get("suites") or []:
        sid = suite["id"]
        for entry in suite.get("cases") or []:
            file_attr = entry.get("file", "")
            if file_attr:
                claim(f"{file_attr}::{entry.get('id', '')}", sid, _EXPLICIT_RANK)
            else:
                for uid in by_id.get(entry.get("id", ""), []):
                    claim(uid, sid, _EXPLICIT_RANK)
        for entry in suite.get("case_dirs") or []:
            if (entry.get("execute") or "是") == "否":
                continue
            path = (entry.get("path") or "").strip().strip("/")
            rank = len([p for p in path.split("/") if p])
            for case in cases:
                if _dir_contains(path, case.get("case_file", "")):
                    claim(_case_uid(case), sid, rank)

    assignment: Dict[str, str] = {}
    errors: List[str] = []
    for uid, bucket in claims.items():
        best = max(bucket.values())
        winners = sorted(sid for sid, rank in bucket.items() if rank == best)
        if len(winners) > 1:
            how = "显式 <case>" if best >= _EXPLICIT_RANK else "相同深度的 <case_dir>"
            errors.append(f"用例 {uid} 被多个测试套以{how}同时命中: {', '.join(winners)}（归属必须唯一）")
            continue
        assignment[uid] = winners[0]
    return assignment, errors


def select_plan(plan: Dict[str, Any], cases: List[Dict[str, Any]], module_dir: Optional[Path]) -> Dict[str, Any]:
    """计划选择。无测试套时等同 ``TestPlanSelection.select()``；有测试套时按套选择并只保留本套认领的用例。

    返回 dict 额外带 ``assignment``（仅有测试套时）。
    """
    if not has_suites(plan):
        return TestPlanSelection(cases, plan, module_dir=module_dir).select()

    errors = check_plan_structure(plan)
    assignment, assign_errors = assign_suites(plan, cases)
    errors.extend(assign_errors)
    if errors:
        raise PlanSuiteError(errors)

    selected: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    stale: List[Dict[str, Any]] = []
    case_index = {_case_uid(c): c for c in cases}

    for suite in plan["suites"]:
        sid = suite["id"]
        owned = [uid for uid, owner in assignment.items() if owner == sid]
        if (plan.get("execute") or "是") == "否" or (suite.get("execute") or "是") == "否":
            reason = "plan_execute_false" if (plan.get("execute") or "是") == "否" else SUITE_EXECUTE_FALSE
            for case in cases:
                uid = _case_uid(case)
                if assignment.get(uid) == sid:
                    skipped.append({"type": "case", "case_id": case.get("case_id", ""),
                                    "case_file": case.get("case_file", ""), "case": case,
                                    "reason": reason, "suite": sid})
            continue
        sub_plan = {
            "id": plan.get("id", ""), "kind": plan.get("kind", ""), "execute": "是", "default_execute": "否",
            "cases": suite.get("cases") or [], "case_dirs": suite.get("case_dirs") or [],
        }
        result = TestPlanSelection(cases, sub_plan, module_dir=module_dir).select()
        owned_set = set(owned)
        seen: Set[Tuple[str, str, Any]] = set()
        for key, target in (("selected", selected), ("skipped", skipped)):
            for entry in result.get(key, []):
                uid = _case_uid(entry)
                if uid not in owned_set:
                    continue
                marker = (uid, entry.get("type", ""), (entry.get("scenario_id"), entry.get("step_no")))
                if key == "selected" and marker in seen:
                    continue   # 同一用例既被 case_dir 又被显式 case 选中：去重
                seen.add(marker)
                entry["suite"] = sid
                target.append(entry)
        for ref in result.get("stale_references", []):
            ref = dict(ref)
            ref["suite"] = sid
            stale.append(ref)

    # 未被任何测试套认领、但显式 <case> 指到的用例已在 stale；case_index 仅用于保持引用存在
    del case_index
    return {"selected": selected, "skipped": skipped, "stale_references": stale, "assignment": assignment}


def order_cases_by_suite(plan: Dict[str, Any], cases: List[Dict[str, Any]],
                         assignment: Dict[str, str]) -> List[Dict[str, Any]]:
    """按测试套顺序重排（套内保持发现顺序），并给用例标 ``_suite_id``。"""
    order = {s["id"]: i for i, s in enumerate(plan.get("suites") or [])}
    for case in cases:
        sid = assignment.get(_case_uid(case))
        if sid:
            case["_suite_id"] = sid
    indexed = list(enumerate(cases))
    indexed.sort(key=lambda item: (order.get(item[1].get("_suite_id", ""), len(order)), item[0]))
    return [c for _, c in indexed]


# ------------------------------------------------------------------ 编译
@dataclass
class CompiledPlan:
    manifest: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    @property
    def digest(self) -> str:
        return self.manifest.get("digest", "")

    def suite(self, sid: str) -> Optional[Dict[str, Any]]:
        for suite in self.manifest.get("suites", []):
            if suite.get("id") == sid:
                return suite
        return None

    def error_payload(self) -> Dict[str, Any]:
        return {"schema": MANIFEST_SCHEMA, "plan_id": self.manifest.get("plan_id", ""), "errors": self.errors}


def _rodski_version() -> str:
    try:
        from rodski import __version__
        return __version__
    except Exception:  # pragma: no cover
        return ""


def _module_label(module_dir: Path) -> str:
    parts = Path(module_dir).resolve().parts
    if "product" in parts:
        idx = len(parts) - 1 - list(reversed(parts)).index("product")
        return "/".join(parts[idx:])
    return "/".join(parts[-3:])


def _stale_text(ref: Dict[str, Any]) -> str:
    kind = ref.get("type", "")
    if kind == "case_dir":
        target = f"case_dir:{ref.get('path', '')}"
    else:
        target = f"{kind}:{ref.get('case_file', '')}::{ref.get('case_id', '')}".replace(":::", ":")
        if ref.get("scenario_id"):
            target += f"/{ref['scenario_id']}"
        if ref.get("step_no") is not None:
            target += f"#{ref['step_no']}"
    suffix = f"（测试套 {ref['suite']}）" if ref.get("suite") else ""
    return f"{target} {ref.get('reason', '')}{suffix}".strip()


def compute_digest(module_dir: Path, rel_paths: Sequence[str]) -> str:
    """sha256(按相对路径排序的「路径 \\0 内容 \\0」序列)。路径为相对模块目录的 POSIX 路径。"""
    h = hashlib.sha256()
    for rel in sorted(set(rel_paths)):
        path = Path(module_dir) / rel
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(path.read_bytes() if path.is_file() else b"")
        h.update(b"\0")
    return "sha256:" + h.hexdigest()


def compile_plan(module_dir: Path, plan_id: str, *, platform: Optional[str] = None,
                 allow_cross_platform: bool = False) -> CompiledPlan:
    """编译计划为分发清单。只读，无副作用；错误收集到 ``errors`` 而不抛出。"""
    from .capability import MOBILE_CAPABILITIES, CapabilityError, CapabilityResolver
    from .case_parser import CaseParser
    from .plan_parser import PlanParser

    module_dir = Path(module_dir)
    plan_id = plan_id.lstrip("@")
    compiled = CompiledPlan(manifest={"schema": MANIFEST_SCHEMA, "plan_id": plan_id})
    plan_path = module_dir / "plan" / f"{plan_id}.xml"
    try:
        plan = PlanParser(str(plan_path)).parse_plan()
    except Exception as e:  # XSD / 文件不存在 / id 不一致
        compiled.errors.append(f"计划 {plan_id} 解析失败: {e}")
        return compiled
    compiled.errors.extend(check_plan_structure(plan))
    if compiled.errors:
        return compiled

    try:
        cases = CaseParser(str(module_dir / "case")).parse_cases()
        selection = select_plan(plan, cases, module_dir)
    except PlanSuiteError as e:
        compiled.errors.extend(e.errors)
        return compiled
    except Exception as e:
        compiled.errors.append(str(e))
        return compiled

    explicit = has_suites(plan)
    assignment: Dict[str, str] = selection.get("assignment") or {}
    cases = scope_plan_cases(plan, cases, selection)
    cases, case_skips = apply_plan_selection(cases, selection)
    if explicit:
        cases = order_cases_by_suite(plan, cases, assignment)
    try:
        from .data_driven import expand_plan_cases
        cases = expand_plan_cases(plan, cases, case_skips, module_dir)
    except Exception as e:
        compiled.errors.append(str(e))
        return compiled

    resolver = CapabilityResolver(module_dir, platform=platform)
    elements: Dict[str, ET.Element] = {}
    file_roots: Dict[str, Optional[ET.Element]] = {}

    def case_elem(case: Dict[str, Any]) -> Optional[ET.Element]:
        case_file = case.get("case_file", "")
        if case_file not in file_roots:
            try:
                file_roots[case_file] = ET.parse(module_dir / "case" / case_file).getroot()
            except (ET.ParseError, OSError):
                file_roots[case_file] = None
        root = file_roots[case_file]
        if root is None:
            return None
        template_id = (case.get("_data_driven") or {}).get("template_case_id") or case.get("case_id", "")
        key = f"{case_file}::{template_id}"
        if key not in elements:
            for elem in root.findall("case"):
                if elem.get("id") == template_id:
                    elements[key] = elem
                    break
        return elements.get(key)

    suites_meta: List[Dict[str, Any]] = []
    for suite in (plan.get("suites") if explicit else [{"id": IMPLICIT_SUITE_ID, "title": plan.get("title", ""),
                                                          "execute": "是", "tags": []}]):
        suites_meta.append({
            "id": suite["id"], "title": suite.get("title", ""),
            "execute": (suite.get("execute") or "是") != "否",
            "requires": set(), "tags": list(suite.get("tags") or []),
            "os_tags": set(), "weight": 0, "cases": [],
        })
    meta_by_id = {m["id"]: m for m in suites_meta}

    skipped: List[Dict[str, str]] = []
    business_refs: Set[str] = set()
    digest_files: Set[str] = {f"plan/{plan_id}.xml", "model/model.xml"}
    requires_cache: Dict[str, Dict[str, Any]] = {}
    for case in cases:
        template_uid = _case_uid(case) if not case.get("_data_driven") else case["_data_driven"].get(
            "template_uid", _case_uid(case))
        sid = case.get("_suite_id") or (assignment.get(template_uid) if explicit else IMPLICIT_SUITE_ID)
        sid = sid or IMPLICIT_SUITE_ID
        template_id = (case.get("_data_driven") or {}).get("template_case_id") or case.get("case_id", "")
        skip_reason = case_skips.get(_case_uid(case))
        if skip_reason:
            item = {"case_file": case.get("case_file", ""), "case_id": template_id, "reason": skip_reason}
            if explicit:
                item["suite_id"] = sid
            skipped.append(item)
            continue
        if template_uid not in requires_cache:
            elem = case_elem(case)
            if elem is None:
                compiled.errors.append(f"用例 {template_uid} 无法读取")
                continue
            try:
                requires_cache[template_uid] = resolver.case_requires(elem, case.get("case_file", ""), business_refs)
            except CapabilityError as e:
                compiled.errors.append(str(e))
                continue
        info = requires_cache[template_uid]
        meta = meta_by_id.get(sid)
        if meta is None:
            continue
        meta["requires"].update(info["requires"])
        meta["os_tags"].update(info["os_tags"])
        meta["weight"] += int(info["steps"])
        meta["cases"].append({
            "case_file": case.get("case_file", ""), "case_id": template_id,
            "instance_id": case.get("case_id", ""), "requires": list(info["requires"]),
        })
        digest_files.add(f"case/{case.get('case_file', '')}")

    for ref in sorted(business_refs):
        path = resolver.business.file_of(ref)
        if path is not None:
            digest_files.add(Path(path).resolve().relative_to(module_dir.resolve()).as_posix())

    for meta in suites_meta:
        mobile = sorted(set(meta["requires"]) & MOBILE_CAPABILITIES)
        if len(mobile) > 1 and not allow_cross_platform:
            compiled.errors.append(
                f"测试套 {meta['id']} 同时需要 {mobile} 设备，单台设备无法执行（CORE §11.5）；"
                f"拆分测试套或加 --allow-cross-platform-plan"
            )

    warnings: List[str] = []
    if explicit:
        file_suites: Dict[str, List[str]] = {}
        for uid, sid in assignment.items():
            case_file = uid.split("::", 1)[0]
            bucket = file_suites.setdefault(case_file, [])
            if sid not in bucket:
                bucket.append(sid)
        order = {s["id"]: i for i, s in enumerate(plan["suites"])}
        for case_file in sorted(file_suites):
            sids = sorted(file_suites[case_file], key=lambda s: order.get(s, 0))
            if len(sids) > 1:
                warnings.append(
                    f"用例文件 {case_file} 被拆到多个测试套（{', '.join(sids)}）：文件内用例的先后依赖需由计划作者保证"
                )

    if compiled.errors:
        return compiled

    suites_out = []
    for meta in suites_meta:
        tags = list(meta["tags"]) + [t for t in sorted(meta["os_tags"]) if t not in meta["tags"]]
        suites_out.append({
            "id": meta["id"], "title": meta["title"], "execute": meta["execute"],
            "requires": sorted(meta["requires"]), "tags": tags,
            "weight": meta["weight"], "cases": meta["cases"],
        })

    compiled.manifest = {
        "schema": MANIFEST_SCHEMA,
        "rodski_version": _rodski_version(),
        "module": _module_label(module_dir),
        "plan_id": plan_id,
        "digest": compute_digest(module_dir, sorted(digest_files)),
        "max_parallel": plan.get("max_parallel"),
        "implicit_suite": not explicit,
        "suites": suites_out,
        "warnings": warnings,
        "skipped": skipped,
        "stale_references": [_stale_text(r) for r in selection.get("stale_references", [])],
    }
    return compiled


def format_summary(compiled: CompiledPlan) -> str:
    """``plan compile`` 不带 --json 时的文本摘要。"""
    if not compiled.ok:
        return "\n".join(f"[ERROR] {e}" for e in compiled.errors)
    m = compiled.manifest
    max_parallel = m.get("max_parallel")
    lines = [
        f"计划 {m['plan_id']}（{m['module']}）",
        f"  digest: {m['digest']}",
        f"  max_parallel: {max_parallel if max_parallel is not None else '不限'}",
        f"  测试套: {len(m['suites'])}{'（隐式测试套）' if m['implicit_suite'] else ''}",
    ]
    for s in m["suites"]:
        state = "" if s["execute"] else "  [停用]"
        lines.append(
            f"  - {s['id']}{(' ' + s['title']) if s['title'] else ''}{state}: 用例 {len(s['cases'])}，"
            f"weight {s['weight']}，requires [{', '.join(s['requires'])}]，tags [{', '.join(s['tags'])}]"
        )
    if m["skipped"]:
        lines.append(f"  跳过: {len(m['skipped'])}")
        for item in m["skipped"]:
            lines.append(f"    {item['case_file']}::{item['case_id']} ({item['reason']})")
    for ref in m["stale_references"]:
        lines.append(f"[WARN] 计划引用失效: {ref}")
    for w in m["warnings"]:
        lines.append(f"[WARN] {w}")
    return "\n".join(lines)
