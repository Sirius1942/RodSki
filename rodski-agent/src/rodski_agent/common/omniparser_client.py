"""OmniParser HTTP 客户端 — 页面元素识别。

通过 HTTP API 调用 OmniParser 服务，获取页面元素列表。
不可用时直接抛 OmniParserUnavailableError。

Python 3.9 兼容：使用 ``from __future__ import annotations`` 延迟求值。
"""

from __future__ import annotations

import base64
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class OmniParserUnavailableError(Exception):
    """OmniParser 服务不可用。"""


def _get_omniparser_url() -> str:
    """获取 OmniParser 服务 URL。

    优先从 rodski 配置中读取，降级使用默认值。
    """
    try:
        from rodski_agent.common.config import AgentConfig

        cfg = AgentConfig.load()
        omni_cfg = cfg.to_dict().get("omniparser", {})
        url = omni_cfg.get("url", "")
        if url:
            return url
    except Exception:
        pass

    return "http://localhost:8000"


def parse_screenshot(
    image_path: str,
    server_url: Optional[str] = None,
    timeout: int = 30,
) -> List[Dict[str, Any]]:
    """调用 OmniParser 解析截图中的页面元素。

    Parameters
    ----------
    image_path:
        截图文件路径。
    server_url:
        OmniParser 服务 URL。未指定时从配置读取。
    timeout:
        HTTP 请求超时秒数。

    Returns
    -------
    list[dict]
        元素列表，每项包含::

            {
                "id": int,
                "label": str,        # 元素标签/文本
                "bbox": [x1, y1, x2, y2],  # 边界框坐标
                "type": str,         # 元素类型 (button/input/text/...)
                "confidence": float, # 置信度
            }

    Raises
    ------
    OmniParserUnavailableError
        服务不可用或请求失败时。
    """
    url = server_url or _get_omniparser_url()

    try:
        import requests
    except ImportError as exc:
        raise OmniParserUnavailableError(
            f"requests library not available: {exc}"
        ) from exc

    try:
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")
    except FileNotFoundError as exc:
        raise OmniParserUnavailableError(
            f"Screenshot not found: {image_path}"
        ) from exc

    # 修复双路径 bug: 如果 URL 已经包含 /parse，不再追加
    parse_url = url.rstrip("/")
    if not parse_url.endswith("/parse"):
        parse_url = f"{parse_url}/parse"

    try:
        response = requests.post(
            parse_url,
            json={"image": image_data},
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()

        elements = data.get("elements", [])
        return [
            {
                "id": i,
                "label": elem.get("label", ""),
                "bbox": elem.get("bbox", [0, 0, 0, 0]),
                "type": elem.get("type", "unknown"),
                "confidence": elem.get("confidence", 0.0),
            }
            for i, elem in enumerate(elements)
        ]
    except requests.exceptions.ConnectionError as exc:
        raise OmniParserUnavailableError(
            f"Cannot connect to OmniParser at {url}: {exc}"
        ) from exc
    except requests.exceptions.Timeout as exc:
        raise OmniParserUnavailableError(
            f"OmniParser request timed out after {timeout}s"
        ) from exc
    except Exception as exc:
        raise OmniParserUnavailableError(
            f"OmniParser request failed: {exc}"
        ) from exc


def capture_screenshot(
    url: str,
    output_path: str,
    headless: bool = True,
    browser: str = "chromium",
    wait_seconds: int = 3,
) -> str:
    """使用 Playwright 截取页面截图。

    Parameters
    ----------
    url:
        要截取的页面 URL。
    output_path:
        截图保存路径。
    headless:
        是否无头模式。
    browser:
        浏览器类型。
    wait_seconds:
        页面加载等待秒数。

    Returns
    -------
    str
        截图文件路径。

    Raises
    ------
    OmniParserUnavailableError
        Playwright 不可用或截图失败时。
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise OmniParserUnavailableError(
            f"Playwright not available: {exc}"
        ) from exc

    try:
        with sync_playwright() as p:
            browser_type = getattr(p, browser, p.chromium)
            b = browser_type.launch(headless=headless)
            page = b.new_page()
            page.goto(url, wait_until="networkidle")
            if wait_seconds > 0:
                page.wait_for_timeout(wait_seconds * 1000)
            page.screenshot(path=output_path, full_page=True)
            b.close()
        return output_path
    except Exception as exc:
        raise OmniParserUnavailableError(
            f"Screenshot capture failed: {exc}"
        ) from exc
