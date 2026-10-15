#!/usr/bin/env bash
#
# run_android_mixed_demo.sh — RodSki 异构设备计划队列验收（Android，v11.3.0）
#
# 验收目标：**一台 Android 真机 + 一台 Android 模拟器同时跑 app 测试**，且
#   - 一个计划只在一台设备上整体执行（计划不被拆分）；
#   - 先跑完的设备回去领下一个计划（动态领取，而非静态均分）；
#   - 两台设备共用同一个 Appium server，互不抢占 systemPort。
#
# 与 run_mixed_device_demo.sh（iOS 真机 + iOS 模拟器）同构：平台相同、设备类别不同。
# 真机走 USB 上的实体手机，模拟器走 AVD —— UiAutomator2 对两者是同一套协议，
# 但设备发现、端口转发、系统镜像都不同，混跑仍是有意义的验收。
#
# 预期排班（模拟器通常快于真机）：
#   模拟器：[ android_queue_a ]→[ android_queue_c ]
#   真机  ：[ ............ android_queue_b ............ ]
# 但调度是动态的，脚本只断言「每个计划恰好被一台设备整体执行一次」与「区间重叠」，
# 不假定哪台设备领哪个计划。
#
# 用法：
#   bash scripts/run_android_mixed_demo.sh
#   AVD_NAME=rodski_api34 bash scripts/run_android_mixed_demo.sh
#   MOCK_PORT=8000 bash scripts/run_android_mixed_demo.sh
#
# 前置：
#   - Android SDK（emulator + platform-tools）+ 已创建的 AVD
#   - Appium server 运行在 127.0.0.1:4723，且已装 uiautomator2 driver
#   - 真机：USB 连接、adb devices 状态为 device、已装 com.rodski.demo
#   - mock 后端：脚本会自己拉起 scripts/mock_server.py 并做 adb reverse
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

ANDROID_HOME="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-$HOME/Library/Android/sdk}}"
JAVA_HOME="${JAVA_HOME:-/opt/homebrew/opt/openjdk@17}"
EMULATOR_BIN="$ANDROID_HOME/emulator/emulator"
ADB="$(command -v adb || echo "$ANDROID_HOME/platform-tools/adb")"

BUNDLE_ID="com.rodski.demo"
APPIUM_PORT="${APPIUM_PORT:-4723}"
AVD_NAME="${AVD_NAME:-rodski_api34}"
MOCK_PORT="${MOCK_PORT:-8000}"
APK_PATH="$MODULE_DIR/demo_android_app/app/build/outputs/apk/debug/app-debug.apk"
PLANS="@android_queue_a,@android_queue_b,@android_queue_c"

# 计划 → 该计划唯一选中的 case id（断言 7 用：证明子进程真走了既有链路）
declare -a PLAN_IDS=(android_queue_a android_queue_b android_queue_c)
declare -a PLAN_CASE_IDS=(APP002 APP003 APP001)

MOCK_PID=""

cleanup() {
  # 只回收本脚本拉起的 mock 后端；用户自己起的 / 已复用的模拟器都不动
  [[ -n "$MOCK_PID" ]] && kill "$MOCK_PID" 2>/dev/null || true
}
trap cleanup EXIT

# ─────────────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────────────
ok()   { echo "[OK]   $*"; }
info() { echo "[INFO] $*"; }
warn() { echo "[WARN] $*"; }
fail() { echo "[FAIL] $*" >&2; exit 1; }

# adb 到某一台设备（真机与模拟器必须逐台指定，否则命令落在默认设备上）
adbd() { "$ADB" -s "$1" "${@:2}"; }

# ─────────────────────────────────────────────────────
# Step 1：环境检查
# ─────────────────────────────────────────────────────
echo ""
echo "=== [1/7] 环境检查 ==="

