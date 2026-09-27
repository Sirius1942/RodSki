#!/usr/bin/env python3
"""Standalone business-model debug CLI.

This entry point deliberately executes one business-model invocation without
creating a Case, a result XML file, or any formal run statistics.  It is meant
for inspecting a graph, its selected data rows, the actual path, and the
assertion output while designing a business model.

Example::

    python3 rodski/business_debug.py \
      --module rodski-demo/DEMO/demo_business_model \
      --ref login_flow \
      --flow F_LOGIN_SUCCESS \
      --input LOGIN_OK_01 \
      --expect LOGIN_OK_01

The graph parser, validator, SQLite data loading, and graph execution are the
same components used by Case ``business_call`` execution.  No formal Case
lifecycle is constructed here.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

# The file is intentionally executable both as ``python -m rodski.business_debug``
# and as ``python rodski/business_debug.py`` from the repository root.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from rodski.core.business_model import (  # type: ignore
        BusinessModel,
        BusinessModelError,
        BusinessModelExecutor,
        BusinessModelParser,
        BusinessModelResult,
    )
    from rodski.core.data_table_parser import DataTableParser  # type: ignore
    from rodski.core.global_value_parser import GlobalValueParser  # type: ignore
else:
    from .core.business_model import (
        BusinessModel,
        BusinessModelError,
        BusinessModelExecutor,
        BusinessModelParser,
        BusinessModelResult,
    )
    from .core.data_table_parser import DataTableParser
    from .core.global_value_parser import GlobalValueParser


class BusinessDebugError(BusinessModelError):
    """Configuration or runtime error specific to the debug entry point."""


class BusinessDebugSession:
    """Prepare the ordinary module assets needed by one debug invocation.

    The session uses a private copy of the parsed data tables.  This is
    important for interface business steps: the same projection used by a
    Case call (business input row -> interface model table) is available to
    the keyword engine, but the source SQLite data and any process-global
    tables are never modified.
    """

    def __init__(self, module_dir: Path, model: BusinessModel):
        self.module_dir = module_dir.resolve()
        self.model = model
        self.data_manager: Optional[DataTableParser] = None
        self.data_source = None
        # Import the browser/interface execution stack lazily.  A graph made
        # only of empty nodes should remain debuggable without initializing a
        # driver or importing optional UI dependencies.
        self.model_parser = None
        self.data_resolver = None
        self.keyword_engine = None

        data_dir = self.module_dir / "data"
        sqlite_file = data_dir / "data.sqlite"
        if not data_dir.is_dir():
            raise BusinessDebugError(f"数据目录不存在: {data_dir}")
        if not sqlite_file.is_file():
            raise BusinessDebugError(f"SQLite 数据库不存在: {sqlite_file}")

        manager = DataTableParser(str(data_dir))
        manager.parse_all_tables()
        if manager._sqlite_source is None:  # pragma: no cover - guarded above
            raise BusinessDebugError(f"无法打开 SQLite 数据库: {sqlite_file}")

        # Keep the DataTableParser facade, including its schema validation, but
        # isolate all runtime projections from the ordinary source tables.
        manager.tables = copy.deepcopy(manager.tables)
        self.data_manager = manager
        self.data_source = manager._sqlite_source

    def _ensure_keyword_engine(self):
        if self.keyword_engine is not None:
            return self.keyword_engine

        if __package__ in (None, ""):
            from rodski.core.keyword_engine import KeywordEngine  # type: ignore
            from rodski.core.model_parser import ModelParser  # type: ignore
            from rodski.data.data_resolver import DataResolver  # type: ignore
        else:
            from .core.keyword_engine import KeywordEngine
            from .core.model_parser import ModelParser
            from .data.data_resolver import DataResolver

        model_file = self.module_dir / "model" / "model.xml"
        if not model_file.is_file():
            raise BusinessDebugError(
                f"业务节点包含可执行步骤，但接口/UI模型文件不存在: {model_file}"
            )

        try:
            self.model_parser = ModelParser(str(model_file))
            global_vars = GlobalValueParser(str(self.module_dir / "data" / "globalvalue.xml")).parse()
            engine = KeywordEngine(
                None,
                self.module_dir / "data",
                model_parser=self.model_parser,
                data_manager=self.data_manager,
                global_vars=global_vars,
                module_dir=str(self.module_dir),
            )
            resolver = DataResolver(
                data_manager=self.data_manager,
                global_vars=global_vars,
                base_path=str(self.module_dir),
                return_provider=engine.get_return,
            )
            engine.data_resolver = resolver
        except Exception as exc:
            raise BusinessDebugError(f"初始化业务步骤执行器失败: {exc}") from exc

        self.data_resolver = resolver
        self.keyword_engine = engine
        return engine

    @staticmethod
    def _resolve_business_data(value: str, context: Mapping[str, Any]) -> str:
        """Resolve the two business identifiers supported by v0.1 step data."""
        resolved = str(value or "")
        business = context.get("Business", {})
        for variable, key in (
            ("${Business.InputDataID}", "InputDataID"),
            ("${Business.ExpectDataID}", "ExpectDataID"),
        ):
            resolved = resolved.replace(variable, str(business.get(key, "")))
        return resolved

    def step_runner(self, step, context: Mapping[str, Any]) -> Mapping[str, Any]:
        """Run one business step through the existing keyword engine.

        The debug CLI deliberately has no browser lifecycle.  Interface steps
        (the common business-model use case) use the existing ``send`` keyword
        implementation.  Stateless keywords such as ``set`` and ``wait`` are
        also delegated.  Browser-dependent actions fail explicitly rather than
        silently pretending that a UI action succeeded.
        """
        action = str(step.action or "").strip().lower()
        if not action:
            raise BusinessDebugError("业务节点 test_step 缺少 action")

        # Do not provide a fake browser.  These actions require Case/ski_run
        # browser setup and must be reported as unsupported in this CLI.
        browser_actions = {
            "navigate", "click", "type", "evaluate", "hover", "screenshot",
            "get", "select", "upload", "launch", "double_click", "right_click",
            "upload_file", "clear", "get_text", "assert",
        }
        if action in browser_actions:
            raise BusinessDebugError(
                f"debug CLI 未创建浏览器驱动，不能执行 UI 关键字 {action!r}; "
                "请将该业务模型嵌入 Case 后使用 ski_run 执行"
            )

        engine = self._ensure_keyword_engine()
        resolved_data = self._resolve_business_data(step.data, context)

        # A business input table is intentionally named after the business
        # model, not after the interface model.  Project only the fields that
        # the ordinary model declares, exactly as Case business_call does.
        if action in {"send", "type"} and resolved_data == str(
            context.get("Business", {}).get("InputDataID", "")
        ):
            model_name = str(step.model or "").strip()
            model_definition = self.model_parser.get_model(model_name) if self.model_parser else None
            if model_definition is not None:
                model_fields = {
                    name for name in model_definition if not name.startswith("__")
                }
                input_row = dict(context.get("Input", {}))
                projected = {
                    key: value for key, value in input_row.items() if key in model_fields
                }
                if projected:
                    self.data_manager.tables.setdefault(model_name, {})[resolved_data] = projected

        history_before = len(engine._context.history)
        params: Dict[str, Any] = dict(step.attributes or {})
        params.update({"model": step.model, "data": resolved_data})
        # ``action`` is not consumed by KeywordEngine, but preserving all
        # attributes above keeps future business-step parameters available.
        engine.execute(action, params)

        if len(engine._context.history) <= history_before:
            return {}
        output = engine._context.history[-1]
        if not isinstance(output, dict):
            return {}
        normalized = dict(output)
        capture = normalized.get("_capture")
        if isinstance(capture, dict):
            normalized.update(capture)
        return normalized

    def close(self) -> None:
        if self.data_manager is not None:
            self.data_manager.close()


def _load_model(module_dir: Path, ref: str) -> BusinessModel:
    business_dir = module_dir / "business"
    if not business_dir.is_dir():
        raise BusinessDebugError(f"业务模型目录不存在: {business_dir}")
    models = BusinessModelParser().parse_directory(business_dir)
    model = models.get(ref)
    if model is None:
        available = ", ".join(sorted(models)) or "<none>"
        raise BusinessDebugError(f"找不到业务模型 ref={ref!r}; 可用模型: {available}")
    return model


def execute_debug(
    *,
    module_dir: Path,
    ref: str,
    flow: str,
    input_data_id: str,
    expect_data_id: str,
) -> BusinessModelResult:
    """Execute exactly one debug invocation and return its in-memory result."""
    module_path = Path(module_dir).expanduser().resolve()
    model = _load_model(module_path, ref)
    session = BusinessDebugSession(module_path, model)
    try:
        executor = BusinessModelExecutor(
            model,
            data_tables=session.data_manager.tables,
            data_source=session.data_source,
            step_runner=session.step_runner,
        )
        return executor.execute(flow, input_data_id, expect_data_id)
    finally:
        # There is intentionally no ResultWriter call here.  Closing the
        # source is the only cleanup required for a debug-only invocation.
        session.close()


def _format_result(result: BusinessModelResult) -> str:
    lines = [
        "DEBUG business model",
        f"model: {result.model_id}",
        f"flow: {result.flow_id}",
        f"input: {result.input_data_id}",
        f"expect: {result.expect_data_id}",
        f"actual_path: {'>'.join(result.actual_path)}",
        f"expected_path: {'>'.join(result.expected_path)}",
        f"actual: {json.dumps(result.actual, ensure_ascii=False, sort_keys=True, default=str)}",
        f"expected: {json.dumps(result.expected, ensure_ascii=False, sort_keys=True, default=str)}",
    ]
    if result.assertion_errors:
        lines.append("errors:")
        lines.extend(f"  - {error}" for error in result.assertion_errors)
    lines.append(f"status: {'PASS' if result.passed else 'FAIL'}")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="business_debug",
        description=(
            "调试一次业务模型调用。仅输出内存中的 DEBUG 结果，"
            "不执行 Case 生命周期、不写正式 result.xml、不计入通过率。"
        ),
    )
    parser.add_argument("--module", required=True, help="测试模块目录，例如 rodski-demo/DEMO/demo_business_model")
    parser.add_argument("--ref", required=True, help="业务模型 id（business_model@id）")
    parser.add_argument("--flow", required=True, help="本次调试选择的目标流程 id")
    parser.add_argument("--input", required=True, dest="input_data_id", help="业务模型 Data 表中的 DataID")
    parser.add_argument("--expect", required=True, dest="expect_data_id", help="业务模型 Verify 表中的 DataID")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = execute_debug(
            module_dir=Path(args.module).expanduser().resolve(),
            ref=args.ref,
            flow=args.flow,
            input_data_id=args.input_data_id,
            expect_data_id=args.expect_data_id,
        )
    except Exception as exc:
        # Errors are also debug-only: do not create a formal result entry or
        # print a Case-style summary that could be mistaken for a test run.
        print(f"DEBUG ERROR: {exc}", file=sys.stderr)
        return 2

    print(_format_result(result))
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
