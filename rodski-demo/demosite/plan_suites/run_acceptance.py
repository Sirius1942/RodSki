#!/usr/bin/env python3
"""demosite/plan_suites 验收脚本：测试计划测试套与分发清单（REQ-016 / CORE §7.9）。

用法（仓库根目录）:
    python3 rodski-demo/demosite/plan_suites/run_acceptance.py            # 全部
    python3 rodski-demo/demosite/plan_suites/run_acceptance.py PS-17      # 按编号

前置:
    - 共享站点 http://localhost:8000（_sites/demosite）。未运行时脚本自行启动，结束时只停自己启动的进程。
    - 每次执行前重建 data/data.sqlite 与 orders.db（data/init_data.py）。

判定:
    每项都真实执行 `rodski ...`（包入口 rodski.rodski_cli），读取 `plan compile --json` 清单、命令输出、
    本次新生成的 result/<run>/result.xml 与 execution.log。会改动计划 / 用例 / 数据的检查在临时目录的
    模块副本上执行，不改动仓库文件。case/mixed/ 下的 Android / iOS / Windows 用例只编译，不执行。
退出码: FAIL=0 时为 0，否则为 1。最后一行: 汇总: PASS=x FAIL=y
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
DEMOSITE_URL = "http://localhost:8000/"
DEMOSITE_APP = REPO / "rodski-demo" / "_sites" / "demosite" / "app.py"
RUN_SNIPPET = ("import sys; from rodski.rodski_cli import main; "
               "sys.argv=['rodski']+sys.argv[1:]; sys.exit(main())")
MANIFEST_SCHEMA = "rodski.plan-manifest/1"

# shop_full / shop_wide 的期望划分（套内顺序 = 模块发现顺序：文件按路径逐段排序，文件内按书写顺序）
EXPECTED_SUITES = {
    "order": ["PS_LOGIN_API", "PS_ORDER_1[r1]", "PS_ORDER_1[r2]", "PS_ORDER_2"],
    "special": ["PS_SPECIAL"],
    "admin": ["PS_ADMIN_UI", "PS_ADMIN_DB", "PS_LOGIN_UI"],
}
# 每个套内选中用例的 test_step 数之和（数据驱动实例各算一次）
EXPECTED_WEIGHT = {"order": 2 + 3 + 3 + 3, "special": 3, "admin": 6 + 3 + 3}
ALL_ACTIVE = [cid for ids in EXPECTED_SUITES.values() for cid in ids]
LEGACY_CASES = ["PS_ADMIN_UI", "PS_ADMIN_DB", "PS_LOGIN_API", "PS_ORDER_1", "PS_ORDER_2", "PS_SPECIAL"]


# ------------------------------------------------------------------ 执行与结果读取
@dataclass
class Run:
    code: int
    output: str
    results: Dict[str, Dict[str, str]]          # case_id -> result 属性
    order: List[str] = field(default_factory=list)   # result.xml 中的书写顺序
    summary: Dict[str, str] = field(default_factory=dict)
    log: str = ""
    result_xml_count: int = 0


def rodski(args: List[str], module: Path = HERE, timeout: int = 900) -> Run:
    result_root = module / "result"
    before = set(p.name for p in result_root.iterdir()) if result_root.is_dir() else set()
    proc = subprocess.run([sys.executable, "-c", RUN_SNIPPET, *args], cwd=module, text=True,
                          capture_output=True, timeout=timeout)
    output = (proc.stdout or "") + (proc.stderr or "")
    run = Run(proc.returncode, output, {})
    if result_root.is_dir():
        new_dirs = sorted(p for p in result_root.iterdir() if p.is_dir() and p.name not in before)
        for run_dir in new_dirs:
            xml_path = run_dir / "result.xml"
            if xml_path.is_file():
                run.result_xml_count += 1
                root = ET.parse(xml_path).getroot()
                summary = root.find("summary")
                if summary is not None:
                    run.summary = dict(summary.attrib)
                for elem in root.iter("result"):
                    cid = elem.get("case_id", "")
                    run.results[cid] = dict(elem.attrib)
                    run.order.append(cid)
            log_path = run_dir / "execution.log"
            if log_path.is_file():
                run.log += log_path.read_text(encoding="utf-8", errors="replace")
    return run


def compile_json(plan: str, *extra: str, module: Path = HERE) -> Tuple[int, dict, str]:
    """rodski plan compile @plan --json；返回 (退出码, 解析后的 JSON, 原始输出)。"""
    proc = subprocess.run([sys.executable, "-c", RUN_SNIPPET, "plan", "compile", f"@{plan}", "--json", *extra],
                          cwd=module, text=True, capture_output=True, timeout=120)
    try:
        data = json.loads(proc.stdout)
    except (json.JSONDecodeError, ValueError):
        data = {}
    return proc.returncode, data, (proc.stdout or "") + (proc.stderr or "")


def statuses(run: Run) -> Dict[str, str]:
    return {cid: attrs.get("status", "") for cid, attrs in run.results.items()}


def ts(value: str) -> float:
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").timestamp()


def suite_windows(run: Run) -> Dict[str, Tuple[float, float]]:
    """每个套的执行区间 [最早开始, 最晚结束]（只看非 SKIP 结果）。"""
    windows: Dict[str, Tuple[float, float]] = {}
    for attrs in run.results.values():
        sid = attrs.get("suite_id", "")
        if not sid or attrs.get("status") == "SKIP" or not attrs.get("start_time") or not attrs.get("end_time"):
            continue
        s, e = ts(attrs["start_time"]), ts(attrs["end_time"])
        old = windows.get(sid)
        windows[sid] = (min(s, old[0]), max(e, old[1])) if old else (s, e)
    return windows


def peak_concurrency(windows: Dict[str, Tuple[float, float]]) -> int:
    events = []
    for s, e in windows.values():
        events.append((s, 1))
        events.append((e, -1))
    events.sort(key=lambda x: (x[0], x[1]))   # 同一秒先结束后开始（秒级时间戳，不把首尾相接算作重叠）
    cur = peak = 0
    for _, d in events:
        cur += d
        peak = max(peak, cur)
    return peak


class CheckFailed(Exception):
    pass


def expect(cond: bool, msg: str) -> None:
    if not cond:
        raise CheckFailed(msg)


def module_copy() -> Path:
    """复制模块到临时目录（product/demo/plan_suites 结构），不含 result/。"""
    tmp = Path(tempfile.mkdtemp(prefix="rodski_ps_"))
    dst = tmp / "product" / "demo" / "plan_suites"
    shutil.copytree(HERE, dst, ignore=shutil.ignore_patterns("result", "__pycache__", "run_acceptance.py"))
    return dst


def drop_copy(module: Path) -> None:
    shutil.rmtree(module.parents[2], ignore_errors=True)


# ------------------------------------------------------------------ 共享运行（多个检查复用）
_cache: Dict[str, object] = {}


def manifest_full() -> dict:
    if "full" not in _cache:
        code, data, out = compile_json("shop_full")
        expect(code == 0, f"plan compile @shop_full 退出码 {code}\n{out[-1500:]}")
        _cache["full"] = data
    return _cache["full"]  # type: ignore[return-value]


def suite_of(manifest: dict, sid: str) -> dict:
    for s in manifest.get("suites", []):
        if s.get("id") == sid:
            return s
    raise CheckFailed(f"清单中没有套 {sid}: {[s.get('id') for s in manifest.get('suites', [])]}")


def instance_ids(suite: dict) -> List[str]:
    return [c.get("instance_id") for c in suite.get("cases", [])]


def run_cached(key: str, args: List[str]) -> Run:
    if key not in _cache:
        _cache[key] = rodski(args)
    return _cache[key]  # type: ignore[return-value]


# ------------------------------------------------------------------ 检查项
def ps01() -> str:
    m = manifest_full()
    expect(m.get("schema") == MANIFEST_SCHEMA, f"schema: {m.get('schema')}")
    expect(m.get("plan_id") == "shop_full", f"plan_id: {m.get('plan_id')}")
    expect(m.get("max_parallel") == 2, f"max_parallel: {m.get('max_parallel')}")
    expect(m.get("implicit_suite") is False, f"implicit_suite: {m.get('implicit_suite')}")
    expect(str(m.get("rodski_version", "")).count(".") == 2, f"rodski_version: {m.get('rodski_version')}")
    ids = [s.get("id") for s in m.get("suites", [])]
    expect(ids == ["order", "special", "admin", "archive"], f"套顺序: {ids}")
    for sid in EXPECTED_SUITES:
        s = suite_of(m, sid)
        expect(s.get("execute") is True, f"{sid}.execute: {s.get('execute')}")
        expect(s.get("requires") == ["web"], f"{sid}.requires: {s.get('requires')}")
        expect(s.get("weight") == EXPECTED_WEIGHT[sid], f"{sid}.weight: {s.get('weight')} != {EXPECTED_WEIGHT[sid]}")
        for c in s.get("cases", []):
            expect(c.get("requires") == ["web"], f"{sid}/{c.get('instance_id')}.requires: {c.get('requires')}")
    archive = suite_of(m, "archive")
    expect(archive.get("execute") is False, f"archive.execute: {archive.get('execute')}")
    expect(archive.get("cases") == [], f"archive 不应有待执行用例: {archive.get('cases')}")
    expect(suite_of(m, "admin").get("tags") == ["后台"], f"admin.tags: {suite_of(m, 'admin').get('tags')}")
    return "schema / plan_id / max_parallel / 套顺序 / execute / requires / tags / weight 均符合"


def ps02() -> str:
    m = manifest_full()
    for sid, ids in EXPECTED_SUITES.items():
        got = instance_ids(suite_of(m, sid))
        expect(got == ids, f"{sid} 套内顺序 {got} != {ids}")
    first = suite_of(m, "order")["cases"][1]
    expect(first.get("case_file") == "order/create.xml" and first.get("case_id") == "PS_ORDER_1",
           f"数据驱动实例的 case_file/case_id: {first}")
    return "套内按发现顺序；PS_ORDER_1[r1]/[r2] 相邻且按行顺序"


def ps03() -> str:
    m = manifest_full()
    expect("PS_SPECIAL" in instance_ids(suite_of(m, "special")), "PS_SPECIAL 不在 special 套")
    expect("PS_SPECIAL" not in instance_ids(suite_of(m, "order")), "PS_SPECIAL 不应在 order 套")
    return "显式 <case> 优先于 <case_dir>"


def ps04() -> str:
    m = manifest_full()
    skipped = {(s.get("case_file"), s.get("case_id")): s.get("reason") for s in m.get("skipped", [])}
    expect(skipped.get(("common/extra.xml", "PS_EXTRA")) == "suite_execute_false", f"skipped: {m.get('skipped')}")
    return "PS_EXTRA → skipped(reason=suite_execute_false)"


def ps05() -> str:
    m = manifest_full()
    expect(any("common/login.xml" in w for w in m.get("warnings", [])), f"warnings: {m.get('warnings')}")
    proc = subprocess.run([sys.executable, "-c", RUN_SNIPPET, "plan", "compile", "@shop_full"], cwd=HERE,
                          text=True, capture_output=True, timeout=120)
    out = proc.stdout + proc.stderr
    expect("[WARN]" in out and "common/login.xml" in out, f"文本输出缺少 [WARN]:\n{out[-1500:]}")
    return "同一文件拆到两个套 → warnings + [WARN]"


def ps06() -> str:
    d1 = manifest_full().get("digest", "")
    expect(d1.startswith("sha256:") and len(d1) == len("sha256:") + 64, f"digest 格式: {d1}")
    _, again, _ = compile_json("shop_full")
    expect(again.get("digest") == d1, "两次编译 digest 不同")
    mod = module_copy()
    try:
        _, copied, out = compile_json("shop_full", module=mod)
        expect(copied.get("digest") == d1, f"模块换目录后 digest 改变（digest 不得含绝对路径）: {copied.get('digest')}\n{out[-800:]}")
        conn = sqlite3.connect(mod / "data" / "data.sqlite")
        conn.execute("UPDATE rs_field SET field_value='changed' WHERE table_name='LoginAPI' AND data_id='D001' "
                     "AND field_name='username'")
        conn.commit()
        conn.close()
        _, after_db, _ = compile_json("shop_full", module=mod)
        expect(after_db.get("digest") == d1, "data.sqlite 变化不应影响 digest")
        case = mod / "case" / "order" / "special.xml"
        case.write_text(case.read_text(encoding="utf-8").replace('data="4"', 'data="3"'), encoding="utf-8")
        _, after_case, _ = compile_json("shop_full", module=mod)
        expect(after_case.get("digest") not in ("", d1), "用例文件变化后 digest 未变")
    finally:
        drop_copy(mod)
    return "digest 稳定、与模块位置无关；改用例变化，改 data.sqlite 不变"


def ps07() -> str:
    code, m, out = compile_json("caps_mixed")
    expect(code == 0, f"caps_mixed 退出码 {code}\n{out[-1500:]}")
    want = {"mix": ["android", "web"], "ios": ["ios"], "desk": ["desktop"],
            "biz": ["android", "web"], "nested": ["android", "web"]}
    for sid, req in want.items():
        got = suite_of(m, sid).get("requires")
        expect(got == req, f"{sid}.requires: {got} != {req}")
    tags = suite_of(m, "desk").get("tags", [])
    expect("os:windows" in tags and "桌面" in tags, f"desk.tags: {tags}")
    return "Web+App+DB=[android,web]；iOS；desktop+os:windows；business_call / if 内步骤计入"


def ps08() -> str:
    code, m, out = compile_json("caps_cross")
    expect(code != 0, "android + ios 同套应编译失败")
    errs = json.dumps(m.get("errors", []), ensure_ascii=False)
    expect(m.get("schema") == MANIFEST_SCHEMA and "android" in errs and "ios" in errs,
           f"JSON errors 不符: {out[-1500:]}")
    code2, m2, out2 = compile_json("caps_cross", "--allow-cross-platform-plan")
    expect(code2 == 0, f"--allow-cross-platform-plan 应放行: {out2[-1500:]}")
    expect(suite_of(m2, "both").get("requires") == ["android", "ios", "web"], f"requires: {suite_of(m2, 'both').get('requires')}")
    return "跨平台套报错（JSON errors），--allow-cross-platform-plan 放行"


def ps09() -> str:
    code, m, out = compile_json("caps_unresolved")
    expect(code != 0, "Mobile.Platform 未配置应编译失败")
    expect("Mobile.Platform" in json.dumps(m.get("errors", []), ensure_ascii=False), f"错误未提示 Mobile.Platform:\n{out[-1500:]}")
    return "driver_type=mobile 且无 Mobile.Platform → 报错并提示"


BAD_PLANS = {
    "bad_mixed_top": """<test_plan id="bad_mixed_top" kind="suite">
    <suite id="a"><case file="order/special.xml" id="PS_SPECIAL"/></suite>
    <case file="order/create.xml" id="PS_ORDER_2"/>
