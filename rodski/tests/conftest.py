"""共享 fixtures"""
import importlib
import importlib.abc
import importlib.machinery
import importlib.util
import os
import sys
from unittest.mock import MagicMock
import pytest
import warnings

# 过滤第三方库的 deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="dateutil")


# ═══════════════════════════════════════════════════════════════════════════
# 模块身份统一：`core.x` 与 `rodski.core.x` 必须指向同一个模块对象
# ═══════════════════════════════════════════════════════════════════════════
#
# 从 rodski/ 目录跑 pytest 时 cwd 进了 sys.path，于是 `core` / `drivers` /
# `data` 这些**子包名**也能被顶层导入。python 把它们当成独立模块再执行一遍，
# 结果是同一个源文件在进程里存在两个互不相等的模块对象：
#
#   >>> import core.keyword_engine as a, rodski.core.keyword_engine as b
#   >>> a is b, a.logger is b.logger
#   (False, True)
#
# 注意 logger 的**对象**是同一个（logging.getLogger 有单例表），但两个模块
# 各有一份指向它的绑定。于是两类失败会静默发生：
#
#   1. `MagicMock(spec=core...PlaywrightDriver)` 过不了引擎里
#      `isinstance(self.driver, rodski...PlaywrightDriver)` —— 两个**类对象**
#      不相等，测试以为在验 evaluate，实际撞的是「仅支持 Web 浏览器驱动」。
#   2. `patch("core.keyword_engine.logger")` 改的是 `core.*` 那份绑定，
#      引擎读的是 `rodski.core.*` 那份 —— patch 打不中，断言永远失败，
#      而日志其实打出来了（真 logger 的输出就在 "Captured log" 里）。
#
# 让裸名成为包名的**别名**（同一个对象、只加载一次），两类问题同时消失。
# 别名而非复制：模块级可变状态（logger、注册表、缓存）天然共享，不会出现
# 「配置写进 A、代码读 B」。
#
# 只在裸名有对应包名时生效；find_spec 为 None 说明不是本项目子包（如标准库
# 的 `json`、第三方 `requests`），返回 None 交回默认查找器，不受影响。

_ALIAS_ROOTS = frozenset({
    "api", "builtin_ops", "config", "core", "data", "drivers", "llm", "load",
    "observability", "report", "reviewers", "rodski_cli", "schemas", "ui",
    "utils", "vision",
})


class _AliasLoader(importlib.abc.Loader):
    """把裸名模块解析到 rodski 包下同名模块，**复用同一个对象**。

    create_module 返回已加载的目标模块（导入系统不会重新执行它）；
    exec_module 把被临时改写的 __name__/__spec__ 等还原，保证
    `module.__name__` 仍是 `rodski.core.keyword_engine` —— patch / pickle /
    日志里的模块名都指向真实身份，不因从哪个名字导入而变。
    """

    def __init__(self, target_name: str):
        self._target_name = target_name
        self._saved = None

    def create_module(self, spec):
        module = importlib.import_module(self._target_name)
        self._saved = (module.__name__, module.__package__,
                       module.__loader__, module.__spec__)
        return module

    def exec_module(self, module):
        if self._saved is not None:
            (module.__name__, module.__package__,
             module.__loader__, module.__spec__) = self._saved


class _AliasFinder(importlib.abc.MetaPathFinder):
    """把「与包名指向同一源文件」的裸名请求改写成别名。

    只认**同一源文件**：`core` / `data` / `utils` / `config` 这些名字足够通用，
    若不加分辨地拦截，第三方库里的 `import utils` 会静默拿到 rodski.utils。
    故先让默认查找器解析裸名，只有它与 `rodski.<name>` 落在同一个 `.py` 上时
    才接管 —— 那正是「同一个文件被加载两遍」的重复条件，也是本文件要消灭的东西。
    解析到别处（第三方包）或压根不存在时一律返回 None，交回默认查找器。

    判定在**根包**上做：子模块的 PathFinder.find_spec 需要父包的 `__path__`，
    而此刻父包可能尚未导入（正是本 finder 要处理的首次导入）。根包同源即可
    推出子模块同源 —— 两者的 `__path__` 是同一个目录。
    """

    def find_spec(self, fullname, path=None, target=None):
        root = fullname.split(".")[0]
        if root not in _ALIAS_ROOTS:
            return None

        try:
            packaged_root = importlib.util.find_spec("rodski." + root)
        except (ImportError, AttributeError, ValueError):
            return None               # 部分初始化的包会抛，交回默认查找器
        if packaged_root is None:
            return None

        bare_root = importlib.machinery.PathFinder.find_spec(root)
        if bare_root is None or bare_root.origin is None or packaged_root.origin is None:
            return None
        # 必须按 **realpath** 比：测试会往 sys.path 插 `tests/unit/../..` 这类
        # 含 `..` 的条目，PathFinder 顺着它解析出的 origin 就带着 `../..`，
        # 与包名那条的 origin **字符串不等但文件相同**。用字符串比会把它误判成
        # 「同名不同文件」而拒绝别名 —— 于是那几个测试又回到重复加载的老样子。
        if os.path.realpath(bare_root.origin) != os.path.realpath(packaged_root.origin):
            return None               # 同名但不同文件 —— 不是重复，别碰

        return importlib.machinery.ModuleSpec(fullname, _AliasLoader("rodski." + fullname))


if not any(getattr(f, "_rodski_alias_finder", False) for f in sys.meta_path):
    _finder = _AliasFinder()
    _finder._rodski_alias_finder = True       # 防止重复导入 conftest 时装两次
    sys.meta_path.insert(0, _finder)


@pytest.fixture
def make_driver():
    """创建一个正确配置的 mock driver（仅 UI 操作）"""
    def _make():
        driver = MagicMock()
        driver.click.return_value = True
        driver.type.return_value = True
        driver.check.return_value = True
        driver.wait.return_value = None
        driver.navigate.return_value = True
        driver.screenshot.return_value = True
        driver.select.return_value = True
        driver.hover.return_value = True
        driver.drag.return_value = True
        driver.scroll.return_value = True
        driver.assert_element = MagicMock(return_value=True)
        driver.upload_file.return_value = True
        driver.clear.return_value = True
        driver.double_click.return_value = True
        driver.right_click.return_value = True
        driver.key_press.return_value = True
        driver.get_text.return_value = "sample text"
        return driver
    return _make
