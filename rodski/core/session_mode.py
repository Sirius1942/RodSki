"""v11.6.0 执行器配置：会话模式、证据（截图）模式、步骤等待单位。

设计文档: .pb/specs/v11.6.0-ai-authoring-and-performance-design.md §5 P1/P2/P5

- SessionMode（``DefaultValue.SessionMode`` / ``--session-mode``）
    * ``isolated``（默认，现状）：用例写 close 即关闭浏览器，下一用例重新启动
    * ``shared_browser``：整个 run 复用同一个浏览器进程，每个用例新建 BrowserContext
      （cookie / storage / 页面隔离）；用例的 close 只关闭 context
    * ``shared_session``：用例间共用同一 context 和页面；Web 用例的 close 不再关闭会话，
      run 结束时统一关闭
- EvidenceMode（``DefaultValue.EvidenceMode`` / ``--evidence``）
    * ``full``（默认）：每步截图 + 失败截图
    * ``concise``：按失败截图方式处理，只在失败时截图；录像行为不变
- WaitTime（``DefaultValue.WaitTime``）：单位统一为毫秒（与 ``<cases step_wait>`` 一致）；
  过渡期内 ``0 < 值 ≤ 30`` 按秒解释并打印一次弃用告警。

优先级：CLI 参数 > globalvalue ``DefaultValue`` > 默认值。取值非法时抛出
:class:`ValueError`，报错附带合法取值与修复提示（校验先于副作用）。
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Mapping, Optional, Tuple

logger = logging.getLogger("rodski")

SESSION_ISOLATED = "isolated"
SESSION_SHARED_BROWSER = "shared_browser"
SESSION_SHARED_SESSION = "shared_session"
SESSION_MODES = (SESSION_ISOLATED, SESSION_SHARED_BROWSER, SESSION_SHARED_SESSION)

EVIDENCE_FULL = "full"
EVIDENCE_CONCISE = "concise"
EVIDENCE_MODES = (EVIDENCE_FULL, EVIDENCE_CONCISE)

# WaitTime 过渡期阈值：≤ 此值（且 > 0）的旧写法按秒解释
LEGACY_WAIT_SECONDS_MAX = 30.0


def _default_value(global_vars: Optional[Mapping[str, Any]], key: str) -> str:
    group = (global_vars or {}).get("DefaultValue") or {}
    value = group.get(key) if isinstance(group, Mapping) else None
    return str(value).strip() if value is not None else ""


def _resolve_choice(
    cli_value: Optional[str],
    global_vars: Optional[Mapping[str, Any]],
    key: str,
    choices: Tuple[str, ...],
    default: str,
    cli_flag: str,
) -> str:
    if cli_value is not None and str(cli_value).strip():
        raw, source = str(cli_value).strip(), f"命令行 {cli_flag}"
    else:
        raw, source = _default_value(global_vars, key), f"globalvalue.xml DefaultValue.{key}"
    if not raw:
        return default
    value = raw.lower()
    if value not in choices:
        raise ValueError(
            f"{source} 取值 '{raw}' 非法，合法取值: {' | '.join(choices)}（默认 {default}）。"
            f"修复: 在 globalvalue.xml 的 DefaultValue 组写 <var name=\"{key}\" value=\"{default}\"/>，"
            f"或使用 {cli_flag} {'|'.join(choices)}"
        )
    return value


def resolve_session_mode(cli_value: Optional[str], global_vars: Optional[Mapping[str, Any]]) -> str:
    """解析会话模式：CLI > DefaultValue.SessionMode > isolated。"""
    return _resolve_choice(cli_value, global_vars, "SessionMode", SESSION_MODES,
                           SESSION_ISOLATED, "--session-mode")


def resolve_evidence_mode(cli_value: Optional[str], global_vars: Optional[Mapping[str, Any]]) -> str:
    """解析证据（截图）模式：CLI > DefaultValue.EvidenceMode > full。"""
    return _resolve_choice(cli_value, global_vars, "EvidenceMode", EVIDENCE_MODES,
                           EVIDENCE_FULL, "--evidence")


DIALOG_POLICIES = ("accept", "dismiss", "fail")


def validate_default_values(global_vars: Optional[Mapping[str, Any]]) -> None:
    """启动驱动前校验 v11.6.0 执行策略键（CORE §7.4：非法取值不静默回落默认值）。

    校验 ``WaitTime``（非负数，毫秒）、``AutoWait``（自动等待，非负数，毫秒）、
    ``DialogPolicy``（accept|dismiss|fail）；未配置 / 空值视为使用默认值。
    旧键 ``VerifyTimeout``（v11.6.0 开发期名称）已更名为 ``AutoWait``，出现即报错。
    ``SessionMode`` / ``EvidenceMode`` 由 :func:`resolve_session_mode` /
    :func:`resolve_evidence_mode` 校验（它们还要考虑 CLI 覆盖）。

    Raises:
        ValueError: 取值非法，信息含合法取值与修复提示。
    """
    if _default_value(global_vars, "VerifyTimeout"):
        raise ValueError(
            "globalvalue.xml DefaultValue.VerifyTimeout 已更名为 DefaultValue.AutoWait（自动等待，单位毫秒，默认 5000）。"
            "修复: 改写为 <var name=\"AutoWait\" value=\"5000\"/>；填 0 关闭 verify 自动重试"
        )
    for key, unit, default in (("WaitTime", "毫秒", "0"), ("AutoWait", "毫秒", "5000")):
        raw = _default_value(global_vars, key)
        if not raw:
            continue
        try:
            ok = float(raw) >= 0
        except ValueError:
            ok = False
        if not ok:
            raise ValueError(
                f"globalvalue.xml DefaultValue.{key} 取值 '{raw}' 非法，必须是非负数（单位{unit}，默认 {default}）。"
                f"修复: 写 <var name=\"{key}\" value=\"{default}\"/>"
            )
    raw = _default_value(global_vars, "DialogPolicy")
    if raw and raw.lower() not in DIALOG_POLICIES:
        raise ValueError(
            f"globalvalue.xml DefaultValue.DialogPolicy 取值 '{raw}' 非法，合法取值: "
            f"{' | '.join(DIALOG_POLICIES)}（默认 fail）。修复: 写 <var name=\"DialogPolicy\" value=\"fail\"/>"
        )


def resolve_wait_time(raw: Any) -> Tuple[float, Optional[str]]:
    """把 ``DefaultValue.WaitTime`` 换算为秒。

    Returns:
        (秒数, 弃用告警文本或 None)。

    规则（决策 D3）：
        - 空 / 非数字 / ≤ 0 → 0（不等待）
        - 0 < 值 ≤ 30 → 旧写法，按**秒**解释，并返回弃用告警
        - 值 > 30 → 按**毫秒**解释
    """
    if raw is None:
        return 0.0, None
    text = str(raw).strip()
    if not text:
        return 0.0, None
    try:
        value = float(text)
    except (TypeError, ValueError):
        return 0.0, (
            f"DefaultValue.WaitTime='{text}' 不是数字，已按 0 毫秒处理。"
            f"WaitTime 单位为毫秒（v11.6.0 起），推荐写 0"
        )
    if value <= 0:
        return 0.0, None
    if value <= LEGACY_WAIT_SECONDS_MAX:
        ms = f"{value * 1000:g}"
        warning = (
            f"[弃用] DefaultValue.WaitTime={text} 按旧单位「秒」兼容解释（每步等待 {value:g} 秒）。"
            f"v11.6.0 起 WaitTime 单位统一为毫秒（与 <cases step_wait> 一致），"
            f"≤30 的旧值将在后续版本按毫秒解释。请改写为 WaitTime={ms}（毫秒），"
            f"或写 0 把交互等待交给智能等待与 verify 自动重试"
        )
        return value, warning
    return value / 1000.0, None


class SharedBrowser:
    """shared_browser 模式下整个 run 共用的浏览器进程。

    只持有 Playwright 实例与 Browser；每个驱动在其上新建自己的 BrowserContext。
    启动逻辑复用驱动的 ``_launch_browser()``（保持 channel / 启动参数与 isolated 一致）。
    """

    def __init__(self) -> None:
        self._pw = None
        self.browser = None
        self.launch_count = 0

    def acquire(self, launcher: Callable[[], Tuple[Any, Any]]):
        """返回共享浏览器；首次调用（或浏览器已断开）时通过 launcher 启动。"""
        alive = False
        if self.browser is not None:
            try:
                alive = bool(self.browser.is_connected())
            except Exception:
                alive = False
        if not alive:
            self._pw, self.browser = launcher()
            self.launch_count += 1
            logger.info("shared_browser: 本次运行共享浏览器已启动（后续用例复用该进程，每用例新建 context）")
        return self.browser

    def close(self) -> None:
        """run 结束时由执行器统一关闭浏览器进程。"""
        browser, pw = self.browser, self._pw
        self.browser = None
        self._pw = None
        if browser is not None:
            try:
                browser.close()
            except Exception as e:  # noqa: BLE001
                logger.debug(f"关闭共享浏览器时出错: {e}")
        if pw is not None:
            try:
                pw.stop()
            except Exception as e:  # noqa: BLE001
                logger.debug(f"停止 Playwright 时出错: {e}")
