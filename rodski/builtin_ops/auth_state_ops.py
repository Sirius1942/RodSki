"""登录态复用 - save_auth_state / use_auth_state（v11.6.0 P3）

- ``save_auth_state(name)``：把当前浏览器 context 的 storage state（cookie + localStorage）
  存到**本次 run 的内存**中；不落盘，避免凭据残留到结果目录或仓库。
- ``use_auth_state(name)``：为当前用例的（新）context 加载已保存的状态，之后可直接
  ``navigate`` 到登录后的页面。必须在该用例的 ``navigate`` 之前调用。

仅在 PlaywrightDriver 下可用。通过 run 关键字调用，model 必须为空：

    <test_step action="run" model="" data="save_auth_state(name='admin')"/>
    <test_step action="run" model="" data="use_auth_state(name='admin')"/>
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("rodski.builtins.auth_state")

# 本次 run（进程）内存中的登录态：name -> storage_state
_AUTH_STATES: Dict[str, Dict[str, Any]] = {}

# 保证 localStorage 只在每个标签页首次进入该 origin 时写入一次，
# 之后应用自身对 localStorage 的修改（如退出登录）不会被再次覆盖。
_APPLIED_FLAG = "__rodski_auth_state_applied"


def clear_auth_states() -> None:
    """清空本次 run 的登录态（执行器在每次 run 开始时调用）。"""
    _AUTH_STATES.clear()


def list_auth_states() -> list:
    return sorted(_AUTH_STATES)


def _normalize_name(name: Any) -> str:
    text = str(name or "").strip()
    if not text:
        raise ValueError(
            "登录态名称不能为空。写法: run model=\"\" data=\"save_auth_state(name='admin')\""
        )
    return text


def _get_driver(context: Optional[dict], func: str):
    if context is None:
        raise RuntimeError(f"{func} 需要运行时上下文（_context），请通过 run 关键字在用例中调用（model 为空）")
    driver = context.get("driver")
    if driver is None:
        raise RuntimeError(f"{func}: 当前没有可用的浏览器驱动（本次运行未创建 Web 驱动）")
    if not (hasattr(driver, "get_storage_state") and hasattr(driver, "apply_storage_state")):
        raise RuntimeError(
            f"{func} 仅支持 Web（Playwright）驱动，当前驱动类型: {type(driver).__name__}"
        )
    return driver


def save_auth_state(name: str = "", _context: Optional[dict] = None, **kwargs) -> dict:
    """保存当前 context 的登录态到本次 run 内存。

    返回值只含摘要（cookie / origin 数量），不含凭据本身，避免写入结果 XML。
    """
    key = _normalize_name(name or kwargs.get("state"))
    driver = _get_driver(_context, "save_auth_state")
    if getattr(driver, "_is_closed", False):
        raise RuntimeError(
            f"save_auth_state('{key}') 失败：浏览器会话已关闭。"
            f"请在同一用例的 close 之前调用 save_auth_state（通常放在登录成功的断言之后）"
        )
    state = driver.get_storage_state()
    if not isinstance(state, dict):
        raise RuntimeError(f"save_auth_state('{key}') 失败：未能读取当前页面的 storage state")
    _AUTH_STATES[key] = json.loads(json.dumps(state))  # 深拷贝，隔离后续修改
    cookies = len(state.get("cookies") or [])
    origins = len(state.get("origins") or [])
    logger.info(f"已保存登录态 '{key}'（cookie {cookies} 个，localStorage origin {origins} 个，仅保存在本次运行内存中）")
    return {"success": True, "name": key, "cookies": cookies, "origins": origins}


def use_auth_state(name: str = "", _context: Optional[dict] = None, **kwargs) -> dict:
    """为当前用例的新 context 加载已保存的登录态（须在 navigate 之前调用）。"""
    key = _normalize_name(name or kwargs.get("state"))
    if key not in _AUTH_STATES:
        saved = ", ".join(list_auth_states()) or "（无）"
        raise RuntimeError(
            f"未找到登录态 '{key}'（本次运行已保存: {saved}）。"
            f"登录态只在同一次 run 的内存中有效：需先执行调用 save_auth_state(name='{key}') 的用例，"
            f"并确保它排在本用例之前（plan 执行顺序 / 同一用例文件内的顺序；--workers 并行时两者需在同一用例文件中）"
        )
    driver = _get_driver(_context, "use_auth_state")
    state = _AUTH_STATES[key]
    driver.apply_storage_state(state)
    cookies = len(state.get("cookies") or [])
    origins = len(state.get("origins") or [])
    logger.info(f"已加载登录态 '{key}'（cookie {cookies} 个，localStorage origin {origins} 个）")
    return {"success": True, "name": key, "cookies": cookies, "origins": origins}


def build_local_storage_init_script(origins: list) -> str:
    """生成把 localStorage 写入对应 origin 的 init script（每个标签页每个 origin 只写一次）。"""
    data: Dict[str, list] = {}
    for entry in origins or []:
        origin = (entry or {}).get("origin")
        if not origin:
            continue
        items = [[i.get("name"), i.get("value")] for i in (entry.get("localStorage") or []) if i.get("name") is not None]
        if items:
            data[origin] = items
    payload = json.dumps(data, ensure_ascii=False)
    flag = json.dumps(_APPLIED_FLAG)
    return (
        "(() => {"
        f" const data = {payload};"
        " const items = data[window.location.origin];"
        " if (!items) return;"
        " try {"
        f"  if (window.sessionStorage.getItem({flag})) return;"
        "  for (const [k, v] of items) window.localStorage.setItem(k, v);"
        f"  window.sessionStorage.setItem({flag}, '1');"
        " } catch (e) {}"
        "})();"
    )
