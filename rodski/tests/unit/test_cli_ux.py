"""CLI 用户体验测试 - 统一使用 SKIExecutor 执行路径"""
import subprocess
import sys
import pytest
from pathlib import Path

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
        """dry-run 模式应验证用例"""
        r = run_cli("run", "examples/product/DEMO/demo_site/case/demo_case.xml",
                     "--dry-run")
        assert r.returncode == 0
        assert "Dry Run" in r.stdout
        assert "验证通过" in r.stdout

    def test_dry_run_with_nonexistent_file(self):
        r = run_cli("run", "/nonexistent/file.xml", "--dry-run")
        assert r.returncode == 1
        assert "不存在" in r.stderr

    def test_dry_run_does_not_execute(self):
        r = run_cli("run", "examples/product/DEMO/demo_site/case/demo_case.xml",
                     "--dry-run")
        assert r.returncode == 0
        assert "Dry Run" in r.stdout

    def test_dry_run_missing_model(self):
        """model 推断失败时应给出提示"""
        r = run_cli("run", "examples/api_test/data/login_request.json", "--dry-run")
        assert r.returncode == 1

    def test_dry_run_with_verbose(self):
        r = run_cli("run", "examples/product/DEMO/demo_site/case/demo_case.xml",
                     "--dry-run", "--verbose")
        assert r.returncode == 0
        assert "Dry Run" in r.stdout


class TestVerbose:
    """--verbose 参数测试"""

    def test_verbose_help_message(self):
        r = run_cli("--help")
        assert r.returncode == 0
        assert "verbose" in r.stdout.lower()

    def test_verbose_in_run_help(self):
        r = run_cli("run", "--help")
        assert r.returncode == 0
        assert "verbose" in r.stdout.lower()

    def test_verbose_with_dry_run(self):
        r = run_cli("run", "examples/product/DEMO/demo_site/case/demo_case.xml",
                     "--dry-run", "--verbose")
        assert r.returncode == 0

    def test_verbose_with_nonexistent_file(self):
        r = run_cli("run", "/nonexistent/file.xlsx", "--verbose")
        assert r.returncode == 1
        assert "不存在" in r.stderr


class TestErrorMessages:
    """错误提示信息测试"""

    def test_file_not_found_error(self):
        r = run_cli("run", "/nonexistent/file.xml")
        assert r.returncode == 1
        assert "不存在" in r.stderr

    def test_invalid_file_missing_model(self):
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as f:
            f.write(b"<cases></cases>")
            tmp_path = f.name
        try:
            r = run_cli("run", tmp_path, "--dry-run")
            assert r.returncode == 1
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_help_includes_examples(self):
        r = run_cli("--help")
        assert r.returncode == 0
        assert "示例" in r.stdout or "dry-run" in r.stdout

    def test_dry_run_in_help(self):
        r = run_cli("run", "--help")
        assert r.returncode == 0
        assert "dry-run" in r.stdout


class TestFormatError:
    """format_error 函数测试"""

    def test_format_error_basic(self):
        sys.path.insert(0, str(PROJECT_ROOT))
        from cli_main import format_error
        err = ValueError("测试错误")
        result = format_error(err)
        assert "ValueError" in result
        assert "测试错误" in result

    def test_format_error_with_hint(self):
        sys.path.insert(0, str(PROJECT_ROOT))
        from cli_main import format_error
        err = FileNotFoundError("文件不存在")
        result = format_error(err)
        assert "提示" in result

    def test_format_error_import_error(self):
        sys.path.insert(0, str(PROJECT_ROOT))
        from cli_main import format_error
        err = ImportError("No module named 'xxx'")
        result = format_error(err)
        assert "pip install" in result

    def test_format_error_verbose_mode(self):
        sys.path.insert(0, str(PROJECT_ROOT))
        from cli_main import format_error
        try:
            raise ValueError("测试错误")
        except ValueError as e:
            result = format_error(e, verbose=True)
            assert "堆栈" in result

    def test_format_error_non_verbose(self):
        sys.path.insert(0, str(PROJECT_ROOT))
        from cli_main import format_error
        err = ValueError("测试错误")
        result = format_error(err, verbose=False)
        assert "堆栈" not in result


class TestProgressBar:
    """进度条功能测试"""

    def test_tqdm_importable(self):
        import tqdm
        assert hasattr(tqdm, "tqdm")

    def test_tqdm_basic_usage(self):
        from tqdm import tqdm
        items = list(tqdm(range(5), disable=True))
        assert items == [0, 1, 2, 3, 4]


class TestCLIBackwardCompatibility:
    """向后兼容性测试"""

    def test_help_still_works(self):
        r = run_cli("--help")
        assert r.returncode == 0
        assert "RodSki" in r.stdout

    def test_version_still_works(self):
        r = run_cli("--version")
        assert r.returncode == 0
        assert "1.0.0" in r.stdout

    def test_no_args_still_works(self):
        r = run_cli()
        assert r.returncode == 0

    def test_run_without_new_flags(self):
        r = run_cli("run", "/nonexistent/file.xml")
        assert r.returncode == 1
        assert "不存在" in r.stderr

    def test_config_still_works(self):
        r = run_cli("config", "list")
        assert r.returncode == 0

    def test_log_clear_still_works(self):
        r = run_cli("log", "clear")
        assert r.returncode == 0

    def test_run_help_shows_options(self):
        """run --help 应显示关键选项"""
        r = run_cli("run", "--help")
        assert r.returncode == 0
        assert "--headless" in r.stdout
        assert "--output" in r.stdout
        assert "--dry-run" in r.stdout
        assert "--verbose" in r.stdout
        assert "--model" in r.stdout
        assert "--browser" in r.stdout
