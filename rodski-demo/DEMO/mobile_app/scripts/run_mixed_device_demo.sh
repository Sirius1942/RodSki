#!/usr/bin/env bash
#
# run_mixed_device_demo.sh — RodSki 异构设备计划队列验收（v11.3.0）
#
# 验收目标：**一台 iOS 真机 + 一台 iOS 模拟器同时跑 app 测试**，且
#   - 一个计划只在一台设备上整体执行（计划不被拆分）；
#   - 先跑完的设备回去领下一个计划（动态领取，而非静态均分）；
#   - 两台设备共用同一个 Appium server，互不抢占 WDA 端口。
#
# 与 run_dual_device_demo.sh（两台模拟器）的区别：本脚本的两台设备**平台相同但
# 设备类别不同** —— 真机走 XCUITest 的真实设备路径（需要签名 WDA），模拟器走
# 模拟器路径。这两条路径在 Appium 内部差异很大，混跑是比双模拟器更强的验收。
#
# 预期排班（真机显著慢于模拟器）：
#   模拟器：[ mixed_short_a ]→[ mixed_short_c ]
#   真机  ：[ ............ mixed_long_b ............ ]
# 但调度是动态的，脚本只断言「每个计划恰好被一台设备整体执行一次」与「区间重叠」，
# 不假定哪台设备领哪个计划。
#
# 用法：
#   bash scripts/run_mixed_device_demo.sh
#   SIMULATOR_NAME="iPhone 16 Pro" bash scripts/run_mixed_device_demo.sh
#   DEVICE_UDID=00008130-001979EE3CF3803A bash scripts/run_mixed_device_demo.sh
#   WARMUP=0 bash scripts/run_mixed_device_demo.sh     # 跳过真机预热（WDA 已建好时）
#
# 前置：
#   - macOS + Xcode（xcrun simctl / devicectl）
#   - Appium server 运行在 127.0.0.1:4723，且已装 xcuitest driver
#   - 真机：USB 连接、已配对、**开发者模式已开**、可信
#   - 真机 App：bash demo_ios_app/build_ios_device_app.sh install
#   - 模拟器 App：bash demo_ios_app/build_ios_app.sh install（或已装）
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

BUNDLE_ID="com.rodski.demo"
APPIUM_PORT="${APPIUM_PORT:-4723}"
SIMULATOR_NAME="${SIMULATOR_NAME:-iPhone 16}"
PLANS="@mixed_short_a,@mixed_long_b,@mixed_short_c"
WARMUP="${WARMUP:-1}"

# 计划 → 该计划唯一选中的 case id（断言 7 用：证明子进程真走了既有链路）
declare -a PLAN_IDS=(mixed_short_a mixed_long_b mixed_short_c)
declare -a PLAN_CASE_IDS=(APP002 APP003 APP001)

# ─────────────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────────────
ok()   { echo "[OK]   $*"; }
info() { echo "[INFO] $*"; }
warn() { echo "[WARN] $*"; }
fail() { echo "[FAIL] $*" >&2; exit 1; }

# ─────────────────────────────────────────────────────
# Step 1：环境检查
# ─────────────────────────────────────────────────────
echo ""
echo "=== [1/6] 环境检查 ==="

[[ "$(uname)" == "Darwin" ]] || fail "iOS 设备测试仅支持 macOS，当前系统：$(uname)"
command -v xcrun  >/dev/null || fail "xcrun 未找到，请安装 Xcode Command Line Tools"
command -v rodski >/dev/null || fail "rodski 命令未找到，请先 pip install -e rodski/"

if ! curl -sf "http://127.0.0.1:${APPIUM_PORT}/status" >/dev/null; then
  fail "Appium server 未在 127.0.0.1:${APPIUM_PORT} 运行。请先执行：appium --address 127.0.0.1 --port ${APPIUM_PORT}"
fi
ok "Appium server: 127.0.0.1:${APPIUM_PORT}"

# ─────────────────────────────────────────────────────
# Step 2：解析真机（devicectl）
# ─────────────────────────────────────────────────────
echo ""
echo "=== [2/6] 解析真机（devicectl）==="

# 真机不走 simctl。devicectl 的 --json-output 是 Apple 唯一承诺对脚本稳定的接口，
# stdout 仅面向人眼、不保证跨版本稳定。
# 判据只用 wired + paired + physical + platform=ios：tunnelState 在开发者模式
# 刚开、隧道尚未建立时是 disconnected，拿它当可用性判据会误杀正常设备。
probe_real_devices() {
  local out
  out="$(mktemp -t rodski_devices)"
  xcrun devicectl list devices --json-output "$out" >/dev/null 2>&1 || true
  [[ -s "$out" ]] || { rm -f "$out"; return 0; }
  python3 - "$out" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1]))
