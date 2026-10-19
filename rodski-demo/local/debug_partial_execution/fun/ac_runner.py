#!/usr/bin/env python3
"""REQ-012 调试与部分执行验收：python3 ac_runner.py AC-001

每个 AC 以子进程真实执行 debug_partial_execution_targets/ 下的被测用例，
按 REQ-012 v2 / SPEC-012-user-guide 的约定判定。通过时 stdout 输出 JSON 报告，
未通过时 stderr 输出逐项明细并以退出码 1 结束（rodski run 关键字据此判定步骤失败）。
"""
from __future__ import annotations

import json
import re
import sys
import time
import traceback

from dbg_harness import (AcFailed, Checker, TargetRun, debug_cli, finish, step_ok,
                         step_skipped)

STEPS_ALL = ["s2", "s3", "s5", "s7", "s8", "s11"]
BIZ_MAIN = ["node_open", "node_fill_vin", "node_submit", "node_confirm"]
BIZ_ALL = ["s_begin"] + BIZ_MAIN + ["inv_start", "inv_platform"] + BIZ_MAIN + ["s_end"]
MARKS_ALL = [f"m{i}" for i in range(1, 11)]
ROWS_ALL = [f"row_{i}" for i in range(1, 6)]


def launch(runs, case_file, *args):
    run = TargetRun(case_file, *args).start()
    runs.append(run)
    return run


def statuses(steps, indexes):
    return {i: (steps.get(i) or {}).get("status", "<缺失>") for i in indexes}


def check_steps_ok(c, run, indexes, desc):
    steps = run.steps()
    c.check(all(step_ok(steps.get(i)) for i in indexes), desc, f"步骤状态: {statuses(steps, indexes)}")


def continue_to_end(c, run, desc="输入 c 后执行完成，退出码 0"):
    run.send("c")
    c.equal(run.wait_exit(), 0, desc)


# ── A. 基础暂停与继续 ────────────────────────────────────────────
def ac_001(c, runs):
    run = launch(runs, "dbg_steps.xml", "--break-at", "step:5")
    pause = run.wait_pause()
    c.matches(pause["line"], r"Step\s*5\b", "暂停提示指明 Step 5")
    c.matches(pause["block"], r"Step\s*5\s*/\s*12", "暂停提示显示进度 Step 5/12")
    c.contains(pause["block"], "DBG_STEPS", "暂停提示包含所属 Case")
    c.equal(pause["markers"], ["s2", "s3"], "暂停时第 1~4 步已执行、第 5 步尚未执行")
    continue_to_end(c, run)
    c.equal(run.markers(), STEPS_ALL, "继续后第 5~12 步全部执行")
    check_steps_ok(c, run, range(1, 13), "execution_summary 中 12 个步骤全部通过")
    c.equal(len(run.pause_lines()), 1, "只暂停一次")


def ac_002(c, runs):
    run = launch(runs, "dbg_steps.xml", "--break-at", "step:9")
    pause = run.wait_pause()
    c.equal(pause["markers"], ["s2", "s3", "s5", "s7", "s8"], "暂停时第 1~8 步已执行")
    time.sleep(10)
    c.check(run.running() and run.markers() == pause["markers"], "暂停 10 秒期间进程保持阻塞、无步骤执行",
            f"running={run.running()} markers={run.markers()}")
    continue_to_end(c, run)
    check_steps_ok(c, run, [9, 10], "继续后第 9~10 步（type/verify 依赖原页面）通过")
    c.equal(run.markers(), STEPS_ALL, "继续后剩余步骤全部执行")
    c.equal(run.execution_log().count("启动浏览器"), 1, "整个执行只启动一次浏览器（继续后复用原浏览器）")


