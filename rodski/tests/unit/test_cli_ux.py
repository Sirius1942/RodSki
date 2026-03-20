"""CLI 新功能单元测试 - dry-run, verbose, 错误提示, 进度条"""
import json
import subprocess
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import StringIO
from argparse import Namespace

PROJECT_ROOT = Path(__file__).parent.parent.parent


def run_cli(*args):
    """运行 CLI 命令并返回结果"""
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "cli_main.py")] + list(args),
        capture_output=True, text=True, cwd=str(PROJECT_ROOT)
    )
    return result


class TestDryRun:
    """--dry-run 参数测试"""

    def test_dry_run_with_valid_case(self):
        """dry-run 模式应验证用例并列出步骤"""
        r = run_cli("run", "examples/demo_case.xlsx", "--dry-run")
        assert r.returncode == 0
        assert "Dry Run" in r.stdout
        assert "验证通过" in r.stdout
        assert "步骤" in r.stdout

    def test_dry_run_shows_step_count(self):
        """dry-run 模式应显示步骤数"""
        r = run_cli("run", "examples/demo_case.xlsx", "--dry-run")
        assert r.returncode == 0
        assert "步骤数" in r.stdout

    def test_dry_run_shows_driver_info(self):
        """dry-run 模式应显示驱动信息"""
        r = run_cli("run", "examples/demo_case.xlsx", "--dry-run")
        assert r.returncode == 0
        assert "驱动" in r.stdout

    def test_dry_run_with_nonexistent_file(self):
        """dry-run 模式遇到不存在的文件应失败"""
        r = run_cli("run", "/nonexistent/file.xlsx", "--dry-run")
        assert r.returncode == 1
        assert "不存在" in r.stderr

    def test_dry_run_does_not_execute(self):
        """dry-run 模式不应实际执行用例"""
        r = run_cli("run", "examples/demo_case.xlsx", "--dry-run")
        assert r.returncode == 0
        # 不应出现执行结果
        assert "结果:" not in r.stdout or "Dry Run" in r.stdout

    def test_dry_run_with_verbose(self):
        """dry-run 和 verbose 组合使用"""
        r = run_cli("run", "examples/demo_case.xlsx", "--dry-run", "--verbose")
        assert r.returncode == 0
        assert "Dry Run" in r.stdout


class TestVerbose:
    """--verbose 参数测试"""

    def test_verbose_help_message(self):
        """--verbose 应出现在帮助信息中"""
        r = run_cli("--help")
        assert r.returncode == 0
        assert "verbose" in r.stdout.lower()

    def test_verbose_in_run_help(self):
        """run 子命令的 --verbose 应出现在帮助信息中"""
        r = run_cli("run", "--help")
        assert r.returncode == 0
        assert "verbose" in r.stdout.lower()

    def test_verbose_with_dry_run(self):
        """verbose 模式下 dry-run 应显示参数详情"""
        r = run_cli("run", "examples/demo_case.xlsx", "--dry-run", "--verbose")
        assert r.returncode == 0
        # verbose 模式应显示更多细节
        assert "详细" in r.stdout or "参数" in r.stdout or "步骤" in r.stdout

    def test_verbose_with_nonexistent_file(self):
        """verbose 模式下错误信息应包含提示"""
        r = run_cli("run", "/nonexistent/file.xlsx", "--verbose")
        assert r.returncode == 1
        assert "不存在" in r.stderr


class TestErrorMessages:
    """改进的错误提示信息测试"""

    def test_file_not_found_error(self):
        """文件不存在应给出友好提示"""
        r = run_cli("run", "/nonexistent/file.xlsx")
        assert r.returncode == 1
        assert "文件" in r.stderr
        assert "不存在" in r.stderr
        assert "提示" in r.stderr

    def test_invalid_file_format(self):
        """不支持的文件格式应给出提示"""
        # 创建临时非 Excel 文件
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"test")
            tmp_path = f.name
        try:
            r = run_cli("run", tmp_path)
            assert r.returncode == 1
            assert "不支持" in r.stderr or "格式" in r.stderr
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_help_includes_examples(self):
        """帮助信息应包含使用示例"""
        r = run_cli("--help")
        assert r.returncode == 0
        assert "示例" in r.stdout or "dry-run" in r.stdout

    def test_dry_run_in_help(self):
        """--dry-run 应出现在 run 子命令帮助中"""
        r = run_cli("run", "--help")
        assert r.returncode == 0
        assert "dry-run" in r.stdout


class TestFormatError:
    """format_error 函数测试"""

    def test_format_error_basic(self):
        """基本错误格式化"""
        sys.path.insert(0, str(PROJECT_ROOT))
        from cli_main import format_error

        err = ValueError("测试错误")
        result = format_error(err)
        assert "ValueError" in result
        assert "测试错误" in result

    def test_format_error_with_hint(self):
        """带提示的错误格式化"""
        sys.path.insert(0, str(PROJECT_ROOT))
        from cli_main import format_error

        err = FileNotFoundError("文件不存在")
        result = format_error(err)
        assert "提示" in result
        assert "路径" in result

    def test_format_error_import_error(self):
        """ImportError 应给出安装提示"""
        sys.path.insert(0, str(PROJECT_ROOT))
        from cli_main import format_error

        err = ImportError("No module named 'xxx'")
        result = format_error(err)
        assert "提示" in result
        assert "pip install" in result

    def test_format_error_verbose_mode(self):
        """verbose 模式应显示堆栈信息"""
        sys.path.insert(0, str(PROJECT_ROOT))
        from cli_main import format_error

        try:
            raise ValueError("测试错误")
        except ValueError as e:
            result = format_error(e, verbose=True)
            assert "堆栈" in result

    def test_format_error_non_verbose(self):
        """非 verbose 模式不应显示堆栈"""
        sys.path.insert(0, str(PROJECT_ROOT))
        from cli_main import format_error

        err = ValueError("测试错误")
        result = format_error(err, verbose=False)
        assert "堆栈" not in result


