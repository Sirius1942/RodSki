"""RodSki 自有测试执行器

不依赖 pytest / unittest 等任何外部测试框架，通过反射自动发现并执行
tests/ 下的测试类和测试方法。

用法（在 rodski/ 目录下）::

    python selftest.py                          # 跑全部
    python selftest.py tests/unit/test_case_parser.py  # 指定文件
    python selftest.py tests/unit/test_case_parser.py tests/unit/test_auto_screenshot.py
"""
from __future__ import annotations

import importlib
import inspect
import os
import shutil
import sys
import tempfile
import time
import traceback
from pathlib import Path
from typing import Any, Callable, List, Optional, Type


# ── 辅助工具 ──────────────────────────────────────────────────

class TmpDir:
    """为每个测试方法创建独立临时目录，测试完成后自动清理。"""

    def __init__(self):
        self._path: Optional[Path] = None

    @property
    def path(self) -> Path:
        if self._path is None:
            self._path = Path(tempfile.mkdtemp(prefix="rodski_test_"))
        return self._path

    def cleanup(self):
        if self._path and self._path.exists():
            shutil.rmtree(self._path, ignore_errors=True)
            self._path = None


def assert_raises(exc_type: Type[BaseException], func: Callable, *args, **kwargs) -> BaseException:
    """断言 func(*args, **kwargs) 抛出指定异常，返回捕获到的异常实例。"""
    try:
        func(*args, **kwargs)
    except exc_type as e:
        return e
    except Exception as e:
        raise AssertionError(
            f"期望抛出 {exc_type.__name__}，实际抛出 {type(e).__name__}: {e}"
        )
    raise AssertionError(f"期望抛出 {exc_type.__name__}，但没有抛出任何异常")


def assert_raises_match(
    exc_type: Type[BaseException],
    pattern: str,
    func: Callable,
    *args,
    **kwargs,
) -> BaseException:
    """断言抛出指定异常且 str(e) 包含 pattern。"""
    import re
    e = assert_raises(exc_type, func, *args, **kwargs)
    if not re.search(pattern, str(e)):
        raise AssertionError(
            f"异常消息不匹配: 期望包含 {pattern!r}，实际为 {str(e)!r}"
        )
    return e


# ── 测试结果 ──────────────────────────────────────────────────

class TestResult:
    def __init__(self, class_name: str, method_name: str):
        self.class_name = class_name
        self.method_name = method_name
        self.status: str = "PASS"
        self.error: Optional[str] = None
        self.traceback: Optional[str] = None
        self.elapsed: float = 0.0


# ── 核心执行器 ────────────────────────────────────────────────