def ac_003(c, runs):
    run = launch(runs, "dbg_steps.xml", "--break-at", "step:5")
    run.wait_pause()
    run.send("s")
    c.equal(run.wait_exit(), 0, "输入 s 后执行完成，退出码 0")
    c.equal(run.markers(), ["s2", "s3", "s7", "s8", "s11"], "第 5 步未执行，第 6 步起继续执行")
    steps = run.steps()
    c.check(step_skipped(steps.get(5)), "execution_summary 中第 5 步状态为 skipped", f"实际: {statuses(steps, [5])}")
    others = [i for i in range(1, 13) if i != 5]
    c.check(all(step_ok(steps.get(i)) for i in others), "其余步骤全部通过", f"步骤状态: {statuses(steps, others)}")
    c.matches(run.output, r"SKIPPED|跳过", "终端提示第 5 步被跳过")


def ac_004(c, runs):
    run = launch(runs, "dbg_steps.xml", "--break-at", "step:5")
    run.wait_pause()
    run.send("q")
    run.wait_exit(timeout=30)
    c.equal(run.markers(), ["s2", "s3"], "中止后第 5 步及之后的步骤都未执行")
    c.matches(run.output, r"中止|abort", "终端提示执行已中止")
    steps = run.steps()
    c.check(not any(step_ok(steps.get(i)) for i in range(5, 13)), "execution_summary 中第 5~12 步没有通过记录",
            f"步骤状态: {statuses(steps, range(5, 13))}")


def ac_005(c, runs):
    run = launch(runs, "dbg_steps.xml", "--break-at", "step:3,step:7,step:11")
    expected = [(3, ["s2"]), (7, ["s2", "s3", "s5"]), (11, ["s2", "s3", "s5", "s7", "s8"])]
    for index, markers in expected:
        pause = run.wait_pause()
        c.matches(pause["line"], rf"Step\s*{index}\b", f"按顺序在 Step {index} 暂停")
        c.equal(pause["markers"], markers, f"Step {index} 暂停时之前的步骤已执行、本步未执行")
        run.send("c")
    c.equal(run.wait_exit(), 0, "三次继续后执行完成，退出码 0")
    c.equal(len(run.pause_lines()), 3, "共暂停 3 次")
    c.equal(run.markers(), STEPS_ALL, "全部步骤执行")


# ── B. 多层级断点 ────────────────────────────────────────────────
def ac_006(c, runs):
    run = launch(runs, "dbg_biz.xml", "--break-at", "node:fill_vin")
    first = run.wait_pause()
    c.contains(first["block"], "fill_vin", "暂停提示指明节点 fill_vin")
    c.equal(first["markers"], ["s_begin", "node_open"], "第一次调用中 fill_vin 节点前暂停")
    run.send("c")
    second = run.wait_pause()
    c.equal(second["markers"], ["s_begin"] + BIZ_MAIN + ["inv_start", "inv_platform", "node_open"],
            "第二次调用 debug_flow 时在 fill_vin 节点前再次暂停")
    continue_to_end(c, run)
    c.equal(len(run.pause_lines()), 2, "fill_vin 节点共命中 2 次")
    c.equal(run.markers(), BIZ_ALL, "继续后全部节点执行")


def ac_007(c, runs):
    run = launch(runs, "dbg_biz.xml", "--break-at", "flow:F_INVOICE_PLATFORM")
    pause = run.wait_pause()
    c.contains(pause["block"], "F_INVOICE_PLATFORM", "暂停提示指明 Flow F_INVOICE_PLATFORM")
    c.equal(pause["markers"], ["s_begin"] + BIZ_MAIN, "在 invoice_flow 的第一个节点之前暂停")
    continue_to_end(c, run)
    c.equal(len(run.pause_lines()), 1, "只在目标 Flow 暂停一次")
    c.equal(run.markers(), BIZ_ALL, "继续后全部节点执行")


def ac_008(c, runs):
    run = launch(runs, "dbg_steps.xml", "--break-at", "scenario:S002")
    pause = run.wait_pause()
    c.contains(pause["block"], "S002", "暂停提示指明 scenario S002")
    c.equal(pause["markers"], ["s2", "s3", "s5", "s7"], "S001 已执行完、S002 第一步尚未执行")
    continue_to_end(c, run)
    c.equal(len(run.pause_lines()), 1, "只暂停一次")
    c.equal(run.markers(), STEPS_ALL, "继续后全部步骤执行")