command -v rodski >/dev/null || fail "rodski 命令未找到，请先 pip install -e rodski/"
[[ -x "$ADB" ]] || fail "adb 未找到（找过 PATH 与 $ANDROID_HOME/platform-tools/adb）"
[[ -x "$EMULATOR_BIN" ]] || fail "emulator 未找到：$EMULATOR_BIN
  安装：sdkmanager --install emulator \"system-images;android-34;google_apis;arm64-v8a\""
ok "adb: $ADB"
ok "emulator: $EMULATOR_BIN"

if ! curl -sf "http://127.0.0.1:${APPIUM_PORT}/status" >/dev/null; then
  fail "Appium server 未在 127.0.0.1:${APPIUM_PORT} 运行。请先执行：appium --address 127.0.0.1 --port ${APPIUM_PORT}"
fi
ok "Appium server: 127.0.0.1:${APPIUM_PORT}"

[[ -f "$APK_PATH" ]] || fail "未找到 APK：$APK_PATH
  构建：cd demo_android_app && ./gradlew assembleDebug"
ok "被测 APK: $APK_PATH"

# ─────────────────────────────────────────────────────
# Step 2：解析真机（adb，排除模拟器）
# ─────────────────────────────────────────────────────
echo ""
echo "=== [2/7] 解析 Android 真机（adb）==="

# 与框架 device_scheduler._is_adb_emulator 同一判据：serial 前缀 `emulator-`
# 即 AVD。不能用 `adb devices` 的顺序或 model 名判断 —— 先 boot 的模拟器会
# 排在真机前面，按顺序取会把模拟器当成真机。
list_real_devices() {
  "$ADB" devices -l 2>/dev/null | python3 -c '
import sys
for line in sys.stdin:
    f = line.split()
    if len(f) < 2 or f[1] != "device":
        continue
    if f[0].startswith("emulator-"):
        continue
    name = next((t.split(":", 1)[1] for t in f[2:] if t.startswith("model:")), "")
    print(f[0] + "\t" + name)
'
}

_real=""
while IFS= read -r _line; do
  [[ -n "$_line" ]] && _real="${_real}${_line}"$'\n'
done < <(list_real_devices)

REAL_COUNT="$(printf '%s' "$_real" | grep -c . || true)"
[[ "$REAL_COUNT" -gt 0 ]] || fail "未探测到 Android 真机。
  排查：
    1) USB 是否连接、手机上是否点了「允许 USB 调试」
    2) adb devices         应显示 <serial>  device
    3) adb kill-server && adb start-server   可救活枚举失败的设备"
if [[ "$REAL_COUNT" -gt 1 ]]; then
  echo "  探测到多台真机，请用 DEVICE_SERIAL 指定其一："
  printf '%s' "$_real" | while IFS=$'\t' read -r s n; do echo "    $s  $n"; done
  fail "目标真机不唯一"
fi
REAL_SERIAL="$(printf '%s' "$_real" | head -1 | cut -f1)"
REAL_NAME="$(printf '%s' "$_real" | head -1 | cut -f2)"
ok "真机：${REAL_NAME:-<无名>}  $REAL_SERIAL"

# ─────────────────────────────────────────────────────
# Step 3：启动模拟器（AVD）
# ─────────────────────────────────────────────────────
echo ""
echo "=== [3/7] 准备 Android 模拟器（AVD）==="

if ! "$EMULATOR_BIN" -list-avds 2>/dev/null | grep -qx "$AVD_NAME"; then
  fail "未找到 AVD：$AVD_NAME
  创建：avdmanager create avd -n $AVD_NAME -k \"system-images;android-34;google_apis;arm64-v8a\" -d pixel_6"
fi
ok "AVD: $AVD_NAME"