</test_plan>""",
    "bad_dup_assign": """<test_plan id="bad_dup_assign" kind="suite">
    <suite id="a"><case_dir path="order"/></suite>
    <suite id="b"><case_dir path="order"/></suite>
</test_plan>""",
    "bad_default_execute": """<test_plan id="bad_default_execute" kind="suite" default_execute="是">
    <suite id="a"><case_dir path="order"/></suite>
</test_plan>""",
    "bad_dup_suite_id": """<test_plan id="bad_dup_suite_id" kind="suite">
    <suite id="a"><case_dir path="order"/></suite>
    <suite id="a"><case_dir path="admin"/></suite>
</test_plan>""",
    "bad_debug_suite": """<test_plan id="bad_debug_suite" kind="scenario_debug">
    <suite id="a"><case file="order/special.xml" id="PS_SPECIAL"/></suite>
</test_plan>""",
    "bad_load_parallel": """<test_plan id="bad_load_parallel" kind="load" max_parallel="2">
    <load_profile mode="api">
        <concurrency>1</concurrency>
        <duration_seconds>5</duration_seconds>
    </load_profile>
    <case file="common/login.xml" id="PS_LOGIN_API"/>
</test_plan>""",
}


def ps10() -> str:
    mod = module_copy()
    problems = []
    try:
        for pid, body in BAD_PLANS.items():
            (mod / "plan" / f"{pid}.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n' + body + "\n",
                                                     encoding="utf-8")
        for pid in BAD_PLANS:
            code, m, out = compile_json(pid, module=mod)
            if code == 0:
                problems.append(f"{pid}: plan compile 应失败")
            elif not m.get("errors"):
                problems.append(f"{pid}: --json 无 errors: {out[-400:]}")
            run = rodski(["run", f"@{pid}", "--headless"], module=mod, timeout=120)
            if run.code == 0:
                problems.append(f"{pid}: run 应失败")
            if run.result_xml_count:
                problems.append(f"{pid}: run 失败前不应产生 result.xml")
    finally:
        drop_copy(mod)
    expect(not problems, "\n".join(problems))
    return f"{len(BAD_PLANS)} 种结构错误：compile / run 均非 0 退出，run 不产生 result.xml"


def ps11() -> str:
    code, m, out = compile_json("shop_legacy")
    expect(code == 0, f"退出码 {code}\n{out[-1500:]}")
    expect(m.get("implicit_suite") is True, f"implicit_suite: {m.get('implicit_suite')}")
    ids = [s.get("id") for s in m.get("suites", [])]
    expect(ids == ["default"], f"套: {ids}")
    got = instance_ids(m["suites"][0])
    expect(got == LEGACY_CASES, f"default 套用例: {got}")
    return "不写 <suite> → 隐式套 default"


def ps12() -> str:
    run = run_cached("legacy", ["run", "@shop_legacy", "--headless"])
    st = statuses(run)
    expect(sorted(st) == sorted(LEGACY_CASES), f"用例集合: {sorted(st)}")
    expect(all(v == "PASS" for v in st.values()) and run.code == 0, f"状态: {st}\n{run.output[-1500:]}")
    with_suite = [cid for cid, a in run.results.items() if "suite_id" in a]
    expect(not with_suite, f"隐式套不应写 suite_id: {with_suite}")
    return "隐式套执行全部 PASS，结果不带 suite_id"


def ps13() -> str:
    run = run_cached("full_seq", ["run", "@shop_full", "--headless"])
    st = statuses(run)
    expect(sorted(st) == sorted(ALL_ACTIVE + ["PS_EXTRA"]), f"用例集合: {sorted(st)}")
    bad = {k: v for k, v in st.items() if k != "PS_EXTRA" and v != "PASS"}
    expect(not bad and run.code == 0, f"未通过: {bad}\n{run.output[-1500:]}")
    expect(st.get("PS_EXTRA") == "SKIP", f"PS_EXTRA: {st.get('PS_EXTRA')}")
    for sid, ids in EXPECTED_SUITES.items():
        for cid in ids:
            expect(run.results[cid].get("suite_id") == sid, f"{cid}.suite_id: {run.results[cid].get('suite_id')}")
    expect(run.results["PS_EXTRA"].get("suite_id") == "archive", "PS_EXTRA.suite_id 应为 archive")
    s = run.summary
    expect(s.get("plan_id") == "shop_full", f"summary.plan_id: {s.get('plan_id')}")
    expect(s.get("suites") == "order,special,admin,archive", f"summary.suites: {s.get('suites')}")
    expect(s.get("digest") == manifest_full().get("digest"), f"summary.digest: {s.get('digest')}")
    return "顺序执行：启用套全部 PASS、停用套 SKIP；结果带 suite_id；summary 带 plan_id / suites / digest"


def ps14() -> str:
    one = rodski(["run", "@shop_full", "--suite", "special", "--headless"])
    expect(sorted(statuses(one)) == ["PS_SPECIAL"], f"--suite special: {statuses(one)}\n{one.output[-1500:]}")
    expect(one.code == 0 and one.results["PS_SPECIAL"].get("status") == "PASS", f"--suite special 未通过")
    expect(one.summary.get("suites") == "special", f"summary.suites: {one.summary.get('suites')}")
    two = rodski(["run", "@shop_full", "--suite", "order,admin", "--headless"])
    want = sorted(EXPECTED_SUITES["order"] + EXPECTED_SUITES["admin"])
    expect(sorted(statuses(two)) == want, f"--suite order,admin: {sorted(statuses(two))}")
    expect(two.code == 0 and all(v == "PASS" for v in statuses(two).values()), f"未全部通过: {statuses(two)}")
    return "--suite 只执行指定套，不出现其他套的 SKIP"


def ps15() -> str:
    cases = [
        (["run", "case", "--suite", "order", "--headless"], "无 @plan"),
        (["run", "@shop_full", "--suite", "nope", "--headless"], "未知套"),
        (["run", "@shop_full", "--suite", "archive", "--headless"], "停用套"),
    ]
    problems = []
    for args, desc in cases:
        run = rodski(args, timeout=120)
        if run.code == 0:
            problems.append(f"{desc}: 应非 0 退出")
        if run.result_xml_count:
            problems.append(f"{desc}: 不应产生 result.xml")
    expect(not problems, "\n".join(problems))
    return "--suite 无 @plan / 未知套 / 停用套 均在副作用前报错"


def ps16() -> str:
    bad = rodski(["run", "@shop_full", "--suite", "special", "--expect-digest", "sha256:" + "0" * 64, "--headless"],
                 timeout=120)
    expect(bad.code != 0 and not bad.result_xml_count, f"错误 digest 应在副作用前失败: code={bad.code}")
    expect("digest" in bad.output, f"输出未提示 digest:\n{bad.output[-800:]}")
    ok = rodski(["run", "@shop_full", "--suite", "special", "--expect-digest", manifest_full()["digest"], "--headless"])
    expect(ok.code == 0 and statuses(ok) == {"PS_SPECIAL": "PASS"}, f"正确 digest 应执行: {statuses(ok)}\n{ok.output[-800:]}")
    return "digest 不一致报错且无副作用；一致时正常执行"


def check_in_suite_order(run: Run) -> None:
    for sid, ids in EXPECTED_SUITES.items():
        starts = [ts(run.results[cid]["start_time"]) for cid in ids]
        ends = [ts(run.results[cid]["end_time"]) for cid in ids]
        for i in range(1, len(ids)):
            expect(ends[i - 1] <= starts[i], f"{sid} 套内顺序错误：{ids[i - 1]} 结束晚于 {ids[i]} 开始")


def ps17() -> str:
    seq = run_cached("full_seq", ["run", "@shop_full", "--headless"])
    run = run_cached("wide_w3", ["run", "@shop_wide", "--workers", "3", "--headless"])
    st = statuses(run)
    expect(sorted(st) == sorted(ALL_ACTIVE), f"用例集合: {sorted(st)}\n{run.output[-1500:]}")
    seq_st = {k: v for k, v in statuses(seq).items() if k != "PS_EXTRA"}
    expect(st == seq_st and run.code == 0, f"并发结果与顺序执行不一致: {st} vs {seq_st}")
    expect(run.order == ALL_ACTIVE, f"合并顺序应按套顺序: {run.order}")
    win = suite_windows(run)
    expect(sorted(win) == sorted(EXPECTED_SUITES), f"套区间: {win}")
    expect(peak_concurrency(win) == 3, f"3 个套应同时执行，峰值 {peak_concurrency(win)}: {win}")
    check_in_suite_order(run)
    return "3 个套同时执行；套内顺序保持；用例集合、状态与顺序执行一致"


def ps18() -> str:
    run = run_cached("full_w3", ["run", "@shop_full", "--workers", "3", "--headless"])
    st = statuses(run)
    expect(sorted(st) == sorted(ALL_ACTIVE + ["PS_EXTRA"]), f"用例集合: {sorted(st)}\n{run.output[-1500:]}")
    expect(run.code == 0 and st.get("PS_EXTRA") == "SKIP", f"状态: {st}")
    win = suite_windows(run)
    peak = peak_concurrency(win)
    expect(peak == 2, f"max_parallel=2 时峰值应为 2，实际 {peak}: {win}")
    check_in_suite_order(run)
    return "--workers 3 + max_parallel=2 → 同时最多 2 个套"


def ps19() -> str:
    run = run_cached("wide_w3", ["run", "@shop_wide", "--workers", "3", "--headless"])
    r1, r2 = run.results.get("PS_ORDER_1[r1]", {}), run.results.get("PS_ORDER_1[r2]", {})
    expect(r1.get("suite_id") == "order" and r2.get("suite_id") == "order", f"实例 suite_id: {r1.get('suite_id')}, {r2.get('suite_id')}")
    expect(r1.get("status") == "PASS" and r2.get("status") == "PASS", "数据驱动实例未通过")
    expect(ts(r1["end_time"]) <= ts(r2["start_time"]), "r1 应先于 r2 执行完")
    return "数据驱动实例跟随模板用例所在套、按行顺序执行"


def ps20() -> str:
    run = rodski(["run", "@shop_legacy", "--workers", "2", "--headless"])
    expect("未生效" not in run.output, f"计划只选中 Web/接口/DB 用例，--workers 不应因 mixed/ 的模型失效:\n{run.output[-1500:]}")
    st = statuses(run)
    expect(sorted(st) == sorted(LEGACY_CASES) and all(v == "PASS" for v in st.values()), f"状态: {st}")
    return "计划模式下 --workers 只看选中用例"


def ps21() -> str:
    proc = subprocess.run([sys.executable, "-c", RUN_SNIPPET, "plan", "compile", "@shop_full"], cwd=HERE,
                          text=True, capture_output=True, timeout=120)
    out = proc.stdout + proc.stderr
    expect(proc.returncode == 0, f"退出码 {proc.returncode}\n{out[-1500:]}")
    for token in ("order", "special", "admin", "archive", "web", "后台", "max_parallel"):
        expect(token in out, f"文本摘要缺少 {token}:\n{out[-1500:]}")
    return "文本摘要列出套 / 能力 / 标签 / 并发上限"


CHECKS: List[Tuple[str, str, Callable[[], str]]] = [
    ("PS-01", "编译清单", ps01),
    ("PS-02", "套内顺序", ps02),
    ("PS-03", "归属裁决", ps03),
    ("PS-04", "停用套", ps04),
    ("PS-05", "同文件拆套 WARN", ps05),
    ("PS-06", "digest", ps06),
    ("PS-07", "混合能力", ps07),
    ("PS-08", "跨平台套", ps08),
    ("PS-09", "mobile 未解析", ps09),
    ("PS-10", "结构错误", ps10),
    ("PS-11", "隐式套编译", ps11),
    ("PS-12", "隐式套执行不变", ps12),
    ("PS-13", "顺序执行带套", ps13),
    ("PS-14", "--suite", ps14),
    ("PS-15", "--suite 报错", ps15),
    ("PS-16", "--expect-digest", ps16),
    ("PS-17", "--workers 按套并发", ps17),
    ("PS-18", "max_parallel", ps18),
    ("PS-19", "数据驱动不拆分", ps19),
    ("PS-20", "计划模式 workers 只看选中用例", ps20),
    ("PS-21", "文本摘要", ps21),
]


# ------------------------------------------------------------------ 站点
def demosite_up() -> bool:
    try:
        urllib.request.urlopen(DEMOSITE_URL, timeout=2)
        return True
    except Exception:
        return False


def main(argv: List[str]) -> int:
    started: Optional[subprocess.Popen] = None
    if not demosite_up():
        started = subprocess.Popen([sys.executable, str(DEMOSITE_APP)], cwd=DEMOSITE_APP.parent,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        for _ in range(60):
            if demosite_up():
                break
            time.sleep(0.5)
    subprocess.run([sys.executable, str(HERE / "data" / "init_data.py")], check=True)
    selected = [c for c in CHECKS if not argv or c[0] in argv]
    passed = failed = 0
    try:
        for code, desc, fn in selected:
            try:
                detail = fn()
                passed += 1
                print(f"PASS\t{code}\t{desc}\t{detail}", flush=True)
            except CheckFailed as e:
                failed += 1
                print(f"FAIL\t{code}\t{desc}\t{e}", flush=True)
            except Exception as e:  # 脚本自身异常也计为失败
                failed += 1
                print(f"FAIL\t{code}\t{desc}\t{type(e).__name__}: {e}", flush=True)
    finally:
        if started is not None:
            started.terminate()
        subprocess.run([sys.executable, str(HERE / "data" / "init_data.py")], capture_output=True)
    print(f"汇总: PASS={passed} FAIL={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