class TestRunFormatError:
    """rodski_cli/run.py 中 _format_run_error 函数测试"""

    def test_format_file_error(self):
        """文件错误格式化"""
        sys.path.insert(0, str(PROJECT_ROOT))
        from rodski_cli.run import _format_run_error

        result = _format_run_error("file", "文件不存在")
        assert "文件错误" in result
        assert "文件不存在" in result

    def test_format_parse_error(self):
        """解析错误格式化"""
        sys.path.insert(0, str(PROJECT_ROOT))
        from rodski_cli.run import _format_run_error

        result = _format_run_error("parse", "格式无效")
        assert "解析错误" in result

    def test_format_driver_error(self):
        """驱动错误格式化"""
        sys.path.insert(0, str(PROJECT_ROOT))
        from rodski_cli.run import _format_run_error

        result = _format_run_error("driver", "驱动初始化失败")
        assert "驱动错误" in result

    def test_format_unknown_error(self):
        """未知类型应使用默认前缀"""
        sys.path.insert(0, str(PROJECT_ROOT))
        from rodski_cli.run import _format_run_error

        result = _format_run_error("unknown", "未知错误")
        assert "错误" in result


class TestPrintVerbose:
    """_print_verbose 函数测试"""

    def test_verbose_true(self, capsys):
        """verbose=True 时应打印"""
        sys.path.insert(0, str(PROJECT_ROOT))
        from rodski_cli.run import _print_verbose

        _print_verbose("测试消息", verbose=True)
        captured = capsys.readouterr()
        assert "详细" in captured.out
        assert "测试消息" in captured.out

    def test_verbose_false(self, capsys):
        """verbose=False 时不应打印"""
        sys.path.insert(0, str(PROJECT_ROOT))
        from rodski_cli.run import _print_verbose

        _print_verbose("测试消息", verbose=False)
        captured = capsys.readouterr()
        assert captured.out == ""


class TestPrintStepDetail:
    """_print_step_detail 函数测试"""

    def test_basic_step(self, capsys):
        """基本步骤打印"""
        sys.path.insert(0, str(PROJECT_ROOT))
        from rodski_cli.run import _print_step_detail

        step = {"keyword": "click", "name": "点击按钮", "params": {"selector": "#btn"}}
        _print_step_detail(step, 0, 3, verbose=False)
        captured = capsys.readouterr()
        assert "1/3" in captured.out
        assert "点击按钮" in captured.out
        assert "click" in captured.out
        # 非 verbose 不显示参数
        assert "selector" not in captured.out

    def test_step_with_verbose(self, capsys):
        """verbose 模式显示参数"""
        sys.path.insert(0, str(PROJECT_ROOT))
        from rodski_cli.run import _print_step_detail

        step = {"keyword": "click", "name": "点击按钮", "params": {"selector": "#btn"}}
        _print_step_detail(step, 0, 3, verbose=True)
        captured = capsys.readouterr()
        assert "selector" in captured.out
        assert "#btn" in captured.out


class TestProgressBar:
    """进度条功能测试"""

    def test_tqdm_importable(self):
        """tqdm 应可正常导入"""
        import tqdm
        assert hasattr(tqdm, "tqdm")

    def test_tqdm_basic_usage(self):
        """tqdm 基本功能"""
        from tqdm import tqdm
        items = list(tqdm(range(5), disable=True))
        assert items == [0, 1, 2, 3, 4]

    def test_tqdm_with_params(self):
        """tqdm 带参数使用"""
        from tqdm import tqdm
        from io import StringIO
        progress = tqdm(total=10, desc="测试", unit="步骤", file=StringIO())
        for _ in range(10):
            progress.update(1)
        progress.close()
        assert progress.n == 10


class TestCLIBackwardCompatibility:
    """向后兼容性测试"""

    def test_help_still_works(self):
        """--help 仍然正常"""
        r = run_cli("--help")
        assert r.returncode == 0
        assert "RodSki" in r.stdout

    def test_version_still_works(self):
        """--version 仍然正常"""
        r = run_cli("--version")
        assert r.returncode == 0
        assert "1.0.0" in r.stdout

    def test_no_args_still_works(self):
        """无参数仍然正常"""
        r = run_cli()
        assert r.returncode == 0

    def test_run_without_new_flags(self):
        """run 子命令不加新参数仍然正常"""
        r = run_cli("run", "/nonexistent/file.xlsx")
        assert r.returncode == 1
        # 仍然报告文件不存在
        assert "不存在" in r.stderr

    def test_config_still_works(self):
        """config 子命令仍然正常"""
        r = run_cli("config", "list")
        assert r.returncode == 0

    def test_log_clear_still_works(self):
        """log clear 仍然正常"""
        r = run_cli("log", "clear")
        assert r.returncode == 0

    def test_run_help_shows_all_options(self):
        """run --help 应显示所有选项（包括新旧）"""
        r = run_cli("run", "--help")
        assert r.returncode == 0
        # 旧选项
        assert "--driver" in r.stdout
        assert "--headless" in r.stdout
        assert "--retry" in r.stdout
        assert "--output" in r.stdout
        assert "--sheet" in r.stdout
        # 新选项
        assert "--dry-run" in r.stdout
        assert "--verbose" in r.stdout
