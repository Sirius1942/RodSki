"""报告数据模型 - 基于 dataclass 的结构化报告数据

提供从 StepReport 到 ReportData 的完整层级：
    ReportData
    ├── EnvironmentInfo
    ├── RunSummary
    └── CaseReport[]
        └── PhaseReport[]
            └── StepReport[]
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


@dataclass
class EnvironmentInfo:
    """运行环境信息"""

    os_name: str = ""
    os_version: str = ""
    python_version: str = ""
    rodski_version: str = ""
    browser: Optional[str] = None
    browser_version: Optional[str] = None


@dataclass
class RunSummary:
    """执行结果汇总"""

    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    error: int = 0
    pass_rate: float = 0.0  # passed / total * 100
    duration: float = 0.0  # 总耗时（秒）


@dataclass
class StepReport:
    """单步执行报告"""

    index: int = 0
    action: str = ""  # 关键字 (type/verify/send/...)
    model: str = ""
    data: str = ""
    status: str = "ok"  # ok / fail / skip
    duration: float = 0.0
    screenshot: Optional[str] = None
    log: str = ""
    return_value: Any = None
    error: Optional[str] = None
    diagnosis: Optional[dict] = None  # Agent 诊断信息
    retry_history: list = field(default_factory=list)


@dataclass
class PhaseReport:
    """阶段报告（pre_process / test_case / post_process）"""

    name: str = ""  # pre_process / test_case / post_process
    steps: list = field(default_factory=list)  # list[StepReport]
    status: str = "ok"
    duration: float = 0.0


@dataclass
class CaseReport:
    """用例报告"""

    case_id: str = ""
    title: str = ""
    description: str = ""
    component_type: str = "界面"
    status: str = "PASS"
    duration: float = 0.0
    tags: list = field(default_factory=list)  # list[str]
    priority: str = ""
    pre_process: Optional[PhaseReport] = None
    test_case: Optional[PhaseReport] = None
    post_process: Optional[PhaseReport] = None


def _serialize(obj: Any) -> Any:
    """将对象递归序列化为可 JSON 化的基础类型"""
    if obj is None:
        return None
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialize(item) for item in obj]
    # dataclass 实例
    if hasattr(obj, "__dataclass_fields__"):
        return {k: _serialize(v) for k, v in asdict(obj).items()}
    return str(obj)


@dataclass
class ReportData:
    """完整的报告数据"""

    run_id: str = ""
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    duration: float = 0.0
    environment: Optional[EnvironmentInfo] = None
    summary: Optional[RunSummary] = None
    cases: list = field(default_factory=list)  # list[CaseReport]

    def to_dict(self) -> dict:
        """序列化为可 JSON 化的 dict"""
        return _serialize(self)

    def to_json(self, path: str) -> None:
        """写入 report_data.json"""
        data = self.to_dict()
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