for x in payload.get("result", {}).get("devices", []):
    props = x.get("deviceProperties", {}) or {}
    conn  = x.get("connectionProperties", {}) or {}
    hw    = x.get("hardwareProperties", {}) or {}
    if (hw.get("platform") or "").lower() != "ios":
        continue
    if (hw.get("reality") or "").lower() != "physical":
        continue
    if conn.get("transportType") != "wired" or conn.get("pairingState") != "paired":
        continue
    print("\t".join([
        hw.get("udid", ""),
        props.get("name", ""),
        props.get("osVersionNumber", ""),
        props.get("developerModeStatus", "unknown"),
    ]))
PY
  rm -f "$out"
}

if [[ -n "${DEVICE_UDID:-}" ]]; then
  REAL_UDID="$DEVICE_UDID"
  REAL_NAME="explicit"
  REAL_IOS=""
  REAL_DEV_MODE="unknown"
  ok "使用显式真机 UDID：$REAL_UDID"
else
  # macOS 自带 bash 3.2 没有 mapfile，用 while-read 收集（进程替换不受影响）
  _real=()
  while IFS= read -r _line; do
    [[ -n "$_line" ]] && _real+=("$_line")
  done < <(probe_real_devices)

  [[ "${#_real[@]}" -gt 0 ]] || fail "未探测到已连接的真机。
  排查：
    1) USB 是否连接、手机上是否点了「信任」
    2) xcrun devicectl list devices      应显示 state=available (paired)
    3) 开发者模式：设置 > 隐私与安全性 > 开发者模式"
  if [[ "${#_real[@]}" -gt 1 ]]; then
    echo "  探测到多台真机，请用 DEVICE_UDID 指定其一："
    for l in "${_real[@]}"; do echo "    $(cut -f1 <<<"$l")  $(cut -f2 <<<"$l")  iOS $(cut -f3 <<<"$l")"; done
    fail "目标真机不唯一"
  fi
  REAL_UDID="$(cut -f1 <<<"${_real[0]}")"
  REAL_NAME="$(cut -f2 <<<"${_real[0]}")"
  REAL_IOS="$(cut -f3 <<<"${_real[0]}")"
  REAL_DEV_MODE="$(cut -f4 <<<"${_real[0]}")"
  ok "真机：$REAL_NAME  iOS $REAL_IOS  $REAL_UDID"
fi

# 开发者模式是硬前置：关闭时 WDA 无法部署，错误信息会埋在 Appium 日志深处
if [[ "$REAL_DEV_MODE" == "disabled" ]]; then
  fail "真机开发者模式未开启。请在手机上：设置 > 隐私与安全性 > 开发者模式 → 打开 → 重启 → 确认。"
elif [[ "$REAL_DEV_MODE" != "unknown" ]]; then
  ok "真机开发者模式：$REAL_DEV_MODE"
fi

# ─────────────────────────────────────────────────────
# Step 3：解析并启动模拟器（simctl）
# ─────────────────────────────────────────────────────
echo ""
echo "=== [3/6] 准备模拟器（simctl）==="

resolve_sim_udid() {
  xcrun simctl list devices available --json 2>/dev/null \
    | python3 -c "
import json, sys
name = sys.argv[1]
data = json.load(sys.stdin)
for runtime, devices in data.get('devices', {}).items():
    for d in devices:
        if d.get('name') == name and d.get('isAvailable'):
            print(d['udid']); raise SystemExit
raise SystemExit(1)
" "$SIMULATOR_NAME" 2>/dev/null
}

SIM_UDID="$(resolve_sim_udid)" || fail "未找到可用模拟器：$SIMULATOR_NAME"
[[ "$SIM_UDID" != "$REAL_UDID" ]] || fail "模拟器与真机解析到同一 UDID：$SIM_UDID"
ok "模拟器：$SIMULATOR_NAME  $SIM_UDID"

if xcrun simctl list devices booted 2>/dev/null | grep -q "$SIM_UDID"; then
  ok "$SIMULATOR_NAME 已是 Booted"
else
  info "启动 $SIMULATOR_NAME ..."
  xcrun simctl boot "$SIM_UDID" 2>/dev/null || true
  waited=0
  while ! xcrun simctl list devices booted 2>/dev/null | grep -q "$SIM_UDID"; do
    sleep 2; waited=$((waited + 2))
    [[ $waited -ge 120 ]] && fail "等待 $SIMULATOR_NAME 启动超时（120s）"
  done
  ok "$SIMULATOR_NAME 已启动"
