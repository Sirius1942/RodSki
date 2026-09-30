"""v11.7.0 自动等待（AutoWait）公共层。

设计文档: .pb/specs/v11.7.0-autowait-unified-design.md §3.1

``DefaultValue.AutoWait``（毫秒；不设置或 0 = 不自动等待）是所有驱动、所有"查找测试对象"
步骤的唯一等待上限。本模块掌握**轮询与 deadline**，驱动只提供两样东西：

1. ``probe(locator, frame=None) -> bool``：即时探测，不等待；
2. 带 ``timeout_ms`` 的动作：可操作性等待（Web actionability / 移动端 clickable）
   只使用公共层给出的剩余预算。

两阶段模型（共享同一个 deadline）::

    deadline = now + AutoWait
    [定位阶段]  loop: 按 priority 对该元素所有 location 做即时探测
                    命中 → 可操作阶段；全部未命中 → sleep(interval) 直到 deadline
    [可操作阶段] 在命中的定位器上执行动作，timeout = remaining（下限 1ms）
    超时 → ElementWaitTimeoutError

要点：
- 按元素计时：type 批量中每个字段独立一个 Deadline；同一元素多个 location 共享它。
- AutoWait=0：每个定位器恰好探测一次；已找到的元素动作 timeout 取下限 MIN_ACTION_TIMEOUT_MS（500ms）。
  **Playwright 的 timeout=0 表示无限等待，严禁把 0 传给驱动**（见 :meth:`Deadline.action_timeout_ms`）。
- 轮询间隔：DOM/原生控件 0.2s；视觉定位（每轮新截图 + 一次匹配）最小 1.0s。
- 契约 / 配置类错误（PerceptionUnavailableError、InvalidParameterError、驱动已停止等）立即失败，不重试。
"""
from __future__ import annotations

import logging
import time
from typing import Any, Callable, Iterable, List, Mapping, Optional, Sequence, Tuple

from .exceptions import (
    DriverError,
    DriverStoppedError,
    ElementNotFoundError,
    ElementNotInteractableError,
    InvalidParameterError,
    StaleElementError,
    TimeoutError as DriverTimeoutError,
    UnexpectedDialogError,
    AssertionFailedError,
)

logger = logging.getLogger("rodski")

# 未配置 DefaultValue.AutoWait 时的取值（毫秒）：0 = 不自动等待。
# 没有隐含的默认等待时长（Owner 决策 2026-09-30）：要自动等待必须在 globalvalue.xml 显式设置时长
DEFAULT_AUTO_WAIT_MS = 0
# DOM / 原生控件的探测轮询间隔（秒），与 v11.6.0 verify 重试间隔一致
DOM_POLL_INTERVAL_S = 0.2
# 视觉定位（vision / vision_image / ocr / vision_bbox）每轮最小间隔（秒）
VISION_POLL_INTERVAL_S = 1.0
# 元素已找到后，交给驱动执行一次动作的 timeout 下限（毫秒）。
# - Playwright timeout=0 表示无限等待，绝不能传 0；
# - 一次真实点击 / 输入本身需要几十毫秒的往返，1ms 会让已就绪的元素也超时（AutoWait=0 时尤甚）。
# 因此一次动作至少给 500ms 执行时间；它只作用于"已找到"的元素，找不到时不会因此多等。
MIN_ACTION_TIMEOUT_MS = 500

# 视觉定位器类型（与 model_parser.VISION_LOCATOR_TYPES 一致）
VISION_LOCATOR_TYPES = frozenset({"vision", "ocr", "vision_bbox", "vision_image"})


# ── 配置解析 ──────────────────────────────────────────────────────


class AutoWaitConfigError(ValueError):
    """DefaultValue.AutoWait / 旧键 VerifyTimeout 配置非法。

    ``param_name`` 为出错的键名，调用方可据此包装为 InvalidParameterError（关键字层）
    或直接作为 ValueError 抛出（启动前校验 session_mode.validate_default_values）。
    """

    def __init__(self, param_name: str, message: str):
        super().__init__(message)
        self.param_name = param_name
        self.message = message


