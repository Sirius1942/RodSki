#!/usr/bin/env python3
"""demosite/data_driven 验收脚本：计划级数据驱动（REQ-013 / CORE §7.8）。

用法（仓库根目录）:
    python3 rodski-demo/demosite/data_driven/run_acceptance.py            # 全部
    python3 rodski-demo/demosite/data_driven/run_acceptance.py DD-12      # 按编号

前置:
    - 共享站点 http://localhost:8000（_sites/demosite）。未运行时脚本自行启动，结束时只停自己启动的进程。
    - 每次执行前重建 data/data.sqlite 与 data/orders.db（data/init_data.py）。

判定:
    每项都真实执行 `rodski ...`（包入口 rodski.rodski_cli），读取本次新生成的 result/<run>/result.xml
    与 execution.log / 命令输出。会修改 data.sqlite / plan 的检查（DD-12 / DD-14 / DD-16）在临时目录中的
    模块副本上执行，不改动仓库文件。
退出码: FAIL=0 时为 0，否则为 1。最后一行: 汇总: PASS=x FAIL=y
"""
from __future__ import annotations

import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
DEMOSITE_URL = "http://localhost:8000/"
DEMOSITE_APP = REPO / "rodski-demo" / "_sites" / "demosite" / "app.py"
RUN_SNIPPET = ("import sys; from rodski.rodski_cli import main; "
               "sys.argv=['rodski']+sys.argv[1:]; sys.exit(main())")
ALL_INSTANCES = [
    "DD_FORM[alice]", "DD_FORM[bob]", "DD_FORM[base]", "DD_FORM[carol]",
    "DD_TWICE[both]", "DD_TWICE[second]", "DD_LOOP[x]",
    "DD_API[ok]", "DD_API[bad]", "DD_STATE[s1]", "DD_STATE[s2]",
]


# ------------------------------------------------------------------ 执行与结果读取
@dataclass
class Run:
    code: int
    output: str
    results: Dict[str, Dict[str, str]]   # case_id -> result 属性
    log: str


def rodski(args: List[str], module: Path = HERE, timeout: int = 600) -> Run:
    result_root = module / "result"
    before = set(p.name for p in result_root.iterdir()) if result_root.is_dir() else set()
    proc = subprocess.run([sys.executable, "-c", RUN_SNIPPET, *args], cwd=module, text=True,
                          capture_output=True, timeout=timeout)
    output = (proc.stdout or "") + (proc.stderr or "")
    results: Dict[str, Dict[str, str]] = {}
    log = ""
    if result_root.is_dir():
        new_dirs = sorted(p for p in result_root.iterdir() if p.is_dir() and p.name not in before)
        for run_dir in new_dirs:
            xml_path = run_dir / "result.xml"
            if xml_path.is_file():
                for elem in ET.parse(xml_path).getroot().iter("result"):
                    results[elem.get("case_id", "")] = dict(elem.attrib)
            log_path = run_dir / "execution.log"
            if log_path.is_file():
                log += log_path.read_text(encoding="utf-8", errors="replace")
    return Run(proc.returncode, output, results, log)


def statuses(run: Run) -> Dict[str, str]:
    return {cid: attrs.get("status", "") for cid, attrs in run.results.items()}


class CheckFailed(Exception):
    pass


def expect(cond: bool, msg: str) -> None:
    if not cond:
        raise CheckFailed(msg)


# ------------------------------------------------------------------ 共享运行（多个检查复用）
_cache: Dict[str, Run] = {}


def suite_run() -> Run:
    if "suite" not in _cache:
        _cache["suite"] = rodski(["run", "@data_driven_suite", "--headless"])
    return _cache["suite"]


# ------------------------------------------------------------------ 检查项
def dd01() -> str:
    run = suite_run()
    st = statuses(run)
    expect(sorted(st) == sorted(ALL_INSTANCES), f"实例集合不符: {sorted(st)}")
    bad = {k: v for k, v in st.items() if v != "PASS"}
    expect(not bad, f"存在未通过实例: {bad}\n{run.output[-1500:]}")
    expect(run.code == 0, f"退出码 {run.code}")
    alice = run.results["DD_FORM[alice]"]
    expect(alice.get("driver") == "FormMatrix", f"driver 属性: {alice.get('driver')}")
    expect(alice.get("data_id") == "alice", f"data_id 属性: {alice.get('data_id')}")
    expect(alice.get("template_case_id") == "DD_FORM", f"template_case_id: {alice.get('template_case_id')}")
    expect(alice.get("instance_title") == "普通用户 alice（role=user）", f"instance_title: {alice.get('instance_title')}")
    expect("TestForm.T001=T101" in alice.get("replacements", ""), f"replacements: {alice.get('replacements')}")
    return "11 个实例全部 PASS，结果带 driver / data_id / template_case_id / instance_title / replacements"


