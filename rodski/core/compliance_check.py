"""合规检查聚合 — on_run_start 前置检查（v8.2.0 Hooks 机制）

聚合四类既有/新增的静态检查，供 CLI 在执行前一次性跑完：
  1. 目录结构（product/{项目}/{模块} 下 case/model/data 必须存在）
  2. @plan_id 与 --tag/--group/--priority selector 互斥
  3. data.sqlite 逻辑表 schema 一致性
  4. 接口/DB 模型 _verify 数据表中禁止使用 ${Return[-1]}（自引用空校验）

设计见 `.pb/specs/rodski-hooks-design.md` §8/§11.4。
每项检查独立 try/except，某一项检查本身抛异常不应导致整个合规检查函数崩溃。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .test_plan_selection import check_plan_selector_conflict
from .data_schema_validator import DataSchemaValidator

REQUIRED_MODULE_DIRS = ("case", "model", "data")


@dataclass
class ComplianceReport:
    """合规检查汇总结果。"""

    passed: bool = True
    failed_checks: List[Dict[str, str]] = field(default_factory=list)

    def add_failure(self, check_name: str, reason: str) -> None:
        self.passed = False
        self.failed_checks.append({"check_name": check_name, "reason": reason})

    def to_dict(self) -> Dict[str, Any]:
        return {"passed": self.passed, "failed_checks": list(self.failed_checks)}


def check_directory_structure(module_dir: Path) -> List[str]:
    """校验测试模块目录下固定目录是否齐全，返回缺失的目录名列表（不抛异常）。"""
    missing = []
    for d in REQUIRED_MODULE_DIRS:
        if not (module_dir / d).is_dir():
            missing.append(d)
    return missing


def scan_return_ref_violations(
    tables: Dict[str, Dict[str, Dict[str, Any]]],
    model_types: Dict[str, str],
) -> List[str]:
    """静态扫描接口/DB 模型的 _verify 数据表，检测 ${Return[-1]} 自引用空校验。

    与 keyword_engine.py 运行时检查（batch_verify 内联逻辑）同款字符串匹配，
    区别是本函数只读扫描、不抛异常，供合规检查阶段提前发现问题。

    Args:
        tables: DataTableParser.tables，结构为 {table_name: {data_id: {field: value}}}
        model_types: {model_name: model_type}，model_type 为 'ui'/'interface'/'database'

    Returns:
        违规描述字符串列表，形如 "LoginAPI_verify.V001.token"；无违规返回空列表
    """
    violations: List[str] = []
    for table_name, rows in tables.items():
        if not table_name.endswith("_verify"):
            continue
        base_model_name = table_name[: -len("_verify")]
        model_type = model_types.get(base_model_name)
        if model_type not in ("interface", "database"):
            continue
        for data_id, row in rows.items():
            for field_name, field_val in row.items():
                if "${Return[-1]" in str(field_val):
                    violations.append(f"{table_name}.{data_id}.{field_name}")
    return violations


def run_compliance_checks(
    case_path: Optional[str] = None,
    module_dir: Optional[str] = None,
    plan_path: Optional[str] = None,
    selector_filters: Optional[Dict[str, Any]] = None,
    tables: Optional[Dict[str, Dict[str, Dict[str, Any]]]] = None,
    schemas: Optional[Dict[str, List[str]]] = None,
    model_types: Optional[Dict[str, str]] = None,
) -> ComplianceReport:
    """跑完四类合规检查，汇总为一份报告。

    每一项检查独立 try/except：某一项检查本身抛异常不会导致整体崩溃，
    而是记录为该项 failed，reason 写异常信息。
    """
    report = ComplianceReport()

    loaded_tables = tables
    loaded_schemas = schemas
    sqlite_load_error: Optional[Exception] = None
    if module_dir and (loaded_tables is None or loaded_schemas is None):
        sqlite_path = Path(module_dir) / "data" / "data.sqlite"
        if sqlite_path.exists():
            source = None
            try:
                from .sqlite_data_source import SQLiteDataSource

                source = SQLiteDataSource(str(sqlite_path))
                if loaded_tables is None:
                    loaded_tables = source.load_tables()
                if loaded_schemas is None:
                    loaded_schemas = source.get_schema()
            except Exception as e:  # noqa: BLE001
                sqlite_load_error = e
            finally:
                if source is not None:
                    source.close()
        else:
            # 显式只传 tables 或 schemas 是既有单测/API 的合法用法：此时不凭空
            # 补一个空的配对值，否则会把“未要求该检查”误报成 schema 不一致。
            if loaded_tables is None and loaded_schemas is None:
                loaded_tables = {}
                loaded_schemas = {}

    loaded_model_types = model_types
    model_load_error: Optional[Exception] = None
    if module_dir and loaded_model_types is None:
        model_path = Path(module_dir) / "model" / "model.xml"
        if model_path.exists():
            try:
                from .model_parser import ModelParser

                models = ModelParser(str(model_path)).models
                loaded_model_types = {
                    name: model.get("__model_type__")
                    for name, model in models.items()
                }
            except Exception as e:  # noqa: BLE001
                model_load_error = e
        else:
            loaded_model_types = {}

    # 1. 目录结构
    if module_dir:
        try:
            missing = check_directory_structure(Path(module_dir))
            if missing:
                report.add_failure(
                    "directory_structure",
                    f"测试模块目录缺少固定子目录: {', '.join(missing)} (module_dir={module_dir})",
                )
        except Exception as e:  # noqa: BLE001
            report.add_failure("directory_structure", f"检查本身出错: {e}")

    # 2. @plan_id 与 selector 互斥
    if selector_filters is not None:
        try:
            check_plan_selector_conflict(plan_path, selector_filters)
        except ValueError as e:
            report.add_failure("plan_selector_conflict", str(e))
        except Exception as e:  # noqa: BLE001
            report.add_failure("plan_selector_conflict", f"检查本身出错: {e}")

    # 3. data.sqlite schema 一致性
    if sqlite_load_error is not None:
        report.add_failure("data_schema_consistency", f"读取 data.sqlite 失败: {sqlite_load_error}")
    elif loaded_tables is not None and loaded_schemas is not None:
        try:
            DataSchemaValidator.check_sqlite_schema(loaded_tables, loaded_schemas)
        except Exception as e:  # noqa: BLE001
            report.add_failure("data_schema_consistency", str(e))

    # 4. 接口/DB _verify 表 Return[-1] 自引用扫描
    if model_load_error is not None:
        report.add_failure("return_ref_self_check", f"读取 model.xml 失败: {model_load_error}")
    elif loaded_tables is not None and loaded_model_types is not None:
        try:
            violations = scan_return_ref_violations(loaded_tables, loaded_model_types)
            if violations:
                report.add_failure(
                    "return_ref_self_check",
                    f"接口/DB _verify 表中检测到 ${{Return[-1]}} 自引用空校验: {', '.join(violations)}",
                )
        except Exception as e:  # noqa: BLE001
            report.add_failure("return_ref_self_check", f"检查本身出错: {e}")

    return report