SIM_SERIAL="$("$ADB" devices 2>/dev/null | awk '/^emulator-/{print $1; exit}')"
if [[ -z "${SIM_SERIAL:-}" ]]; then
  info "启动模拟器 $AVD_NAME ..."
  # -no-snapshot-save 保证每次都是干净启动；-no-boot-anim 省掉开机动画时间。
  # 刻意**不**在 trap 里关它：模拟器启动是分钟级成本，脚本退出后留着它，
  # 复跑时直接复用（下面这段逻辑本身也会跳过已在运行的实例）。
  "$EMULATOR_BIN" -avd "$AVD_NAME" -no-snapshot-save -no-boot-anim \
                  >/dev/null 2>&1 &
  waited=0
  while [[ -z "${SIM_SERIAL:-}" ]]; do
    sleep 3; waited=$((waited + 3))
    [[ $waited -ge 180 ]] && fail "等待模拟器启动超时（180s）。请手动执行：$EMULATOR_BIN -avd $AVD_NAME"
    SIM_SERIAL="$("$ADB" devices 2>/dev/null | awk '/^emulator-/{print $1; exit}')"
  done
fi
ok "模拟器：$SIM_SERIAL"

# adb 见到设备 ≠ 系统起来了：boot completed 之前 Appium 建会话必然失败
info "等待模拟器 boot 完成 ..."
waited=0
until [[ "$(adbd "$SIM_SERIAL" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" == "1" ]]; do
  sleep 3; waited=$((waited + 3))
  [[ $waited -ge 180 ]] && fail "模拟器 $SIM_SERIAL 启动 180s 仍未 boot_completed"
done
# 关掉锁屏：锁屏状态下 Appium 起 App 会停在锁屏页
adbd "$SIM_SERIAL" shell input keyevent 82 >/dev/null 2>&1 || true
ok "模拟器已就绪"

[[ "$SIM_SERIAL" != "$REAL_SERIAL" ]] || fail "模拟器与真机解析到同一 serial：$SIM_SERIAL"

# ─────────────────────────────────────────────────────
# Step 4：mock 后端 + 逐台 adb reverse
# ─────────────────────────────────────────────────────
echo ""
echo "=== [4/7] 准备 mock 后端（登录/订单接口）==="

if curl -sf "http://127.0.0.1:${MOCK_PORT}/health" >/dev/null; then
  ok "mock 后端已在 127.0.0.1:${MOCK_PORT} 运行"
else
  # 端口被别的服务占用（本机 8000 常被其它 demo 占用）时，Flask 会「启动成功但
  # 监听失败」——日志里只有一行 Address already in use，进程随即退出，而 curl
  # 探测看起来只是「还没起来」。先探明白，别让 20s 超时冒充「启动慢」。
  if lsof -nP -iTCP:"${MOCK_PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
    fail "端口 ${MOCK_PORT} 已被占用（另一个服务在监听），mock 后端起不来：
  $(lsof -nP -iTCP:"${MOCK_PORT}" -sTCP:LISTEN | tail -1)
  处置：用 MOCK_PORT=<其它端口> 重跑本脚本 —— 脚本会把设备侧的 8000 转发到该端口
  （APK 里的 API_BASE_URL 是编译期常量 http://127.0.0.1:8000，改不了，故只能改转发目标）。"
  fi
  info "拉起 mock 后端 ..."
  ( cd "$MODULE_DIR" && python3 scripts/mock_server.py --port "$MOCK_PORT" >/tmp/rodski_mock_server.log 2>&1 ) &
  MOCK_PID=$!
  waited=0
  until curl -sf "http://127.0.0.1:${MOCK_PORT}/health" >/dev/null; do
    sleep 1; waited=$((waited + 1))
    [[ $waited -ge 20 ]] && fail "mock 后端 20s 未就绪，见 /tmp/rodski_mock_server.log"
  done
  ok "mock 后端已启动（pid=${MOCK_PID}，日志 /tmp/rodski_mock_server.log）"
fi

