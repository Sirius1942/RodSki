"""v11.6.0 run 级并行：``rodski run ... --workers N``（设计文档 §P4）。

调度模型
--------
- **调度单位是用例文件**（case_file）。父进程按文件的步骤数做贪心装箱（LPT），把全部
  用例文件静态分给 N 个 worker 进程；同一文件的用例只会落在同一个 worker，并在其中
  **顺序执行**，文件内依赖（共享会话、``save_auth_state`` / ``use_auth_state``、前后置）
  不会被打乱。
- 每个 worker 是独立进程（``spawn``），拥有独立的执行器与浏览器；worker 内部仍是一个
  普通的 :class:`SKIExecutor`，所以 ``SessionMode``（shared_browser / shared_session）
  在**每个 worker 内**生效。
- worker 的执行器与顺序执行使用**同一个 case_path**（同样的发现、plan / selector 选择
  语义），只额外按 ``case_file_filter`` 保留分给自己的文件 —— 这样并行与顺序执行选中的
  用例集合、SKIP 语义完全一致。

结果合并
--------
- 父进程先创建本次运行目录（``result/rodski_<时间戳>``），worker 通过
  :meth:`ResultWriter.attach_run_dir` 挂到同一目录：用例级产物照常镜像到
  ``case/<用例文件>/screenshots|recordings``（文件互不相同，天然无冲突），日志逐行追加到
  同一个 ``execution.log``（每行带 ``[wN]`` 标记）。
- worker 不写 ``result.xml``，把结果（已转成纯 JSON 数据）交回父进程；父进程按用例文件的
  发现顺序合并后，一次性写出汇总全部用例的 ``result.xml``。
- worker 异常时，父进程为它**已选中**（plan / selector 过滤后）却没有结果的用例补 FAIL
  （plan 判定为 SKIP 的补 SKIP），不会静默丢用例；worker 未走到选择阶段就崩溃时，回落为
  它负责的文件内的全部用例。
"""
from __future__ import annotations

import json
import logging
import multiprocessing
import os
import re
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger("rodski")

__all__ = [
    "CaseFileTask",
    "discover_case_file_tasks",
    "partition_tasks",
    "merge_worker_results",
    "run_parallel",
    "worker_entry",
]

_STEP_RE = re.compile(r"<test_step\b")
# 仅在 XML 无法解析时兜底：同时支持单 / 双引号属性
_CASE_TAG_RE = re.compile(r"<case\b([^>]*)>")
_ATTR_RE = re.compile(r"\b(id|title)\s*=\s*(?:\"([^\"]*)\"|'([^']*)')")


def _parse_cases(text: str) -> List[Dict[str, str]]:
    """列出用例文件内的 <case id title>（ET 解析，属性引号不限；XML 损坏时回落正则）。"""
    import xml.etree.ElementTree as ET
    try:
        root = ET.fromstring(text)
        return [
            {"case_id": (el.get("id") or "").strip(), "title": el.get("title", "")}
            for el in root.iter("case") if (el.get("id") or "").strip()
        ]
    except ET.ParseError:
        cases = []
        for m in _CASE_TAG_RE.finditer(text):
            attrs = {k: (dq or sq) for k, dq, sq in _ATTR_RE.findall(m.group(1))}
            if attrs.get("id"):
                cases.append({"case_id": attrs["id"], "title": attrs.get("title", "")})
        return cases


class CaseFileTask(dict):
    """一个用例文件的调度单元：``case_file``（相对 case/）、``path``、``weight``、``cases``。"""

    @property
    def case_file(self) -> str:
        return self["case_file"]

    @property
    def weight(self) -> int:
        return self["weight"]


def _relative_case_file(module_dir: Path, xml_path: Path) -> str:
    try:
        from .case_discovery import relative_case_file
    except ImportError:  # pragma: no cover - 顶层包方式导入
        from core.case_discovery import relative_case_file
    try:
        return relative_case_file(module_dir, xml_path)
    except ValueError:
        return xml_path.name


