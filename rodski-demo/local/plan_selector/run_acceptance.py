#!/usr/bin/env python3
"""local/plan_selector —— 执行范围选择验收（F081 / F091 / F092 / F093 / F094）。

用法（仓库根目录）:
    python3 rodski-demo/local/plan_selector/run_acceptance.py            # 全部检查项
    python3 rodski-demo/local/plan_selector/run_acceptance.py P01 P13    # 指定编号
    python3 rodski-demo/local/plan_selector/run_acceptance.py --strict   # KNOWN 也按失败计（退出码 1）

做什么:
  每个检查项都**真实执行** `rodski run`（用例步骤只有 run fun/mark.py，不需要浏览器与外部服务），
  通过环境变量 RODSKI_PS_MARKER 收集执行轨迹（精确到 scenario 内第几步），
  再与 result.xml 中 PASS/FAIL 的用例集合交叉核对，断言"实际执行集合"与文档描述一致。
  会改写 plan/ 的检查（rodski plan 子命令、默认计划解析、调试计划矩阵）先把模块复制到临时目录再做。

判定口径: 用例与期望按文档描述的正确行为编写；框架行为与文档不符的项登记在 KNOWN 表中，
输出 KNOWN（不计入失败、不迁就框架）；KNOWN 项若意外通过会提示"可能已修复"。
退出码: 0 = 无意外失败（PASS/KNOWN）；1 = 存在 FAIL（--strict 时 KNOWN 也计为失败）。
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Set

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
CLI = [sys.executable, str(REPO / "rodski" / "cli_main.py")]
PLAN_XSD = REPO / "rodski" / "schemas" / "plan.xsd"

# ---------------------------------------------------------------- 期望集合的积木
CHK1_S01 = ["CHK_001/S01/1", "CHK_001/S01/2", "CHK_001/S01/3"]
CHK1_WRAP = ["CHK_001/pre", "CHK_001/bare", "CHK_001/post"]          # 用例被执行时 pre/裸步骤/post 总会执行
CHK1_ALL = CHK1_WRAP + CHK1_S01 + ["CHK_001/S02/1", "CHK_001/S03/1"]
CHK2_ALL = ["CHK_002/S01/1", "CHK_002/S02/1"]
CAT_ALL = ["CAT_001", "CAT_002", "CAT_003"]
FULL = CAT_ALL + ["RPT_001"] + CHK1_ALL + CHK2_ALL                       # CHK_003 execute=否，永不执行

# ---------------------------------------------------------------- KNOWN 缺陷登记
_SEL = ("selector 模式下（--tag/--tags/--priority/--exclude-tag 任一生效）只为带 scenario 的用例生成选择项，"
        "不含 scenario 的用例一律 SKIP(plan_not_selected)（ski_executor.py:1047-1049 + test_plan_selection.py:compile_from_selector）")
KNOWN: Dict[str, str] = {
    "P02": "用例级 tags 属性被忽略（case_parser.py:118 只取 <cases tags>）；且 --tag 先按文件级 tags 做用例级过滤"
           "（ski_executor.py:1312-1319），scenario 的 tag 在此之前就被丢掉 → --tags smoke 0 条执行；" + _SEL,
    "P03": "--priority 多值只取第一个参与 scenario 选择（ski_executor.py:648 / run.py:903 priority_str=raw_priority[0]）；" + _SEL,
    "P05": _SEL + "；用例级 tags=slow 也未参与排除（case_parser.py:118）",
    "P11": "无 case 路径时 run.py:590-603 总是解析默认计划 project_full，再与 selector 判冲突（SKI703）；"
           "模块无默认计划时报“未找到默认测试计划”，GUIDE §10.5 的 `rodski run --group negative` 写法不可用",
    "P21": "plan add-scenario 只写 <case id>（无 file，CLI 也无 file 参数，plan.py:185 _find_or_create_case_node），"
           "多用例文件模块中生成的计划校验报 SKI207、执行报错",
    "P22": "plan create --from-tag 生成的 <case> 不带 file（plan.py:542），多用例文件模块中计划校验报 SKI207；"
           "且未包含用例级 tags=smoke 的 CAT_001",
    "P28": "plan debug-scenario 生成的 <case> 不带 file（CLI 无 file 参数，plan.py:746），多用例文件模块中 run @plan --debug 报 SKI207",
    "P29": "plan debug-step 生成的 <case> 不带 file（CLI 无 file 参数，plan.py:764），多用例文件模块中 run @plan --debug 报 SKI207",
    "P33": "prepare=none 时 _execute_debug_case 跳过 _run_steps，直接 _execute_step_list → _execute_step_item 引用未初始化的 "
           "self._phase_runtime_seq（ski_executor.py:2000）→ AttributeError，用例 FAIL",
}


# ---------------------------------------------------------------- 运行封装
class Run:
    def __init__(self, proc: subprocess.CompletedProcess, run_dir: Optional[Path], marks: List[str]):
        self.code = proc.returncode
        self.out = (proc.stdout or "") + (proc.stderr or "")
        self.run_dir = run_dir
        self.marks = marks

    def results(self) -> Dict[str, str]:
        """{case_id: status}"""
        if not self.run_dir or not (self.run_dir / "result.xml").is_file():
            return {}
        root = ET.parse(self.run_dir / "result.xml").getroot()
        return {r.get("case_id", ""): r.get("status", "") for r in root.iter("result")}

    def executed_cases(self) -> Set[str]:
        return {cid for cid, st in self.results().items() if st in ("PASS", "FAIL")}


def rodski_run(module: Path, *args: str) -> Run:
    marker = Path(tempfile.mkstemp(prefix="rodski_ps_marker_", suffix=".txt")[1])
    result_dir = module / "result"
    before = set(result_dir.iterdir()) if result_dir.is_dir() else set()
    env = dict(os.environ, RODSKI_PS_MARKER=str(marker), PYTHONUNBUFFERED="1")
    proc = subprocess.run([*CLI, "run", *args, "--headless"], cwd=str(module), env=env,
                          capture_output=True, text=True, timeout=600)
    after = set(result_dir.iterdir()) if result_dir.is_dir() else set()
    new_dirs = sorted(p for p in after - before if p.is_dir())
    marks = [ln for ln in marker.read_text(encoding="utf-8").splitlines() if ln] if marker.exists() else []
    marker.unlink(missing_ok=True)
    return Run(proc, new_dirs[-1] if new_dirs else None, marks)


def rodski_plan(module: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([*CLI, "plan", *args], cwd=str(module), capture_output=True, text=True, timeout=300)


class TempModule:
    """把模块复制到临时目录（plan 改写类检查不污染仓库内的 plan/）。"""

    def __enter__(self) -> Path:
        self.root = Path(tempfile.mkdtemp(prefix="rodski_ps_"))
        self.mod = self.root / "plan_selector"
        shutil.copytree(HERE, self.mod, ignore=shutil.ignore_patterns("result", "logs", "__pycache__"))
        return self.mod

    def __exit__(self, *exc) -> None:
        shutil.rmtree(self.root, ignore_errors=True)


def expect(cond: bool, msg: str, ctx: str = "") -> None:
    if not cond:
        raise AssertionError(msg + (f"\n     --- 输出 ---\n{ctx[-2500:]}" if ctx else ""))


def expect_executed(r: Run, expected: Iterable[str], ignore: Iterable[str] = ()) -> None:
    """断言实际执行集合：执行轨迹（步骤级）== 期望；result.xml 中 PASS/FAIL 的用例 == 期望涉及的用例且全部 PASS。"""
    ign = set(ignore)
    exp = sorted(set(expected) - ign)
    act = [m for m in r.marks if m not in ign]
    expect(len(act) == len(set(act)), f"存在重复执行的步骤: {act}", r.out)
    expect(sorted(act) == exp,
           f"实际执行集合不符（退出码 {r.code}）:\n       期望 {exp}\n       实际 {sorted(act)}"
           f"\n       result.xml {r.results()}", r.out)
    exp_cases = {m.split("/")[0] for m in exp}
    expect(r.executed_cases() == exp_cases,
           f"result.xml 中执行过（PASS/FAIL）的用例应为 {sorted(exp_cases)}，实际 {r.results()}", r.out)
    bad = {c: s for c, s in r.results().items() if c in exp_cases and s != "PASS"}
    expect(not bad, f"被执行的用例应全部 PASS: {bad}", r.out)


def xsd_ok(path: Path) -> None:
    x = subprocess.run(["xmllint", "--noout", "--schema", str(PLAN_XSD), str(path)], capture_output=True, text=True)
    expect(x.returncode == 0, f"{path.name} 不符合 plan.xsd: {x.stderr.strip()}")


# ================================================================ F081 用例级过滤（GUIDE §9.7 / §3.2）
def p01() -> None:
    """P01 F081 --tags catalog（套件 tags）→ 执行 CAT_001/002/003（不含 scenario 的用例）"""
    expect_executed(rodski_run(HERE, "case/", "--tags", "catalog"), CAT_ALL)


def p02() -> None:
    """P02 F081/F091 --tags smoke → CAT_001（用例级 tags）+ CHK_001/S01 + CHK_002/S01（scenario tag）"""
    expect_executed(rodski_run(HERE, "case/", "--tags", "smoke"),
                    ["CAT_001"] + CHK1_WRAP + CHK1_S01 + ["CHK_002/S01/1"])


def p03() -> None:
    """P03 F081 --priority P0,P1（多值）→ CAT_001、CAT_002、CHK_001 全部、CHK_002 全部"""
    expect_executed(rodski_run(HERE, "case/", "--priority", "P0,P1"),
                    ["CAT_001", "CAT_002"] + CHK1_ALL + CHK2_ALL)


def p04() -> None:
    """P04 F081 --priority P1（单值）→ CAT_002、CHK_002 全部"""
    expect_executed(rodski_run(HERE, "case/", "--priority", "P1"), ["CAT_002"] + CHK2_ALL)


def p05() -> None:
    """P05 F081 --exclude-tags slow → 排除 CAT_003（用例级 tags）与 CHK_001/S02（scenario tag），其余全部执行"""
    exp = [m for m in FULL if m not in ("CAT_003", "CHK_001/S02/1")]
    expect_executed(rodski_run(HERE, "case/", "--exclude-tags", "slow"), exp)


def p06() -> None:
    """P06 F081 --tags regression --priority P0（标签 AND 优先级）→ 只执行 CAT_001"""
    expect_executed(rodski_run(HERE, "case/", "--tags", "regression", "--priority", "P0"), ["CAT_001"])


# ================================================================ F091 scenario 级 selector（GUIDE §10.5）
def p08() -> None:
    """P08 F091 --tag p0（只出现在 scenario@tag）→ 只执行 CHK_001/S01（及其 pre/裸步骤/post）"""
    expect_executed(rodski_run(HERE, "case/", "--tag", "p0"), CHK1_WRAP + CHK1_S01)


def p09() -> None:
    """P09 F091 --group negative → CHK_001/S02 + CHK_002/S01（其余 scenario 与无 scenario 用例不执行）"""
    expect_executed(rodski_run(HERE, "case/", "--group", "negative"),
                    CHK1_WRAP + ["CHK_001/S02/1", "CHK_002/S01/1"])


def p10() -> None:
    """P10 F091 --tag checkout --exclude-tag slow → CHK_001（除 S02）+ CHK_002 全部"""
    exp = [m for m in CHK1_ALL if m != "CHK_001/S02/1"] + CHK2_ALL
    expect_executed(rodski_run(HERE, "case/", "--tag", "checkout", "--exclude-tag", "slow"), exp)


def p11() -> None:
    """P11 F091 无用例路径 `rodski run --group negative`（GUIDE §10.5 原文写法）→ 同 P09"""
    expect_executed(rodski_run(HERE, "--group", "negative"), CHK1_WRAP + ["CHK_001/S02/1", "CHK_002/S01/1"])


def p12() -> None:
    """P12 F091 --tag smoke --dry-run 只预览不执行：输出含 CHK_001/S01、CHK_002/S01，且无任何步骤执行"""
    r = rodski_run(HERE, "case/", "--tag", "smoke", "--dry-run")
    expect(r.code == 0, f"dry-run 退出码应为 0，实际 {r.code}", r.out)
    expect(not r.marks, f"dry-run 不应执行任何步骤: {r.marks}", r.out)
    for cid in ("CHK_001", "CHK_002"):
        expect(re.search(rf"{cid}\b.*S01", r.out) is not None, f"dry-run 输出应列出 {cid} / S01", r.out)


# ================================================================ F092 执行优先级（GUIDE §10.9 / CORE §7.7）
def p13() -> None:
    """P13 F092 优先级矩阵：case execute=否 > plan case 否 > scenario 否 > step 否 > default_execute=否"""
    r = rodski_run(HERE, "@priority_regression")
    expect_executed(r, ["CAT_001", "CHK_001/pre", "CHK_001/bare", "CHK_001/S01/1", "CHK_001/S01/3", "CHK_001/post"])
    expect(r.results().get("CHK_002") in (None, "SKIP"), f"CHK_002 应 SKIP 或不出现: {r.results()}")
    expect("CHK_003" not in r.results() or r.results()["CHK_003"] == "SKIP", f"CHK_003 不应执行: {r.results()}")


def p14() -> None:
    """P14 F092 test_plan execute=否 → 计划内显式 execute=是 的用例也不执行"""
    expect_executed(rodski_run(HERE, "@disabled_regression"), [])


def p15() -> None:
    """P15 F092 default_execute=是：未提及的全部执行；显式 case/scenario execute=否 不执行；CHK_003 仍不执行"""
    exp = [m for m in FULL if m not in ("CAT_002", "CHK_001/S02/1")]
    expect_executed(rodski_run(HERE, "@defaulton_regression"), exp)


# ================================================================ F093 plan 子命令与默认计划（GUIDE §10.3/§10.4/§10.8）
def p17() -> None:
    """P17 F093 无参数 `rodski run` → 默认计划 plan/project_full.xml（全量）"""
    with TempModule() as mod:
        expect_executed(rodski_run(mod), FULL)


def p18() -> None:
    """P18 F093 默认计划解析：无 project_full 时唯一 *_full 计划生效；多个 *_full 时报错要求显式 @plan_id"""
    with TempModule() as mod:
        (mod / "plan" / "project_full.xml").unlink()
        (mod / "plan" / "nightly_full.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<test_plan id="nightly_full" title="夜间" kind="suite" default_execute="否">\n'
            '  <case file="report/report_basic.xml" id="RPT_001" execute="是"/>\n'
            '</test_plan>\n', encoding="utf-8")
        expect_executed(rodski_run(mod), ["RPT_001"])
        shutil.copy(mod / "plan" / "nightly_full.xml", mod / "plan" / "weekly_full.xml")
        f = mod / "plan" / "weekly_full.xml"
        f.write_text(f.read_text(encoding="utf-8").replace('id="nightly_full"', 'id="weekly_full"'), encoding="utf-8")
        r = rodski_run(mod)
        expect(r.code != 0 and not r.marks, "存在多个 *_full 计划时应报错且不执行", r.out)
        expect("@plan_id" in r.out and "nightly_full" in r.out and "weekly_full" in r.out,
               "错误信息应列出候选 full 计划并提示显式 @plan_id", r.out)


def p19() -> None:
    """P19 F093 plan init：生成合法 project_full（suite / default_execute=是）；已存在时不覆盖，--force 覆盖"""
    with TempModule() as mod:
        pf = mod / "plan" / "project_full.xml"
        pf.unlink()
        r = rodski_plan(mod, "init")
        expect(r.returncode == 0 and pf.is_file(), f"plan init 应创建 project_full.xml: {r.stdout}{r.stderr}")
        xsd_ok(pf)
        root = ET.parse(pf).getroot()
        expect(root.get("id") == "project_full" and root.get("kind") == "suite" and root.get("default_execute") == "是",
               f"project_full 属性不符: {root.attrib}")
        pf.write_text(pf.read_text(encoding="utf-8").replace('default_execute="是"', 'default_execute="否"'),
                      encoding="utf-8")
        before = pf.read_text(encoding="utf-8")
        rodski_plan(mod, "init")
        expect(pf.read_text(encoding="utf-8") == before, "已存在时不加 --force 不应覆盖")
        rodski_plan(mod, "init", "--force")
        expect(ET.parse(pf).getroot().get("default_execute") == "是", "--force 应覆盖为默认全量计划")


def p20() -> None:
    """P20 F093 plan create + add-case + add-dir → list/preview 可见，真实执行 = CAT_002 + RPT_001"""
    with TempModule() as mod:
        steps = [
            ("create", "smoke_suite", "--kind", "suite", "--default-execute", "否", "--title", "冒烟"),
            ("add-case", "smoke_suite", "catalog/catalog_basic.xml", "CAT_002"),
            ("add-dir", "smoke_suite", "report"),
        ]
        for s in steps:
            r = rodski_plan(mod, *s)
            expect(r.returncode == 0, f"plan {' '.join(s)} 失败: {r.stdout}{r.stderr}")
        xsd_ok(mod / "plan" / "smoke_suite.xml")
        lst = rodski_plan(mod, "list")
        expect("smoke_suite" in lst.stdout and "冒烟" in lst.stdout, f"plan list 应列出 smoke_suite: {lst.stdout}")
        pv = rodski_plan(mod, "preview", "smoke_suite")
        expect(pv.returncode == 0 and "CAT_002" in pv.stdout and "RPT_001" in pv.stdout,
               f"preview 应列出 CAT_002 与 RPT_001: {pv.stdout}{pv.stderr}")
        expect_executed(rodski_run(mod, "@smoke_suite"), ["CAT_002", "RPT_001"])


def p21() -> None:
    """P21 F093 plan add-scenario（GUIDE §10.3 原文用法）→ 计划校验通过，执行 CHK_001/S03"""
    with TempModule() as mod:
        rodski_plan(mod, "create", "sc_suite", "--kind", "suite", "--default-execute", "否")
        r = rodski_plan(mod, "add-scenario", "sc_suite", "CHK_001", "S03")
        expect(r.returncode == 0, f"add-scenario 失败: {r.stdout}{r.stderr}")
        v = rodski_plan(mod, "validate", "sc_suite")
        expect(v.returncode == 0, f"add-scenario 生成的计划应能通过 plan validate: {v.stdout}{v.stderr}")
        expect_executed(rodski_run(mod, "@sc_suite"), CHK1_WRAP + ["CHK_001/S03/1"])


def p22() -> None:
    """P22 F093 plan create --from-tag smoke → 计划校验通过，执行集合 = `--tag smoke` 的选择结果"""
    with TempModule() as mod:
        r = rodski_plan(mod, "create", "smoke_tag_suite", "--kind", "suite", "--from-tag", "smoke", "--title", "tag冒烟")
        expect(r.returncode == 0, f"create --from-tag 失败: {r.stdout}{r.stderr}")
        xsd_ok(mod / "plan" / "smoke_tag_suite.xml")
        v = rodski_plan(mod, "validate", "smoke_tag_suite")
        expect(v.returncode == 0, f"--from-tag 生成的计划应能通过 plan validate: {v.stdout}{v.stderr}")
        expect_executed(rodski_run(mod, "@smoke_tag_suite"),
                        ["CAT_001"] + CHK1_WRAP + CHK1_S01 + ["CHK_002/S01/1"])


def p23() -> None:
    """P23 F093 plan migrate：为省略 file 的 <case> 自动补全 file，迁移后校验通过并可执行"""
    with TempModule() as mod:
        legacy = mod / "plan" / "legacy_regression.xml"
        legacy.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<test_plan id="legacy_regression" title="存量计划" kind="suite" default_execute="否">\n'
            '  <case id="CAT_003" execute="是"/>\n'
            '  <case id="CHK_002" execute="是"><scenario id="S02" execute="是"/></case>\n'
            '</test_plan>\n', encoding="utf-8")
        v0 = rodski_plan(mod, "validate", "legacy_regression")
        expect(v0.returncode != 0 and "SKI207" in v0.stdout + v0.stderr, f"迁移前应报 SKI207: {v0.stdout}{v0.stderr}")
        m = rodski_plan(mod, "migrate", str(mod))
        expect(m.returncode == 0, f"plan migrate 失败: {m.stdout}{m.stderr}")
        files = {c.get("id"): c.get("file") for c in ET.parse(legacy).getroot().iter("case")}
        expect(files == {"CAT_003": "catalog/catalog_basic.xml", "CHK_002": "checkout/checkout_flow.xml"},
               f"migrate 应补全 file: {files}")
        v1 = rodski_plan(mod, "validate", "legacy_regression")
        expect(v1.returncode == 0, f"迁移后应校验通过: {v1.stdout}{v1.stderr}")
        expect_executed(rodski_run(mod, "@legacy_regression"), ["CAT_003", "CHK_002/S02/1"])


def p24() -> None:
    """P24 F093 plan list / validate：仓库内计划全部合法（xsd + validate）；stale 引用 validate 非 0 并指出 ID"""
    for p in sorted((HERE / "plan").glob("*.xml")):
        xsd_ok(p)
    lst = rodski_plan(HERE, "list")
    for pid in ("project_full", "priority_regression", "disabled_regression", "defaulton_regression",
                "checkout_step_debug", "checkout_scenario_debug"):
        expect(pid in lst.stdout, f"plan list 应列出 {pid}: {lst.stdout}")
    v = rodski_plan(HERE, "validate")
    expect(v.returncode == 0, f"仓库内计划应全部校验通过: {v.stdout}{v.stderr}")
    with TempModule() as mod:
        (mod / "plan" / "stale_regression.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<test_plan id="stale_regression" kind="suite" default_execute="否">\n'
            '  <case file="catalog/catalog_basic.xml" id="CAT_999" execute="是"/>\n'
            '</test_plan>\n', encoding="utf-8")
        s = rodski_plan(mod, "validate", "stale_regression")
        expect(s.returncode != 0 and "CAT_999" in s.stdout + s.stderr, f"stale 引用应校验失败并指出 CAT_999: {s.stdout}{s.stderr}")


def p25() -> None:
    """P25 F093 disable-case / disable-scenario / enable-case / enable-scenario 改写计划并改变执行集合"""
    with TempModule() as mod:
        for s in (("disable-case", "priority_regression", "CAT_001"),
                  ("enable-case", "priority_regression", "CHK_002"),
                  ("disable-scenario", "priority_regression", "CHK_001", "S01"),
                  ("enable-scenario", "priority_regression", "CHK_001", "S02")):
            r = rodski_plan(mod, *s)
            expect(r.returncode == 0, f"plan {' '.join(s)} 失败: {r.stdout}{r.stderr}")
        pf = mod / "plan" / "priority_regression.xml"
        xsd_ok(pf)
        root = ET.parse(pf).getroot()
        cases = {c.get("id"): c for c in root.iter("case")}
        expect(cases["CAT_001"].get("execute") == "否" and cases["CHK_002"].get("execute") == "是",
               "disable-case / enable-case 应改写 case@execute")
        sc = {s.get("id"): s.get("execute") for s in cases["CHK_001"].iter("scenario")}
        expect(sc == {"S01": "否", "S02": "是"}, f"disable/enable-scenario 应改写 scenario@execute: {sc}")
        expect_executed(rodski_run(mod, "@priority_regression"), CHK1_WRAP + ["CHK_001/S02/1", "CHK_002/S01/1"])


def p26() -> None:
    """P26 F093 plan preview 与 run @plan --dry-run 只预览不执行，输出选中范围"""
    pv = rodski_plan(HERE, "preview", "priority_regression")
    expect(pv.returncode == 0 and "CAT_001" in pv.stdout and re.search(r"CHK_001\b.*S01", pv.stdout),
           f"preview 应列出 CAT_001 与 CHK_001/S01: {pv.stdout}{pv.stderr}")
    r = rodski_run(HERE, "@priority_regression", "--dry-run")
    expect(r.code == 0 and not r.marks, f"dry-run 应 0 退出且不执行（轨迹 {r.marks}）", r.out)
    expect("CAT_001" in r.out and "CHK_002" in r.out, "dry-run 输出应包含选中项与跳过项", r.out)


# ================================================================ F094 调试计划（GUIDE §10.7）
def _debug_plan(mod: Path, pid: str, kind: str, prepare: str, cleanup: str,
                scenario: str, step: Optional[int] = None, step_mode: Optional[str] = None) -> None:
    dbg = f'prepare="{prepare}" cleanup="{cleanup}"' + (f' step_mode="{step_mode}"' if step_mode else "")
    inner = f'<step no="{step}" execute="是"/>' if step else ""
    (mod / "plan" / f"{pid}.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<test_plan id="{pid}" kind="{kind}" default_execute="否">\n'
        f'  <debug {dbg}/>\n'
        f'  <case file="checkout/checkout_flow.xml" id="CHK_001" execute="是">\n'
        f'    <scenario id="{scenario}" execute="是">{inner}</scenario>\n'
        '  </case>\n</test_plan>\n', encoding="utf-8")
    xsd_ok(mod / "plan" / f"{pid}.xml")


# prepare=auto 文档写"pre_process + 目标 step 之前的步骤"，未说明 test_case 裸步骤是否算"之前的步骤"，不对其断言
_IGN_BARE = ("CHK_001/bare",)


def p28() -> None:
    """P28 F094 plan debug-scenario（GUIDE §10.7 原文用法）+ run --debug → 只执行 pre + 目标 scenario + post"""
    with TempModule() as mod:
        r = rodski_plan(mod, "debug-scenario", "chk_debug", "--case", "CHK_001", "--scenario", "S03",
                        "--prepare", "case", "--cleanup", "是")
        expect(r.returncode == 0, f"debug-scenario 失败: {r.stdout}{r.stderr}")
        root = ET.parse(mod / "plan" / "chk_debug.xml").getroot()
        expect(root.get("kind") == "scenario_debug", f"kind 应为 scenario_debug: {root.attrib}")
        expect_executed(rodski_run(mod, "@chk_debug", "--debug"),
                        ["CHK_001/pre", "CHK_001/S03/1", "CHK_001/post"], ignore=_IGN_BARE)


def p29() -> None:
    """P29 F094 plan debug-step --step 2 --step-mode only --prepare auto + run --debug → pre + S01 第 1、2 步"""
    with TempModule() as mod:
        r = rodski_plan(mod, "debug-step", "chk_step_debug", "--case", "CHK_001", "--scenario", "S01", "--step", "2",
                        "--step-mode", "only", "--prepare", "auto", "--cleanup", "否")
        expect(r.returncode == 0, f"debug-step 失败: {r.stdout}{r.stderr}")
        root = ET.parse(mod / "plan" / "chk_step_debug.xml").getroot()
        dbg = root.find("debug")
        expect(root.get("kind") == "step_debug" and dbg is not None and dbg.get("step_mode") == "only",
               f"应生成 step_debug + step_mode=only: {ET.tostring(root, encoding='unicode')}")
        expect_executed(rodski_run(mod, "@chk_step_debug", "--debug"),
                        ["CHK_001/pre", "CHK_001/S01/1", "CHK_001/S01/2"], ignore=_IGN_BARE)


def p30() -> None:
    """P30 F094 仓库内 checkout_step_debug（auto + only + cleanup=否）--debug → pre + S01 第 1、2 步，无 post"""
    expect_executed(rodski_run(HERE, "@checkout_step_debug", "--debug"),
                    ["CHK_001/pre", "CHK_001/S01/1", "CHK_001/S01/2"], ignore=_IGN_BARE)


def p31() -> None:
    """P31 F094 仓库内 checkout_scenario_debug（prepare=case + cleanup=是）--debug → pre + S03 + post"""
    expect_executed(rodski_run(HERE, "@checkout_scenario_debug", "--debug"),
                    ["CHK_001/pre", "CHK_001/S03/1", "CHK_001/post"], ignore=_IGN_BARE)


def p32() -> None:
    """P32 F094 step_debug 矩阵 prepare(auto/case) × step_mode(only/from/all)，目标 S01 第 2 步，cleanup=否"""
    pre, s1, s2, s3 = "CHK_001/pre", "CHK_001/S01/1", "CHK_001/S01/2", "CHK_001/S01/3"
    matrix = {
        ("auto", "only"): [pre, s1, s2], ("auto", "from"): [pre, s1, s2, s3], ("auto", "all"): [pre, s1, s2, s3],
        ("case", "only"): [pre, s2], ("case", "from"): [pre, s2, s3], ("case", "all"): [pre, s1, s2, s3],
    }
    errors = []
    with TempModule() as mod:
        for (prepare, mode), exp in matrix.items():
            pid = f"m_{prepare}_{mode}_debug"
            _debug_plan(mod, pid, "step_debug", prepare, "否", "S01", step=2, step_mode=mode)
            try:
                expect_executed(rodski_run(mod, f"@{pid}", "--debug"), exp, ignore=_IGN_BARE)
            except AssertionError as e:
                errors.append(f"prepare={prepare} step_mode={mode}: {str(e).splitlines()[0]} {str(e).splitlines()[1:3]}")
    expect(not errors, "；".join(errors))


def p33() -> None:
    """P33 F094 prepare=none：不执行 pre_process，直接执行目标（step_debug only / scenario_debug 各一）"""
    errors = []
    with TempModule() as mod:
        _debug_plan(mod, "none_step_debug", "step_debug", "none", "否", "S01", step=2, step_mode="only")
        _debug_plan(mod, "none_scenario_debug", "scenario_debug", "none", "否", "S03")
        for pid, exp in (("none_step_debug", ["CHK_001/S01/2"]), ("none_scenario_debug", ["CHK_001/S03/1"])):
            r = rodski_run(mod, f"@{pid}", "--debug")
            try:
                expect_executed(r, exp, ignore=_IGN_BARE)
            except AssertionError as e:
                err = re.search(r"- CHK_001: .*", r.out)
                errors.append(f"{pid}: {str(e).splitlines()[0]} {str(e).splitlines()[1:3]}"
                              + (f" 框架报错: {err.group(0)}" if err else ""))
    expect(not errors, "；".join(errors))


def p34() -> None:
    """P34 F094 --debug 只对 scenario_debug/step_debug 生效：suite 计划加 --debug 执行集合与 P13 相同"""
    expect_executed(rodski_run(HERE, "@priority_regression", "--debug"),
                    ["CAT_001", "CHK_001/pre", "CHK_001/bare", "CHK_001/S01/1", "CHK_001/S01/3", "CHK_001/post"])


def p35() -> None:
    """P35 F094/CORE §7.7 @plan_id 与 --tag/--group/--exclude-tag/--priority/--case-id 固定互斥：报错且不执行"""
    errors = []
    for sel in (("--tag", "smoke"), ("--group", "negative"), ("--exclude-tag", "slow"),
                ("--priority", "P0"), ("--case-id", "CAT_001")):
        r = rodski_run(HERE, "@project_full", *sel)
        if r.code == 0 or r.marks or r.run_dir is not None:
            errors.append(f"@project_full {' '.join(sel)}: 退出码 {r.code}，轨迹 {r.marks}，运行目录 {r.run_dir}")
    expect(not errors, "；".join(errors))


CHECKS: Dict[str, Callable[[], None]] = {
    "P01": p01, "P02": p02, "P03": p03, "P04": p04, "P05": p05, "P06": p06,
    "P08": p08, "P09": p09, "P10": p10, "P11": p11, "P12": p12,
    "P13": p13, "P14": p14, "P15": p15,
    "P17": p17, "P18": p18, "P19": p19, "P20": p20, "P21": p21, "P22": p22, "P23": p23,
    "P24": p24, "P25": p25, "P26": p26,
    "P28": p28, "P29": p29, "P30": p30, "P31": p31, "P32": p32, "P33": p33, "P34": p34, "P35": p35,
}


def main(argv: List[str]) -> int:
    strict = "--strict" in argv
    selected = [a.upper() for a in argv if not a.startswith("--")] or list(CHECKS)
    unknown = [k for k in selected if k not in CHECKS]
    if unknown:
        print(f"未知检查项: {unknown}；可选 {list(CHECKS)}")
        return 2
    subprocess.run([sys.executable, str(HERE / "data" / "init_data.py")], check=True,
                   capture_output=True, text=True)

    counts = {"PASS": 0, "FAIL": 0, "KNOWN": 0}
    failed: List[str] = []
    for key in selected:
        fn = CHECKS[key]
        title = fn.__doc__.splitlines()[0]
        try:
            fn()
            counts["PASS"] += 1
            note = "（登记为 KNOWN 但已通过，可能已修复，请核对后移出 KNOWN 表）" if key in KNOWN else ""
            print(f"PASS  {title}{note}")
        except AssertionError as e:
            lines = str(e).splitlines()
            if key in KNOWN:
                counts["KNOWN"] += 1
                print(f"KNOWN {title}\n     缺陷: {KNOWN[key]}\n     现象: {' '.join(l.strip() for l in lines[:3])}")
                if strict:
                    failed.append(key)
            else:
                counts["FAIL"] += 1
                failed.append(key)
                print(f"FAIL  {title}\n     {e}")
    print(f"\n验收结果: PASS {counts['PASS']} / KNOWN {counts['KNOWN']} / FAIL {counts['FAIL']}"
          f"（共 {len(selected)} 项）" + (f"，计为失败: {', '.join(failed)}" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
