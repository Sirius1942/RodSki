"""run 关键字路径规范化和 builtin_call 单元测试

覆盖：
- data="fun/desktop/key_combo.py" 不产生双重 fun/ 前缀
- data="desktop/key_combo.py" 正常解析
- model="desktop_ops" data="key_combo.py" 正常解析
- 路径穿越攻击 (../../etc/passwd) 被拦截
- builtin_call (mock_route) 被识别并尝试执行
"""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from core.keyword_engine import KeywordEngine
from core.exceptions import InvalidParameterError


def _make_engine(module_dir: str):
    """创建带 module_dir 的 KeywordEngine 实例"""
    driver = MagicMock()
    model_parser = MagicMock()
    data_manager = MagicMock()
    engine = KeywordEngine(
        driver=driver,
        model_parser=model_parser,
        data_manager=data_manager,
        module_dir=module_dir,
    )
    return engine


class TestRunPathNormalization:
    """run 关键字路径规范化测试"""

    def test_fun_prefix_no_double(self, tmp_path):
        """data='fun/desktop/key_combo.py' 不应产生 fun/fun/ 双重路径"""
        # 创建目录结构
        fun_dir = tmp_path / "fun" / "desktop"
        fun_dir.mkdir(parents=True)
        script = fun_dir / "key_combo.py"
        script.write_text("print('ok')")

        engine = _make_engine(str(tmp_path))

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="", stderr=""
            )
            engine._kw_run({"model": "", "data": "fun/desktop/key_combo.py"})

        # 验证调用的脚本路径正确（不含双重 fun/）
        called_args = mock_run.call_args[0][0]
        called_script = called_args[1]
        assert "fun/fun/" not in called_script
        assert str(script) == called_script

    def test_relative_path_without_fun_prefix(self, tmp_path):
        """data='desktop/key_combo.py' 应正确解析到 fun/desktop/key_combo.py"""
        fun_dir = tmp_path / "fun" / "desktop"
        fun_dir.mkdir(parents=True)
        script = fun_dir / "key_combo.py"
        script.write_text("print('ok')")

        engine = _make_engine(str(tmp_path))

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="", stderr=""
            )
            engine._kw_run({"model": "", "data": "desktop/key_combo.py"})

        called_args = mock_run.call_args[0][0]
        called_script = called_args[1]
        assert str(script) == called_script

    def test_model_project_name(self, tmp_path):
        """model='desktop_ops' data='key_combo.py' 应解析到 fun/desktop_ops/key_combo.py"""
        fun_dir = tmp_path / "fun" / "desktop_ops"
        fun_dir.mkdir(parents=True)
        script = fun_dir / "key_combo.py"
        script.write_text("print('ok')")

        engine = _make_engine(str(tmp_path))

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="", stderr=""
            )
            engine._kw_run({"model": "desktop_ops", "data": "key_combo.py"})

        called_args = mock_run.call_args[0][0]
        called_script = called_args[1]
        assert str(script) == called_script

    def test_path_traversal_blocked(self, tmp_path):
        """../../etc/passwd 路径穿越应被拦截"""
        fun_dir = tmp_path / "fun"
        fun_dir.mkdir(parents=True)

        engine = _make_engine(str(tmp_path))

        with pytest.raises(InvalidParameterError, match="不能逃出 fun/ 目录"):
            engine._kw_run({"model": "", "data": "../../etc/passwd"})

    def test_path_traversal_with_model_blocked(self, tmp_path):
        """model 模式下路径穿越也应被拦截"""
        fun_dir = tmp_path / "fun" / "myproject"
        fun_dir.mkdir(parents=True)

        engine = _make_engine(str(tmp_path))

        with pytest.raises(InvalidParameterError, match="不能逃出 fun/ 目录"):
            engine._kw_run({"model": "myproject", "data": "../../../etc/passwd"})


class TestBuiltinCallRecognition:
    """builtin_call 识别测试"""

    def test_mock_route_recognized(self):
        """mock_route(...) 格式应被识别为内置函数调用"""
        engine = _make_engine("/tmp/fake_module")

        with patch.object(engine, "_try_builtin_call", wraps=engine._try_builtin_call) as mock_try:
            # mock_route 是已注册的内置函数，但 driver 不是 Playwright
            # 所以会抛异常或返回 True，关键是它被识别并尝试了
            try:
                engine._kw_run({
                    "model": "",
                    "data": "mock_route('/api/users', status=200, body='[]')",
                })
            except Exception:
                pass  # 可能因为 driver 不对而失败，但不影响测试

            mock_try.assert_called_once_with(
                "mock_route('/api/users', status=200, body='[]')"
            )

    def test_non_builtin_not_intercepted(self, tmp_path):
        """普通脚本路径不应被 builtin_call 拦截"""
        fun_dir = tmp_path / "fun"
        fun_dir.mkdir(parents=True)
        script = fun_dir / "my_script.py"
        script.write_text("print('hello')")

        engine = _make_engine(str(tmp_path))

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="", stderr=""
            )
            engine._kw_run({"model": "", "data": "my_script.py"})

        # 应该走到 subprocess.run，说明没被 builtin 拦截
        mock_run.assert_called_once()