def discover_case_file_tasks(case_path: Path, module_dir: Path) -> List[CaseFileTask]:
    """按与顺序执行相同的发现顺序列出用例文件，并估算每个文件的工作量（步骤数）。"""
    try:
        from .case_discovery import discover_case_files
    except ImportError:  # pragma: no cover
        from core.case_discovery import discover_case_files

    case_path = Path(case_path)
    files = discover_case_files(case_path) if case_path.is_dir() else [case_path]
    tasks: List[CaseFileTask] = []
    for f in files:
        try:
            text = Path(f).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            text = ""
        cases = _parse_cases(text)
        tasks.append(CaseFileTask(
            case_file=_relative_case_file(Path(module_dir), Path(f)),
            path=str(f),
            weight=max(1, len(_STEP_RE.findall(text))),
            cases=cases,
        ))
    return tasks


def partition_tasks(tasks: Sequence[CaseFileTask], workers: int) -> List[List[CaseFileTask]]:
    """把用例文件静态分给 ``workers`` 个桶（LPT 贪心：按工作量从大到小放入当前最轻的桶）。

    - 同一个文件只进一个桶（文件是最小调度单位）；
    - 空桶会被丢弃，所以返回的桶数 = min(workers, 文件数)；
    - 桶内文件保持原发现顺序（执行器也按发现顺序遍历）。
    """
    workers = max(1, int(workers or 1))
    order = {t.case_file: i for i, t in enumerate(tasks)}
    buckets: List[List[CaseFileTask]] = [[] for _ in range(min(workers, len(tasks)) or 1)]
    loads = [0] * len(buckets)
    for task in sorted(tasks, key=lambda t: (-t.weight, order[t.case_file])):
        idx = min(range(len(buckets)), key=lambda i: (loads[i], i))
        buckets[idx].append(task)
        loads[idx] += task.weight
    return [sorted(b, key=lambda t: order[t.case_file]) for b in buckets if b]