def ac_009(c, runs):
    run = launch(runs, "dbg_steps.xml", "--break-at", "driver:click")
    first = run.wait_pause()
    c.contains(first["line"], "click", "暂停提示指明驱动动作 click")
    c.contains(first["block"], "loginBtn", "暂停提示显示目标元素定位信息")
    c.equal(first["markers"], ["s2", "s3"], "第一次 click 在第 4 步 type 中暂停")
    run.send("c")
    second = run.wait_pause()
    c.equal(second["markers"], ["s2", "s3", "s5", "s7", "s8"], "第二次 click 在第 9 步 type 中暂停")
    continue_to_end(c, run)
    c.equal(len(run.pause_lines()), 2, "用例中 2 次 click 各暂停一次")


def ac_010(c, runs):
    run = launch(runs, "dbg_rows.xml", "--break-at", "batch:row:3")
    pause = run.wait_pause()
    c.matches(pause["block"], r"row\s*3", "暂停提示指明第 3 行")
    c.contains(pause["block"], "USER003", "暂停提示显示数据行 data_id=USER003")
    c.equal(pause["markers"], ["row_1", "row_2"], "前 2 行已完成，第 3 行尚未开始")
    continue_to_end(c, run)
    c.equal(len(run.pause_lines()), 1, "只暂停一次")
    c.equal(run.markers(), ROWS_ALL, "继续后第 3~5 行执行")


def ac_011(c, runs):
    run = launch(runs, "dbg_biz.xml", "--break-at", "business_call:call_again.node:fill_vin")
    pause = run.wait_pause()
    c.contains(pause["block"], "fill_vin", "暂停提示指明节点 fill_vin")
    c.equal(pause["markers"], ["s_begin"] + BIZ_MAIN + ["inv_start", "inv_platform", "node_open"],
            "只在 call_again 调用内的 fill_vin 前暂停（call_main 内的同名节点不命中）")
    continue_to_end(c, run)
    c.equal(len(run.pause_lines()), 1, "嵌套断点只命中一次")


# ── C. 部分执行 ──────────────────────────────────────────────────
def ac_012(c, runs):
    run = launch(runs, "dbg_marks.xml", "--start-from", "6")
    c.equal(run.wait_exit(), 0, "执行完成，退出码 0")
    c.equal(run.markers(), MARKS_ALL[5:], "只执行第 6~10 步")
    steps = run.steps()
    c.check(all(step_skipped(steps.get(i)) for i in range(1, 6)), "第 1~5 步标记为 skipped",
            f"步骤状态: {statuses(steps, range(1, 6))}")
    c.check(all(step_ok(steps.get(i)) for i in range(6, 11)), "第 6~10 步通过",
            f"步骤状态: {statuses(steps, range(6, 11))}")
    reasons = json.dumps([steps.get(i) for i in range(1, 6)], ensure_ascii=False)
    c.contains(reasons, "start-from", "跳过原因记录为 --start-from")
    c.matches(run.output, r"跳过|SKIPPED", "终端提示前 5 步被跳过")


def _business_partial(c, runs, case_file, expected, skipped_nodes):
    run = launch(runs, case_file)
    c.equal(run.wait_exit(), 0, "执行完成，退出码 0")
    c.equal(run.markers(), expected, f"只执行 {', '.join(m for m in expected if m.startswith('node_'))}")
    steps = run.steps().values()
    calls = [s for s in steps if s.get("action") == "business_call"]
    c.check(calls and step_ok(calls[0]), "business_call 步骤通过", f"business_call 记录: {calls}")
    detail = json.dumps(calls, ensure_ascii=False)
    for node in skipped_nodes:
        c.matches(detail, rf'{node}[^{{}}]*skip', f"business_result 记录节点 {node} 为 skipped")


def ac_013(c, runs):
    _business_partial(c, runs, "dbg_biz_from.xml",
                      ["s_begin", "node_submit", "node_confirm", "s_end"], ["open", "fill_vin"])


def ac_014(c, runs):
    _business_partial(c, runs, "dbg_biz_to.xml",
                      ["s_begin", "node_open", "node_fill_vin", "s_end"], ["submit", "confirm"])