class RodskiTestRunner:
    """RodSki 自有测试执行器"""

    def __init__(self, verbosity: int = 1):
        self.verbosity = verbosity
        self.results: List[TestResult] = []

    # ── 发现 ──

    @staticmethod
    def discover_files(paths: List[str], test_dir: str = "tests") -> List[Path]:
        """发现测试文件。

        paths 为空时从 test_dir 递归查找 test_*.py；
        paths 非空时直接使用给定路径。
        """
        if paths:
            return [Path(p) for p in paths if Path(p).is_file()]

        root = Path(test_dir)
        if not root.is_dir():
            return []
        return sorted(root.rglob("test_*.py"))

    @staticmethod
    def _import_module_from_path(file_path: Path) -> Any:
        """从文件路径导入模块（不依赖 PYTHONPATH）。"""
        module_name = file_path.stem
        spec = importlib.util.spec_from_file_location(module_name, str(file_path))
        if spec is None or spec.loader is None:
            raise ImportError(f"无法导入: {file_path}")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = mod
        spec.loader.exec_module(mod)
        return mod

    @staticmethod
    def _discover_test_classes(module: Any) -> List[type]:
        """找出模块里所有 Test* 开头的类。"""
        classes = []
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if name.startswith("Test") and obj.__module__ == module.__name__:
                classes.append(obj)
        return classes

    @staticmethod
    def _discover_test_methods(cls: type) -> List[str]:
        """找出类中所有 test_ 开头的方法，按定义顺序排列。"""
        methods = []
        for name in dir(cls):
            if name.startswith("test_") and callable(getattr(cls, name)):
                methods.append(name)
        return sorted(methods)

    # ── 执行 ──

    def _run_method(self, instance: Any, method_name: str, tmp: TmpDir) -> TestResult:
        class_name = type(instance).__name__
        result = TestResult(class_name, method_name)
        method = getattr(instance, method_name)

        sig = inspect.signature(method)
        kwargs: dict = {}
        for param_name in sig.parameters:
            if param_name == "tmp_path":
                kwargs["tmp_path"] = tmp.path

        start = time.time()
        try:
            method(**kwargs)
        except AssertionError as e:
            result.status = "FAIL"
            result.error = str(e) or "AssertionError"
            result.traceback = traceback.format_exc()
        except Exception as e:
            result.status = "ERROR"
            result.error = f"{type(e).__name__}: {e}"
            result.traceback = traceback.format_exc()
        finally:
            result.elapsed = round(time.time() - start, 4)

        return result

    def run_file(self, file_path: Path) -> List[TestResult]:
        """执行单个测试文件中的所有测试。"""
        results: List[TestResult] = []
        try:
            mod = self._import_module_from_path(file_path)
        except Exception as e:
            r = TestResult("<import>", str(file_path))
            r.status = "ERROR"
            r.error = f"导入失败: {e}"
            r.traceback = traceback.format_exc()
            results.append(r)
            return results

        classes = self._discover_test_classes(mod)
        for cls in classes:
            methods = self._discover_test_methods(cls)
            for method_name in methods:
                tmp = TmpDir()
                instance = cls()

                if hasattr(instance, "setup_method"):
                    try:
                        setup_sig = inspect.signature(instance.setup_method)
                        setup_kw: dict = {}
                        for pn in setup_sig.parameters:
                            if pn == "tmp_path":
                                setup_kw["tmp_path"] = tmp.path
                        instance.setup_method(**setup_kw)
                    except Exception as e:
                        r = TestResult(cls.__name__, method_name)
                        r.status = "ERROR"
                        r.error = f"setup_method 失败: {e}"
                        r.traceback = traceback.format_exc()
                        results.append(r)
                        tmp.cleanup()
                        continue

                result = self._run_method(instance, method_name, tmp)
                results.append(result)

                if hasattr(instance, "teardown_method"):
                    try:
                        instance.teardown_method()
                    except Exception:
                        pass

                tmp.cleanup()

        return results

    def run(self, file_paths: List[Path]) -> int:
        """执行全部测试文件，打印结果，返回退出码。"""
        total_start = time.time()
        all_results: List[TestResult] = []

        for fp in file_paths:
            rel = fp.as_posix()
            if self.verbosity >= 1:
                print(f"\n{'─' * 60}")
                print(f"  {rel}")
                print(f"{'─' * 60}")

            file_results = self.run_file(fp)
            all_results.extend(file_results)

            for r in file_results:
                mark = "✓" if r.status == "PASS" else "✗"
                label = f"{r.class_name}.{r.method_name}"
                if self.verbosity >= 1:
                    status_text = r.status
                    print(f"  {mark} {label}  ({r.elapsed}s) {status_text}")
                    if r.status != "PASS" and r.error and self.verbosity >= 2:
                        print(f"    {r.error}")

        self.results = all_results
        elapsed = round(time.time() - total_start, 3)

        passed = sum(1 for r in all_results if r.status == "PASS")
        failed = sum(1 for r in all_results if r.status == "FAIL")
        errors = sum(1 for r in all_results if r.status == "ERROR")
        total = len(all_results)

        print(f"\n{'═' * 60}")
        print(f"  总计: {total}  通过: {passed}  失败: {failed}  错误: {errors}  耗时: {elapsed}s")
        print(f"{'═' * 60}")

        if failed + errors > 0:
            print("\n失败详情:\n")
            for r in all_results:
                if r.status != "PASS":
                    print(f"  ✗ {r.class_name}.{r.method_name}")
                    if r.traceback:
                        for line in r.traceback.strip().splitlines():
                            print(f"    {line}")
                    print()

        return 0 if (failed + errors) == 0 else 1