def merge_worker_results(
    tasks: Sequence[CaseFileTask],
    worker_outputs: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """按用例文件的发现顺序合并各 worker 的结果；文件内保持 worker 给出的执行顺序。

    worker 失败（``error`` 非空）时，为其负责、却没有结果的文件内全部用例补 FAIL，
    保证合并后的 result.xml 不会静默少用例。
    """
    by_file: Dict[str, List[Dict[str, Any]]] = {}
    unknown: List[Dict[str, Any]] = []
    known = {t.case_file for t in tasks}
    task_by_file = {t.case_file: t for t in tasks}

    for out in worker_outputs:
        for r in out.get("results") or []:
            cf = r.get("case_file", "")
            if cf in known:
                by_file.setdefault(cf, []).append(r)
            else:
                unknown.append(r)
        err = out.get("error")
        if err:
            # 补行范围：优先用 worker 已完成选择（plan / selector 过滤后）的用例清单，
            # 未走到选择阶段才回落为文件内的全部用例；已有结果的用例不重复补
            selected = out.get("selected")
            if selected is None:
                planned = [
                    {"case_file": cf, "case_id": c.get("case_id", ""), "title": c.get("title", "")}
                    for cf in (out.get("case_files") or [])
                    for c in (task_by_file[cf]["cases"] if cf in task_by_file else [])
                ]
            else:
                planned = list(selected)
            for c in planned:
                cf = c.get("case_file", "")
                done = {r.get("case_id") for r in by_file.get(cf, [])}
                if c.get("case_id") in done:
                    continue
                skip_reason = c.get("skip_reason")
                row = {
                    "case_id": c.get("case_id", ""),
                    "title": c.get("title", ""),
                    "case_file": cf,
                    "status": "SKIP" if skip_reason else "FAIL",
                    "execution_time": 0,
                    "screenshot_path": "",
                }
                if skip_reason:
                    row["error"] = skip_reason
                else:
                    row["error_type"] = "WorkerError"
                    row["error"] = f"并行 worker {out.get('worker_id')} 异常，用例未执行: {err}"
                if cf in known:
                    by_file.setdefault(cf, []).append(row)
                else:
                    unknown.append(row)

    merged: List[Dict[str, Any]] = []
    for t in tasks:
        merged.extend(by_file.get(t.case_file, []))
    merged.extend(unknown)
    return merged


def _to_plain(results: Any) -> Any:
    """把结果转成纯 JSON 数据（跨进程安全；result.xml 本就把每个值写成字符串）。"""
    return json.loads(json.dumps(results, ensure_ascii=False, default=str))


# --------------------------------------------------------------------------- worker
def _import_runtime():
    try:
        from .ski_executor import SKIExecutor
        from .config_manager import ConfigManager
        from .diagnosis_engine import DiagnosisEngine
        from .driver_factory import DriverFactory
        from ..drivers.playwright_driver import PlaywrightDriver
    except ImportError:  # pragma: no cover - 顶层包方式导入
        from core.ski_executor import SKIExecutor
        from core.config_manager import ConfigManager
        from core.diagnosis_engine import DiagnosisEngine
        from core.driver_factory import DriverFactory
        from drivers.playwright_driver import PlaywrightDriver
    return SKIExecutor, ConfigManager, DiagnosisEngine, DriverFactory, PlaywrightDriver


def _build_failure_hook(spec: Dict[str, Any]) -> Optional[Callable]:
    """在 worker 内重建 on_case_failure 外部命令 hook（与顺序执行语义一致）。"""
    failure_specs = spec.get("on_case_failure_specs")
    if not failure_specs:
        return None
    try:
        from .hooks_runner import run_external_hook
    except ImportError:  # pragma: no cover
        from core.hooks_runner import run_external_hook
    hook_context = dict(spec.get("hook_context") or {})

    def _notify_case_failure(case, error, screenshot_path):
        decision = run_external_hook(
            "on_case_failure",
            {
                **hook_context,
                "case_id": case.get("case_id", ""),
                "title": case.get("title", ""),
                "description": case.get("description", ""),
                "component_type": case.get("component_type", ""),
                "error_type": type(error).__name__,
                "error_message": str(error),
                "screenshot_path": screenshot_path,
            },
            failure_specs,
        )
        if not decision.allow:
            logger.warning("on_case_failure hook 返回 deny；用例已失败，继续失败处理: %s", decision.reason)

    return _notify_case_failure


def worker_entry(spec: Dict[str, Any]) -> Dict[str, Any]:
    """worker 进程入口：用一个执行器顺序执行分给自己的用例文件，返回纯数据结果。

    ``spec`` 字段：worker_id, case_path, module_dir, run_dir, case_files, headless, browser,
    needs_browser, config_overrides, plan_path, selector_filters, on_case_failure_specs,
    hook_context。
    """
    worker_id = spec.get("worker_id")
    case_files = list(spec.get("case_files") or [])
    out: Dict[str, Any] = {"worker_id": worker_id, "case_files": case_files, "results": [], "error": None}
    started = time.time()
    executor = None
    driver = None
    try:
        SKIExecutor, ConfigManager, DiagnosisEngine, DriverFactory, PlaywrightDriver = _import_runtime()
        headless = bool(spec.get("headless"))
        browser = spec.get("browser") or "chromium"
        needs_browser = bool(spec.get("needs_browser", True))

        config = ConfigManager()
        config.config.update(dict(spec.get("config_overrides") or {}))

        def create_driver(driver_type: str = "web", **kwargs):
            if driver_type in ("", "web"):
                if not needs_browser:
                    return None
                return PlaywrightDriver(headless=headless, browser=browser)
            return DriverFactory.get_driver(driver_type, **kwargs)

        hooks: Dict[str, List[Callable]] = {}
        failure_hook = _build_failure_hook(spec)
        if failure_hook is not None:
            hooks["on_case_failure"] = [failure_hook]

        driver = create_driver("web")
        executor = SKIExecutor(
            spec["case_path"],
            driver,
            config=config,
            driver_factory=create_driver,
            module_dir=spec["module_dir"],
            hooks=hooks or None,
            diagnosis_engine=DiagnosisEngine(),
        )
        # 挂到父进程创建的运行目录；worker 只收集结果，不写 result.xml
        executor.result_writer.attach_run_dir(spec["run_dir"], worker_tag=f"w{worker_id}")
        executor.result_writer.collect_only = True
        executor.case_file_filter = set(case_files)
        selector_filters = dict(spec.get("selector_filters") or {})
        executor.selector_filters = selector_filters
        if spec.get("plan_path"):
            executor.plan_path = spec["plan_path"]

        def _on_cases_selected(cases, plan_case_skips):
            # 记录经 plan / selector 过滤后的用例清单：worker 中途异常时父进程只为这些用例补行
            selected = []
            for c in cases:
                cf = c.get("case_file", "")
                uid = f"{cf}::{c.get('case_id', '')}" if cf else c.get("case_id", "")
                selected.append({"case_file": cf, "case_id": c.get("case_id", ""),
                                 "title": c.get("title", ""),
                                 "skip_reason": (plan_case_skips or {}).get(uid) or ""})
            out["selected"] = selected
            sel_file = spec.get("selected_file")
            if sel_file:
                try:
                    Path(sel_file).write_text(json.dumps(selected, ensure_ascii=False), encoding="utf-8")
                except OSError as e:  # pragma: no cover
                    logger.debug(f"[并行] 写入已选用例清单失败（忽略）: {e}")

        executor.on_cases_selected = _on_cases_selected
        logger.info(f"[并行] worker {worker_id} 开始，负责 {len(case_files)} 个用例文件: {', '.join(case_files)}")
        results = executor.execute_all_cases(
            filter_tags=selector_filters.get("filter_tags"),
            filter_priority=selector_filters.get("filter_priority"),
            exclude_tags=selector_filters.get("exclude_tags"),
            filter_case_ids=selector_filters.get("filter_case_ids"),
        )
        out["results"] = _to_plain(results)
    except BaseException as e:  # noqa: BLE001 - worker 内任何异常都要带回父进程
        out["error"] = f"{type(e).__name__}: {e}"
        try:
            logger.error(f"[并行] worker {worker_id} 异常: {out['error']}")
        except Exception:  # pragma: no cover
            pass
    finally:
        try:
            if executor is not None:
                executor.close()
            elif driver is not None:
                driver.close()
        except Exception as e:  # noqa: BLE001
            logger.debug(f"[并行] worker {worker_id} 关闭执行器出错: {e}")
    out["seconds"] = round(time.time() - started, 2)
    return out


# --------------------------------------------------------------------------- parent
def _default_pool_factory(max_workers: int):
    return ProcessPoolExecutor(max_workers=max_workers, mp_context=multiprocessing.get_context("spawn"))


def run_parallel(
    case_path: Path,
    module_dir: Path,
    workers: int,
    run_dir: Path,
    worker_options: Dict[str, Any],
    *,
    tasks: Optional[List[CaseFileTask]] = None,
    worker_fn: Callable[[Dict[str, Any]], Dict[str, Any]] = worker_entry,
    pool_factory: Optional[Callable[[int], Any]] = None,
    on_worker_done: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """把用例文件分给 N 个 worker 并行执行，返回 ``(合并后的结果, 各 worker 输出)``。

    ``worker_options`` 会原样并入每个 worker 的 spec（headless / browser / needs_browser /
    config_overrides / plan_path / selector_filters / hook 配置等）。``worker_fn`` 与
    ``pool_factory`` 仅为单元测试注入。
    """
    case_path = Path(case_path).expanduser().resolve()
    module_dir = Path(module_dir).expanduser().resolve()
    if tasks is None:
        tasks = discover_case_file_tasks(case_path, module_dir)
    buckets = partition_tasks(tasks, workers)
    import shutil
    import tempfile
    selected_dir = tempfile.mkdtemp(prefix="rodski_parallel_")
    specs = []
    for i, bucket in enumerate(buckets, 1):
        spec = dict(worker_options)
        spec.update({
            "worker_id": i,
            "case_path": str(case_path),
            "module_dir": str(module_dir),
            "run_dir": str(run_dir),
            "case_files": [t.case_file for t in bucket],
            # worker 进程崩溃（拿不到返回值）时从这里读回已选用例清单
            "selected_file": str(Path(selected_dir) / f"w{i}_selected.json"),
        })
        specs.append(spec)

    outputs: List[Dict[str, Any]] = []
    factory = pool_factory or _default_pool_factory
    try:
        with factory(len(specs)) as pool:
            futures = {pool.submit(worker_fn, spec): spec for spec in specs}
            for fut in as_completed(futures):
                spec = futures[fut]
                try:
                    out = fut.result()
                except BaseException as e:  # noqa: BLE001 - 进程崩溃（BrokenProcessPool 等）
                    out = {"worker_id": spec["worker_id"], "case_files": spec["case_files"],
                           "results": [], "error": f"{type(e).__name__}: {e}"}
                    try:
                        out["selected"] = json.loads(
                            Path(spec["selected_file"]).read_text(encoding="utf-8"))
                    except (OSError, ValueError):
                        pass  # worker 未走到选择阶段：按文件内全部用例补行
                outputs.append(out)
                if on_worker_done is not None:
                    on_worker_done(out)
    finally:
        shutil.rmtree(selected_dir, ignore_errors=True)

    outputs.sort(key=lambda o: o.get("worker_id") or 0)
    return merge_worker_results(tasks, outputs), outputs