def ac_015(c, runs):
    _business_partial(c, runs, "dbg_biz_range.xml",
                      ["s_begin", "node_fill_vin", "node_submit", "s_end"], ["open", "confirm"])


def ac_016(c, runs):
    first = launch(runs, "dbg_steps.xml", "--break-at", "step:9")
    pause = first.wait_pause()
    c.equal(pause["markers"], ["s2", "s3", "s5", "s7", "s8"], "第一次执行在第 9 步前暂停")
    first.send("q")
    first.wait_exit(timeout=30)
    second = launch(runs, "dbg_steps.xml", "--start-from", "9")
    second.wait_for(r"检测到现有浏览器对象", what="现有浏览器对象检测提示")
    c.contains(second.output, "DBG_STEPS.browser_obj_1", "提示中指明可复用对象 DBG_STEPS.browser_obj_1")
    c.contains(second.output, "[Y/n]", "提示询问是否复用 [Y/n]")
    second.send("Y")
    c.equal(second.wait_exit(), 0, "选择 Y 后执行完成，退出码 0")
    c.matches(second.output, r"复用", "终端提示已复用对象")
    check_steps_ok(c, second, [9, 10], "复用第一次执行的页面后第 9~10 步通过")
    c.equal(second.markers(), ["s11"], "第二次执行只从第 9 步开始")


def ac_017(c, runs):
    run = launch(runs, "dbg_needs_browser.xml", "--start-from", "3")
    run.wait_for(r"需要浏览器对象|浏览器对象.{0,40}(不存在|未检测到)", what="对象缺失警告")
    c.matches(run.output, r"\[1\].{0,6}中止", "提供选项 [1] 中止执行")
    c.matches(run.output, r"\[2\].{0,6}继续", "提供选项 [2] 继续执行")
    run.send("1")
    rc = run.wait_exit(timeout=30)
    c.check(rc != 0, "选择中止后退出码非 0", f"exit={rc}")
    c.equal(run.markers(), [], "中止后没有执行任何步骤")


def ac_018(c, runs):
    run = launch(runs, "dbg_steps.xml", "--group", "grp_second")
    c.equal(run.wait_exit(), 0, "执行完成，退出码 0")
    markers = run.markers()
    c.check("s8" in markers, "目标 scenario S002 已执行", f"轨迹: {markers}")
    c.check(not {"s3", "s5", "s7"} & set(markers), "非目标 scenario S001 未执行", f"轨迹: {markers}")
    # 未选中的 scenario 不进入步骤记录，序号会重排，按 scenario 定位而非全局序号
    steps = list(run.steps().values())
    s001 = [s for s in steps if "S001" in str(s.get("phase", ""))]
    s002 = [s for s in steps if "S002" in str(s.get("phase", ""))]
    c.check(not s001, "步骤记录中没有 S001 的步骤", f"S001 步骤: {s001}")
    c.check([s.get("action") for s in s002] == ["run", "type", "verify"] and all(step_ok(s) for s in s002),
            "S002 的 3 个步骤（含 type/verify）全部通过",
            f"S002 步骤: {[(s.get('action'), s.get('status')) for s in s002]}")


# ── D. 单步执行 ──────────────────────────────────────────────────
def ac_019(c, runs):
    run = launch(runs, "dbg_marks.xml", "--step-mode")
    pauses = run.drive(lambda pause: "c")
    counts = [len(p["markers"]) for p in pauses]
    c.check(len(pauses) >= 9, "单步模式下每个步骤之间都暂停（≥9 次）", f"暂停次数: {len(pauses)}")
    c.check(all(b - a == 1 for a, b in zip(counts, counts[1:])), "相邻两次暂停之间恰好执行一个步骤",
            f"每次暂停时已执行步骤数: {counts}")
    c.equal(run.proc.returncode, 0, "执行完成，退出码 0")
    c.equal(run.markers(), MARKS_ALL, "全部步骤执行")


