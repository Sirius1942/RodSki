#!/usr/bin/env bash
#
# run_dual_device_demo.sh — RodSki 多设备计划队列验收（v11.2.0）
#
# 验收目标：**两台 iOS 模拟器同时跑 app 测试**，且
#   - 一个计划只在一台设备上整体执行（计划不被拆分）；
#   - 先跑完的设备回去领下一个计划（动态领取，而非静态均分）。
#
# 做法：三个长度不等的计划放进 `rodski queue`，两台模拟器各领其一；
# 再用「同样三个计划、只给一台设备」作负对照（必然串行）。
#
# 预期排班（两台设备）：
#   设备 x：[ queue_short_a ]→[ queue_short_c ]
#   设备 y：[ ............ queue_long_b ............ ]
#
# 用法：
#   bash scripts/run_dual_device_demo.sh
#   SKIP_BOOT=1 bash scripts/run_dual_device_demo.sh     # 模拟器已 boot 时跳过启动
#   DEVICE_NAMES="iPhone 16,iPhone 16 Pro" bash scripts/run_dual_device_demo.sh
#
# 前置：
#   - macOS + Xcode（xcrun simctl）
#   - Appium server 运行在 127.0.0.1:4723，且已装 xcuitest driver
#   - demo_ios_app 已编译（build/Build/Products/Debug-iphonesimulator/RodskiDemo.app）
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$MODULE_DIR/../../.." && pwd)"

BUNDLE_ID="com.rodski.demo"
APPIUM_PORT="${APPIUM_PORT:-4723}"
APP_PATH="$MODULE_DIR/demo_ios_app/build/Build/Products/Debug-iphonesimulator/RodskiDemo.app"
PLANS="@queue_short_a,@queue_long_b,@queue_short_c"
DEVICE_NAMES="${DEVICE_NAMES:-iPhone 16,iPhone 16 Pro}"

# 计划 → 该计划唯一选中的 case id（断言 7 用：证明子进程真走了既有链路）
declare -a PLAN_IDS=(queue_short_a queue_long_b queue_short_c)
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
echo "=== [1/5] 环境检查 ==="

if [[ "$(uname)" != "Darwin" ]]; then
  fail "iOS Simulator 仅支持 macOS，当前系统：$(uname)"
fi
command -v xcrun >/dev/null || fail "xcrun 未找到，请安装 Xcode Command Line Tools"
command -v rodski >/dev/null || fail "rodski 命令未找到，请先 pip install -e rodski/"

if ! curl -sf "http://127.0.0.1:${APPIUM_PORT}/status" >/dev/null; then
  fail "Appium server 未在 127.0.0.1:${APPIUM_PORT} 运行。请先执行：appium --address 127.0.0.1 --port ${APPIUM_PORT}"
fi
ok "Appium server: 127.0.0.1:${APPIUM_PORT}"

if [[ ! -d "$APP_PATH" ]]; then
  fail "未找到已编译的 App：$APP_PATH。请先执行：bash demo_ios_app/build_ios_app.sh"
fi
ok "被测 App: $APP_PATH"

# ─────────────────────────────────────────────────────
# Step 2：解析并启动两台模拟器
# ─────────────────────────────────────────────────────
echo ""
echo "=== [2/5] 准备两台 iOS 模拟器 ==="

IFS=',' read -r NAME_A NAME_B <<< "$DEVICE_NAMES"
[[ -n "${NAME_A:-}" && -n "${NAME_B:-}" ]] || fail "DEVICE_NAMES 需要恰好两台，当前：$DEVICE_NAMES"
[[ "$NAME_A" != "$NAME_B" ]] || fail "两台模拟器不能同名：$NAME_A"

# 按名字动态解析 UDID（不硬编码，换机器/换 Xcode 版本仍然可用）
resolve_udid() {
  local name="$1"
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
" "$name" 2>/dev/null
}

UDID_A="$(resolve_udid "$NAME_A")" || fail "未找到可用模拟器：$NAME_A"
UDID_B="$(resolve_udid "$NAME_B")" || fail "未找到可用模拟器：$NAME_B"
[[ "$UDID_A" != "$UDID_B" ]] || fail "两台模拟器解析到同一 UDID：$UDID_A"
ok "$NAME_A = $UDID_A"
ok "$NAME_B = $UDID_B"

boot_simulator() {
  local udid="$1" name="$2"
  if xcrun simctl list devices booted 2>/dev/null | grep -q "$udid"; then
    ok "$name 已是 Booted"
    return 0
  fi
  [[ "${SKIP_BOOT:-0}" == "1" ]] && fail "$name 未启动，且指定了 SKIP_BOOT=1"
  info "启动 $name ..."
  xcrun simctl boot "$udid" 2>/dev/null || true
  local waited=0
  while ! xcrun simctl list devices booted 2>/dev/null | grep -q "$udid"; do
    sleep 2; waited=$((waited + 2))
    [[ $waited -ge 120 ]] && fail "等待 $name 启动超时（120s）"
  done
  ok "$name 已启动"
}

