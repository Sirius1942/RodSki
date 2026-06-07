"""SharedLoadContext — 压测共享只读上下文。
在 LoadExecutor 中构建一次，所有 VU greenlet 共享（只读，greenlet 安全）。
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

# 模块级导入使 @patch 能够拦截；在 build() 内调用，而非顶层执行，
# 避免循环依赖（模块导入时不触发实际解析逻辑）。
try:
    from ..core.case_parser import CaseParser
    from ..core.model_parser import ModelParser
    from ..core.data_table_parser import DataTableParser
    from ..core.global_value_parser import GlobalValueParser
except ImportError:
    from core.case_parser import CaseParser  # type: ignore[no-redef]
    from core.model_parser import ModelParser  # type: ignore[no-redef]
    from core.data_table_parser import DataTableParser  # type: ignore[no-redef]
    from core.global_value_parser import GlobalValueParser  # type: ignore[no-redef]


@dataclass(frozen=True)
class SharedLoadContext:
    """压测只读共享上下文。frozen=True 保证不可变。"""
    case_registry: Dict[str, Any]    # {case_id: case_def dict}
    model_registry: Dict[str, Any]   # {model_name: elements dict}
    data_store: Any                  # DataTableParser 实例（只读查询）
    global_values: Dict[str, Any]    # {group_name: {var_name: value}}
    module_dir: Path

    @classmethod
    def build(cls, module_dir: Path) -> "SharedLoadContext":
        """从模块目录构建只读上下文。"""
        module_dir = Path(module_dir)

        # 解析 case：CaseParser(path) 接受目录或单文件
        case_dir = module_dir / "case"
        case_registry: Dict[str, Any] = {}
        if case_dir.exists():
            case_parser = CaseParser(str(case_dir))
            cases = case_parser.parse_cases()
            for c in cases:
                case_registry[c["case_id"]] = c

        # 解析 model：ModelParser(xml_path) 构造时即完成解析
        model_path = module_dir / "model" / "model.xml"
        model_registry: Dict[str, Any] = {}
        if model_path.exists():
            model_parser = ModelParser(str(model_path))
            model_registry = model_parser.models

        # 解析 data（SQLite）：DataTableParser(data_dir) 构造，parse_all_tables() 加载
        data_dir = module_dir / "data"
        data_store = DataTableParser(str(data_dir))
        if (data_dir / "data.sqlite").exists():
            data_store.parse_all_tables()

        # 解析 globalvalue：GlobalValueParser(globalvalue_path) 构造，parse() 解析
        gv_path = module_dir / "data" / "globalvalue.xml"
        global_values: Dict[str, Any] = {}
        if gv_path.exists():
            gv_parser = GlobalValueParser(str(gv_path))
            global_values = gv_parser.parse()

        return cls(
            case_registry=case_registry,
            model_registry=model_registry,
            data_store=data_store,
            global_values=global_values,
            module_dir=module_dir,
        )