def ac_020(c, runs):
    run = launch(runs, "dbg_marks.xml", "--step-mode")
    skipped = []

    def respond(pause):
        if len(pause["markers"]) == 3 and not skipped:
            skipped.append(pause)
            return "s"
        return "c"

    run.drive(respond)
    c.check(bool(skipped), "在第 4 步执行前出现暂停", "没有出现已执行 3 步时的暂停")
    c.equal(run.markers(), [m for m in MARKS_ALL if m != "m4"], "第 4 步被跳过，其余步骤执行")
    steps = run.steps()
    c.check(step_skipped(steps.get(4)), "execution_summary 中第 4 步为 skipped", f"实际: {statuses(steps, [4])}")


def ac_021(c, runs):
    run = launch(runs, "dbg_driver.xml", "--step-mode", "--driver-level")
    pauses = run.drive(lambda pause: "c")
    inside = [p for p in pauses if p["markers"] == ["d2"]]
    c.check(len(inside) >= 3, "第 3 步 type 内按驱动动作逐个暂停（≥3 次）", f"type 内暂停次数: {len(inside)}")
    text = "\n".join(p["block"][:400] for p in inside)
    c.contains(text, "fill", "驱动级单步暂停中出现 fill 动作")
    c.contains(text, "click", "驱动级单步暂停中出现 click 动作")
    c.equal(run.proc.returncode, 0, "执行完成，退出码 0")
    c.equal(run.markers(), ["d2", "d4"], "全部步骤执行")


# ── E. 驱动级别控制 ──────────────────────────────────────────────
def ac_022(c, runs):
    run = launch(runs, "dbg_driver.xml", "--break-at", "step:4")
    run.wait_pause()
    queue = debug_cli("queue")
    c.equal(queue["rc"], 0, "rodski debug queue 执行成功")
    for action in ("find_element", "fill", "click"):
        c.contains(queue["out"], action, f"执行队列包含驱动动作 {action}")
    c.check(queue["out"].count("✅") >= 4, "执行队列显示已完成动作（≥4 个 ✅）", queue["out"][-800:])
    c.matches(queue["out"], r"\d+\s*ms", "执行队列显示动作耗时")
    pending = debug_cli("queue", "--filter", "pending")
    c.equal(pending["rc"], 0, "rodski debug queue --filter pending 执行成功")
    c.check("✅" not in pending["out"], "--filter pending 不显示已完成动作", pending["out"][-800:])
    failed = debug_cli("queue", "--filter", "failed")
    c.equal(failed["rc"], 0, "rodski debug queue --filter failed 执行成功")
    continue_to_end(c, run)


def ac_023(c, runs):
    run = launch(runs, "dbg_driver.xml", "--break-at", "driver:fill")
    first = run.wait_pause()
    c.contains(first["line"], "fill", "暂停提示指明驱动动作 fill")
    c.contains(first["block"], "username", "第一次 fill 指向 username")
    c.equal(first["markers"], ["d2"], "在第 3 步 type 内暂停")
    run.send("c")
    second = run.wait_pause()
    c.contains(second["block"], "password", "第二次 fill 指向 password")
    continue_to_end(c, run)
    c.equal(len(run.pause_lines()), 2, "两次 fill 各暂停一次")
    c.equal(run.markers(), ["d2", "d4"], "全部步骤执行")


def ac_024(c, runs):
    run = launch(runs, "dbg_driver.xml")
    c.equal(run.wait_exit(), 0, "执行完成，退出码 0")
    records = run.driver_actions()
    required = ("seq", "timestamp", "action", "params", "duration_ms", "status", "context")
    missing = [r for r in records if any(k not in r for k in required)]
    c.check(records and not missing, "每条驱动动作都有 seq/timestamp/action/params/duration_ms/status/context",
            f"缺字段记录: {missing[:3]}")
    c.equal([r.get("seq") for r in records], list(range(1, len(records) + 1)), "seq 从 1 开始连续递增")
    actions = {r.get("action") for r in records}
    for action in ("navigate_to", "find_element", "fill", "click"):
        c.check(action in actions, f"记录了驱动动作 {action}", f"实际动作: {sorted(map(str, actions))}")
    bad_ctx = [r for r in records if not all((r.get("context") or {}).get(k) for k in ("case", "phase", "step"))]
    c.check(not bad_ctx, "每条记录的 context 包含 case/phase/step", f"示例: {bad_ctx[:2]}")
    c.check(all((r.get("context") or {}).get("case") == "DBG_DRIVER" for r in records), "context.case = DBG_DRIVER")
    c.contains(run.execution_log(), "[DriverAction]", "execution.log 记录驱动动作")