fi
open -a Simulator 2>/dev/null || warn "无法打开 Simulator.app（headless 可忽略）"

# ─────────────────────────────────────────────────────
# Step 4：确认两台设备都装了被测 App
# ─────────────────────────────────────────────────────
echo ""
echo "=== [4/6] 校验被测 App ==="

SIM_HAS_APP="$(xcrun simctl listapps "$SIM_UDID" 2>/dev/null | grep -c "$BUNDLE_ID" || true)"
if [[ "$SIM_HAS_APP" -gt 0 ]]; then
  ok "模拟器已装 $BUNDLE_ID"
else
  fail "模拟器未装 ${BUNDLE_ID}。请运行：bash demo_ios_app/build_ios_app.sh install"
fi

# 注意 --include-all-apps：默认调用在部分 Xcode 版本上**静默返回 0 个应用**
# （不报错、退出码 0），会被误读成「真机没装 App」。显式要求列出全部应用才可靠。
REAL_APPS="$(xcrun devicectl device info apps --device "$REAL_UDID" --include-all-apps 2>&1 || true)"
if grep -q "$BUNDLE_ID" <<<"$REAL_APPS"; then
  ok "真机已装 $BUNDLE_ID"
elif grep -q "kAMDMobileImageMounterDeviceLocked\|could not be mounted" <<<"$REAL_APPS"; then
  # 手机锁屏时开发者磁盘映像挂不上，devicectl 会以「查不到应用」的形式失败 ——
  # 直接断言「未装 App」会把人引向错误的排查方向（重装 App 没有用，解锁才有用）。
  fail "真机锁屏：开发者磁盘映像无法挂载，devicectl 读不到应用列表。
  请在手机上**解锁并保持亮屏**，然后重跑本脚本。
  （一旦解锁过，后续 Appium 建会话也不需要保持亮屏，但首次 DDI 挂载需要。）"
else
  fail "真机未装 ${BUNDLE_ID}。请运行：bash demo_ios_app/build_ios_device_app.sh install
  （该脚本需要**有效**的开发证书：security find-identity -v -p codesigning 有输出。
    证书被吊销时它不列出，但 find-identity -p codesigning 会显示 CSSMERR_TP_CERT_REVOKED。）"
fi

# ─────────────────────────────────────────────────────
# Step 5：真机预热（可选）+ 队列执行
# ─────────────────────────────────────────────────────
echo ""
echo "=== [5/6] 真机预热（首次会编译并部署 WebDriverAgent，可能需要数分钟）==="

# 预热的意义：真机首次跑 XCUITest 要现编译 WDA 并部署到手机上，这一步又慢又容易
# 在冷环境下失败。把它放在计时窗口之外，队列里测的才是「调度」而不是「首次部署」。
if [[ "$WARMUP" == "1" ]]; then
  info "在真机上跑一次 @mixed_short_c 预热（结果不计入本脚本断言）"
  cd "$MODULE_DIR"
  set +e
  rodski run @mixed_short_c --platform ios --udid "$REAL_UDID"
  WARM_CODE=$?
  set -e
  if [[ $WARM_CODE -eq 0 ]]; then
    ok "真机预热通过"
  else
    fail "真机预热失败（exit=${WARM_CODE}）。请先单独排查真机链路：
    cd $MODULE_DIR && rodski run @mixed_short_c --platform ios --udid $REAL_UDID
  常见原因：开发者模式未开、证书过期、手机未信任本机、WDA 编译失败（看 Appium 日志）"
  fi
else
  warn "WARMUP=0，跳过预热（真机 WDA 未建好时首次队列执行会很慢或失败）"
fi

echo ""
echo "=== [5/6] 队列执行：真机 + 模拟器（设备由执行层配置决定）==="
info "计划：$PLANS"
info "设备：真机 ${REAL_UDID:0:12}  +  模拟器 ${SIM_UDID:0:8}"

# v11.3.0：设备数量与组合来自 data/globalvalue_ios.xml 的 Mobile 组
#   DeviceCount=2 / DeviceMix=real,simulator
# 队列据此自动发现并选择，**不需要**在这里手敲 UDID 列表 —— 命令里能写死的
# 设备池，换台机器就失效；写在用例目录里的配置才是随用例版本化的。
#
# 先干跑一次确认「配置选中的」正好是本脚本 boot 的这两台：本机可能同时有别的
# 模拟器处于 Booted，那样配置会合法地选到另一台（而那台上未必装了被测 app）。
# 与其在断言阶段才发现，不如在这里就说清楚，并给出可执行的处置办法。
cd "$MODULE_DIR"
set +e
DRY_OUT=$(rodski queue --plans "$PLANS" --platform ios --dry-run 2>&1)
DRY_CODE=$?
set -e
echo "$DRY_OUT"
[[ $DRY_CODE -eq 0 ]] || fail "设备预检失败（exit=${DRY_CODE}）"

