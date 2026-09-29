#!/usr/bin/env python3
"""v11.5.0 用例目录多级嵌套 —— rodski-demo 验收脚本。

设计文档: .pb/specs/v11.5.0-nested-case-directory-design.md
验收方案: .pb/iterations/iteration-63/ACCEPTANCE.md

用法:
    python3 rodski-demo/DEMO/demo_nested_case/run_acceptance.py          # 全部
    python3 rodski-demo/DEMO/demo_nested_case/run_acceptance.py A05 A07  # 指定编号

每个检查项真实调用 `rodski` CLI（headless Chromium，页面为内嵌 data: URL，
不依赖外部服务），再对退出码、result.xml 与结果目录镜像结构做断言。
"""
from __future__ import annotations

import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
DEMO = HERE.parent
MOD = HERE                                   # demo_nested_case
SINGLE = DEMO / "demo_nested_case_single"
DUP = DEMO / "demo_nested_case_dup_id"

# 全量执行时期望出现的 (case_file, case_id)
FULL_EXPECTED = {
    ("smoke_root.xml", "TC001"),
    ("order/order_basic.xml", "TC001"),
    ("order/order_basic.xml", "TC002"),
    ("order/refund/refund_apply.xml", "TC001"),
    ("order/refund/approve/refund_approve_flow.xml", "TC001"),
    ("user/login/login_basic.xml", "TC001"),
}


class Run:
    def __init__(self, proc: subprocess.CompletedProcess, run_dir: Optional[Path]):
        self.code = proc.returncode
        self.out = (proc.stdout or "") + (proc.stderr or "")
        self.run_dir = run_dir

    def results(self) -> List[Tuple[str, str, str]]:
        """返回 [(case_file, case_id, status)]。"""
        if not self.run_dir or not (self.run_dir / "result.xml").is_file():
            return []
        root = ET.parse(self.run_dir / "result.xml").getroot()
        return [
            (r.get("case_file", ""), r.get("case_id", ""), r.get("status", ""))
            for r in root.iter("result")
        ]

    def keys(self) -> set:
        return {(f, i) for f, i, _ in self.results()}


def rodski(args: List[str], module: Path = MOD, cwd: Optional[Path] = None) -> Run:
    result_dir = module / "result"
    before = set(result_dir.iterdir()) if result_dir.is_dir() else set()
    proc = subprocess.run(
        ["rodski", "run", *args, "--headless"],
        cwd=str(cwd or module), capture_output=True, text=True, timeout=600,
    )
    after = set(result_dir.iterdir()) if result_dir.is_dir() else set()
    new_dirs = sorted(p for p in after - before if p.is_dir())
    return Run(proc, new_dirs[-1] if new_dirs else None)


def rodski_cli(args: List[str], cwd: Path = MOD) -> subprocess.CompletedProcess:
    return subprocess.run(["rodski", *args], cwd=str(cwd),
                          capture_output=True, text=True, timeout=300)


def expect(cond: bool, msg: str, ctx: str = "") -> None:
    if not cond:
        raise AssertionError(msg + (f"\n--- 输出 ---\n{ctx[-3000:]}" if ctx else ""))


def all_passed(r: Run) -> bool:
    return bool(r.results()) and all(s == "PASS" for _, _, s in r.results())


def pngs(d: Path) -> List[Path]:
    return sorted(d.rglob("*.png")) if d.is_dir() else []


# ---------------------------------------------------------------- 检查项
def a01_full_tree() -> None:
    """A01 递归执行 case/ 全树：6 个用例全部通过，.draft/ 与 README.md 被忽略。"""
    r = rodski(["case/"])
    expect(r.code == 0, f"退出码应为 0，实际 {r.code}", r.out)
    expect(r.keys() == FULL_EXPECTED, f"执行集合不符:\n期望 {sorted(FULL_EXPECTED)}\n实际 {sorted(r.keys())}", r.out)
    expect(all_passed(r), f"存在未通过用例: {r.results()}", r.out)
    expect("SKI204" not in r.out and "not_a_case" not in r.out, ".draft/ 下的文件不应被扫描", r.out)


