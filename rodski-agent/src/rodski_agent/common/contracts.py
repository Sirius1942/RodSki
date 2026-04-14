"""输出契约 — 定义 rodski-agent 所有命令的结构化输出格式。

AgentOutput 是所有命令的统一输出信封，内部的 output 字段根据命令类型
承载不同的 payload（RunOutput / DesignOutput / DiagnoseOutput）。

Python 3.9 兼容：使用 ``from __future__ import annotations`` 延迟求值。
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


# ============================================================
# 命令级 payload
# ============================================================


@dataclass
class RunOutput:
    """``run`` 命令的输出 payload。"""

    total: int = 0
    passed: int = 0
    failed: int = 0
    cases: List[Dict[str, Any]] = field(default_factory=list)
    diagnosis: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if d.get("diagnosis") is None:
            del d["diagnosis"]
        return d


@dataclass
class DesignOutput:
    """``design`` 命令的输出 payload。"""

    cases: List[str] = field(default_factory=list)
    models: List[str] = field(default_factory=list)
    data: List[str] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DiagnoseOutput:
    """``diagnose`` 命令的输出 payload。"""

    root_cause: str = ""
    confidence: float = 0.0
    category: str = ""
    suggestion: str = ""
    evidence: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================
# 统一输出信封
# ============================================================


@dataclass
class AgentOutput:
    """所有命令的统一输出信封。

    Attributes
    ----------
    status : str
        ``"success"`` | ``"failure"`` | ``"error"``
    command : str
        触发该输出的命令名（run / design / diagnose / pipeline / config）。
    output : dict
        命令级 payload，由 RunOutput / DesignOutput / DiagnoseOutput 的
        ``to_dict()`` 生成。
    error : str | None
        当 status 为 ``"error"`` 时的错误描述。
    metadata : dict | None
        可选元信息（版本号、耗时等）。
    """

    status: str
    command: str
    output: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    # ----------------------------------------------------------
    # 序列化
    # ----------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """转换为可被 ``json.dumps`` 序列化的字典。

        省略值为 ``None`` 的可选字段，保持输出简洁。
        """
        d: Dict[str, Any] = {
            "status": self.status,
            "command": self.command,
            "output": self.output,
        }
        if self.error is not None:
            d["error"] = self.error
        if self.metadata is not None:
            d["metadata"] = self.metadata
        return d

    def to_json(self, ensure_ascii: bool = False, indent: int | None = None) -> str:
        """序列化为 JSON 字符串。"""
        return json.dumps(self.to_dict(), ensure_ascii=ensure_ascii, indent=indent)

    def to_human(self) -> str:
        """返回人类可读的文本摘要。

        根据 command 类型格式化，error 时显示错误信息。
        """
        if self.status == "error":
            msg = f"Error: {self.error or 'unknown error'}"
            if self.metadata:
                msg += f"\n  (code: {self.metadata.get('error_code', 'N/A')})"
            return msg

        if self.command == "run":
            total = self.output.get("total", 0)
            passed = self.output.get("passed", 0)
            failed = self.output.get("failed", 0)
            if failed == 0:
                return f"All {total} case(s) passed."
            if passed == 0:
                return f"All {total} case(s) failed."
            return f"{passed}/{total} passed, {failed} failed."

        if self.command == "design":
            summary = self.output.get("summary", "")
            cases = self.output.get("cases", [])
            return f"Design complete: {len(cases)} case(s). {summary}"

        if self.command == "diagnose":
            root_cause = self.output.get("root_cause", "unknown")
            suggestion = self.output.get("suggestion", "")
            confidence = self.output.get("confidence", 0.0)
            return (
                f"Root cause: {root_cause} (confidence: {confidence:.0%})\n"
                f"Suggestion: {suggestion}"
            )

        # 通用 fallback
        return f"[{self.command}] status={self.status}"