boot_simulator "$UDID_A" "$NAME_A"
boot_simulator "$UDID_B" "$NAME_B"
open -a Simulator 2>/dev/null || warn "无法打开 Simulator.app（headless 可忽略）"

# 安装被测 App（已装则跳过）
for udid in "$UDID_A" "$UDID_B"; do
  if xcrun simctl listapps "$udid" 2>/dev/null | grep -q "$BUNDLE_ID"; then
    ok "$BUNDLE_ID 已安装于 ${udid:0:8}"
  else
    info "安装 $BUNDLE_ID 到 ${udid:0:8} ..."
    xcrun simctl install "$udid" "$APP_PATH" || fail "安装失败：$udid"
    ok "安装完成 ${udid:0:8}"
  fi
done

# ─────────────────────────────────────────────────────
# Step 3：设备枚举自检
# ─────────────────────────────────────────────────────
echo ""
echo "=== [3/5] 设备枚举自检（rodski queue --list-devices）==="
cd "$MODULE_DIR"
rodski queue --list-devices --platform ios | head -8
ok "设备发现可用"

# ─────────────────────────────────────────────────────
# Step 4：Run A 并行 + Run B 单设备负对照
# ─────────────────────────────────────────────────────
echo ""
echo "=== [4/5] Run A：两台设备并行 ==="
info "计划：$PLANS"
info "设备：${UDID_A:0:8} + ${UDID_B:0:8}"

RUN_A_START=$(date +%s)
set +e
rodski queue --plans "$PLANS" --devices "$UDID_A,$UDID_B" --platform ios
RUN_A_CODE=$?
set -e
RUN_A_WALL=$(( $(date +%s) - RUN_A_START ))
echo ""
echo "Run A 退出码=$RUN_A_CODE 墙钟=${RUN_A_WALL}s"
[[ $RUN_A_CODE -eq 0 ]] || fail "Run A 未通过（exit=$RUN_A_CODE）"
ok "Run A 完成"