def a02_result_mirror() -> None:
    """A02 结果目录镜像 case 目录结构；跨文件同 ID 的截图互不覆盖；根目录无散落截图。"""
    r = rodski(["case/"])
    expect(r.code == 0 and r.run_dir is not None, "全量执行失败", r.out)
    base = r.run_dir / "case"
    for rel in ["smoke_root", "order/order_basic", "order/refund/refund_apply",
                "order/refund/approve/refund_approve_flow", "user/login/login_basic"]:
        shots = pngs(base / rel / "screenshots")
        expect(bool(shots), f"缺少镜像截图目录或截图: {base / rel / 'screenshots'}")
        # 仅检查 screenshots/ 直接子级文件的命名规则（场景步骤截图位于子目录内，按 CORE 设计其文件名不含 caseid 前缀）
        direct_shots = [p for p in (base / rel / "screenshots").iterdir() if p.is_file() and p.suffix == ".png"]
        expect(all(p.name.startswith("TC00") for p in direct_shots), f"截图文件名规则应保持 {{caseid}}_... : {direct_shots}")
    basic = [p.name for p in pngs(base / "order/order_basic/screenshots")]
    expect(any(n.startswith("TC001_") for n in basic) and any(n.startswith("TC002_") for n in basic),
           f"order_basic 应同时有 TC001/TC002 截图: {basic}")
    scen = [p for p in (base / "order/refund/approve/refund_approve_flow/screenshots").iterdir() if p.is_dir()]
    expect(any(d.name.startswith("TC001_S01") for d in scen), f"场景截图子目录应位于镜像目录内: {scen}")
    legacy = r.run_dir / "screenshots"
    expect(not pngs(legacy), f"运行目录根下不应再有 screenshots/*.png: {pngs(legacy)}")
    for name in ("result.xml", "execution_summary.json", "execution.log"):
        expect((r.run_dir / name).is_file(), f"汇总文件应保留在运行目录根: {name}")


def a03_result_case_file() -> None:
    """A03 result.xml 的每条 result 都带 case_file（相对 case/ 的 POSIX 路径），且符合 result.xsd。"""
    r = rodski(["case/order/refund/"])
    expect(r.code == 0, f"退出码应为 0，实际 {r.code}", r.out)
    files = sorted(f for f, _, _ in r.results())
    expect(files == ["order/refund/approve/refund_approve_flow.xml", "order/refund/refund_apply.xml"],
           f"case_file 不符: {files}", r.out)
    x = subprocess.run(["xmllint", "--noout", "--schema",
                        str(DEMO.parent.parent / "rodski/schemas/result.xsd"), str(r.run_dir / "result.xml")],
                       capture_output=True, text=True)
    expect(x.returncode == 0, f"result.xml 不符合 result.xsd: {x.stderr}")


def a04_subdir() -> None:
    """A04 执行子目录 case/order/（递归 3 层）：4 个用例。"""
    r = rodski(["case/order/"])
    exp = {k for k in FULL_EXPECTED if k[0].startswith("order/")}
    expect(r.code == 0 and r.keys() == exp and all_passed(r), f"期望 {sorted(exp)}，实际 {r.results()}", r.out)


def a05_single_file() -> None:
    """A05 执行单个文件：该文件内所有 execute=是 的用例。"""
    r = rodski(["case/user/login/login_basic.xml"])
    expect(r.code == 0 and r.keys() == {("user/login/login_basic.xml", "TC001")},
           f"应只执行 TC001（TC002 execute=否），实际 {r.results()}", r.out)


def a06_file_and_case_id() -> None:
    """A06 文件 + --case-id：只执行指定用例。"""
    r = rodski(["case/order/order_basic.xml", "--case-id", "TC002"])
    expect(r.code == 0 and r.keys() == {("order/order_basic.xml", "TC002")} and all_passed(r),
           f"实际 {r.results()}", r.out)


def a07_case_id_requires_file() -> None:
    """A07 --case-id 与目录一起使用必须报错（跨文件同 ID 会有歧义），且不执行任何用例。"""
    r = rodski(["case/order/", "--case-id", "TC001"])
    expect(r.code != 0, "--case-id + 目录应非 0 退出", r.out)
    expect(not r.results(), f"不应执行任何用例: {r.results()}", r.out)


def a08_case_id_plan_exclusive() -> None:
    """A08 --case-id 与 @plan_id 固定互斥。"""
    r = rodski(["@refund_regression", "--case-id", "TC001"])
    expect(r.code != 0 and not r.results(), "@plan_id + --case-id 应报错", r.out)


def a09_plan_file_and_id() -> None:
    """A09 plan 按"文件 + ID"选择：两个文件的同名 TC001 分别被选中，含 scenario 选择。"""
    r = rodski(["@refund_regression"])
    exp = {("order/refund/refund_apply.xml", "TC001"), ("order/refund/approve/refund_approve_flow.xml", "TC001")}
    expect(r.code == 0 and r.keys() == exp and all_passed(r), f"实际 {r.results()}", r.out)


def a10_plan_case_dir() -> None:
    """A10 plan 的 case_dir（可选）与 case 混合选择。"""
    r = rodski(["@mixed_selection"])
    exp = {("user/login/login_basic.xml", "TC001"), ("order/order_basic.xml", "TC002")}
    expect(r.code == 0 and r.keys() == exp and all_passed(r), f"实际 {r.results()}", r.out)


def a11_plan_stale() -> None:
    """A11 stale 引用（文件 / ID / 目录不存在）只记录不崩溃；有效引用照常执行。"""
    d = rodski(["@stale_reference", "--dry-run"])
    for token in ("order/not_exist.xml", "TC999", "payment"):
        expect(token in d.out, f"dry-run 输出应包含 stale 引用 {token}", d.out)
    r = rodski(["@stale_reference"])
    expect(r.code == 0 and r.keys() == {("smoke_root.xml", "TC001")}, f"实际 {r.results()}", r.out)


