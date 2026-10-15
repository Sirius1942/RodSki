#!/usr/bin/env python3
"""REQ-012 验收脚本公共库：以子进程真实执行被测用例，观察其暂停/继续/跳过/中止行为。

判定依据（全部来自真实执行，不自造数据）：
1. 执行轨迹：被测用例中的 run mark.py <标签> 写入 RODSKI_DEBUG_MARKER 指向的文件；
2. 终端输出：断点提示行（含 [Breakpoint] 或"已暂停"）、对象/日志提示；
3. 结果目录：被测模块 result/ 下本次新生成的 execution_summary.json / execution.log /
   driver_actions.jsonl 等；
4. 另一进程中的 rodski debug status/queue/objects/context/get-object 输出。

交互约定（SPEC-012-user-guide §2.2）：暂停后从 stdin 读取 c(继续) / s(跳过) / q(中止)。
"""
from __future__ import annotations

import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable, Dict, List, Optional

REPO = Path(__file__).resolve().parents[4]
TARGETS = REPO / "rodski-demo" / "DEMO" / "debug_partial_execution_targets"
PAGES = TARGETS / "fun" / "pages"
PAGES_PORT = 18765

# 一次暂停 = 一行包含 [Breakpoint] 或"已暂停"的提示（单步模式同样要求输出该提示行）
PAUSE_LINE = re.compile(r"^.*(\[Breakpoint\]|已暂停).*$", re.M)
PAUSE_TIMEOUT = 90
EXIT_TIMEOUT = 120


class AcFailed(Exception):
    """前置条件不满足，当前 AC 无法继续判定。"""


def rodski_cmd() -> List[str]:
    sibling = Path(sys.executable).parent / "rodski"
    if sibling.exists():
        return [str(sibling)]
    found = shutil.which("rodski")
    if found:
        return [found]
    return [sys.executable, "-m", "rodski.rodski_cli"]


def ensure_pages_server() -> None:
    """被测页面由本进程提供（端口与被测模块 globalvalue Site.URL 一致）。"""
    with socket.socket() as sock:
        if sock.connect_ex(("127.0.0.1", PAGES_PORT)) == 0:
            return

    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, *args):  # noqa: D401 - 静默访问日志
            pass

    server = ThreadingHTTPServer(("127.0.0.1", PAGES_PORT),
                                 partial(QuietHandler, directory=str(PAGES)))
    threading.Thread(target=server.serve_forever, daemon=True).start()


class Checker:
    """软断言集合：一个 AC 内的所有检查点都执行完再统一报告。"""

    def __init__(self, ac_id: str):
        self.ac_id = ac_id
        self.items: List[Dict[str, object]] = []

    def check(self, ok: bool, desc: str, detail: str = "") -> bool:
        self.items.append({"ok": bool(ok), "desc": desc, "detail": "" if ok else detail})
        return bool(ok)

    def equal(self, actual, expected, desc: str) -> bool:
        return self.check(actual == expected, desc, f"期望 {expected!r}，实际 {actual!r}")

    def contains(self, text: str, needle: str, desc: str) -> bool:
        return self.check(needle in (text or ""), desc,
                          f"未包含 {needle!r}；相关输出末尾:\n{tail(text)}")

    def matches(self, text: str, pattern: str, desc: str) -> bool:
        return self.check(re.search(pattern, text or "", re.I | re.M) is not None, desc,
                          f"未匹配 /{pattern}/；相关输出末尾:\n{tail(text)}")

    @property
    def failed(self) -> List[Dict[str, object]]:
        return [item for item in self.items if not item["ok"]]


def tail(text: str, lines: int = 25) -> str:
    return "\n".join((text or "").splitlines()[-lines:])


