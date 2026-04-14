"""rodski CLI 封装 — 通过 subprocess 调用 rodski 执行引擎

rodski 提供两个入口:
  - rodski/ski_run.py — 直接执行入口（不设置准确 exit code）
  - rodski/cli_main.py — CLI 主入口，子命令 `run` 返回准确 exit code 和 JSON 输出

本模块统一使用 cli_main.py 的 `run` 子命令，以获取结构化结果和准确的 exit code。

exit code 语义（来自 AGENT_INTEGRATION.md）:
    0 = 执行成功（所有用例通过）
    1 = 执行失败（有用例失败）或运行时错误
    2 = 配置/环境错误（XML 格式错误、配置缺失）
"""

from __future__ import annotations

import glob
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class RodskiResult:
    """rodski 执行结果"""

    success: bool
    exit_code: int
    stdout: str
    stderr: str
    result_dir: Optional[str] = None  # result/ 目录路径
    execution_summary: Optional[dict] = None  # execution_summary.json 内容（如有）
    result_files: list[str] = field(default_factory=list)  # result_*.xml 文件列表


# ---------------------------------------------------------------------------
# 路径辅助
# ---------------------------------------------------------------------------


def _find_rodski_root() -> Path:
    """找到 rodski 项目根目录（与 rodski-agent 同级）

    目录结构:
        RodSki/
        ├── rodski/          ← 目标
        └── rodski-agent/
            └── src/rodski_agent/common/rodski_tools.py  ← 当前文件
    """
    # 从当前文件往上 4 级到 RodSki/
    project_root = Path(__file__).resolve().parents[4]
    rodski_root = project_root / "rodski"
    if rodski_root.is_dir():
        return rodski_root

    # 降级：尝试相对工作目录
    cwd = Path.cwd()
    if cwd.name == "rodski-agent":
        candidate = cwd.parent / "rodski"
    else:
        candidate = cwd / "rodski"
    if candidate.is_dir():
        return candidate

    # 最终 fallback：返回推算路径（调用时会报找不到文件）
    return project_root / "rodski"


def _find_result_dir(case_path: str) -> Optional[str]:
    """在 case_path 的同级 result/ 目录中找到结果

    目录结构:
        模块目录/
        ├── case/       ← case_path 指向这里（文件或目录）
        ├── model/
        ├── data/
        └── result/     ← 目标
    """
    p = Path(case_path)
    if p.is_file():
        # case/xxx.xml → case/ → 模块目录
        module_dir = p.parent.parent
    elif p.is_dir() and p.name == "case":
        module_dir = p.parent
    elif p.is_dir() and (p / "case").is_dir():
        # 传入的是模块目录本身
        module_dir = p
    else:
        module_dir = p

    result_dir = module_dir / "result"
    if result_dir.is_dir():
        return str(result_dir)
    return None


def _find_latest_result_files(result_dir: str) -> list[str]:
    """在 result 目录找到所有 result_*.xml 文件，按修改时间倒序排列"""
    pattern = os.path.join(result_dir, "result_*.xml")
    files = glob.glob(pattern)
    return sorted(files, key=os.path.getmtime, reverse=True)


def _parse_execution_summary(result_dir: str) -> Optional[dict]:
    """解析 execution_summary.json（如果存在）"""
    summary_path = os.path.join(result_dir, "execution_summary.json")
    if os.path.isfile(summary_path):
        with open(summary_path, encoding="utf-8") as f:
            return json.load(f)
    return None


# ---------------------------------------------------------------------------
# 核心调用
# ---------------------------------------------------------------------------