# APK 的 API_BASE_URL 是编译期常量 http://127.0.0.1:8000，设备上的 127.0.0.1 不是
# 本机，故必须逐台 reverse。**真机与模拟器都要做** —— 漏掉任何一台，那台上的用例
# 会在登录页超时失败，而错误信息看起来像「应用 bug」。
#
# 设备侧端口固定 8000（改不了），本机侧端口随 MOCK_PORT —— 这样 MOCK_PORT 与
# 其它 demo 占用的 8000 可以共存。
for _serial in "$REAL_SERIAL" "$SIM_SERIAL"; do
  adbd "$_serial" reverse --remove-all >/dev/null 2>&1 || true
  adbd "$_serial" reverse "tcp:8000" "tcp:${MOCK_PORT}" >/dev/null \
    || fail "adb reverse 失败：$_serial"
  ok "端口转发已建立：$_serial 127.0.0.1:8000 → 本机 127.0.0.1:${MOCK_PORT}"
done

# ─────────────────────────────────────────────────────
# Step 5：确认两台设备都装了被测 App 与 UiAutomator2 server
# ─────────────────────────────────────────────────────
echo ""
echo "=== [5/7] 校验被测 App 与 UiAutomator2 server ==="

# 包是否已安装
has_pkg() { adbd "$1" shell pm list packages 2>/dev/null | tr -d '\r' | grep -q "^package:$2\$"; }

# 安装一个 APK，并在**需要用户在手机上确认**时等待用户点「继续安装」。
#
# 为什么不是一条 `pm install` 了事：华为 HarmonyOS/EMUI 对 adb 侧安装外部 APK
# 会弹「风险提示 / 来历不明的应用」确认框，不点就一直阻塞（实测 `adb install -r`
# 挂起 2 分钟无输出、`pm install` 直接返回
# `INSTALL_FAILED_ABORTED: User rejected permissions`）。
# 关掉设备校验（`settings put global package_verifier_enable 0` 等）属于降低设备
# 安全策略，**本脚本不做**；这里只做「发起安装 → 等用户在手机上确认」。
#
# 超时不是失败而是警告：真机装不上时队列会在该设备上建会话失败，届时能看到
# 具体原因，比在这里硬中断更接近真实问题。
INSTALL_WAIT="${INSTALL_WAIT:-120}"
install_apk() {
  local serial="$1" apk="$2" pkg="$3" label="${4:-$3}"
  local log="/tmp/rodski_install_$(echo "$serial" | tr -c 'A-Za-z0-9' '_').log"

  adbd "$serial" push "$apk" /data/local/tmp/rodski_install.apk >/dev/null 2>&1 \
    || { warn "${label}：推送 APK 到 $serial 失败"; return 1; }
  adbd "$serial" shell pm install -r -t /data/local/tmp/rodski_install.apk >"$log" 2>&1 &
  local pid=$!
  local waited=0
  info "${label}：正在安装到 $serial ..."
  while kill -0 "$pid" 2>/dev/null; do
    sleep 3; waited=$((waited + 3))
    if [[ $waited -eq 6 ]]; then
      info "  ⚠️  若手机上弹出「风险提示 / 继续安装」，请手动点【继续安装】"
    fi
    if [[ $waited -ge $INSTALL_WAIT ]]; then
      kill "$pid" 2>/dev/null || true
      warn "${label}：等待用户确认超时（${INSTALL_WAIT}s），跳过"
      adbd "$serial" shell rm -f /data/local/tmp/rodski_install.apk >/dev/null 2>&1 || true
      return 1
    fi
  done
  adbd "$serial" shell rm -f /data/local/tmp/rodski_install.apk >/dev/null 2>&1 || true

  if has_pkg "$serial" "$pkg"; then
    ok "${label}：已在 $serial 就绪"
    return 0
  fi
  warn "${label}：安装未成功 —— $(tr -d '\r' <"$log" | tail -2 | tr '\n' ' ')"
  return 1
}

