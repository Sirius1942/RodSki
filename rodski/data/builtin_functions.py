"""RodSki 内置函数模块，支持 ${random(...)} 和 ${date(...)} 语法。"""

import random as _random
import string as _string
import time as _time
import uuid as _uuid
from datetime import datetime as _datetime
from datetime import timedelta as _timedelta

_FUNC_REGISTRY: dict[str, callable] = {}

# 函数分类 —— 决定它能否出现在 Case XML 的 `data` 属性中。
#
# **数据生成类**：每次求值结果都不同（随机、当前时间）。放进 Case XML 会破坏
# 用例可复现性 —— loop 每轮重新解析、失败重跑重新解析，同一个用例两次跑出的
# 值不一样，而 result.xml 又不记录解析后的值，事后无从对账。只允许写在
# data.sqlite 字段值里（数据行本就是"每次执行现取"的语义）。
#
# **纯函数类**：同输入同输出（编码、大小写、进制转换、拼接）。用例层必须能用
# —— v11.0.0 起 `set` 靠它做分步表达式（`set data="enc=${encodeURI(${raw})}"`），
# 而 `set` 只能从 Case XML 的 data 属性取值。
#
# 见 CORE_DESIGN_CONSTRAINTS.md §4.4.6 规则 5。
NONDETERMINISTIC_FUNCTIONS = frozenset({
    "random", "date", "timestamp", "timestamp_ms", "timestamp36",
})


def is_nondeterministic(name: str) -> bool:
    """该内置函数是否每次求值结果都不同（→ 禁止写在 Case XML data 属性中）。"""
    return name in NONDETERMINISTIC_FUNCTIONS


def _register(name: str):
    def decorator(fn):
        _FUNC_REGISTRY[name] = fn
        return fn
    return decorator


@_register("random")
def _builtin_random(type_: str, *args: str) -> str:
    if type_ == "int":
        if len(args) == 0:
            return str(_random.randint(0, 9999))
        if len(args) == 1:
            length = int(args[0])
            low = 10 ** (length - 1)
            high = 10 ** length - 1
            return str(_random.randint(low, high))
        return str(_random.randint(int(args[0]), int(args[1])))
    elif type_ == "float":
        min_val = float(args[0])
        max_val = float(args[1])
        precision = int(args[2]) if len(args) > 2 else 2
        value = _random.uniform(min_val, max_val)
        return f"{value:.{precision}f}"
    elif type_ == "str":
        length = int(args[0]) if args else 8
        chars = _string.ascii_letters + _string.digits
        return "".join(_random.choice(chars) for _ in range(length))
    elif type_ == "digits":
        length = int(args[0]) if args else 6
        return "".join(_random.choice(_string.digits) for _ in range(length))
    elif type_ == "phone":
        prefix = _random.choice(["13", "15", "18"])
        return prefix + str(_random.randint(0, 9)) + "".join(
            _random.choice(_string.digits) for _ in range(8)
        )
    elif type_ == "email":
        chars = _string.ascii_lowercase + _string.digits
        local = "".join(_random.choice(chars) for _ in range(8))
        return f"{local}@test.com"
    elif type_ == "choice":
        return _random.choice(list(args))
    elif type_ == "uuid":
        return str(_uuid.uuid4())
    raise ValueError(f"random 不支持类型: {type_}")


@_register("date")
def _builtin_date(type_: str, *args: str) -> str:
    if type_ == "now":
        fmt = args[0] if args else "%Y-%m-%d %H:%M:%S"
        return _datetime.now().strftime(fmt)
    elif type_ == "today":
        fmt = args[0] if args else "%Y-%m-%d"
        return _datetime.now().strftime(fmt)
    elif type_ == "time":
        fmt = args[0] if args else "%H:%M:%S"
        return _datetime.now().strftime(fmt)
    elif type_ == "timestamp":
        return str(int(_time.time()))
    elif type_ == "timestamp_ms":
        return str(int(_time.time() * 1000))
    elif type_ == "offset":
        value = args[0]
        if value.endswith("h"):
            delta = _timedelta(hours=int(value[:-1]))
            fmt = args[1] if len(args) > 1 else "%Y-%m-%d %H:%M:%S"
        else:
            delta = _timedelta(days=int(value))
            fmt = args[1] if len(args) > 1 else "%Y-%m-%d"
        return (_datetime.now() + delta).strftime(fmt)
    raise ValueError(f"date 不支持类型: {type_}")



@_register("urlencode")
def _builtin_urlencode(value: str) -> str:
    """encodeURIComponent-equivalent: percent-encode all reserved chars except A-Za-z0-9-_.!~*'()"""
    from urllib.parse import quote
    return quote(str(value), safe="A-Za-z0-9-_.!~*'()")


@_register("encodeURI")
def _builtin_encodeuri(value: str) -> str:
    """encodeURIComponent alias."""
    return _builtin_urlencode(value)


@_register("encodeURIComponent")
def _builtin_encodeuricomponent(value: str) -> str:
    """encodeURIComponent alias (JS-compatible)."""
    return _builtin_urlencode(value)


@_register("upper")
def _builtin_upper(value: str) -> str:
    return str(value).upper()


@_register("lower")
def _builtin_lower(value: str) -> str:
    return str(value).lower()


@_register("timestamp")
def _builtin_timestamp() -> str:
    return str(int(_time.time()))


@_register("timestamp_ms")
def _builtin_timestamp_ms() -> str:
    return str(int(_time.time() * 1000))


@_register("timestamp36")
def _builtin_timestamp36() -> str:
    """JS Date.now().toString(36).toUpperCase() equivalent."""
    n = int(_time.time() * 1000)
    # base36 of a Python int
    chars = "0123456789abcdefghijklmnopqrstuvwxyz"
    out = ""
    if n == 0:
        return "0"
    while n:
        n, r = divmod(n, 36)
        out = chars[r] + out
    return out.upper()


@_register("concat")
def _builtin_concat(*args: str) -> str:
    return "".join(str(a) for a in args)


# ============ v11.0.0 新增函数（规范命名） ============

@_register("toUpperCase")
def _builtin_toUpperCase(value: str) -> str:
    """v11.0.0 规范命名：转大写"""
    return str(value).upper()


@_register("toLowerCase")
def _builtin_toLowerCase(value: str) -> str:
    """v11.0.0 规范命名：转小写"""
    return str(value).lower()


@_register("toString36")
def _builtin_toString36(number: str) -> str:
    """v11.0.0 规范命名：转 36 进制（大写）

    Args:
        number: 数字字符串或整数

    Returns:
        36 进制字符串（大写）

    Example:
        toString36(1234567890) → "KF12OI"
    """
    try:
        n = int(number)
    except (ValueError, TypeError):
        raise ValueError(f"toString36 需要整数参数，得到: {number}")

    if n == 0:
        return "0"

    chars = "0123456789abcdefghijklmnopqrstuvwxyz"
    out = ""
    negative = n < 0
    n = abs(n)

    while n:
        n, r = divmod(n, 36)
        out = chars[r] + out

    result = out.upper()
    return f"-{result}" if negative else result


@_register("decodeURI")
def _builtin_decodeURI(value: str) -> str:
    """v11.0.0 新增：URL 解码（percent-decode）

    Args:
        value: URL 编码的字符串

    Returns:
        解码后的字符串

    Example:
        decodeURI("hello%20world") → "hello world"
    """
    from urllib.parse import unquote
    return unquote(str(value))


def call_function(name: str, args: list[str]) -> str:
    if name not in _FUNC_REGISTRY:
        raise ValueError(f"未知内置函数: {name}")
    return _FUNC_REGISTRY[name](*args)