def dd02() -> str:
    run = suite_run()
    base = run.results.get("DD_FORM[base]", {})
    expect(base.get("status") == "PASS", "DD_FORM[base] 未通过")
    expect(base.get("replacements", "") == "", f"BLANK 行不应有替换: {base.get('replacements')}")
    expect("TestForm: T001 → T101（FormMatrix[alice]）" in run.log, "日志缺少 alice 的替换标注")
    expect("LoginForm: L001 →" not in run.log, "驱动表未列出的 LoginForm.L001 被替换了")
    second = run.results.get("DD_TWICE[second]", {})
    expect(second.get("replacements", "").count("=") == 2, f"只替换第二次提交: {second.get('replacements')}")
    return "未列出的步骤与 BLANK 单元格使用基础 DataID；日志标注替换"


def dd03() -> str:
    run = rodski(["run", "case/form_flow.xml", "--case-id", "DD_FORM", "--headless"])
    st = statuses(run)
    expect(st == {"DD_FORM": "PASS"}, f"单独运行结果: {st}\n{run.output[-1500:]}")
    expect("driver" not in run.results["DD_FORM"], "单独运行不应带 driver 属性")
    expect("数据驱动替换" not in run.log, "单独运行不应发生替换")
    return "不经计划只执行 1 次，全部使用基础 DataID"


def dd04() -> str:
    run = rodski(["run", "@failure_isolation_suite", "--headless"])
    st = statuses(run)
    want = {"DD_FORM[first]": "PASS", "DD_FORM[wrong]": "FAIL", "DD_FORM[third]": "PASS", "DD_API": "PASS"}
    expect(st == want, f"结果: {st}")
    expect(run.code != 0, "有实例失败时退出码应非 0")
    return "第 2 个实例 FAIL，第 1、3 个实例与普通用例 PASS，退出码非 0"


def dd05() -> str:
    run = suite_run()
    st = statuses(run)
    expect(st.get("DD_STATE[s1]") == "PASS" and st.get("DD_STATE[s2]") == "PASS", f"DD_STATE: {st}")
    expect("R_LEAK" not in run.log.split("DD_STATE[s2]", 1)[-1].split("执行用例", 1)[0], "第 2 个实例执行了泄漏分支")
    return "第 2 个实例看不到第 1 个实例的 Return 历史与 set 变量"


def dd06() -> str:
    st = statuses(suite_run())
    expect(st.get("DD_TWICE[both]") == "PASS" and st.get("DD_TWICE[second]") == "PASS", f"DD_TWICE: {st}")
    return "同一模型 T001 / T002 两列分别替换"


def dd07() -> str:
    st = statuses(suite_run())
    expect(st.get("DD_API[ok]") == "PASS" and st.get("DD_API[bad]") == "PASS", f"DD_API: {st}")
    return "send / verify / DB 按驱动表替换"


def dd11() -> str:
    run = rodski(["run", "@data_driven_suite", "--data-id", "alice,DD_API[bad]", "--headless"])
    st = statuses(run)
    expect(st == {"DD_FORM[alice]": "PASS", "DD_API[bad]": "PASS"}, f"--data-id 结果: {st}\n{run.output[-800:]}")
    run2 = rodski(["run", "@failure_isolation_suite", "--exclude-data-id", "wrong", "--headless"])
    st2 = statuses(run2)
    expect(st2 == {"DD_FORM[first]": "PASS", "DD_FORM[third]": "PASS", "DD_API": "PASS"}, f"--exclude-data-id 结果: {st2}")
    expect(run2.code == 0, f"退出码 {run2.code}")
    return "--data-id（DataID 与 用例ID[DataID] 两种写法）与 --exclude-data-id 只过滤数据驱动实例，可与 @plan 同用"


def dd13() -> str:
    run = suite_run()
    expect(statuses(run).get("DD_LOOP[x]") == "PASS", "DD_LOOP[x] 未通过")
    expect(run.results["DD_LOOP[x]"].get("replacements") == "TestForm.T001=T201; TestForm_verify.V001=V201",
           f"replacements: {run.results['DD_LOOP[x]'].get('replacements')}")
    return "字面 T001 被替换为 T201，loop 中 T00${i} 第 1 轮仍读 T001（V001 断言通过）"