# Appium 的 UiAutomator2 server 也必须预装。若留给 Appium 在建会话时现装，
# 那一步同样会弹确认框，而它藏在 Appium 内部（默认 20s 超时），表现为
# 「建会话失败」而不是「待确认安装」—— 极难定位。故在此提前装好。
U2_APK_DIR="$HOME/.appium/node_modules/appium-uiautomator2-driver/node_modules/appium-uiautomator2-server/apks"
U2_SERVER_APK="$U2_APK_DIR/appium-uiautomator2-server-v10.1.0.apk"
U2_TEST_APK="$U2_APK_DIR/appium-uiautomator2-server-debug-androidTest.apk"

for _serial in "$REAL_SERIAL" "$SIM_SERIAL"; do
  _is_real=0; [[ "$_serial" == "$REAL_SERIAL" ]] && _is_real=1

  if has_pkg "$_serial" "$BUNDLE_ID"; then
    ok "$_serial 已装 $BUNDLE_ID"
  else
    install_apk "$_serial" "$APK_PATH" "$BUNDLE_ID" "被测 App" \
      || { [[ $_is_real -eq 1 ]] && fail "真机 $_serial 上未装 ${BUNDLE_ID}，无法继续"; }
  fi

  if has_pkg "$_serial" "io.appium.uiautomator2.server"; then
    ok "$_serial 已装 UiAutomator2 server"
  elif [[ -f "$U2_SERVER_APK" ]]; then
    install_apk "$_serial" "$U2_SERVER_APK" "io.appium.uiautomator2.server" "UiAutomator2 server" || true
    [[ -f "$U2_TEST_APK" ]] && \
      install_apk "$_serial" "$U2_TEST_APK" "io.appium.uiautomator2.server.test" "UiAutomator2 server test" || true
  else
    warn "未找到 Appium 自带的 UiAutomator2 server APK（${U2_APK_DIR}），将由 Appium 在建会话时安装"
  fi
done

# ─────────────────────────────────────────────────────
# Step 6：设备预检 + 队列执行（设备由执行层配置决定）
# ─────────────────────────────────────────────────────
echo ""
echo "=== [6/7] 队列执行：真机 + 模拟器（设备由执行层配置决定）==="
info "计划：$PLANS"
info "设备：真机 $REAL_SERIAL  +  模拟器 $SIM_SERIAL"

# v11.3.0：设备数量与组合来自 data/globalvalue.xml 的 Mobile 组
#   DeviceCount=2 / DeviceMix=real,simulator
# 队列据此自动发现并选择，**不需要**在这里手敲 serial —— 命令里能写死的设备
# 池，换台机器就失效；写在用例目录里的配置才是随用例版本化的。
#
# 先干跑一次确认「配置选中的」正好是本脚本准备的这两台：本机可能同时连着别的
# 设备，那样配置会合法地选到另一台（而那台上未必装了被测 app）。与其在断言阶段
# 才发现，不如在这里就说清楚，并给出可执行的处置办法。
cd "$MODULE_DIR"
set +e
DRY_OUT=$(rodski queue --plans "$PLANS" --platform android --dry-run 2>&1)
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
# 真机优先排序（v11.3.0 D6b）保证选中顺序是「真机,模拟器」——与实际类别无关的
# 顺序断言在这里会误报，故按集合比较、并把顺序单独打出来供人核对。
SELECTED_SORTED=$(python3 -c "
import sys
print(','.join(sorted(sys.argv[1].split(','))))" "$SELECTED")
EXPECT_SORTED=$(python3 -c "
import sys
print(','.join(sorted(sys.argv[1:])))" "$REAL_SERIAL" "$SIM_SERIAL")
if [[ "$SELECTED_SORTED" != "$EXPECT_SORTED" ]]; then
  echo ""
  fail "配置选中的设备与预期不符。
  配置选中：$SELECTED
  本脚本预期：$REAL_SERIAL,$SIM_SERIAL

  多半是另有一台设备（真机或已启动的模拟器）也被发现，被 DeviceCount=2 合法地选了进去。
  处置（任选其一）：
    1) 拔掉/关掉多余的设备，或用 adb -s <serial> emu kill 关掉多余的模拟器
    2) 在 globalvalue.xml 里用 DeviceList 显式钉住设备池"