def _default_group(global_vars: Optional[Mapping[str, Any]]) -> Mapping[str, Any]:
    group = (global_vars or {}).get("DefaultValue") or {}
    return group if isinstance(group, Mapping) else {}


def resolve_auto_wait_ms(global_vars: Optional[Mapping[str, Any]]) -> float:
    """读取 ``DefaultValue.AutoWait``（毫秒）。

    - 未配置 / 空值 → 0：**不自动等待**（没有隐含默认时长）
    - 0 → 不等待（每个定位器探测一次）
    - 正数 → 最多等待该毫秒数
    - 负数 / 非数字 → :class:`AutoWaitConfigError`
    - 旧键 ``VerifyTimeout``（v11.6.0 开发期名称）有值 → :class:`AutoWaitConfigError` 提示改名

    Returns:
        毫秒数（float，可能带小数）。
    """
    group = _default_group(global_vars)
    legacy = group.get("VerifyTimeout")
    if legacy is not None and str(legacy).strip() != "":
        raise AutoWaitConfigError(
            "VerifyTimeout",
            "DefaultValue.VerifyTimeout 已更名为 DefaultValue.AutoWait（自动等待，单位毫秒；不设置或 0 = 不自动等待）。"
            "修复: 改写为 <var name=\"AutoWait\" value=\"5000\"/>；填 0 关闭自动等待",
        )
    raw = group.get("AutoWait")
    if raw is None or str(raw).strip() == "":
        return float(DEFAULT_AUTO_WAIT_MS)
    text = str(raw).strip()
    try:
        value = float(text)
    except ValueError:
        value = -1.0
    if value < 0 or value != value:  # 负数 / NaN
        raise AutoWaitConfigError(
            "AutoWait",
            f"DefaultValue.AutoWait 取值 '{raw}' 非法，必须是非负数（单位毫秒）。"
            f"修复: 写 <var name=\"AutoWait\" value=\"5000\"/> 表示最多等待 5 秒；不设置或填 0 表示不自动等待",
        )
    return value


def format_ms(ms: float) -> str:
    """把毫秒数格式化为错误信息里的 ``5000`` / ``0`` / ``1500.5``。"""
    return f"{float(ms):g}"


# ── 错误 ──────────────────────────────────────────────────────────


class ElementWaitTimeoutError(ElementNotFoundError):
    """元素在 AutoWait 内未找到 / 不可操作。

    是 :class:`DriverError`（经 ElementNotFoundError）的子类；已等满 AutoWait，
    步骤级重试不再重试它（KeywordEngine.execute）。

    消息格式::

        元素 Model.field 在 AutoWait=5000ms 内未找到；尝试定位器: id=a, text=b；最后错误: ...
    """

    error_code = "SKI326"
    error_level = "ERROR"

    def __init__(
        self,
        element: str,
        auto_wait_ms: float,
        locators: Sequence[str] = (),
        last_error: Any = None,
        found: bool = False,
    ):
        self.element = element
        self.auto_wait_ms = auto_wait_ms
        self.locators = list(locators)
        self.last_error = last_error
        self.found = found
        state = "不可操作" if found else "未找到"
        tried = ", ".join(self.locators) if self.locators else "(无)"
        last = _brief_error(last_error) if last_error is not None else "无"
        message = (
            f"元素 {element} 在 AutoWait={format_ms(auto_wait_ms)}ms 内{state}；"
            f"尝试定位器: {tried}；最后错误: {last}"
        )
        cause = last_error if isinstance(last_error, BaseException) else None
        super().__init__(message, cause=cause)


def _brief_error(err: Any) -> str:
    if isinstance(err, BaseException):
        text = getattr(err, "message", None) or str(err)
    else:
        text = str(err)
    text = " ".join(str(text).split())
    return text[:500]


# ── Deadline ──────────────────────────────────────────────────────