def ac_025(c, runs):
    run = launch(runs, "dbg_driver_fail.xml")
    rc = run.wait_exit()
    c.check(rc != 0, "被测用例失败（预期）", f"exit={rc}")
    records = run.driver_actions()
    failed = [r for r in records if str(r.get("status")).lower() == "failed"]
    if not c.check(bool(failed), "driver_actions.jsonl 中存在 status=failed 的动作", f"动作状态: {[r.get('status') for r in records]}"):
        return
    record = failed[0]
    seq = record.get("seq")
    c.contains(json.dumps(record.get("params"), ensure_ascii=False), "missing_button", "失败动作参数指明定位器 missing_button")
    c.check(bool(record.get("error")), "失败动作记录错误信息", json.dumps(record, ensure_ascii=False))
    ctx = record.get("context") or {}
    c.check(ctx.get("case") == "DBG_DRIVER_FAIL" and ctx.get("step"), "失败动作记录所属 Case 与步骤", json.dumps(ctx, ensure_ascii=False))
    c.check(bool(run.find_files(f"driver_action_{seq}_failed.png")), f"保存失败截图 driver_action_{seq}_failed.png",
            f"结果目录: {run.result_dir()}")
    text = run.output + run.execution_log()
    c.matches(text, rf"Driver\s*Action\]?\s*#{seq}\b.*(失败|❌)", f"日志显示 [Driver Action #{seq}] ... 失败")


def ac_026(c, runs):
    run = launch(runs, "dbg_driver.xml", "--trace", "--report", "html")
    c.equal(run.wait_exit(), 0, "执行完成，退出码 0")
    records = run.driver_actions()
    c.check(records and all(isinstance(r.get("duration_ms"), (int, float)) and r["duration_ms"] >= 0 for r in records),
            "每个驱动动作都有数值型 duration_ms（可用 jq 排序）", f"示例: {records[:2]}")
    c.check(bool(run.find_files("trace.json")), "--trace 生成 trace.json")
    reports = run.find_files("*.html")
    html = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in reports)
    c.check(bool(reports), "--report html 生成 HTML 报告")
    c.contains(html, "find_element", "报告性能统计包含驱动动作")
    c.matches(html, r"最慢|slowest", "报告列出最慢的驱动动作")


# ── F. 对象生命周期 ──────────────────────────────────────────────
def ac_027(c, runs):
    run = launch(runs, "dbg_steps.xml", "--break-at", "step:9")
    run.wait_pause()
    objects = debug_cli("objects")
    c.equal(objects["rc"], 0, "暂停时 rodski debug objects 执行成功")
    c.contains(objects["out"], "DBG_STEPS.browser_obj_1", "对象池中有 DBG_STEPS.browser_obj_1")
    c.contains(objects["out"], "alive", "暂停时对象状态为 alive")
    c.contains(objects["out"], "form.html", "浏览器对象显示当前 URL")
    continue_to_end(c, run)
    check_steps_ok(c, run, [9, 10], "继续后第 9~10 步在原页面上通过")
    c.equal(run.execution_log().count("启动浏览器"), 1, "继续后没有新建浏览器")


def ac_028(c, runs):
    names = []
    for round_no in (1, 2):
        run = launch(runs, "dbg_driver.xml")
        c.equal(run.wait_exit(), 0, f"第 {round_no} 次完整执行通过")
        found = re.search(r"新建浏览器对象\s*(DBG_DRIVER\.browser_obj_\d+)", run.output)
        c.check(bool(found), f"第 {round_no} 次执行提示新建浏览器对象", tail_of(run))
        c.contains(run.output, "rodski debug get-object", f"第 {round_no} 次执行提示可通过 rodski debug get-object 访问")
        names.append(found.group(1) if found else None)
    c.check(names[0] and names[1] and names[0] != names[1], "两次执行创建的是不同对象", f"对象名: {names}")


