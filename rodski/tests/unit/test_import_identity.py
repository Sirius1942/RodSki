"""回归锁：`core.x` 与 `rodski.core.x` 必须是同一个模块对象。

背景（v11.3.0 修复）：从 rodski/ 目录跑 pytest 时 cwd 进了 sys.path，`core` /
`drivers` / `data` 这些**子包名**因此也能被顶层导入。python 把同一个源文件执行
了两遍，进程里出现两个互不相等的模块对象 —— 模块级可变状态（logger、注册表、
缓存）各有一份绑定：

    1. `MagicMock(spec=core...PlaywrightDriver)` 过不了引擎的
       `isinstance(self.driver, rodski...PlaywrightDriver)`（两个类对象不等）
       → 测试撞的是「仅支持 Web 浏览器驱动」，而不是它想验的东西；
    2. `patch("core.keyword_engine.logger")` 改的是 `core.*` 那份绑定，引擎读的
       是 `rodski.core.*` 那份 → patch 打不中，断言永远失败，而日志其实打出来了。

修法见 tests/conftest.py 的 `_AliasFinder`：裸名成为包名的**别名**（同一对象）。
这组测试锁住「别名成立」这个前提 —— 一旦有人删掉那个 finder，或把测试挪到别的
rootdir 导致它不加载，这里会立刻红，而不是让 6 个测试以「元素定位失败」式的
误导性报错重新出现。
"""
import importlib
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# 裸名 ↔ 包名，覆盖生产代码里 fallback import 会踩到的全部子包
_ALIAS_ROOTS = [
    "core", "drivers", "data", "api", "vision", "builtin_ops",
    "report", "utils", "config",
]


class TestBareNameIsAnAlias:
    """裸名导入必须复用包名模块，而不是重新执行一遍源文件。"""

    @pytest.mark.parametrize("submodule", [
        "core.keyword_engine",
        "core.exceptions",
        "core.case_parser",
        "core.ski_executor",
        "drivers.playwright_driver",
        "data.data_resolver",
    ])
    def test_bare_and_packaged_are_the_same_object(self, submodule):
        bare = importlib.import_module(submodule)
        packaged = importlib.import_module("rodski." + submodule)

        assert bare is packaged, (
            f"{submodule} 与 rodski.{submodule} 是两个模块对象 —— "
            f"conftest 的 _AliasFinder 没生效，或 sys.path 里混进了 rodski/ 之外的入口"
        )

    @pytest.mark.parametrize("root", _ALIAS_ROOTS)
    def test_root_package_identity(self, root):
        """连包本身也要同一 —— 子模块别名依赖父模块的 __path__ 一路正确。"""
        try:
            bare = importlib.import_module(root)
        except ImportError:
            pytest.skip(f"{root} 在本环境不可导入")
        packaged = importlib.import_module("rodski." + root)

        assert bare is packaged

    def test_module_keeps_its_real_name(self):
        """别名不得污染 __name__：patch / pickle / 日志都按真实身份工作。"""
        bare = importlib.import_module("core.keyword_engine")

        assert bare.__name__ == "rodski.core.keyword_engine"
        assert bare.__spec__.name == "rodski.core.keyword_engine"

    def test_sys_modules_has_no_duplicate(self):
        """从两个名字导入后，sys.modules 里不应留下两份不同的对象。"""
        importlib.import_module("core.keyword_engine")
        packaged = importlib.import_module("rodski.core.keyword_engine")

        assert sys.modules["core.keyword_engine"] is packaged


class TestIdentityFailureModesAreLocked:
    """把这两个具体失败模式单独钉住 —— 它们是这个缺陷当初暴露出来的形态。"""

    def test_isinstance_accepts_mock_built_from_bare_class(self):
        """失败形态 1：测试用裸名建 mock，引擎用包名检查 isinstance。"""
        from drivers.playwright_driver import PlaywrightDriver as BareDriver
        from rodski.core.keyword_engine import KeywordEngine
        from rodski.drivers.playwright_driver import PlaywrightDriver as PackagedDriver

        assert BareDriver is PackagedDriver
        mock_driver = MagicMock(spec=BareDriver)
        mock_driver.page = MagicMock()
        mock_driver.page.evaluate.return_value = 42

        engine = KeywordEngine.__new__(KeywordEngine)
        engine.driver = mock_driver
        # 不抛 DriverError（「仅支持 Web 浏览器驱动」）即为通过
        assert isinstance(engine.driver, PackagedDriver)

    def test_patch_on_bare_path_hits_the_engine_logger(self):
        """失败形态 2：patch("core.x.logger") 必须改到引擎真正读的那份绑定。"""
        import rodski.core.keyword_engine as engine_module

        with patch("core.keyword_engine.logger") as mock_logger:
            engine_module.logger.warning("probe")

        mock_logger.warning.assert_called_once_with("probe")