class TargetRun:
    """以子进程执行一次被测用例：rodski run <target> --headless <args>。"""

    def __init__(self, case_file: str, *args: str):
        self.case_path = TARGETS / "case" / case_file
        self.args = list(args)
        self.marker = Path(tempfile.mkstemp(prefix="rodski_marker_", suffix=".txt")[1])
        self.proc: Optional[subprocess.Popen] = None
        self._buf = bytearray()
        self._lock = threading.Lock()
        self._before: set = set()
        self.pauses_seen = 0

    # ── 进程控制 ──────────────────────────────────────────────
    def start(self) -> "TargetRun":
        ensure_pages_server()
        result_root = TARGETS / "result"
        result_root.mkdir(exist_ok=True)
        self._before = {p.name for p in result_root.iterdir()}
        env = dict(os.environ, RODSKI_DEBUG_MARKER=str(self.marker), PYTHONUNBUFFERED="1")
        cmd = rodski_cmd() + ["run", str(self.case_path), "--headless"] + self.args
        self.cmd = cmd
        self.proc = subprocess.Popen(
            cmd, cwd=str(REPO), env=env, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True,
        )
        threading.Thread(target=self._pump, daemon=True).start()
        return self

    def _pump(self) -> None:
        fd = self.proc.stdout.fileno()
        while True:
            chunk = os.read(fd, 4096)
            if not chunk:
                return
            with self._lock:
                self._buf.extend(chunk)

    @property
    def output(self) -> str:
        with self._lock:
            return self._buf.decode("utf-8", errors="replace")

    def running(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def send(self, command: str) -> None:
        if not self.running():
            raise AcFailed(f"进程已退出，无法输入 {command!r}；输出末尾:\n{tail(self.output)}")
        self.proc.stdin.write((command + "\n").encode())
        self.proc.stdin.flush()

    def wait_exit(self, timeout: float = EXIT_TIMEOUT) -> int:
        try:
            return self.proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            raise AcFailed(f"{timeout}s 内未结束（可能仍阻塞在暂停/提示处）；输出末尾:\n{tail(self.output)}")

    def stop(self) -> None:
        """结束被测进程及其进程组（含浏览器）。"""
        if self.proc is None:
            return
        try:
            os.killpg(self.proc.pid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            pass
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(self.proc.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass

    # ── 等待与观察 ────────────────────────────────────────────
    def wait_for(self, pattern: str, timeout: float = PAUSE_TIMEOUT, what: str = "") -> re.Match:
        regex = re.compile(pattern, re.I | re.M)
        deadline = time.time() + timeout
        while time.time() < deadline:
            found = regex.search(self.output)
            if found:
                return found
            if not self.running():
                found = regex.search(self.output)
                if found:
                    return found
                raise AcFailed(f"进程已退出（exit={self.proc.returncode}），未出现{what or pattern}；"
                               f"输出末尾:\n{tail(self.output)}")
            time.sleep(0.1)
        raise AcFailed(f"{timeout}s 内未出现{what or pattern}；输出末尾:\n{tail(self.output)}")

    def pause_lines(self) -> List[str]:
        return [m.group(0).strip() for m in PAUSE_LINE.finditer(self.output)]

    def wait_pause(self, timeout: float = PAUSE_TIMEOUT) -> Dict[str, object]:
        """等待下一次暂停，并确认进程确实阻塞（轨迹不再增长、进程仍存活）。"""
        want = self.pauses_seen + 1
        deadline = time.time() + timeout
        while time.time() < deadline:
            lines = self.pause_lines()
            if len(lines) >= want:
                start = self.output.rfind(lines[want - 1])
                time.sleep(1.5)
                before = self.markers()
                time.sleep(1.0)
                if not self.running():
                    raise AcFailed(f"出现暂停提示后进程直接退出（exit={self.proc.returncode}），并未阻塞等待输入；"
                                   f"提示: {lines[want - 1]}")
                if self.markers() != before:
                    raise AcFailed(f"出现暂停提示后用例仍在继续执行（轨迹 {before} → {self.markers()}）")
                self.pauses_seen = want
                return {"line": lines[want - 1], "block": self.output[start:], "markers": before}
            if not self.running():
                raise AcFailed(f"进程已退出（exit={self.proc.returncode}），未出现第 {want} 次暂停提示"
                               f"（含 [Breakpoint] 或 已暂停）；输出末尾:\n{tail(self.output)}")
            time.sleep(0.1)
        raise AcFailed(f"{timeout}s 内未出现第 {want} 次暂停提示；输出末尾:\n{tail(self.output)}")

    def drive(self, respond: Callable[[Dict[str, object]], str], max_pauses: int = 200) -> List[Dict[str, object]]:
        """反复等待暂停并按 respond(pause) 的返回值输入，直到进程结束。"""
        pauses = []
        while len(pauses) < max_pauses:
            try:
                pause = self.wait_pause(timeout=PAUSE_TIMEOUT)
            except AcFailed:
                if not self.running():
                    break
                raise
            pauses.append(pause)
            self.send(respond(pause))
        self.wait_exit()
        return pauses

    def markers(self) -> List[str]:
        if not self.marker.exists():
            return []
        return [line for line in self.marker.read_text(encoding="utf-8").splitlines() if line]

    # ── 结果目录 ──────────────────────────────────────────────
    def result_dir(self) -> Path:
        root = TARGETS / "result"
        fresh = sorted((p for p in root.iterdir() if p.is_dir() and p.name not in self._before),
                       key=lambda p: p.stat().st_mtime)
        if not fresh:
            raise AcFailed(f"被测模块 result/ 下没有本次运行生成的结果目录；输出末尾:\n{tail(self.output)}")
        return fresh[-1]

    def summary(self) -> Dict[str, object]:
        path = self.result_dir() / "execution_summary.json"
        if not path.exists():
            raise AcFailed(f"结果目录中没有 execution_summary.json: {path.parent}")
        return json.loads(path.read_text(encoding="utf-8"))

    def steps(self) -> Dict[int, Dict[str, object]]:
        return {int(s["index"]): s for s in self.summary().get("steps", []) if "index" in s}

    def execution_log(self) -> str:
        logs = list(self.result_dir().rglob("execution.log"))
        return "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in logs)

    def find_files(self, pattern: str) -> List[Path]:
        return sorted(self.result_dir().rglob(pattern))

    def driver_actions(self) -> List[Dict[str, object]]:
        files = self.find_files("driver_actions*.jsonl")
        if not files:
            raise AcFailed(f"结果目录 {self.result_dir()} 中没有 driver_actions.jsonl")
        records = []
        for path in files:
            for no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if not line.strip():
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise AcFailed(f"{path.name} 第 {no} 行不是合法 JSON: {exc}")
        return records


def debug_cli(*args: str, timeout: float = 15) -> Dict[str, object]:
    """在另一个进程中执行 rodski debug ...（模拟"另一个终端"）。"""
    started = time.time()
    try:
        done = subprocess.run(rodski_cmd() + ["debug"] + list(args), cwd=str(REPO),
                              capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"rc": -1, "out": f"rodski debug {' '.join(args)} 超过 {timeout}s 未返回", "ms": timeout * 1000}
    return {"rc": done.returncode, "out": (done.stdout or "") + (done.stderr or ""),
            "ms": (time.time() - started) * 1000}


def step_ok(step: Optional[Dict[str, object]]) -> bool:
    return bool(step) and str(step.get("status", "")).lower() in ("ok", "pass", "passed", "success")


def step_skipped(step: Optional[Dict[str, object]]) -> bool:
    return bool(step) and str(step.get("status", "")).lower() in ("skip", "skipped")


def finish(checker: Checker, runs: List[TargetRun]) -> int:
    """输出报告：通过时 stdout 打印 JSON（成为步骤返回值），失败时 stderr 打印明细并返回 1。"""
    for run in runs:
        run.stop()
    report = {
        "ac": checker.ac_id,
        "passed": not checker.failed,
        "checks": [f"{'✅' if i['ok'] else '❌'} {i['desc']}" for i in checker.items],
        "commands": [" ".join(Path(c).name if n == 0 else c for n, c in enumerate(r.cmd))
                     for r in runs if getattr(r, "cmd", None)],
    }
    if checker.failed:
        lines = [f"{checker.ac_id} 验收未通过（{len(checker.failed)}/{len(checker.items)} 项失败）"]
        lines += report["commands"]
        for item in checker.items:
            lines.append(f"{'✅' if item['ok'] else '❌'} {item['desc']}")
            if item["detail"]:
                lines.append("    " + str(item["detail"]).replace("\n", "\n    "))
        print("\n".join(lines), file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False))
    return 0
