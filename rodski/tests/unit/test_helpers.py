"""utils/helpers.py 单元测试

测试 utils/helpers.py 中的通用工具函数。
覆盖：文件路径处理、字符串工具、时间格式化等辅助方法。
"""
import pytest
from pathlib import Path
import tempfile
import shutil
from utils.helpers import ensure_dir, safe_filename, truncate_text, format_duration


class TestEnsureDir:
    def test_create_new_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "new_folder"
            result = ensure_dir(str(path))
            assert result.exists()
            assert result.is_dir()

    def test_existing_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = ensure_dir(tmpdir)
            assert result.exists()

    def test_nested_dirs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "a" / "b" / "c"
            result = ensure_dir(str(path))
            assert result.exists()


class TestSafeFilename:
    def test_normal_name(self):
        assert safe_filename("test.txt") == "test.txt"

    def test_special_chars(self):
        assert safe_filename("file@#$%name.txt") == "file____name.txt"

    def test_spaces_allowed(self):
        assert safe_filename("my file.txt") == "my file.txt"

    def test_empty_string(self):
        assert safe_filename("") == ""

    def test_only_special_chars(self):
        result = safe_filename("@#$%")
        assert all(c == "_" for c in result)


class TestTruncateText:
    def test_short_text(self):
        assert truncate_text("hello", 100) == "hello"

    def test_exact_length(self):
        text = "a" * 100
        assert truncate_text(text, 100) == text

    def test_long_text(self):
        text = "a" * 150
        result = truncate_text(text, 100)
        assert len(result) == 100
        assert result.endswith("...")

    def test_custom_max_len(self):
        text = "hello world"
        result = truncate_text(text, 8)
        assert result == "hello..."


class TestFormatDuration:
    def test_seconds_only(self):
        assert format_duration(45.5) == "45.50s"

    def test_minutes_and_seconds(self):
        assert format_duration(125.75) == "2m 5.75s"

    def test_exact_minute(self):
        assert format_duration(120) == "2m 0.00s"

    def test_zero_seconds(self):
        assert format_duration(0) == "0.00s"

    def test_large_duration(self):
        result = format_duration(3661.5)
        assert result == "61m 1.50s"
