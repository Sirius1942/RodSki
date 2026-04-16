"""网络操作 - Mock API 响应、等待网络请求、清除 mock route

仅在 PlaywrightDriver 下可用，其他 driver 调用时返回明确错误。
通过 _context 参数接收当前驱动实例。
"""
import json
import logging
import re
from typing import Any, Optional

logger = logging.getLogger("rodski.builtins.network")


def _get_playwright_page(context: Optional[dict] = None):
    """从上下文中获取 Playwright page 对象

    Args:
        context: 运行时上下文，包含 driver 实例

    Returns:
        Playwright page 对象

    Raises:
        RuntimeError: 驱动不是 PlaywrightDriver 或 context 中无 driver
    """
    if context is None:
        raise RuntimeError(
            "network_ops 需要运行时上下文（_context），"
            "请通过 run 关键字在测试用例中调用"
        )

    driver = context.get("driver")
    if driver is None:
        raise RuntimeError("运行时上下文中未找到 driver 实例")

    # 检查是否为 PlaywrightDriver
    driver_class = type(driver).__name__
    if driver_class != "PlaywrightDriver":
        raise RuntimeError(
            f"network_ops 仅支持 PlaywrightDriver，"
            f"当前 driver 类型: {driver_class}"
        )

    page = getattr(driver, "page", None)
    if page is None:
        raise RuntimeError("PlaywrightDriver 的 page 对象不可用")

    return page


def mock_route(
    url_pattern: str,
    status: int = 200,
    body: str = "",
    content_type: str = "application/json",
    _context: Optional[dict] = None,
    **kwargs,
) -> dict:
    """Mock API 响应

    拦截匹配 url_pattern 的网络请求，返回自定义响应。

    Args:
        url_pattern: URL 匹配模式（支持 glob 和正则表达式）
        status: HTTP 状态码，默认 200
        body: 响应体字符串，默认空
        content_type: 响应 Content-Type，默认 application/json
        _context: 运行时上下文（由 keyword_engine 自动注入）
        **kwargs: 额外响应头

    Returns:
        操作结果字典 {"success": True, "pattern": url_pattern}

    Raises:
        RuntimeError: 驱动不是 PlaywrightDriver
    """
    page = _get_playwright_page(_context)

    headers = {"Content-Type": content_type}
    headers.update(kwargs.get("headers", {}))

    def handle_route(route):
        route.fulfill(
            status=status,
            body=body,
            headers=headers,
        )

    # Playwright route 支持 glob 和正则
    if url_pattern.startswith("re:"):
        # 正则模式: re:pattern
        pattern = re.compile(url_pattern[3:])
        page.route(pattern, handle_route)
    else:
        # glob 模式（Playwright 默认支持）
        page.route(url_pattern, handle_route)

    logger.info(f"mock_route: {url_pattern} -> status={status}")
    return {"success": True, "pattern": url_pattern}


def wait_for_response(
    url_pattern: str,
    timeout: int = 30,
    _context: Optional[dict] = None,
) -> dict:
    """等待特定网络请求完成

    阻塞等待匹配 url_pattern 的网络响应。

    Args:
        url_pattern: URL 匹配模式（子串匹配）
        timeout: 超时秒数，默认 30
        _context: 运行时上下文（由 keyword_engine 自动注入）

    Returns:
        响应信息字典 {"url": str, "status": int, "body": str}

    Raises:
        RuntimeError: 驱动不是 PlaywrightDriver 或等待超时
    """
    page = _get_playwright_page(_context)

    def predicate(response):
        return url_pattern in response.url

    try:
        response = page.wait_for_response(
            predicate,
            timeout=timeout * 1000,  # Playwright 使用毫秒
        )
    except Exception as e:
        raise RuntimeError(
            f"等待网络响应超时 ({timeout}s): {url_pattern} - {e}"
        )

    # 提取响应信息
    result = {
        "url": response.url,
        "status": response.status,
    }

    try:
        body_text = response.text()
        result["body"] = body_text
        # 尝试 JSON 解析
        try:
            result["json"] = json.loads(body_text)
        except (json.JSONDecodeError, ValueError):
            pass
    except Exception:
        result["body"] = ""

    logger.info(f"wait_for_response: {response.url} -> {response.status}")
    return result


def clear_routes(
    _context: Optional[dict] = None,
) -> bool:
    """清除所有 mock route

    移除通过 mock_route 设置的所有路由拦截。

    Args:
        _context: 运行时上下文（由 keyword_engine 自动注入）

    Returns:
        True 表示成功

    Raises:
        RuntimeError: 驱动不是 PlaywrightDriver
    """
    page = _get_playwright_page(_context)

    # Playwright 没有直接的 "clear all routes" API，
    # 使用 unroute_all 清除所有路由（Playwright >= 1.29）
    if hasattr(page, "unroute_all"):
        page.unroute_all()
    else:
        # 降级：通过新建 context 实现（记录警告）
        logger.warning(
            "当前 Playwright 版本不支持 unroute_all，"
            "请升级到 1.29+。路由未完全清除。"
        )
        return False

    logger.info("clear_routes: 所有 mock route 已清除")
    return True