class TestForeignSameNameModulesAreNotHijacked:
    """`core`/`utils`/`config` 这类名字很通用，别名**只能**在指向同一源文件时生效。

    否则第三方库里的 `import utils` 会静默拿到 rodski.utils —— 那是比重复加载
    更糟的失败（拿到别人的代码，且不报错）。
    """

    def _finder(self):
        """取 conftest 里装的 finder —— 按路径加载，不依赖它注册成哪个模块名。"""
        import importlib.util
        conftest_path = Path(__file__).resolve().parents[1] / "conftest.py"
        spec = importlib.util.spec_from_file_location("_rodski_conftest", conftest_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module._AliasFinder()

    def test_same_name_different_file_is_not_aliased(self, monkeypatch):
        import importlib.machinery

        foreign = importlib.machinery.ModuleSpec("utils", loader=None,
                                                 origin="/tmp/thirdparty/utils.py")
        monkeypatch.setattr(importlib.machinery.PathFinder, "find_spec",
                            staticmethod(lambda name, path=None: foreign))

        assert self._finder().find_spec("utils") is None

    def test_name_absent_from_sys_path_is_not_aliased(self, monkeypatch):
        import importlib.machinery

        monkeypatch.setattr(importlib.machinery.PathFinder, "find_spec",
                            staticmethod(lambda name, path=None: None))

        assert self._finder().find_spec("utils") is None

    def test_unrelated_root_is_ignored(self):
        """不在白名单里的名字一律不管（如标准库 json、第三方 requests）。"""
        assert self._finder().find_spec("json") is None
        assert self._finder().find_spec("requests") is None


class TestOriginComparisonUsesRealpath:
    """同源判定必须按 realpath，不能按字符串。

    回归锁：测试文件头部会往 sys.path 插 `tests/unit/../..` 这种带 `..` 的条目
    （多个文件都有这行），PathFinder 顺着它解析出的 origin 就带着 `../..`，与
    包名那条的 origin **字符串不等但文件相同**。用字符串比会把它误判成「同名
    不同文件」而拒绝别名 —— 症状是 `report` 那几个测试又回到重复加载（
    `isinstance(env, EnvironmentInfo)` 为假），且看不出与路径写法有任何关联。
    """

    def test_dotted_sys_path_entry_still_aliases(self):
        """复现真实路径形态：sys.path 含 `..` 条目时 `report` 仍须成为别名。"""
        package_root = Path(__file__).resolve().parents[2]
        dotted_path = str(package_root / "tests" / "unit" / ".." / "..")
        conftest_path = package_root / "tests" / "conftest.py"

        code = (
            "import importlib.util, sys;"
            "sys.path.insert(0, {dotted!r});"
            "spec = importlib.util.spec_from_file_location('_c', {conf!r});"
            "m = importlib.util.module_from_spec(spec);"
            "spec.loader.exec_module(m);"
            "import report.data_model as bare;"
            "import rodski.report.data_model as packaged;"
            "print('SAME' if bare is packaged and bare.EnvironmentInfo is packaged.EnvironmentInfo"
            "      else 'SPLIT')"
        ).format(dotted=dotted_path, conf=str(conftest_path))
        result = subprocess.run([sys.executable, "-c", code],
                                capture_output=True, text=True, timeout=60,
                                cwd=str(package_root))

        assert result.returncode == 0, result.stderr
        assert "SAME" in result.stdout, (
            f"sys.path 含 `..` 条目时 report 被加载了两份：{result.stdout.strip()}"
        )


class TestProductionFallbackImportsStillWork:
    """生产代码里 `try: from ..core.x / except ImportError: from core.x` 的
    fallback 分支必须仍能解析 —— 别名 finder 让它是同一对象，而不是第二份状态。"""

    def test_fallback_import_resolves_to_the_same_class(self):
        from core.exceptions import ElementNotFoundError as bare
        from rodski.core.exceptions import ElementNotFoundError as packaged

        assert bare is packaged

    def test_fresh_interpreter_can_import_both_spellings(self):
        """干净解释器里两种写法都能导入（别名 finder 只在 pytest 下装）。

        这条跑在子进程里：若有人把别名逻辑写成了「只能在 conftest 已加载时成立」，
        真实运行路径（没有 conftest）会崩，而进程内测试发现不了。
        """
        # 包根目录 = 本文件的上上级（tests/unit/x.py → rodski/），不依赖 cwd
        package_root = Path(__file__).resolve().parents[2]
        code = (
            "import sys; sys.path.insert(0, {root!r});"
            "from rodski.core.keyword_engine import KeywordEngine;"
            "import core.keyword_engine;"
            "print('ok')"
        ).format(root=str(package_root))
        result = subprocess.run([sys.executable, "-c", code],
                                capture_output=True, text=True, timeout=60,
                                cwd=str(package_root))

        assert result.returncode == 0, result.stderr