def dd17() -> str:
    run = suite_run()
    carol = run.results.get("DD_FORM[carol]", {})
    expect(carol.get("status") == "PASS", "缺备注不应阻断执行")
    expect(carol.get("instance_title") == "访客 carol（被引用数据行未写备注 → WARN）", f"instance_title: {carol.get('instance_title')}")
    for ref in ("TestForm.T103", "TestForm_verify.V103"):
        expect(f"{ref} 被 FormMatrix[carol] 引用，未写备注" in run.output + run.log, f"缺少 {ref} 的备注 WARN")
    expect("TestForm.T101 被" not in run.output + run.log, "已写备注的行不应 WARN")
    return "实例标题取驱动表行备注；被引用数据行缺备注只 WARN，用例照常 PASS"


# ---------------- 临时副本中的负向 / CLI 检查
def temp_module() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="rodski_dd_"))
    dst = tmp / "product" / "demo" / "data_driven"
    shutil.copytree(HERE, dst, ignore=shutil.ignore_patterns("result", "__pycache__"))
    return dst


def add_driver(db: Path, name: str, case_uid: str, remark: str, columns: List[str],
               rows: List[Tuple[str, List[str]]]) -> None:
    conn = sqlite3.connect(db)
    conn.execute("INSERT INTO rs_datatable(table_name,model_name,table_kind,row_mode,remark) "
                 "VALUES(?,?,'driver','standard',?)", (name, case_uid, remark))
    conn.executemany("INSERT INTO rs_datatable_field(table_name,field_name,field_order) VALUES(?,?,?)",
                     [(name, c, i) for i, c in enumerate(columns)])
    for data_id, cells in rows:
        conn.execute("INSERT INTO rs_row(table_name,data_id,remark) VALUES(?,?,'')", (name, data_id))
        conn.executemany("INSERT INTO rs_field(table_name,data_id,field_name,field_value) VALUES(?,?,?,?)",
                         [(name, data_id, c, v) for c, v in zip(columns, cells)])
    conn.commit()
    conn.close()


def write_plan(module: Path, plan_id: str, case_xml: str, kind: str = "suite", debug: str = "") -> None:
    (module / "plan" / f"{plan_id}.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<test_plan id="{plan_id}" kind="{kind}">{debug}{case_xml}</test_plan>\n',
        encoding="utf-8")


NEGATIVES = [
    # (说明, 驱动表定义或 None, 计划 <case> 片段, 计划 kind, 期望错误关键字)
    ("驱动表不存在", None, '<case file="form_flow.xml" id="DD_FORM" data_driven="NoSuchMatrix"/>', "suite",
     ["NoSuchMatrix", "数据驱动表不存在"]),
    ("引用的是模型数据表", None, '<case file="form_flow.xml" id="DD_FORM" data_driven="TestForm"/>', "suite",
     ["TestForm", "不是数据驱动表"]),
    ("0 行", ("EmptyMatrix", "form_flow.xml::DD_FORM", "空表", ["TestForm.T001"], []),
     '<case file="form_flow.xml" id="DD_FORM" data_driven="EmptyMatrix"/>', "suite", ["EmptyMatrix", "没有任何行"]),
    ("列名不是 表名.DataID", ("BadColMatrix", "form_flow.xml::DD_FORM", "列名错误", ["TestForm"], [("r1", ["T101"])]),
     '<case file="form_flow.xml" id="DD_FORM" data_driven="BadColMatrix"/>', "suite", ["TestForm", "列名"]),
    ("列名含动态 DataID", ("DynColMatrix", "form_flow.xml::DD_LOOP", "动态列", ["TestForm.T00${i}"], [("r1", ["T101"])]),
     '<case file="form_flow.xml" id="DD_LOOP" data_driven="DynColMatrix"/>', "suite", ["T00${i}", "列名"]),
    ("列的表不存在", ("NoTableMatrix", "form_flow.xml::DD_FORM", "表不存在", ["NoTable.T001"], [("r1", ["T101"])]),
     '<case file="form_flow.xml" id="DD_FORM" data_driven="NoTableMatrix"/>', "suite", ["NoTable", "不存在"]),
    ("基础 DataID 未被用例引用", ("UnrefMatrix", "form_flow.xml::DD_FORM", "未引用", ["TestForm.T002"], [("r1", ["T101"])]),
     '<case file="form_flow.xml" id="DD_FORM" data_driven="UnrefMatrix"/>', "suite", ["TestForm.T002", "未被用例"]),
    ("单元格 DataID 不存在", ("MissMatrix", "form_flow.xml::DD_FORM", "单元格不存在", ["TestForm.T001"], [("r1", ["T999"])]),
     '<case file="form_flow.xml" id="DD_FORM" data_driven="MissMatrix"/>', "suite", ["T999", "不存在"]),
    ("单元格写变量", ("VarMatrix", "form_flow.xml::DD_FORM", "单元格变量", ["TestForm.T001"], [("r1", ["${x}"])]),
     '<case file="form_flow.xml" id="DD_FORM" data_driven="VarMatrix"/>', "suite", ["${x}", "只能是 DataID"]),
    ("驱动表与模型同名", ("NavMenu_verify", "form_flow.xml::DD_FORM", "与模型同名", ["TestForm.T001"], [("r1", ["T101"])]),
     '<case file="form_flow.xml" id="DD_FORM" data_driven="NavMenu_verify"/>', "suite", ["NavMenu_verify", "同名"]),
    ("表备注为空", ("NoRemarkMatrix", "form_flow.xml::DD_FORM", "", ["TestForm.T001"], [("r1", ["T101"])]),
     '<case file="form_flow.xml" id="DD_FORM" data_driven="NoRemarkMatrix"/>', "suite", ["NoRemarkMatrix", "备注"]),
    ("DD-16 挂错用例", None, '<case file="form_flow.xml" id="DD_TWICE" data_driven="FormMatrix"/>', "suite",
     ["FormMatrix", "form_flow.xml::DD_FORM", "绑定"]),
    ("调试计划使用 data_driven", None,
     '<case file="form_flow.xml" id="DD_FORM" data_driven="FormMatrix"/>', "scenario_debug", ["data_driven", "suite"]),
]


