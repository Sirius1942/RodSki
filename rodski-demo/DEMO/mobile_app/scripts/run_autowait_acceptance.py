#!/usr/bin/env python3
"""v11.7.0 移动端自动等待（AutoWait）验收 —— Android 模拟器实跑。

设计依据：.pb/specs/v11.7.0-autowait-unified-design.md §4.3

两个场景，均真实调用 `rodski run --udid <serial>` 并解析 result.xml + trace.json：

  场景 P（正向）：mock 登录/订单接口延迟 MOCK_DELAY_MS=2500
      case/autowait.xml::AW001 —— 无固定 wait、step_wait=0，
      登录 → 点「查看订单」→ 点首条订单 → verify 详情，必须全部通过。
      同时断言「点查看订单」「点首条订单」两步的耗时确实吸收了接口延迟
      （证明用例面对的是真实异步，而不是碰巧已就绪）。

  场景 N（负向）：MOCK_DELAY_MS=20000 + MOCK_LOGIN_DELAY_MS=0
      订单接口 20s 才响应（超过 App OkHttp 10s 读超时，列表始终为空），
      case/autowait.xml::AW_F01（文件里 execute="否"，本脚本临时生成启用副本）
      点首条订单必须失败，且失败步骤耗时 ∈ [4.5s, 7.5s]（≈ AutoWait 默认 5000ms，
      不是驱动硬编码的 10s，也不是 N 个定位器 × 10s），错误信息含
      `AutoWait=5000ms` 与元素名 `firstOrderItem`。

用法：
  /usr/local/bin/python3 rodski-demo/DEMO/mobile_app/scripts/run_autowait_acceptance.py
  UDID=emulator-5554 MOCK_PORT=18000 python3 .../run_autowait_acceptance.py
  python3 .../run_autowait_acceptance.py P      # 只跑正向
  python3 .../run_autowait_acceptance.py N      # 只跑负向

前置（脚本只检查，不替你安装/启动）：
  - 模拟器已 boot（adb devices 可见 $UDID，默认 emulator-5554）
  - 设备已装 com.rodski.demo（见 README「构建并安装 APK」）
  - Appium server 运行在 127.0.0.1:4723
  - 设备侧 API 端口固定 8000（APK 编译期常量）；本机 mock 端口默认 18000
    （8000 常被 demo_full 的 demosite 占用），脚本做 `adb reverse tcp:8000 tcp:$MOCK_PORT`，
    结束时移除该 reverse。

退出码：0 全部断言通过；1 有断言失败；2 环境前置不满足。
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple

MOD = Path(__file__).resolve().parents[1]
CASE = MOD / "case" / "autowait.xml"
NEG_TMP = MOD / "case" / "autowait_negative_tmp.xml"
MOCK = MOD / "scripts" / "mock_server.py"

UDID = os.environ.get("UDID", "emulator-5554")
MOCK_PORT = int(os.environ.get("MOCK_PORT", "18000"))
DEVICE_API_PORT = 8000
APPIUM = os.environ.get("APPIUM_URL", "http://127.0.0.1:4723")
PY = os.environ.get("PYTHON", sys.executable)
RODSKI = os.environ.get("RODSKI", shutil.which("rodski") or "rodski")

AUTOWAIT_MS = 5000                   # globalvalue 未显式配置 → 默认值
FAIL_WINDOW = (4.5, 7.5)             # 设计 §4.1/§4.3：≈ AutoWait，不是 10s/30s
P_DELAY_MS = 2500
N_DELAY_MS = 20000


# ---------------------------------------------------------------- 工具
class Check:
    def __init__(self) -> None:
        self.rows: List[Tuple[str, bool, str]] = []

    def __call__(self, name: str, ok: bool, detail: str = "") -> bool:
        self.rows.append((name, bool(ok), detail))
        print(f"  {'✅' if ok else '❌'} {name}" + (f" —— {detail}" if detail else ""), flush=True)
        return ok


def sh(cmd: List[str], timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def http(url: str, data: Optional[bytes] = None, timeout: float = 30) -> Tuple[int, str]:
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read().decode("utf-8", "replace")


def preflight() -> Optional[str]:
    """返回 None 表示环境可用，否则返回原因。"""
    if not shutil.which("adb"):
        return "adb 不在 PATH"
    devs = sh(["adb", "devices"]).stdout
    if not re.search(rf"^{re.escape(UDID)}\s+device\s*$", devs, re.M):
        return f"adb devices 中没有处于 device 状态的 {UDID}：\n{devs.strip()}"
    boot = sh(["adb", "-s", UDID, "shell", "getprop", "sys.boot_completed"]).stdout.strip()
    if boot != "1":
        return f"{UDID} 尚未 boot_completed（getprop={boot!r}）"
    pkgs = sh(["adb", "-s", UDID, "shell", "pm", "list", "packages", "com.rodski.demo"]).stdout
    if "package:com.rodski.demo" not in pkgs:
        return f"{UDID} 未安装 com.rodski.demo（见 README 构建并安装 APK）"
    try:
        _, body = http(f"{APPIUM}/status", timeout=5)
        if '"ready":true' not in body.replace(" ", ""):
            return f"Appium {APPIUM} 未就绪：{body[:200]}"
    except Exception as exc:  # noqa: BLE001
        return f"Appium {APPIUM} 不可达：{exc}"
    try:
        http(f"http://127.0.0.1:{MOCK_PORT}/health", timeout=2)
        return f"本机端口 {MOCK_PORT} 已被占用（有服务在响应 /health），请换 MOCK_PORT"
    except Exception:  # noqa: BLE001
        pass
    return None


class MockServer:
    def __init__(self, env_extra: Dict[str, str]) -> None:
        self.env_extra = env_extra
        self.proc: Optional[subprocess.Popen] = None
        self.log = Path(os.environ.get("TMPDIR", "/tmp")) / f"rodski_autowait_mock_{MOCK_PORT}.log"

    def __enter__(self) -> "MockServer":
        env = dict(os.environ)
        for k in ("MOCK_DELAY_MS", "MOCK_LOGIN_DELAY_MS", "MOCK_ORDERS_DELAY_MS"):
            env.pop(k, None)
        env.update(self.env_extra)
        self.proc = subprocess.Popen(
            [PY, str(MOCK), "--host", "127.0.0.1", "--port", str(MOCK_PORT)],
            env=env, stdout=open(self.log, "w"), stderr=subprocess.STDOUT,
        )
        for _ in range(50):
            try:
                http(f"http://127.0.0.1:{MOCK_PORT}/health", timeout=1)
                return self
            except Exception:  # noqa: BLE001
                time.sleep(0.2)
        raise RuntimeError(f"mock 后端 20s 内未就绪，日志 {self.log}")

    def __exit__(self, *exc) -> None:
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()


class Run:
    def __init__(self, proc: subprocess.CompletedProcess, run_dir: Optional[Path], seconds: float) -> None:
        self.code = proc.returncode
        self.out = (proc.stdout or "") + (proc.stderr or "")
        self.run_dir = run_dir
        self.seconds = seconds

    def result(self, case_id: str) -> Optional[ET.Element]:
        if not self.run_dir or not (self.run_dir / "result.xml").is_file():
            return None
        for r in ET.parse(self.run_dir / "result.xml").getroot().iter("result"):
            if r.get("case_id") == case_id:
                return r
        return None

    def keyword_spans(self, case_id: str) -> List[dict]:
        """trace.json 中该用例的 keyword.* span（按开始时间排序），附带 duration 秒。"""
        p = self.run_dir / "trace.json" if self.run_dir else None
        if not p or not p.is_file():
            return []
        doc = json.loads(p.read_text(encoding="utf-8"))
        spans: List[dict] = []
        for rs in doc.get("trace", {}).get("resourceSpans", []):
            for ss in rs.get("scopeSpans", []):
                spans.extend(ss.get("spans", []))

        def attr(s: dict, key: str) -> str:
            for a in s.get("attributes", []):
                if a.get("key") == key:
                    return str(next(iter(a.get("value", {}).values()), ""))
            return ""

        case_ids = {s["spanId"] for s in spans if s.get("name") == "case" and attr(s, "case_id") == case_id}
        kws = [s for s in spans if s.get("parentSpanId") in case_ids and s.get("name", "").startswith("keyword.")]
        kws.sort(key=lambda s: s["startTimeUnixNano"])
        for s in kws:
            end = s.get("endTimeUnixNano") or s["startTimeUnixNano"]
            s["duration"] = (end - s["startTimeUnixNano"]) / 1e9
        return kws

    def steps(self, case_id: str, case_file: Path) -> List[dict]:
        """按执行顺序返回该用例的步骤（action/model/phase/status/duration）。

        注意：v11.6.0 的 result.xml 不记录失败的那一步（只有 error_message），
        因此以 trace.json 的 keyword span 为准（失败步骤 span status.code=2），
        再按用例 XML 的 pre/test/post 顺序对齐出 model；失败后同阶段剩余步骤跳过、
        直接进入 post_process。
        """
        root = ET.parse(case_file).getroot()
        node = next((c for c in root.iter("case") if c.get("id") == case_id), None)
        if node is None:
            return []
        expected: List[dict] = []
        post_start = 0
        for phase in ("pre_process", "test_case", "post_process"):
            if phase == "post_process":
                post_start = len(expected)
            ph = node.find(phase)
            for st in (ph.iter("test_step") if ph is not None else []):
                expected.append({"phase": phase, "action": st.get("action", ""), "model": st.get("model", "")})
        out: List[dict] = []
        j = 0
        for sp in self.keyword_spans(case_id):
            action = sp["name"][len("keyword."):]
            while j < len(expected) and expected[j]["action"].lower() != action:
                j += 1
            if j >= len(expected):
                break
            ok = (sp.get("status") or {}).get("code") != 2
            out.append({**expected[j], "index": len(out) + 1,
                        "status": "PASS" if ok else "FAIL", "duration": sp["duration"]})
            if not ok and expected[j]["phase"] != "post_process":
                j = post_start
            else:
                j += 1
        return out

    def log(self) -> str:
        p = self.run_dir / "execution.log" if self.run_dir else None
        return p.read_text(encoding="utf-8", errors="ignore") if p and p.is_file() else ""


def rodski_run(case_rel: str, extra: List[str]) -> Run:
    result_dir = MOD / "result"
    before = set(result_dir.iterdir()) if result_dir.is_dir() else set()
    cmd = [RODSKI, "run", case_rel, "--udid", UDID, "--trace", *extra]
    print(f"  $ (cd {MOD}) {' '.join(cmd)}", flush=True)
    t0 = time.monotonic()
    proc = subprocess.run(cmd, cwd=str(MOD), capture_output=True, text=True, timeout=600)
    seconds = time.monotonic() - t0
    after = set(result_dir.iterdir()) if result_dir.is_dir() else set()
    new_dirs = sorted(p for p in after - before if p.is_dir())
    return Run(proc, new_dirs[-1] if new_dirs else None, seconds)


def fmt_steps(steps: List[dict]) -> str:
    return "; ".join(
        f"#{s.get('index')} {s.get('action')}({s.get('model') or '-'})={s.get('status')}"
        + (f" {s['duration']:.2f}s" if "duration" in s else "")
        for s in steps
    )


def step_of(steps: List[dict], action: str, model: str) -> Optional[dict]:
    for s in steps:
        if s.get("action") == action and s.get("model") == model:
            return s
    return None


# ---------------------------------------------------------------- 静态检查
def static_checks(check: Check) -> None:
    print("\n[S] 用例静态约束", flush=True)
    root = ET.parse(CASE).getroot()
    check("S1 step_wait=\"0\"", root.get("step_wait") == "0", f"step_wait={root.get('step_wait')!r}")
    waits = [s for s in root.iter("test_step") if s.get("action") == "wait"]
    check("S2 不含任何固定 wait 步骤", not waits, f"wait 步骤数={len(waits)}")
    ids = {c.get("id"): c.get("execute") for c in root.iter("case")}
    check("S3 AW001 默认执行、AW_F01 默认不执行（由本脚本控制）",
          ids.get("AW001") == "是" and ids.get("AW_F01") == "否", str(ids))


# ---------------------------------------------------------------- 场景 P
def scenario_p(check: Check) -> None:
    print(f"\n[P] 正向：MOCK_DELAY_MS={P_DELAY_MS}，AW001 全链路仅依赖自动等待", flush=True)
    with MockServer({"MOCK_DELAY_MS": str(P_DELAY_MS)}):
        t0 = time.monotonic()
        http(f"http://127.0.0.1:{MOCK_PORT}/api/login",
             json.dumps({"username": "demo", "password": "demo123"}).encode(), timeout=30)
        lat = time.monotonic() - t0
        check("P1 mock 登录接口确实延迟 ≥2.4s", lat >= 2.4, f"{lat:.2f}s")

        r = rodski_run("case/autowait.xml", ["--case-id", "AW001"])
        res = r.result("AW001")
        steps = r.steps("AW001", CASE)
        status = res.get("status") if res is not None else None
        err = res.get("error_message", "") if res is not None else ""
        check("P2 AW001 通过", r.code == 0 and status == "PASS",
              f"exit={r.code} status={status} 墙钟={r.seconds:.1f}s run_dir={r.run_dir} {err[:300]}")
        print(f"     步骤耗时：{fmt_steps(steps)}", flush=True)

        home = step_of(steps, "type", "HomeScreen")
        order = step_of(steps, "type", "OrderListScreen")
        hd = home.get("duration") if home else None
        od = order.get("duration") if order else None
        check("P3 点「查看订单」步骤吸收了登录接口延迟（≥2.0s，真实异步）",
              hd is not None and hd >= 2.0, f"{hd if hd is None else f'{hd:.2f}s'}")
        check("P4 点首条订单步骤吸收了订单接口延迟（≥1.5s，真实异步）",
              od is not None and od >= 1.5, f"{od if od is None else f'{od:.2f}s'}")


# ---------------------------------------------------------------- 场景 N
def scenario_n(check: Check) -> None:
    print(f"\n[N] 负向：MOCK_DELAY_MS={N_DELAY_MS} MOCK_LOGIN_DELAY_MS=0，点首条订单应 ≈{AUTOWAIT_MS}ms 失败",
          flush=True)
    text = CASE.read_text(encoding="utf-8")
    enabled, n = re.subn(r'(<case\s+)execute="否"(\s+id="AW_F01")', r'\1execute="是"\2', text)
    if n != 1:
        check("N0 生成 AW_F01 启用副本", False, "autowait.xml 中未找到 execute=\"否\" id=\"AW_F01\"")
        return
    NEG_TMP.write_text(enabled, encoding="utf-8")
    try:
        with MockServer({"MOCK_DELAY_MS": str(N_DELAY_MS), "MOCK_LOGIN_DELAY_MS": "0"}):
            r = rodski_run(f"case/{NEG_TMP.name}", ["--case-id", "AW_F01"])
            steps = r.steps("AW_F01", NEG_TMP)
    finally:
        NEG_TMP.unlink(missing_ok=True)

    res = r.result("AW_F01")
    status = res.get("status") if res is not None else None
    err = res.get("error_message", "") if res is not None else ""
    print(f"     exit={r.code} status={status} 墙钟={r.seconds:.1f}s run_dir={r.run_dir}", flush=True)
    print(f"     步骤耗时：{fmt_steps(steps)}", flush=True)
    check("N1 AW_F01 失败（订单项始终不出现）", status in ("FAIL", "ERROR") and r.code != 0,
          f"exit={r.code} status={status}")

    login = step_of(steps, "type", "LoginScreen")
    home = step_of(steps, "type", "HomeScreen")
    order = step_of(steps, "type", "OrderListScreen")
    check("N2 失败发生在「点首条订单」且前序登录/进入列表通过",
          bool(login and home and order) and login.get("status") == "PASS"
          and home.get("status") == "PASS" and order.get("status") not in ("PASS", None),
          fmt_steps([s for s in (login, home, order) if s]))

    od = order.get("duration") if order else None
    lo, hi = FAIL_WINDOW
    check(f"N3 失败步骤耗时 ∈ [{lo}s, {hi}s]（≈AutoWait={AUTOWAIT_MS}ms，不是 10s / N×10s）",
          od is not None and lo <= od <= hi, f"{od if od is None else f'{od:.2f}s'}")

    evidence = err
    check(f"N4 错误信息含 AutoWait={AUTOWAIT_MS}ms 与元素名 firstOrderItem",
          f"AutoWait={AUTOWAIT_MS}ms" in evidence and "firstOrderItem" in evidence,
          evidence.strip().replace("\n", " ")[:300])


def main(argv: List[str]) -> int:
    which = {a.upper() for a in argv} or {"P", "N"}
    print(f"RodSki v11.7.0 移动端自动等待验收  UDID={UDID} MOCK_PORT={MOCK_PORT} rodski={RODSKI}", flush=True)
    reason = preflight()
    if reason:
        print(f"❌ 环境前置不满足：{reason}", flush=True)
        return 2

    rev = sh(["adb", "-s", UDID, "reverse", f"tcp:{DEVICE_API_PORT}", f"tcp:{MOCK_PORT}"])
    if rev.returncode != 0:
        print(f"❌ adb reverse 失败：{rev.stderr.strip()}", flush=True)
        return 2
    print(f"adb -s {UDID} reverse tcp:{DEVICE_API_PORT} tcp:{MOCK_PORT}", flush=True)

    check = Check()
    t0 = time.monotonic()
    try:
        static_checks(check)
        if "P" in which:
            scenario_p(check)
        if "N" in which:
            scenario_n(check)
    finally:
        sh(["adb", "-s", UDID, "reverse", "--remove", f"tcp:{DEVICE_API_PORT}"])
        NEG_TMP.unlink(missing_ok=True)

    passed = sum(1 for _, ok, _ in check.rows if ok)
    total = len(check.rows)
    wall = time.monotonic() - t0
    if passed == total:
        print(f"\n✅ 移动端自动等待验收通过（{passed}/{total} 断言）—— 墙钟 {wall:.0f}s", flush=True)
        return 0
    print(f"\n❌ 移动端自动等待验收未通过（{passed}/{total} 断言通过）—— 墙钟 {wall:.0f}s", flush=True)
    for name, ok, detail in check.rows:
        if not ok:
            print(f"   - {name}: {detail}", flush=True)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