QUEUE_A_DIR=$(python3 -c "
import glob, os
dirs = glob.glob('result/rodski_*_queue')
print(max(dirs, key=os.path.getmtime) if dirs else '')
")
[[ -n "$QUEUE_A_DIR" ]] || fail "未找到 Run A 的队列目录"
ok "Run A 队列目录：$QUEUE_A_DIR"

echo ""
echo "=== [4/5] Run B：单设备负对照（同样三个计划，只给一台设备）==="
RUN_B_START=$(date +%s)
set +e
rodski queue --plans "$PLANS" --devices "$UDID_A" --platform ios
RUN_B_CODE=$?
set -e
RUN_B_WALL=$(( $(date +%s) - RUN_B_START ))
echo ""
echo "Run B 退出码=$RUN_B_CODE 墙钟=${RUN_B_WALL}s"
[[ $RUN_B_CODE -eq 0 ]] || fail "Run B 未通过（exit=$RUN_B_CODE）"
ok "Run B 完成"

QUEUE_B_DIR=$(python3 -c "
import glob, os, sys
exclude = sys.argv[1]
dirs = [d for d in glob.glob('result/rodski_*_queue') if d != exclude]
print(max(dirs, key=os.path.getmtime) if dirs else '')
" "$QUEUE_A_DIR")
[[ -n "$QUEUE_B_DIR" ]] || fail "未找到 Run B 的队列目录"
ok "Run B 队列目录：$QUEUE_B_DIR"

# ─────────────────────────────────────────────────────
# Step 5：断言
# ─────────────────────────────────────────────────────
echo ""
echo "=== [5/5] 验收断言 ==="

python3 - "$QUEUE_A_DIR" "$QUEUE_B_DIR" "$UDID_A" "$UDID_B" \
          "$RUN_A_WALL" "$RUN_B_WALL" "${PLAN_IDS[@]}" -- "${PLAN_CASE_IDS[@]}" <<'PY'
import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

argv = sys.argv[1:]
sep = argv.index("--")
queue_a, queue_b, udid_a, udid_b, wall_a, wall_b = argv[:6]
plan_ids = argv[6:sep]
case_ids = argv[sep + 1:]
expected_case = dict(zip(plan_ids, case_ids))
wall_a, wall_b = int(wall_a), int(wall_b)

failures = []


def check(no, title, condition, detail=""):
    mark = "✅" if condition else "❌"
    print(f"  {mark} 断言 {no}：{title}" + (f"  —— {detail}" if detail else ""))
    if not condition:
        failures.append(no)


def load(queue_dir):
    return json.loads((Path(queue_dir) / "summary.json").read_text(encoding="utf-8"))


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


summary_a = load(queue_a)
summary_b = load(queue_b)
plans_a = summary_a["plans"]
by_id_a = {p["plan_id"]: p for p in plans_a}

print(f"\n  排队结果（Run A，{queue_a}）：")
for p in plans_a:
    print(f"    {p['plan_id']:16} {p['device_udid'][:8]}  {p['status']:5} "
          f"{p['started_at'][11:23]} → {p['finished_at'][11:23]}  {p['duration']:6.1f}s")

# ── 断言 1：真并行（区间重叠 > 5s，串行不可能产生）──────────────────
best = (0.0, None, None)
for i, p1 in enumerate(plans_a):
    for p2 in plans_a[i + 1:]:
        if p1["device_udid"] == p2["device_udid"]:
            continue
        ov = overlap_seconds(p1, p2)
        if ov > best[0]:
            best = (ov, p1, p2)
ov, p1, p2 = best
check(1, "两个计划在不同设备上时间区间重叠 > 5s（真并行）",
      ov > 5.0,
      f"最大重叠 {ov:.1f}s（{p1['plan_id']}@{p1['device_udid'][:8]} × "
      f"{p2['plan_id']}@{p2['device_udid'][:8]}）")

# ── 断言 2：设备隔离 ────────────────────────────────────────────
used = {p["device_udid"] for p in plans_a}
check(2, "每个计划都归属两台已 boot 的设备之一（无空值、无越界）",
      used and used <= {udid_a, udid_b} and all(p["device_udid"] for p in plans_a),
      f"实际使用 {sorted(u[:8] for u in used)}")

# ── 断言 3：计划不被拆分 ────────────────────────────────────────
ids = [p["plan_id"] for p in plans_a]
check(3, "每个计划恰好出现在一条结果里（计划粒度，不被拆分）",
      len(ids) == len(set(ids)) == len(plan_ids) and set(ids) == set(plan_ids),
      f"计划 {sorted(ids)}")

# ── 断言 4：动态领取（有设备跑了 ≥2 个计划）──────────────────────
per_device = {}
for p in plans_a:
    per_device.setdefault(p["device_udid"], []).append(p["plan_id"])
multi = {u: v for u, v in per_device.items() if len(v) >= 2}
long_dev = by_id_a["queue_long_b"]["device_udid"]
check(4, "某台设备领了 ≥2 个计划（先跑完的回去再领），且不是跑长计划的那台",
      bool(multi) and long_dev not in multi,
      f"{ {u[:8]: v for u, v in per_device.items()} }，长计划在 {long_dev[:8]}")

# ── 断言 5：全通过 ─────────────────────────────────────────────
check(5, "Run A 全部通过（exit_code=0、failed=0、每条计划 exit_code=0）",
      summary_a["exit_code"] == 0 and summary_a["summary"]["failed"] == 0
      and summary_a["summary"]["error"] == 0
      and all(p["status"] == "PASS" and p["exit_code"] == 0 for p in plans_a),
      f"{summary_a['summary']}")

# ── 断言 6：负对照（单设备必串行，且更慢）───────────────────────
plans_b = summary_b["plans"]
devs_b = {p["device_udid"] for p in plans_b}
overlap_b = max(
    (overlap_seconds(x, y) for i, x in enumerate(plans_b) for y in plans_b[i + 1:]),
    default=0.0,
)
check(6, "负对照：单设备上三个计划只有一台设备、无区间重叠，且墙钟明显更慢",
      devs_b == {udid_a} and overlap_b < 1.0 and wall_b > wall_a + 10,
      f"设备数 {len(devs_b)}，最大重叠 {overlap_b:.2f}s，墙钟 A={wall_a}s < B={wall_b}s")

# ── 断言 7：子进程证据（run_dir 里的 result.xml 与计划相符）──────
evidence = []
for p in plans_a:
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

print("")
if failures:
    print(f"❌ 双设备并行验收失败，未通过断言：{sorted(failures)}")
    raise SystemExit(1)

print(f"✅ 双设备并行验收通过（7/7 断言）"
      f" —— 并行墙钟 {wall_a}s vs 串行 {wall_b}s，加速 {wall_b / wall_a:.2f}x")
PY

echo ""
echo "=== 验收完成 ==="
echo ""
echo "产物："
echo "  Run A（并行）：$QUEUE_A_DIR/summary.json"
echo "  Run B（串行）：$QUEUE_B_DIR/summary.json"