SELECTED=$(python3 - "$DRY_OUT" <<'PY'
import re, sys
udids = re.findall(r"-\s+\[\S+\]\s+(\S+)", sys.argv[1])
print(",".join(udids))
PY
)
if [[ "$SELECTED" != "$REAL_UDID,$SIM_UDID" ]]; then
  echo ""
  fail "配置选中的设备与预期不符。
  配置选中：$SELECTED
  本脚本预期：$REAL_UDID,$SIM_UDID

  多半是另一台模拟器也处于 Booted，被 DeviceMix=simulator 合法地选了进去。
  处置（任选其一）：
    1) 关掉多余的模拟器：xcrun simctl shutdown <多余的 UDID>
    2) 指定本脚本要用的那台：SIMULATOR_NAME=\"$SIMULATOR_NAME\" bash $0
    3) 在 globalvalue_ios.xml 里用 DeviceList 显式钉住设备池"
fi
ok "配置选中设备与预期一致：真机 + 模拟器"

RUN_START=$(date +%s)
set +e
rodski queue --plans "$PLANS" --platform ios
RUN_CODE=$?
set -e
RUN_WALL=$(( $(date +%s) - RUN_START ))
echo ""
echo "队列退出码=$RUN_CODE 墙钟=${RUN_WALL}s"
[[ $RUN_CODE -eq 0 ]] || fail "队列未通过（exit=${RUN_CODE}）"
ok "队列执行完成"