def dd12() -> str:
    module = temp_module()
    db = module / "data" / "data.sqlite"
    problems = []
    try:
        for i, (desc, driver, case_xml, kind, keywords) in enumerate(NEGATIVES):
            if driver:
                add_driver(db, *driver)
            plan_id = f"neg{i:02d}_suite"
            write_plan(module, plan_id, case_xml, kind=kind,
                       debug='<debug prepare="none"/>' if kind != "suite" else "")
            args = ["run", f"@{plan_id}", "--headless"] + (["--debug"] if kind != "suite" else [])
            run = rodski(args, module=module, timeout=120)
            text = run.output + run.log
            missing = [k for k in keywords if k not in text]
            if run.code == 0 or missing or run.results or "执行用例" in text:
                problems.append(f"[{desc}] code={run.code} 缺少关键字={missing} results={list(run.results)}\n"
                                f"    输出尾部: {run.output.strip()[-300:]}")
    finally:
        shutil.rmtree(module.parents[2], ignore_errors=True)
    expect(not problems, "\n".join(problems))
    return f"{len(NEGATIVES)} 种错误配置均在执行任何用例前报错（含 DD-13 动态列、DD-16 挂错表）"


def dd14() -> str:
    module = temp_module()
    mod = str(module)
    problems = []

    def cli(args: List[str], ok: bool, *keywords: str) -> str:
        run = rodski(args, module=module, timeout=120)
        text = run.output
        if (run.code == 0) != ok or any(k not in text for k in keywords):
            problems.append(f"{' '.join(args)} → code={run.code}，期望{'成功' if ok else '失败'}，关键字 {keywords}\n"
                            f"    {text.strip()[-300:]}")
        return text

    try:
        cols = "TestForm.T001,TestForm_verify.V001"
        cli(["data", "create-driver", mod, "NewMatrix", "--case", "form_flow.xml::DD_FORM", "--remark", "",
             "--columns", cols], False, "备注")
        cli(["data", "create-driver", mod, "NewMatrix", "--case", "form_flow.xml::NOPE", "--remark", "x",
             "--columns", cols], False, "NOPE")
        cli(["data", "create-driver", mod, "NewMatrix", "--case", "form_flow.xml::DD_FORM", "--remark", "x",
             "--columns", "TestForm.T009"], False, "未被用例")
        cli(["data", "create-driver", mod, "NavMenu", "--case", "form_flow.xml::DD_FORM", "--remark", "x",
             "--columns", cols], False, "NavMenu")
        cli(["data", "create-driver", mod, "NewMatrix", "--case", "form_flow.xml::DD_FORM",
             "--remark", "CLI 新建；计划 cli_suite", "--columns", cols], True)
        cli(["data", "add-row", mod, "NewMatrix", "r1", "TestForm.T001=T101", "TestForm_verify.V001=V101",
             "--remark", "CLI 实例 r1"], True)
        cli(["data", "add-row", mod, "NewMatrix", "r2", "TestForm.T001=T999", "TestForm_verify.V001=V101"],
            False, "T999")
        cli(["data", "add-field", mod, "NewMatrix", "LoginForm.L001"], True)
        cli(["data", "set", mod, "TestForm", "T103", "--remark", "data_driven_suite / FormMatrix[carol]：访客"], True)
        out = cli(["data", "show", mod, "TestForm", "T103"], True, "data_driven_suite / FormMatrix[carol]：访客")
        out = cli(["data", "show", mod, "NewMatrix", "r1"], True, "CLI 实例 r1", "T101")
        cli(["data", "list", mod], True, "NewMatrix", "driver", "form_flow.xml::DD_FORM")
        cli(["data", "validate", mod], True)
        # 旧版 data.sqlite（table_kind CHECK 只允许 data/verify）首次写入 driver 表时自动迁移
        db = module / "data" / "data.sqlite"
        conn = sqlite3.connect(db)
        conn.executescript("""
            DELETE FROM rs_field WHERE table_name IN (SELECT table_name FROM rs_datatable WHERE table_kind='driver');
            DELETE FROM rs_row WHERE table_name IN (SELECT table_name FROM rs_datatable WHERE table_kind='driver');
            DELETE FROM rs_datatable_field WHERE table_name IN (SELECT table_name FROM rs_datatable WHERE table_kind='driver');
            DELETE FROM rs_datatable WHERE table_kind='driver';
            PRAGMA foreign_keys=OFF;
            CREATE TABLE rs_datatable_old (
                table_name TEXT PRIMARY KEY, model_name TEXT NOT NULL,
                table_kind TEXT NOT NULL CHECK (table_kind IN ('data', 'verify')),
                row_mode TEXT NOT NULL CHECK (row_mode IN ('standard', 'db_query', 'db_sql')),
                remark TEXT DEFAULT '', updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
            INSERT INTO rs_datatable_old SELECT * FROM rs_datatable;
            DROP TABLE rs_datatable;
            ALTER TABLE rs_datatable_old RENAME TO rs_datatable;
        """)
        conn.commit()
        conn.close()
        cli(["run", "case/form_flow.xml", "--case-id", "DD_FORM", "--headless"], True)
        cli(["data", "create-driver", mod, "MigMatrix", "--case", "form_flow.xml::DD_FORM",
             "--remark", "迁移后新建", "--columns", cols], True, "迁移")
        ddl = sqlite3.connect(db).execute("SELECT sql FROM sqlite_master WHERE name='rs_datatable'").fetchone()[0]
        if "'driver'" not in ddl:
            problems.append(f"迁移后 CHECK 未包含 driver: {ddl}")
        if not (module / "data" / "data.sqlite.bak").is_file():
            problems.append("迁移未保留 data.sqlite.bak")
        cli(["data", "validate", mod], False, "MigMatrix", "没有任何行")
        cli(["data", "add-row", mod, "MigMatrix", "m1", "TestForm.T001=T101", "TestForm_verify.V001=V101",
             "--remark", "迁移后实例"], True)
        cli(["data", "validate", mod], True, "数据驱动表校验通过")
    finally:
        shutil.rmtree(module.parents[2], ignore_errors=True)
    expect(not problems, "\n".join(problems))
    return "create-driver / add-row / add-field / set --remark / show / list / validate 可用；旧库自动迁移并保留 .bak"


CHECKS: List[Tuple[str, str, Callable[[], str]]] = [
    ("DD-01", "基本展开与结果字段", dd01),
    ("DD-02", "部分替换 / BLANK", dd02),
    ("DD-03", "用例单独运行", dd03),
    ("DD-04", "失败隔离", dd04),
    ("DD-05", "Return / set 隔离", dd05),
    ("DD-06", "同表多 DataID", dd06),
    ("DD-07", "接口 + DB", dd07),
    ("DD-11", "实例过滤", dd11),
    ("DD-12", "静态校验（含 DD-13 / DD-16 负向）", dd12),
    ("DD-13", "动态 DataID 不替换", dd13),
    ("DD-14", "数据命令与旧库迁移", dd14),
    ("DD-17", "备注", dd17),
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
        # 恢复被运行改写的跟踪产物
        subprocess.run([sys.executable, str(HERE / "data" / "init_data.py")], capture_output=True)
    print(f"汇总: PASS={passed} FAIL={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
