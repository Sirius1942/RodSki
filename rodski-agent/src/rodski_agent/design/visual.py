"""视觉探索节点 — 页面截图 + OmniParser + LLM 语义增强。

包含两个 Design Agent 节点：
  - explore_page: 截取页面截图并通过 OmniParser 识别元素
  - identify_elem: 通过 LLM Vision 为元素添加语义标签

当 OmniParser/Playwright/LLM 不可用时优雅降级。

Python 3.9 兼容：使用 ``from __future__ import annotations`` 延迟求值。
"""

from __future__ import annotations

import logging
import os
import tempfile
from typing import Any

logger = logging.getLogger(__name__)


def explore_page(state: dict) -> dict:
    """截取页面截图并识别元素。

    当 target_url 存在时：
    1. 使用 Playwright 截取页面截图
    2. 使用 OmniParser 识别页面元素

    当不可用时返回空 page_elements，后续节点使用 fallback。

    Reads: state["target_url"], state["output_dir"]
    Writes: state["page_elements"], state["screenshots"]
    """
    target_url = state.get("target_url", "")
    if not target_url:
        logger.info("No target_url provided, skipping page exploration")
        return {"page_elements": [], "screenshots": []}

    output_dir = state.get("output_dir", "")
    screenshot_dir = os.path.join(output_dir, "screenshots") if output_dir else tempfile.mkdtemp()

    os.makedirs(screenshot_dir, exist_ok=True)
    screenshot_path = os.path.join(screenshot_dir, "page_screenshot.png")

    # Step 1: Capture screenshot
    try:
        from rodski_agent.common.omniparser_client import (
            capture_screenshot,
            OmniParserUnavailableError,
        )

        capture_screenshot(
            url=target_url,
            output_path=screenshot_path,
            headless=state.get("headless", True),
        )
        logger.info("Screenshot captured: %s", screenshot_path)
    except Exception as exc:
        logger.warning("Screenshot capture failed, continuing without: %s", exc)
        return {"page_elements": [], "screenshots": []}

    # Step 2: Parse screenshot with OmniParser
    try:
        from rodski_agent.common.omniparser_client import parse_screenshot

        elements = parse_screenshot(screenshot_path)
        logger.info("OmniParser found %d elements", len(elements))
        return {
            "page_elements": elements,
            "screenshots": [screenshot_path],
        }
    except Exception as exc:
        logger.warning("OmniParser failed, continuing without elements: %s", exc)
        return {
            "page_elements": [],
            "screenshots": [screenshot_path],
        }


def identify_elem(state: dict) -> dict:
    """通过 LLM Vision 为元素添加语义标签。

    使用 LLM 分析截图和 OmniParser 元素列表，为每个元素添加：
    - semantic_name: 语义名称（如 "username_input"）
    - purpose: 功能描述
    - suggested_locator_type: 建议的定位方式

    不可用时返回原始 page_elements 作为 enriched_elements。

    Reads: state["page_elements"], state["screenshots"]
    Writes: state["enriched_elements"]
    """
    page_elements = state.get("page_elements", [])
    screenshots = state.get("screenshots", [])

    if not page_elements:
        return {"enriched_elements": []}

    # Try LLM enrichment
    try:
        from rodski_agent.common.llm_bridge import call_llm_text, LLMUnavailableError
        import json

        elements_desc = json.dumps(page_elements, ensure_ascii=False)
        screenshot_info = f"Screenshots: {', '.join(screenshots)}" if screenshots else "No screenshots"

        prompt = f"""\
分析以下页面元素列表，为每个元素添加语义信息。

页面元素：
{elements_desc}

{screenshot_info}

为每个元素输出 JSON 数组，每项包含：
- id: 原始 id
- semantic_name: 语义名称（英文，小写下划线风格，如 username_input）
- purpose: 功能描述
- suggested_locator_type: 建议的定位方式（id/css/xpath/text/name 之一）
- original_label: 原始标签

严格以 JSON 数组格式输出。"""

        response = call_llm_text(prompt)

        # Parse response
        text = response.strip()
        if "```json" in text:
            start = text.index("```json") + len("```json")
            end = text.index("```", start)
            text = text[start:end].strip()
        elif "```" in text:
            start = text.index("```") + len("```")
            end = text.index("```", start)
            text = text[start:end].strip()

        enriched = json.loads(text)
        if isinstance(enriched, list):
            return {"enriched_elements": enriched}

    except Exception as exc:
        logger.warning("LLM element enrichment failed: %s", exc)

    # Fallback: convert page_elements to enriched format without LLM
    enriched = _fallback_enrichment(page_elements)
    return {"enriched_elements": enriched}


def _fallback_enrichment(elements: list[dict]) -> list[dict]:
    """不依赖 LLM 的简单元素增强。"""
    enriched: list[dict] = []
    for elem in elements:
        label = elem.get("label", "")
        elem_type = elem.get("type", "unknown")

        # Generate semantic name from label
        semantic = label.lower().replace(" ", "_").replace("-", "_")
        if not semantic:
            semantic = f"element_{elem.get('id', 0)}"
        # Remove non-alphanumeric chars
        semantic = "".join(c for c in semantic if c.isalnum() or c == "_")
        if not semantic:
            semantic = f"element_{elem.get('id', 0)}"

        # Suggest locator type based on element type
        locator_map = {
            "button": "css",
            "input": "css",
            "text": "text",
            "link": "text",
            "image": "css",
            "select": "css",
        }
        suggested_locator = locator_map.get(elem_type, "css")

        enriched.append({
            "id": elem.get("id", 0),
            "semantic_name": semantic,
            "purpose": f"{elem_type}: {label}" if label else elem_type,
            "suggested_locator_type": suggested_locator,
            "original_label": label,
        })

    return enriched