def ac_029(c, runs):
    run = launch(runs, "dbg_multi.xml", "--break-at", "step:3")
    run.wait_pause()
    objects = debug_cli("objects")
    c.equal(objects["rc"], 0, "rodski debug objects 执行成功")
    for name, page in (("DBG_MULTI.buyer_browser", "buyer.html"), ("DBG_MULTI.seller_browser", "seller.html")):
        c.contains(objects["out"], name, f"对象池中有 {name}")
        c.contains(objects["out"], page, f"{name} 显示各自的当前 URL")
    continue_to_end(c, run)
    check_steps_ok(c, run, [3, 4, 5], "target 指定对象的 type/verify 通过，卖家页面不受买家操作影响")


def ac_030(c, runs):
    run = launch(runs, "dbg_driver.xml", "--break-at", "step:4")
    run.wait_pause()
    objects = debug_cli("objects")
    c.matches(objects["out"], r"DBG_DRIVER\.browser_obj_\d+", "暂停时浏览器对象仍在对象池中")
    c.contains(objects["out"], "alive", "暂停时对象未被清理（alive）")
    continue_to_end(c, run)
    text = run.output + run.execution_log()
    c.matches(text, r"\[Object\]\s*DBG_DRIVER\.browser_obj_\d+\s+closed\s*\(total lifetime:\s*[\d.]+\s*s\)",
              "用例结束后自动关闭对象并记录 [Object] ... closed (total lifetime: Ns)")


# ── G. 执行查看与日志 ────────────────────────────────────────────
def _paused_at_step5(runs):
    run = launch(runs, "dbg_steps.xml", "--break-at", "step:5")
    run.wait_pause()
    return run


def ac_031(c, runs):
    run = _paused_at_step5(runs)
    status = debug_cli("status")
    c.equal(status["rc"], 0, "rodski debug status 执行成功")
    c.contains(status["out"], "DBG_STEPS", "显示当前 Case")
    c.matches(status["out"], r"5\s*/\s*12", "显示当前位置 Step 5/12")
    c.matches(status["out"], r"暂停|paused", "显示暂停状态")
    c.matches(status["out"], r"已完成|completed|待执行|pending", "显示已完成/待执行统计")
    continue_to_end(c, run)


def ac_032(c, runs):
    run = _paused_at_step5(runs)
    context = debug_cli("context")
    c.equal(context["rc"], 0, "rodski debug context 执行成功")
    c.contains(context["out"], "Return[-1]", "显示 ${Return[-1]}")
    c.contains(context["out"], "Return[-2]", "显示 ${Return[-2]}")
    c.contains(context["out"], "s3", "Return 栈包含第 3 步的真实返回值 s3")
    c.contains(context["out"], "GlobalValue", "显示 GlobalValue")
    c.contains(context["out"], "127.0.0.1:18765", "GlobalValue 显示 Site.URL 的真实值")
    c.contains(context["out"], "S001", "显示当前 scenario")
    continue_to_end(c, run)


def ac_033(c, runs):
    run = _paused_at_step5(runs)
    found = debug_cli("get-object", "DBG_STEPS.browser_obj_1")
    c.equal(found["rc"], 0, "rodski debug get-object 执行成功")
    c.contains(found["out"], "form.html", "显示对象当前 URL")
    c.contains(found["out"], "alive", "显示对象状态")
    c.contains(found["out"], "get_object(", "提供 Python 访问示例")
    missing = debug_cli("get-object", "DBG_STEPS.no_such_object")
    c.check(missing["rc"] != 0, "获取不存在的对象时返回非 0", missing["out"][-400:])
    continue_to_end(c, run)


def ac_034(c, runs):
    run = launch(runs, "dbg_biz.xml")
    c.equal(run.wait_exit(), 0, "执行完成，退出码 0")
    log = run.execution_log()
    for level in ("[Case]", "[Phase]", "[BusinessCall]", "[Flow]", "[Node]", "[Step]", "[DriverAction]"):
        c.contains(log, level, f"execution.log 包含 {level} 层级")
    c.matches(log, r"完成.{0,6}\(\d+\s*ms\)", "各层级记录完成与耗时")
    c.matches(log, r"\]\s{2,}\[DriverAction\]", "DriverAction 相对 Step 缩进")
    c.check(bool(run.find_files("driver_actions*.jsonl")), "同时生成 driver_actions.jsonl")