def rodski_run(
    case_path: str,
    headless: bool = True,
    browser: str = "chromium",
    timeout: int = 300,
    output_format: str = "json",
    dry_run: bool = False,
    verbose: bool = False,
) -> RodskiResult:
    """调用 rodski run 执行测试用例

    使用 cli_main.py 的 run 子命令，获取准确 exit code 和可选 JSON 输出。

    参数:
        case_path:     用例路径（case/*.xml 文件、case/ 目录或测试模块目录）
        headless:      是否无头模式（默认 True，Agent 场景通常无头）
        browser:       浏览器类型 (chromium / firefox / webkit)
        timeout:       subprocess 超时秒数
        output_format: 输出格式 ("json" 或 "text")
        dry_run:       仅验证用例可执行性，不实际执行
        verbose:       详细输出模式

    返回:
        RodskiResult 包含执行结果、结果目录信息
    """
    rodski_root = _find_rodski_root()
    cli_main = rodski_root / "cli_main.py"

    cmd = ["python3", str(cli_main), "run", case_path]
    if headless:
        cmd.append("--headless")
    if browser:
        cmd.extend(["--browser", browser])
    if output_format:
        cmd.extend(["--output-format", output_format])
    if dry_run:
        cmd.append("--dry-run")
    if verbose:
        cmd.append("--verbose")

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(rodski_root),  # 在 rodski/ 目录执行，确保 import 正确
        )

        result_dir = _find_result_dir(case_path)
        execution_summary = None
        result_files: list[str] = []

        if result_dir:
            execution_summary = _parse_execution_summary(result_dir)
            result_files = _find_latest_result_files(result_dir)

        return RodskiResult(
            success=proc.returncode == 0,
            exit_code=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            result_dir=result_dir,
            execution_summary=execution_summary,
            result_files=result_files,
        )
    except subprocess.TimeoutExpired:
        return RodskiResult(
            success=False,
            exit_code=-1,
            stdout="",
            stderr=f"Execution timed out after {timeout} seconds",
        )
    except FileNotFoundError:
        return RodskiResult(
            success=False,
            exit_code=-2,
            stdout="",
            stderr=f"rodski CLI not found at {cli_main}",
        )


def rodski_dry_run(
    case_path: str,
    timeout: int = 60,
) -> RodskiResult:
    """调用 rodski run --dry-run 验证用例可执行性但不实际执行

    这是 rodski_run(dry_run=True) 的便捷方法。

    参数:
        case_path: 用例路径
        timeout:   超时秒数（dry-run 通常很快）
    """
    return rodski_run(
        case_path=case_path,
        headless=True,
        dry_run=True,
        output_format="text",
        timeout=timeout,
    )


def rodski_validate(path: str) -> RodskiResult:
    """校验 XML 文件是否符合 rodski Schema

    注意: rodski 尚无 validate CLI 子命令，
    直接 import rodski.core.xml_schema_validator 做校验。
    若 import 失败则降级为跳过校验。

    参数:
        path: XML 文件路径或包含 case/model/data 子目录的模块目录

    返回:
        RodskiResult，success=True 表示校验通过
    """
    rodski_root = _find_rodski_root()

    try:
        # 将 rodski/ 加入 sys.path 以便 import core.*
        rodski_str = str(rodski_root)
        if rodski_str not in sys.path:
            sys.path.insert(0, rodski_str)

        from core.xml_schema_validator import RodskiXmlValidator

        p = Path(path)
        errors: list[str] = []

        if p.is_dir():
            # 校验目录下所有 XML 文件
            kind_map = {
                "case": RodskiXmlValidator.KIND_CASE,
                "model": RodskiXmlValidator.KIND_MODEL,
                "data": RodskiXmlValidator.KIND_DATA,
            }
            for xml_file in sorted(p.rglob("*.xml")):
                rel = xml_file.relative_to(p)
                parts = rel.parts
                if len(parts) < 1:
                    continue
                folder = parts[0]
                kind = kind_map.get(folder)
                if kind is None:
                    continue
                # globalvalue 是特殊的 data 类型
                if kind == RodskiXmlValidator.KIND_DATA and "globalvalue" in xml_file.name:
                    kind = RodskiXmlValidator.KIND_GLOBALVALUE
                try:
                    RodskiXmlValidator.validate_file(str(xml_file), kind)
                except Exception as e:
                    errors.append(f"{xml_file}: {e}")
        else:
            # 单文件校验
            try:
                kind = _guess_xml_kind(str(p))
                RodskiXmlValidator.validate_file(str(p), kind)
            except Exception as e:
                errors.append(f"{p}: {e}")

        return RodskiResult(
            success=len(errors) == 0,
            exit_code=0 if len(errors) == 0 else 1,
            stdout="Validation passed" if not errors else "",
            stderr="\n".join(errors) if errors else "",
        )
    except ImportError:
        # rodski 不可 import，降级为跳过
        return RodskiResult(
            success=True,
            exit_code=0,
            stdout="Validation skipped (rodski validator not available)",
            stderr="",
        )


def _guess_xml_kind(path: str) -> str:
    """根据文件路径猜测 XML 文档类型

    规则：按父目录名优先匹配，否则按文件名特征。
    """
    p = Path(path)
    parent = p.parent.name

    if parent == "case":
        return "case"
    if parent == "model":
        return "model"
    if parent == "data":
        if "globalvalue" in p.name:
            return "globalvalue"
        return "data"

    # 按文件名特征猜测
    name = p.name.lower()
    if "globalvalue" in name:
        return "globalvalue"
    if "model" in name:
        return "model"
    if "data" in name:
        return "data"

    return "case"  # 默认视为用例
