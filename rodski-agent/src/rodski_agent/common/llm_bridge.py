"""LLM 桥接层 — 复用 rodski LLM 能力

通过动态导入 rodski/llm/client.py 的 LLMClient，为 rodski-agent 提供
LLM 调用能力。当 rodski 不可导入或 LLM 配置缺失时，所有函数优雅降级。

Python 3.9 兼容：使用 ``from __future__ import annotations`` 延迟求值。
"""

from __future__ import annotations

import base64
import logging
import sys
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ============================================================
# 异常
# ============================================================

class LLMUnavailableError(Exception):
    """LLM 服务不可用 — rodski 不可导入、配置缺失或连接失败。"""


# ============================================================
# 核心：获取 LLMClient 实例
# ============================================================

def _find_rodski_root() -> Path:
    """找到 rodski 项目根目录（与 rodski-agent 同级）。

    目录结构:
        RodSki/
        ├── rodski/          ← 目标
        └── rodski-agent/
            └── src/rodski_agent/common/llm_bridge.py  ← 当前文件
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

    raise LLMUnavailableError(
        f"Cannot find rodski/ directory (searched from {project_root})"
    )


def get_llm_client() -> Any:
    """获取 rodski LLMClient 实例。

    找不到 rodski 或 LLM 配置时抛 LLMUnavailableError。

    Returns
    -------
    LLMClient
        rodski.llm.client.LLMClient 实例。
    """
    try:
        rodski_root = _find_rodski_root()
    except LLMUnavailableError:
        raise

    rodski_str = str(rodski_root)
    if rodski_str not in sys.path:
        sys.path.insert(0, rodski_str)

    try:
        from llm.client import LLMClient
    except ImportError as exc:
        raise LLMUnavailableError(
            f"Cannot import LLMClient from rodski/llm/client.py: {exc}"
        ) from exc

    try:
        client = LLMClient()
        return client
    except Exception as exc:
        raise LLMUnavailableError(
            f"Failed to initialize LLMClient: {exc}"
        ) from exc


# ============================================================
# 高级 API：截图分析
# ============================================================

def analyze_screenshot(image_path: str, question: str) -> dict:
    """调用 screenshot_verifier 能力分析截图。

    Parameters
    ----------
    image_path:
        截图文件路径。
    question:
        需要回答的问题（如 "页面上是否显示错误信息？"）。

    Returns
    -------
    dict
        分析结果，格式为 ``{"answer": str, "confidence": float}``。
        LLM 不可用时返回 ``{"answer": "", "error": str}``。
    """
    try:
        client = get_llm_client()
    except LLMUnavailableError as exc:
        logger.warning("LLM unavailable for screenshot analysis: %s", exc)
        return {"answer": "", "error": str(exc)}

    try:
        # 读取图片并转换为 base64
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        result_text = client.call_vision(image_data, question)
        return {"answer": result_text, "confidence": 0.8}
    except FileNotFoundError:
        return {"answer": "", "error": f"Screenshot not found: {image_path}"}
    except Exception as exc:
        logger.warning("Screenshot analysis failed: %s", exc)
        return {"answer": "", "error": str(exc)}


# ============================================================
# 高级 API：测试结果审查
# ============================================================

def review_test_result(result_data: dict) -> dict:
    """调用 test_reviewer 能力审查测试结果。

    Parameters
    ----------
    result_data:
        测试结果数据字典，包含 case_results 等信息。

    Returns
    -------
    dict
        审查结果，格式为 ``{"review": str, "suggestions": list}``。
        LLM 不可用时返回 ``{"review": "", "error": str}``。
    """
    try:
        client = get_llm_client()
    except LLMUnavailableError as exc:
        logger.warning("LLM unavailable for test result review: %s", exc)
        return {"review": "", "error": str(exc)}

    try:
        capability = client.get_capability("test_reviewer")
        review = capability.review(result_data)
        return {"review": review, "suggestions": []}
    except Exception as exc:
        logger.warning("Test result review failed: %s", exc)
        return {"review": "", "error": str(exc)}


# ============================================================
# 高级 API：文本诊断（供 diagnose 节点使用）
# ============================================================

def call_llm_text(prompt: str) -> str:
    """调用 LLM 纯文本 API。

    Parameters
    ----------
    prompt:
        完整的 prompt 文本。

    Returns
    -------
    str
        LLM 返回的文本。

    Raises
    ------
    LLMUnavailableError
        LLM 不可用时抛出。
    """
    client = get_llm_client()
    try:
        return client.call_text(prompt)
    except Exception as exc:
        raise LLMUnavailableError(
            f"LLM text call failed: {exc}"
        ) from exc