class Deadline:
    """一个元素的等待预算。

    Args:
        budget_ms: AutoWait 毫秒数（0 = 不等待）。
        clock / sleep: 可注入，便于单元测试。
    """

    def __init__(
        self,
        budget_ms: float,
        clock: Optional[Callable[[], float]] = None,
        sleep: Optional[Callable[[float], None]] = None,
    ):
        self.budget_ms = max(0.0, float(budget_ms))
        # 运行期再取 time.monotonic / time.sleep，便于测试 monkeypatch
        self._clock = clock or (lambda: time.monotonic())
        self._sleep = sleep or (lambda s: time.sleep(s))
        self.start = self._clock()
        self.end = self.start + self.budget_ms / 1000.0

    def now(self) -> float:
        return self._clock()

    def remaining_s(self) -> float:
        return max(0.0, self.end - self._clock())

    def remaining_ms(self) -> float:
        return self.remaining_s() * 1000.0

    def expired(self) -> bool:
        return self._clock() >= self.end

    def elapsed_s(self) -> float:
        return self._clock() - self.start

    def action_timeout_ms(self) -> int:
        """交给驱动动作的 timeout（毫秒，整数，下限 MIN_ACTION_TIMEOUT_MS，永不为 0）。"""
        return max(MIN_ACTION_TIMEOUT_MS, int(round(self.remaining_ms())))

    def sleep_round(self, round_start: float, interval_s: float) -> None:
        """一轮结束后睡到 ``round_start + interval_s``（不超过 deadline）。"""
        target = min(round_start + max(0.0, interval_s), self.end)
        delay = target - self._clock()
        if delay > 0:
            self._sleep(delay)


def poll_interval_for(locator_types: Iterable[str]) -> float:
    """含视觉定位器 → 1.0s，否则 0.2s。"""
    return VISION_POLL_INTERVAL_S if any(t in VISION_LOCATOR_TYPES for t in locator_types) else DOM_POLL_INTERVAL_S


def fatal_error_types() -> Tuple[type, ...]:
    """保留给外部调用方的兼容接口：列出"立即失败"的典型错误类型。

    v11.7.0 起 :func:`run_element` 采用**白名单**：只有 :data:`RETRYABLE_ERRORS` 会被捕获后等待重试，
    其余一切异常（含本函数列出的类型）都直接抛出。
    """
    types: List[type] = [
        InvalidParameterError,
        DriverStoppedError,
        UnexpectedDialogError,
        AssertionFailedError,
        ElementWaitTimeoutError,
        FileNotFoundError,
    ]
    try:
        from ..vision.perception_interface import PerceptionUnavailableError
    except ImportError:  # pragma: no cover - 以 rodski/ 为根运行
        try:
            from vision.perception_interface import PerceptionUnavailableError  # type: ignore
        except ImportError:
            PerceptionUnavailableError = None  # type: ignore
    if PerceptionUnavailableError is not None:
        types.append(PerceptionUnavailableError)
    return tuple(types)


#: 自动等待捕获的异常白名单："测试对象暂时找不到 / 暂时不可操作"。
#: 驱动必须把原生异常（Playwright TimeoutError、Selenium NoSuchElement / StaleElement /
#: ElementNotInteractable、视觉未匹配等）转换为这些类型抛出；其余异常一律不重试、直接抛出。
RETRYABLE_ERRORS: Tuple[type, ...] = (
    ElementNotFoundError,
    ElementNotInteractableError,
    StaleElementError,
    DriverTimeoutError,
)


# ── 自动等待循环 ──────────────────────────────────────────────────