# ── H. 与数据驱动联动（数据行只由调试命令动态指定） ────────────────
def ac_035(c, runs):
    run = launch(runs, "dbg_rows.xml", "--rows", "USER003", "--break-at", "driver:fill")
    pause = run.wait_pause()
    c.contains(pause["block"], "USER003", "暂停提示显示当前数据行 USER003")
    c.matches(pause["block"], r"Row", "暂停提示显示 Row 信息")
    c.equal(pause["markers"], [], "第 1~2 行未执行（只执行 USER003）")
    context = debug_cli("context")
    c.contains(context["out"], "${ROW.", "rodski debug context 显示 ${ROW.*}")
    c.contains(context["out"], "USER003", "ROW 变量对应 USER003")
    run.send("c")
    run.drive(lambda p: "c")
    c.equal(run.proc.returncode, 0, "执行完成，退出码 0")
    c.equal(run.markers(), ["row_3"], "只执行了数据行 USER003")


def ac_036(c, runs):
    first = launch(runs, "dbg_rows.xml", "--rows", "USER003", "--break-at", "step:3")
    pause = first.wait_pause()
    c.equal(pause["markers"], [], "第一次执行在 USER003 行的第 3 步前暂停")
    first.send("q")
    first.wait_exit(timeout=30)
    second = launch(runs, "dbg_rows.xml", "--rows", "USER003", "--start-from", "3")
    second.wait_for(r"检测到数据行\s*USER003", what="数据行续跑提示")
    c.matches(second.output, r"上次执行到\s*Step\s*2", "提示上次执行到 Step 2")
    c.contains(second.output, "[Y/n]", "询问是否继续 [Y/n]")
    second.send("Y")
    c.equal(second.wait_exit(), 0, "选择 Y 后执行完成，退出码 0")
    c.matches(second.output, r"复用", "复用第一次执行的浏览器对象")
    check_steps_ok(c, second, [3], "从第 3 步 verify 继续，并在原页面上通过")
    c.equal(second.markers(), ["row_3"], "第二次执行只完成 USER003 的剩余步骤")


def ac_037(c, runs):
    run = launch(runs, "dbg_rows.xml")
    c.equal(run.wait_exit(), 0, "执行完成，退出码 0")
    records = run.driver_actions()
    fills = [r for r in records if r.get("action") == "fill"]
    c.equal(len(fills), 10, "5 行 × 2 个输入框共 10 次 fill")
    pairs = {((r.get("context") or {}).get("row"), (r.get("context") or {}).get("data_id")) for r in fills}
    c.equal(pairs, {(i, f"USER00{i}") for i in range(1, 6)}, "每个 fill 的 context 记录 row 与 data_id")
    row2 = [r for r in records if (r.get("context") or {}).get("row") == 2]
    c.check(row2 and all(r["context"].get("data_id") == "USER002" for r in row2),
            "按 context.row == 2 过滤只得到 USER002 的动作", f"row=2 记录数: {len(row2)}")


def tail_of(run):
    return "\n".join(run.output.splitlines()[-20:])


ACS = {f"AC-{name[3:]}": fn for name, fn in globals().items() if re.fullmatch(r"ac_\d{3}", name)}


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in ACS:
        print(f"用法: ac_runner.py <{'|'.join(sorted(ACS))}>", file=sys.stderr)
        return 2
    checker = Checker(sys.argv[1])
    runs = []
    try:
        ACS[sys.argv[1]](checker, runs)
    except AcFailed as exc:
        checker.check(False, "执行过程中断", str(exc))
    except Exception:  # 验收脚本自身异常也要如实报告
        checker.check(False, "验收脚本异常", traceback.format_exc())
    return finish(checker, runs)


if __name__ == "__main__":
    sys.exit(main())