fi
ok "配置选中设备与预期一致：真机 + 模拟器（顺序 ${SELECTED}）"

RUN_START=$(date +%s)
set +e
rodski queue --plans "$PLANS" --platform android
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
# Step 7：断言
# ─────────────────────────────────────────────────────
echo ""
echo "=== [7/7] 验收断言 ==="

python3 - "$QUEUE_DIR" "$REAL_SERIAL" "$SIM_SERIAL" "$RUN_WALL" "${PLAN_IDS[@]}" -- "${PLAN_CASE_IDS[@]}" <<'PY'
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

argv = sys.argv[1:]
sep = argv.index("--")
queue_dir, real_serial, sim_serial, wall = argv[:4]
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


def port_slot(serial: str) -> int:
    """与框架 core/keyword_engine.mobile_port_slot 同一算法（并发端口槽）。"""
    return int(hashlib.sha1(str(serial).encode()).hexdigest(), 16) % 100


summary = json.loads((Path(queue_dir) / "summary.json").read_text(encoding="utf-8"))
plans = summary["plans"]
by_id = {p["plan_id"]: p for p in plans}

print(f"\n  排队结果（{queue_dir}）：")
for p in plans:
    kind = "真机  " if p["device_udid"] == real_serial else "模拟器"
    print(f"    {p['plan_id']:18} {kind} {p['device_udid'][:14]:14}  {p['status']:5} "
          f"{p['started_at'][11:23]} → {p['finished_at'][11:23]}  {p['duration']:6.1f}s")
print(f"    并发端口槽：真机 systemPort={8200 + port_slot(real_serial) * 10}  "
      f"模拟器 systemPort={8200 + port_slot(sim_serial) * 10}\n")

# ── 断言 1：两台**异构**设备都被用上（一台真机、一台模拟器）──────────
used = {p["device_udid"] for p in plans}
check(1, "真机与模拟器都被实际调度到（异构设备混跑）",
      used == {real_serial, sim_serial},
      f"实际使用 {sorted(used)}；期望 {{{real_serial}, {sim_serial}}}")

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
      f"{ {(('真机' if u == real_serial else '模拟器')): v for u, v in per_device.items()} }")

# ── 断言 5：全通过 ─────────────────────────────────────────────
check(5, "队列全部通过（exit_code=0、failed=0、error=0、每条计划 exit_code=0）",
      summary["exit_code"] == 0 and summary["summary"]["failed"] == 0
      and summary["summary"]["error"] == 0
      and all(p["status"] == "PASS" and p["exit_code"] == 0 for p in plans),
      f"{summary['summary']}")

# ── 断言 6：并发端口隔离（真机与模拟器拿到不同 systemPort 槽）──────────
slot_real, slot_sim = port_slot(real_serial), port_slot(sim_serial)
check(6, "真机与模拟器的 systemPort 槽不同（不会复用彼此的 UiAutomator2 会话端口）",
      slot_real != slot_sim,
      f"真机 slot={slot_real} (systemPort {8200 + slot_real * 10})，"
      f"模拟器 slot={slot_sim} (systemPort {8200 + slot_sim * 10})")

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
real_plans = per_device.get(real_serial, [])
check(8, "真机至少完整执行了 1 个计划（真机链路真实生效，非空跑）",
      len(real_plans) >= 1,
      f"真机执行 {real_plans or '无'}")

print("")
if failures:
    print(f"❌ Android 真机 + 模拟器混跑验收失败，未通过断言：{sorted(failures)}")
    raise SystemExit(1)

print(f"✅ Android 真机 + 模拟器混跑验收通过（8/8 断言）—— 墙钟 {wall}s")
PY

echo ""
echo "=== 验收完成 ==="
echo ""
echo "产物："
echo "  $QUEUE_DIR/summary.json"