def a12_plan_missing_file_multi() -> None:
    """A12 多用例文件模块中 plan 省略 file：报错并提示补充 file，列出候选文件，不执行。"""
    r = rodski(["@legacy_missing_file"])
    expect(r.code != 0 and not r.results(), "应非 0 退出且不执行", r.out)
    expect("file" in r.out and "TC001" in r.out, "错误信息应提示为 TC001 补充 file", r.out)
    expect("order/order_basic.xml" in r.out, "错误信息应列出包含 TC001 的候选文件", r.out)


def a13_plan_missing_file_single() -> None:
    """A13 模块只有一个用例文件（位于子目录）时，plan 省略 file 兼容执行。"""
    r = rodski(["@legacy_plan"], module=SINGLE)
    expect(r.code == 0 and r.keys() == {("only/only_case.xml", "TC002")} and all_passed(r),
           f"实际 {r.results()}", r.out)


def a14_dup_id_in_file() -> None:
    """A14 同一文件内用例 ID 重复（含 execute=否）：执行前报错，指出文件与 ID，不启动浏览器。"""
    r = rodski(["case/"], module=DUP)
    expect(r.code != 0, "应非 0 退出", r.out)
    expect("dup/dup_in_file.xml" in r.out and "TC001" in r.out, "错误信息应指出文件与重复 ID", r.out)
    expect(not r.results(), f"不应执行任何用例: {r.results()}", r.out)


def a15_cwd_nested() -> None:
    """A15 在嵌套子目录内作为 cwd 执行 @plan_id，仍能定位模块根。"""
    r = rodski(["@refund_regression"], cwd=MOD / "case" / "order" / "refund")
    expect(r.code == 0 and len(r.results()) == 2, f"实际 {r.results()}", r.out)


def a16_html_report_tree() -> None:
    """A16 HTML 报告含按目录视图（出现嵌套目录路径）。"""
    r = rodski(["case/", "--report", "html"])
    expect(r.code == 0 and r.run_dir is not None, "执行失败", r.out)
    htmls = sorted(r.run_dir.rglob("*.html"))
    expect(bool(htmls), "应生成 HTML 报告", r.out)
    text = "".join(h.read_text(encoding="utf-8", errors="ignore") for h in htmls)
    expect("order/refund/approve" in text, "HTML 报告应包含目录树路径 order/refund/approve")


def a17_lint() -> None:
    """A17 rodski case lint：正常模块 0 退出；文件内重复 ID 模块非 0 且报 ERROR。"""
    ok = rodski_cli(["case", "lint", str(MOD)])
    expect(ok.returncode == 0, f"lint 正常模块应 0 退出: {ok.stdout}{ok.stderr}")
    bad = rodski_cli(["case", "lint", str(DUP)])
    out = bad.stdout + bad.stderr
    expect(bad.returncode != 0 and "ERROR" in out and "dup_in_file.xml" in out, f"lint 应报 ERROR: {out}")


def a18_plan_validate() -> None:
    """A18 plan XML 符合新 plan.xsd（case@file、case_dir）。"""
    xsd = DEMO.parent.parent / "rodski/schemas/plan.xsd"
    for p in sorted((MOD / "plan").glob("*.xml")):
        x = subprocess.run(["xmllint", "--noout", "--schema", str(xsd), str(p)], capture_output=True, text=True)
        expect(x.returncode == 0, f"{p.name} 不符合 plan.xsd: {x.stderr}")


CHECKS: Dict[str, Callable[[], None]] = {
    "A01": a01_full_tree, "A02": a02_result_mirror, "A03": a03_result_case_file,
    "A04": a04_subdir, "A05": a05_single_file, "A06": a06_file_and_case_id,
    "A07": a07_case_id_requires_file, "A08": a08_case_id_plan_exclusive,
    "A09": a09_plan_file_and_id, "A10": a10_plan_case_dir, "A11": a11_plan_stale,
    "A12": a12_plan_missing_file_multi, "A13": a13_plan_missing_file_single,
    "A14": a14_dup_id_in_file, "A15": a15_cwd_nested, "A16": a16_html_report_tree,
    "A17": a17_lint, "A18": a18_plan_validate,
}


def main(argv: List[str]) -> int:
    selected = argv or list(CHECKS)
    failed = []
    for key in selected:
        fn = CHECKS[key]
        try:
            fn()
            print(f"PASS {key} {fn.__doc__.splitlines()[0]}")
        except AssertionError as e:
            failed.append(key)
            print(f"FAIL {key} {fn.__doc__.splitlines()[0]}\n     {e}")
    print(f"\n验收结果: {len(selected) - len(failed)}/{len(selected)} 通过" + (f"，失败: {', '.join(failed)}" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