QUEUE_DIR=$(python3 -c "
import glob, os
dirs = glob.glob('result/rodski_*_queue')
print(max(dirs, key=os.path.getmtime) if dirs else '')
")
[[ -n "$QUEUE_DIR" ]] || fail "未找到队列结果目录"
ok "队列结果目录：$QUEUE_DIR"

# ─────────────────────────────────────────────────────
# Step 6：断言
# ─────────────────────────────────────────────────────
echo ""
echo "=== [6/6] 验收断言 ==="

python3 - "$QUEUE_DIR" "$REAL_UDID" "$SIM_UDID" "$RUN_WALL" "${PLAN_IDS[@]}" -- "${PLAN_CASE_IDS[@]}" <<'PY'
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

argv = sys.argv[1:]
sep = argv.index("--")
queue_dir, real_udid, sim_udid, wall = argv[:4]
plan_ids = argv[4:sep]
case_ids = argv[sep + 1:]
expected_case = dict(zip(plan_ids, case_ids))
wall = int(wall)

failures = []


def check(no, title, condition, detail=""):
    mark = "✅" if condition else "❌"
    print(f"  {mark} 断言 {no}：{title}" + (f"  —— {detail}" if detail else ""))
    if not condition:
        failures.append(no)


def ts(value):
    return datetime.fromisoformat(value)


def overlap_seconds(p1, p2):
    start = max(ts(p1["started_at"]), ts(p2["started_at"]))
    end = min(ts(p1["finished_at"]), ts(p2["finished_at"]))
    return max(0.0, (end - start).total_seconds())


def distinct_cases(result_xml: Path):
    """result.xml 里**实际执行**的 case_id 集合 —— 证明子进程真的走了既有 run 链路。

    result.xml 会列出模块内全部用例：计划选中的执行、未选中的记为 SKIP。
    故这里只取非 SKIP 的，它才等于该计划实际选的 case。
    """
    root = ET.parse(result_xml).getroot()
    return {r.get("case_id") for r in root.iter("result")
            if r.get("case_id") and (r.get("status") or "").upper() != "SKIP"}


def port_slot(udid: str) -> int:
    """与框架 core/keyword_engine.mobile_port_slot 同一算法（并发端口槽）。"""
    return int(hashlib.sha1(str(udid).encode()).hexdigest(), 16) % 100


summary = json.loads((Path(queue_dir) / "summary.json").read_text(encoding="utf-8"))
plans = summary["plans"]
by_id = {p["plan_id"]: p for p in plans}

print(f"\n  排队结果（{queue_dir}）：")
for p in plans:
    kind = "真机  " if p["device_udid"] == real_udid else "模拟器"
    print(f"    {p['plan_id']:16} {kind} {p['device_udid'][:12]:12}  {p['status']:5} "
          f"{p['started_at'][11:23]} → {p['finished_at'][11:23]}  {p['duration']:6.1f}s")
print(f"    并发端口槽：真机 wda={8100 + port_slot(real_udid) * 10}  "
      f"模拟器 wda={8100 + port_slot(sim_udid) * 10}\n")

# ── 断言 1：两台**异构**设备都被用上（一台真机、一台模拟器）──────────
used = {p["device_udid"] for p in plans}
check(1, "真机与模拟器都被实际调度到（异构设备混跑）",
      used == {real_udid, sim_udid},
      f"实际使用 {sorted(u[:12] for u in used)}；期望 {{{real_udid[:12]}, {sim_udid[:8]}}}")

# ── 断言 2：真并行（区间重叠 > 5s，串行不可能产生）──────────────────
best = (0.0, None, None)
for i, p1 in enumerate(plans):
    for p2 in plans[i + 1:]:
        if p1["device_udid"] == p2["device_udid"]:
            continue
        ov = overlap_seconds(p1, p2)
        if ov > best[0]:
            best = (ov, p1, p2)
ov, p1, p2 = best
check(2, "真机与模拟器上的计划时间区间重叠 > 5s（真并行，非串行）",
      ov > 5.0,
      f"最大重叠 {ov:.1f}s（{p1['plan_id']}×{p2['plan_id']}）" if p1
      else "无跨设备计划对")

# ── 断言 3：计划不被拆分 ────────────────────────────────────────
ids = [p["plan_id"] for p in plans]
check(3, "每个计划恰好出现在一条结果里（计划粒度，不被拆分到两台设备）",
      len(ids) == len(set(ids)) == len(plan_ids) and set(ids) == set(plan_ids),
      f"计划 {sorted(ids)}")

# ── 断言 4：动态领取（有设备跑了 ≥2 个计划）──────────────────────
per_device = {}
for p in plans:
    per_device.setdefault(p["device_udid"], []).append(p["plan_id"])
multi = {u: v for u, v in per_device.items() if len(v) >= 2}
check(4, "某台设备领了 ≥2 个计划（先跑完的回去再领，动态而非静态均分）",
      bool(multi),
      f"{ {(('真机' if u == real_udid else '模拟器')): v for u, v in per_device.items()} }")

# ── 断言 5：全通过 ─────────────────────────────────────────────
check(5, "队列全部通过（exit_code=0、failed=0、error=0、每条计划 exit_code=0）",
      summary["exit_code"] == 0 and summary["summary"]["failed"] == 0
      and summary["summary"]["error"] == 0
      and all(p["status"] == "PASS" and p["exit_code"] == 0 for p in plans),
      f"{summary['summary']}")

# ── 断言 6：并发端口隔离（真机与模拟器拿到不同 WDA 端口槽）──────────
slot_real, slot_sim = port_slot(real_udid), port_slot(sim_udid)
check(6, "真机与模拟器的 WDA 端口槽不同（不会复用彼此的 WebDriverAgent）",
      slot_real != slot_sim,
      f"真机 slot={slot_real} (wda {8100 + slot_real * 10})，"
      f"模拟器 slot={slot_sim} (wda {8100 + slot_sim * 10})")

# ── 断言 7：子进程证据（run_dir 里的 result.xml 与计划相符）──────────
evidence = []
for p in plans:
    run_dir = Path(p["run_dir"]) if p["run_dir"] else None
    result_xml = (run_dir / "result.xml") if run_dir else None
    if not result_xml or not result_xml.exists():
        evidence.append(f"{p['plan_id']}: 无 result.xml")
        continue
    got = distinct_cases(result_xml)
    want = {expected_case[p["plan_id"]]}
    if not got <= want or not got:
        evidence.append(f"{p['plan_id']}: 期望 {want}，实际 {got}")
    else:
        evidence.append(f"{p['plan_id']}→{sorted(got)[0]}")
check(7, "每个计划的结果目录里都有与计划相符的 result.xml（子进程走了既有链路）",
      all("→" in e for e in evidence),
      ", ".join(evidence))

# ── 断言 8：真机确实执行了计划（不是被模拟器全包）──────────────────
real_plans = per_device.get(real_udid, [])
check(8, "真机至少完整执行了 1 个计划（真机链路真实生效，非空跑）",
      len(real_plans) >= 1,
      f"真机执行 {real_plans or '无'}")

print("")
if failures:
    print(f"❌ 真机 + 模拟器混跑验收失败，未通过断言：{sorted(failures)}")
    raise SystemExit(1)

print(f"✅ 真机 + 模拟器混跑验收通过（8/8 断言）—— 墙钟 {wall}s")
PY

echo ""
echo "=== 验收完成 ==="
echo ""
echo "产物："
echo "  $QUEUE_DIR/summary.json"