def run_element(
    element: str,
    candidates: Sequence[Any],
    probe: Callable[[Any], Any],
    act: Callable[[Any, Any, "Deadline"], Any],
    deadline: Deadline,
    *,
    describe: Callable[[Any], str] = str,
    interval_s: float = DOM_POLL_INTERVAL_S,
    fatal: Optional[Tuple[type, ...]] = None,
) -> Tuple[Any, Any]:
    """自动等待：try 查找并执行 → catch "未找到/不可操作" → 等待 → 再执行；成功或超时跳出。

    ::

        while True:
            for 候选定位器 in 按 priority:
                try:
                    hit = probe(候选)            # 查找测试对象（即时，不等待）
                    if not hit: raise ElementNotFoundError
                    return act(候选, hit, deadline)   # 执行动作，timeout = 剩余预算
                except RETRYABLE_ERRORS:        # 白名单：未找到 / 不可操作 / 已失效 / 驱动单次超时
                    记录最后错误，试下一个候选
            if 超过 AutoWait: raise ElementWaitTimeoutError
            sleep(interval)

    - 只有 :data:`RETRYABLE_ERRORS` 被捕获；其余异常（契约错误、驱动已停止、未预期弹窗、
      PerceptionUnavailableError 等）直接抛出，不等待。``fatal`` 仅用于在白名单内再排除某些类型。
    - ``probe`` 抛 ``NotImplementedError``：驱动不支持该定位器类型，之后跳过；全部不支持 → 立即 DriverError。
    - ``act`` 必须以抛异常表示失败；返回 ``False`` 属于驱动契约违规，直接抛 DriverError。
    - 只按时间设上限；AutoWait=0 时每个候选恰好尝试一次。

    Returns:
        (命中的候选, act 的返回值)
    """
    excluded = tuple(fatal) if fatal else ()
    candidates = list(candidates)
    tried = [describe(c) for c in candidates]
    unsupported: set = set()
    last_error: Any = None
    found = False
    rounds = 0
    while True:
        rounds += 1
        round_start = deadline.now()
        for idx, cand in enumerate(candidates):
            if idx in unsupported:
                continue
            stage = "查找"
            try:
                hit = probe(cand)
                if not hit:
                    raise ElementNotFoundError(f"{describe(cand)} 未找到")
                stage = "执行"
                found = True
                result = act(cand, hit, deadline)
            except NotImplementedError as e:
                if stage != "查找":
                    raise
                unsupported.add(idx)
                last_error = e
                logger.debug(f"  ↳ 驱动不支持定位器 {describe(cand)}，跳过")
                continue
            except ElementWaitTimeoutError:
                raise  # 内层已等满（如 drag 目标），不再外层重试
            except RETRYABLE_ERRORS as e:
                if excluded and isinstance(e, excluded):
                    raise
                last_error = e
                logger.debug(f"  ↳ {describe(cand)} {stage}未成功（自动等待中）: {_brief_error(e)}")
                continue
            if result is False:
                raise DriverError(
                    f"元素 {element} 定位器 {describe(cand)} 的动作返回 False：驱动必须以抛异常表示失败"
                )
            if rounds > 1:
                logger.debug(
                    f"{element}: 自动等待 {deadline.elapsed_s() * 1000:.0f}ms 后命中 {describe(cand)}（第 {rounds} 轮）"
                )
            return cand, result
        if candidates and len(unsupported) == len(candidates):
            raise DriverError(
                f"元素 {element} 的所有定位器当前驱动均不支持: {', '.join(tried)}；最后错误: {_brief_error(last_error)}"
            )
        if deadline.expired():
            raise ElementWaitTimeoutError(element, deadline.budget_ms, tried, last_error, found=found)
        deadline.sleep_round(round_start, interval_s)


def wait_until(
    element: str,
    check: Callable[[], Any],
    deadline: Deadline,
    *,
    locators: Sequence[str] = (),
    interval_s: float = DOM_POLL_INTERVAL_S,
    fatal: Optional[Tuple[type, ...]] = None,
) -> Any:
    """单个条件的轮询：``check()`` 返回真值即返回该值；超时 → ElementWaitTimeoutError。"""
    _, value = run_element(
        element, [None], lambda _c: check(), lambda _c, hit, _d: hit, deadline,
        describe=lambda _c: ", ".join(locators) if locators else element,
        interval_s=interval_s, fatal=fatal,
    )
    return value
