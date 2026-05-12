"""RodSki 内置函数模块，支持 ${random(...)} 和 ${date(...)} 语法。"""

import random as _random
import string as _string
import time as _time
import uuid as _uuid
from datetime import datetime as _datetime
from datetime import timedelta as _timedelta

_FUNC_REGISTRY: dict[str, callable] = {}


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


def call_function(name: str, args: list[str]) -> str:
    if name not in _FUNC_REGISTRY:
        raise ValueError(f"未知内置函数: {name}")
    return _FUNC_REGISTRY[name](*args)
