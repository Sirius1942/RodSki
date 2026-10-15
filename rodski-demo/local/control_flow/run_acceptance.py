#!/usr/bin/env python3
"""local/control_flow —— 控制流与执行语义验收（F062 / F066~F070）。

用法（仓库根目录）:
    python3 rodski-demo/local/control_flow/run_acceptance.py            # 全部检查项
    python3 rodski-demo/local/control_flow/run_acceptance.py C05 C21    # 指定编号
    python3 rodski-demo/local/control_flow/run_acceptance.py --strict   # KNOWN 也按失败计（退出码 1）

做什么:
  1. 调用 data/init_data.py 重建 data.sqlite（回归结束时 data.sqlite 会被 git 还原，不能依赖手工数据）；
  2. 真实执行 `rodski run case/flow/ --headless`（页面为内嵌 data: URL，DB 为 result/ 下临时 SQLite，不依赖 :8000），
     通过环境变量 RODSKI_CF_MARKER 收集 fun/mark.py 写下的执行轨迹；
  3. 对 result.xml（状态 / [预期失败] 前缀）、execution.log（scenario SKIP 原因）、执行轨迹逐项断言；
  4. F070 把模块复制到临时目录，改写 DefaultValue.WaitTime / step_wait 后计时执行。

判定口径: 用例按文档描述的正确行为编写。框架行为与文档不符导致的失败登记在 KNOWN 表中，
输出 KNOWN（不计入失败、不改用例迁就框架）；KNOWN 项若意外通过会提示"可能已修复"。
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
from typing import Callable, Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
CLI = [sys.executable, str(REPO / "rodski" / "cli_main.py")]
FLOW_DIR = "case/flow/"

# ---------------------------------------------------------------- KNOWN 缺陷登记
# 检查项编号 -> 简述（详细的文档条款 / 代码位置见 README.md「KNOWN 缺陷」）
KNOWN: Dict[str, str] = {
    "C06": "set 写入的变量在 <if condition> 中不可见：set 同步到 DynamicExecutor 时以 model(空串) 为键，"
           "且 ${var} 解析只剥掉 '$' 去查 '{var}'（ski_executor.py:2393、dynamic_executor.py:236-239）",
    "C07": "Return 条件永远为假：DynamicExecutor 以 `return_values or []` 接收空的 history 列表，"
           "空列表为假值导致另建新列表、与 RuntimeContext.history 脱钩（dynamic_executor.py:23 / ski_executor.py:230）；"
           "GUIDE §3.8 的 ${Return[-1].status} == 200 写法也不被 _eval_return_condition 正则识别",
    "C08": "同 C07：${Return[-1].status == 200}（CORE §12.3 写法）因 Return 历史脱钩永远为假",
    "C09": "element_exists/element_not_exists 以 1 个参数调用 PlaywrightDriver.locate_element(locator_type, locator_value)，"
           "TypeError 被吞掉 → element_exists 恒假、element_not_exists 恒真（dynamic_executor.py:209、playwright_driver.py:516）",
    "C12": "<loop> 内的 <if>/<elif>/<else> 被解析器静默丢弃（case_parser.py:_parse_branch_steps 只收 test_step/business_call），"
           "而 case.xsd LoopContainerType 允许 if/elif/else",
    "C13": "同 C12（loop 内 if 被丢弃）+ 同 C06（${i} 在条件中不解析）",
    "C14": "同 C06：${login_status} == 401 中的变量不解析，elif 链全部为假走 else",
    "C15": "同 C06 + C16：${total} > 0 中变量不解析（float('${total}') 异常 → 条件块整体跳过）",
    "C16": "运算符拆分顺序为 ['==','!=','>','<','>=','<=']，'>=' / '<=' 先被 '>' / '<' 拆开 → float('= 3') 异常 → "
           "条件块被当作“评估失败”整体跳过（dynamic_executor.py:90）",
}


# ---------------------------------------------------------------- 运行封装
class Run:
    def __init__(self, proc: subprocess.CompletedProcess, run_dir: Optional[Path], marks: List[str]):
        self.code = proc.returncode
        self.out = (proc.stdout or "") + (proc.stderr or "")
        self.run_dir = run_dir
        self.marks = marks

    def results(self) -> Dict[str, Dict[str, str]]:
        if not self.run_dir or not (self.run_dir / "result.xml").is_file():
            return {}
        root = ET.parse(self.run_dir / "result.xml").getroot()
        return {r.get("case_id", ""): dict(r.attrib) for r in root.iter("result")}

    def log(self) -> str:
        p = self.run_dir / "execution.log" if self.run_dir else None
        return p.read_text(encoding="utf-8", errors="ignore") if p and p.is_file() else ""

    def case_log(self, case_id: str) -> str:
        """execution.log 中某条用例的片段（从"执行用例 i/n: ID"到下一条用例开始）。"""
        text = self.log()
        m = re.search(rf"执行用例 \d+/\d+: {re.escape(case_id)} .*?(?=执行用例 \d+/\d+: |\Z)", text, re.S)
        return m.group(0) if m else ""

    def case_marks(self, case_id: str) -> List[str]:
        return [m for m in self.marks if m.startswith(case_id + "_")]


def rodski_run(module: Path, target: str, *extra: str) -> Run:
    marker = Path(tempfile.mkstemp(prefix="rodski_cf_marker_", suffix=".txt")[1])
    result_dir = module / "result"
    before = set(result_dir.iterdir()) if result_dir.is_dir() else set()
    env = dict(os.environ, RODSKI_CF_MARKER=str(marker), PYTHONUNBUFFERED="1")
    proc = subprocess.run([*CLI, "run", target, "--headless", *extra], cwd=str(module), env=env,
                          capture_output=True, text=True, timeout=900)
    after = set(result_dir.iterdir()) if result_dir.is_dir() else set()
    new_dirs = sorted(p for p in after - before if p.is_dir())
    marks = [ln for ln in marker.read_text(encoding="utf-8").splitlines() if ln] if marker.exists() else []
    marker.unlink(missing_ok=True)
    return Run(proc, new_dirs[-1] if new_dirs else None, marks)


_MAIN: Optional[Run] = None


def main_run() -> Run:
    """case/flow/ 只真实执行一次，各检查项共享结果。"""
    global _MAIN
    if _MAIN is None:
        _MAIN = rodski_run(HERE, FLOW_DIR)
    return _MAIN


def expect(cond: bool, msg: str, ctx: str = "") -> None:
    if not cond:
        raise AssertionError(msg + (f"\n     --- 上下文 ---\n{ctx[-2500:]}" if ctx else ""))


def status_of(r: Run, case_id: str) -> Tuple[str, str]:
    res = r.results().get(case_id)
    expect(res is not None, f"result.xml 中缺少用例 {case_id}", r.out)
    return res.get("status", ""), res.get("error_message", "")


def expect_pass(r: Run, case_id: str) -> None:
    st, err = status_of(r, case_id)
    expect(st == "PASS", f"{case_id} 应 PASS，实际 {st}: {err[:300]}")


def expect_failed_as_designed(r: Run, case_id: str, token: str) -> None:
    """expect_fail=是 的用例：result 为 PASS 且 error_message 带 [预期失败] 前缀并指向故意失败的步骤。"""
    st, err = status_of(r, case_id)
    expect(st == "PASS" and err.startswith("[预期失败]"),
           f"{case_id} 应被框架判定为失败（expect_fail → PASS + [预期失败]），实际 status={st} error={err[:300]!r}")
    expect(token in err, f"{case_id} 的失败应来自 {token}，实际: {err[:300]!r}")


def expect_marks(r: Run, case_id: str, expected: List[str]) -> None:
    actual = r.case_marks(case_id)
    expect(actual == expected, f"{case_id} 执行轨迹不符:\n       期望 {expected}\n       实际 {actual}")


# ---------------------------------------------------------------- F062 三阶段
def c01() -> None:
    """C01 F062 预处理失败 → 跳过用例阶段（及预处理剩余步骤），仍执行后处理，整条判失败"""
    r = main_run()
    expect_failed_as_designed(r, "F062_01", "F062_01_pre_2_intended")
    expect_marks(r, "F062_01", ["F062_01_pre_1", "F062_01_post"])


def c02() -> None:
    """C02 F062 用例阶段失败 → 仍执行后处理，整条判失败"""
    r = main_run()
    expect_failed_as_designed(r, "F062_02", "F062_02_tc_2_intended")
    expect_marks(r, "F062_02", ["F062_02_pre", "F062_02_tc_1", "F062_02_post"])


def c03() -> None:
    """C03 F062 用例阶段通过、后处理失败 → 整条用例记为失败"""
    r = main_run()
    expect_failed_as_designed(r, "F062_03", "F062_03_post_intended")
    expect_marks(r, "F062_03", ["F062_03_tc"])


# ---------------------------------------------------------------- F066 depends
def c04() -> None:
    """C04 F066 depends 依赖 FAIL/SKIP → 依赖方 SKIP（含多依赖）；无关 scenario 照常；case 失败、后处理执行"""
    r = main_run()
    expect_failed_as_designed(r, "F066_01", "F066_01_S01_intended")
    expect_marks(r, "F066_01", ["F066_01_S03", "F066_01_S05", "F066_01_post"])
    seg = r.case_log("F066_01")
    for sid, dep in (("S02", "S01"), ("S04", "S02"), ("S06", "S01")):
        expect(re.search(rf"scenario {sid} .*-> SKIP \(depends not passed: {dep}\)", seg) is not None,
               f"execution.log 应记录 scenario {sid} SKIP（depends not passed: {dep}）", seg)
    expect_pass(r, "F066_02")
    expect_marks(r, "F066_02", ["F066_02_S01", "F066_02_S02"])


# ---------------------------------------------------------------- F067 if/else
def c05() -> None:
    """C05 F067 文本条件为假走 else（含为真对照、text_not_contains）"""
    r = main_run()
    expect_pass(r, "F067_01")
    expect_marks(r, "F067_01", ["F067_01_else", "F067_01_then", "F067_01_not_contains_else"])


def c06() -> None:
    """C06 F067 变量条件 ${flag}：为假走 else、为真走 then（GUIDE §3.8 支持变量引用）"""
    r = main_run()
    expect_pass(r, "F067_02")
    expect_marks(r, "F067_02", ["F067_02_else", "F067_02_then"])


def c07() -> None:
    """C07 F067 Return 条件 ${Return[-1].status} == 200（GUIDE §3.8 写法）：404 走 else、200 走 then"""
    r = main_run()
    expect_pass(r, "F067_03")
    expect_marks(r, "F067_03", ["F067_03_else", "F067_03_then"])


def c08() -> None:
    """C08 F067 Return 条件 ${Return[-1].status == 200}（CORE §12.3 写法）：404 走 else、200 走 then"""
    r = main_run()
    expect_pass(r, "F067_04")
    expect_marks(r, "F067_04", ["F067_04_else", "F067_04_then"])


def c09() -> None:
    """C09 F067 element_exists / element_not_exists 条件（CORE §12.3）"""
    r = main_run()
    expect_pass(r, "F067_05")
    expect_marks(r, "F067_05", ["F067_05_exists_missing_else", "F067_05_exists_present_then",
                                "F067_05_not_exists_present_else"])


# ---------------------------------------------------------------- F068 elif / 嵌套
def c10() -> None:
    """C10 F068 elif 链：命中第二个 elif；全假走 else；if 为真时 elif 不评估"""
    r = main_run()
    expect_pass(r, "F068_01")
    expect_marks(r, "F068_01", ["F068_01_a_elif2", "F068_01_b_else", "F068_01_c_if"])


def c11() -> None:
    """C11 F068 if 嵌套 2 层（内层 if/else）；外层为假时内层不评估"""
    r = main_run()
    expect_pass(r, "F068_02")
    expect_marks(r, "F068_02", ["F068_02_outer_then", "F068_02_inner1_else", "F068_02_inner2_then",
                                "F068_02_false_outer_else"])


def c12() -> None:
    """C12 F068 loop 内嵌 if/else（文本条件）：每轮都命中 then"""
    r = main_run()
    expect_pass(r, "F068_03")
    expect_marks(r, "F068_03", ["F068_03_iter_1", "F068_03_loopif_1", "F068_03_iter_2", "F068_03_loopif_2"])


def c13() -> None:
    """C13 F068 loop 内 if/elif/else 按 ${i} 分流：1→else、2→if、3→elif"""
    r = main_run()
    expect_pass(r, "F068_04")
    expect_marks(r, "F068_04", ["F068_04_else_1", "F068_04_if_2", "F068_04_elif_3"])


def c14() -> None:
    """C14 F068 变量 elif（GUIDE §3.8 变量引用 + CORE §12.2 elif 结构）：login_status=401 命中 elif"""
    r = main_run()
    expect_pass(r, "F068_05")
    expect_marks(r, "F068_05", ["F068_05_elif"])


def c15() -> None:
    """C15 F068 嵌套 if（CORE §12.2 原文 ${total} > 0 / ${total} >= 3）"""
    r = main_run()
    expect_pass(r, "F068_06")
    expect_marks(r, "F068_06", ["F068_06_outer", "F068_06_inner"])


def c16() -> None:
    """C16 F068 比较运算符 > < >= <= 均可正确求值"""
    r = main_run()
    expect_pass(r, "F068_07")


# ---------------------------------------------------------------- F069 loop
def c17() -> None:
    """C17 F069 loop range="1,2,3" 列举形式，${i} 在 run/DB/verify 的 data 中逐轮解析"""
    r = main_run()
    expect_pass(r, "F069_01")
    expect_marks(r, "F069_01", [f"F069_01_list_{i}" for i in (1, 2, 3)])


def c18() -> None:
    """C18 F069 loop range="1-3" 闭区间形式"""
    r = main_run()
    expect_pass(r, "F069_02")
    expect_marks(r, "F069_02", [f"F069_02_range_{i}" for i in (1, 2, 3)])


def c19() -> None:
    """C19 F069 loop range="1,5" 只循环 1 和 5 两次"""
    r = main_run()
    expect_pass(r, "F069_03")
    expect_marks(r, "F069_03", ["F069_03_sparse_1", "F069_03_sparse_5"])


# ---------------------------------------------------------------- F070 WaitTime / step_wait
def _wait_copy(wait_time: str, step_wait: Optional[str] = None) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="rodski_cf_wait_")) / "control_flow"
    shutil.copytree(HERE, tmp, ignore=shutil.ignore_patterns("result", "logs", "*.html", "__pycache__"))
    gv = tmp / "data" / "globalvalue.xml"
    text = re.sub(r'(<var name="WaitTime" value=")[^"]*(")', rf"\g<1>{wait_time}\2", gv.read_text(encoding="utf-8"))
    gv.write_text(text, encoding="utf-8")
    if step_wait is not None:
        f = tmp / "case" / "flow" / "wait_override.xml"
        f.write_text(re.sub(r'step_wait="[^"]*"', f'step_wait="{step_wait}"', f.read_text(encoding="utf-8")),
                     encoding="utf-8")
    return tmp


def _timed(case_file: str, case_id: str, wait_time: str, step_wait: Optional[str] = None) -> Tuple[float, str]:
    """在临时副本中执行，返回 (result.xml 中该用例 execution_time 秒, execution.log 文本)。"""
    mod = _wait_copy(wait_time, step_wait)
    try:
        r = rodski_run(mod, f"case/flow/{case_file}")
        expect_pass(r, case_id)
        expect(len(r.case_marks(case_id)) == 3, f"{case_id} 应执行 3 步，实际轨迹 {r.case_marks(case_id)}")
        return float(r.results()[case_id].get("execution_time") or 0), r.log()
    finally:
        shutil.rmtree(mod.parent, ignore_errors=True)


def c20() -> None:
    """C20 F070 WaitTime=0 不等待（3 步耗时 < 1s）"""
    t, _ = _timed("wait_basic.xml", "F070_01", "0")
    expect(t < 1.0, f"WaitTime=0 时 3 步耗时应 < 1s，实际 {t}s")


def c21() -> None:
    """C21 F070 WaitTime=800 按毫秒解释（3 步 × 0.8s，2.2s ≤ 耗时 < 4.5s，且无弃用告警）"""
    t, log = _timed("wait_basic.xml", "F070_01", "800")
    expect(2.2 <= t < 4.5, f"WaitTime=800ms × 3 步，耗时应在 [2.2, 4.5)s，实际 {t}s")
    expect(bool(log) and "[弃用]" not in log, "WaitTime=800 不应触发旧单位弃用告警", log)


def c22() -> None:
    """C22 F070 WaitTime=1（≤30 旧值）过渡期按秒解释：3 步 ≥ 2.7s，并打印一次弃用告警"""
    t, log = _timed("wait_basic.xml", "F070_01", "1")
    expect(2.7 <= t < 6.0, f"WaitTime=1（按秒）× 3 步，耗时应在 [2.7, 6)s，实际 {t}s")
    expect(log.count("[弃用] DefaultValue.WaitTime=1") == 1, "应打印且只打印一次 WaitTime 弃用告警", log)


def c23() -> None:
    """C23 F070 WaitTime=31（> 30 边界）按毫秒解释：3 步耗时 < 1s"""
    t, _ = _timed("wait_basic.xml", "F070_01", "31")
    expect(t < 1.0, f"WaitTime=31 应按 31ms 解释，3 步耗时应 < 1s，实际 {t}s")


def c24() -> None:
    """C24 F070 <cases step_wait="300"> 覆盖 WaitTime=1（旧秒值）：0.8s ≤ 耗时 < 2s（远小于按 WaitTime 的 3s）"""
    t, _ = _timed("wait_override.xml", "F070_02", "1")
    expect(0.8 <= t < 2.0, f"step_wait=300ms × 3 步应覆盖 WaitTime=1s，耗时应在 [0.8, 2)s，实际 {t}s")


def c25() -> None:
    """C25 F070 step_wait="0" 同样覆盖 WaitTime=800（写了就覆盖）：3 步耗时 < 1s"""
    t, _ = _timed("wait_override.xml", "F070_02", "800", step_wait="0")
    expect(t < 1.0, f"step_wait=0 应覆盖 WaitTime=800，耗时应 < 1s，实际 {t}s")


CHECKS: Dict[str, Callable[[], None]] = {
    "C01": c01, "C02": c02, "C03": c03, "C04": c04,
    "C05": c05, "C06": c06, "C07": c07, "C08": c08, "C09": c09,
    "C10": c10, "C11": c11, "C12": c12, "C13": c13, "C14": c14, "C15": c15, "C16": c16,
    "C17": c17, "C18": c18, "C19": c19,
    "C20": c20, "C21": c21, "C22": c22, "C23": c23, "C24": c24, "C25": c25,
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
            if key in KNOWN:
                counts["KNOWN"] += 1
                print(f"KNOWN {title}\n     缺陷: {KNOWN[key]}\n     现象: {str(e).splitlines()[0]}")
                if strict:
                    failed.append(key)
            else:
                counts["FAIL"] += 1
                failed.append(key)
                print(f"FAIL  {title}\n     {e}")
    if _MAIN is not None and _MAIN.run_dir:
        print(f"\n主运行目录: {_MAIN.run_dir}")
    print(f"验收结果: PASS {counts['PASS']} / KNOWN {counts['KNOWN']} / FAIL {counts['FAIL']}"
          f"（共 {len(selected)} 项）" + (f"，计为失败: {', '.join(failed)}" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
