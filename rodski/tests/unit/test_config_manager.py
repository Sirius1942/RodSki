"""ConfigManager 单元测试

测试 core/config_manager.py 中的配置管理器。
覆盖：默认值（driver/headless/timeout）、set/get、
      持久化（写入 JSON 文件后重新加载）、
      from_dict / to_dict、自定义配置项。
"""
import json
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock
from core.config_manager import ConfigManager, DEFAULTS


@pytest.fixture
def config(tmp_path):
    path = str(tmp_path / "config.json")
    return ConfigManager(config_path=path)


class TestConfigManager:
    def test_defaults(self, config):
        assert config.get("driver") == "web"
        assert config.get("headless") is False
        assert config.get("timeout") == 30

    def test_set_and_get(self, config):
        config.set("custom_key", "custom_value")
        assert config.get("custom_key") == "custom_value"

    def test_get_default(self, config):
        assert config.get("nonexistent", "fallback") == "fallback"

    def test_set_persists(self, tmp_path):
        path = str(tmp_path / "config.json")
        c1 = ConfigManager(config_path=path)
        c1.set("foo", "bar")
        c2 = ConfigManager(config_path=path)
        assert c2.get("foo") == "bar"

    def test_list_all(self, config):
        all_config = config.list_all()
        assert isinstance(all_config, dict)
        assert "driver" in all_config

    def test_delete(self, config):
        config.set("temp", "val")
        assert config.delete("temp") is True
        assert config.get("temp") is None

    def test_delete_nonexistent(self, config):
        assert config.delete("nonexistent") is False

    def test_validate_all(self, config):
        assert config.validate() is True

    def test_validate_invalid(self, config):
        config.config["driver"] = "invalid"
        assert config.validate() is False

    def test_validate_key(self, config):
        assert config.validate("driver") is True
        assert config.validate("nonexistent") is False

    def test_reset(self, config):
        config.set("driver", "desktop")
        config.set("custom", "val")
        config.reset()
        assert config.get("driver") == "web"
        assert config.get("custom") is None

    def test_save_creates_directory(self, tmp_path):
        path = str(tmp_path / "subdir" / "config.json")
        c = ConfigManager(config_path=path)
        c.save()
        assert (tmp_path / "subdir" / "config.json").exists()

    def test_load_existing_config(self, tmp_path):
        path = tmp_path / "config.json"
        path.write_text(json.dumps({"driver": "desktop", "extra": "value"}))
        c = ConfigManager(config_path=str(path))
        assert c.get("driver") == "desktop"
        assert c.get("extra") == "value"
        assert c.get("timeout") == 30  # default still present

    def test_default_config_path(self, tmp_path, monkeypatch):
        """未指定 config_path 时应使用默认路径 config/config.json（相对当前工作目录）"""
        monkeypatch.chdir(tmp_path)
        c = ConfigManager()
        assert c.config_path == Path("config/config.json")

    def test_load_encoding_is_utf8(self, tmp_path):
        """load() 读取配置文件应使用 utf-8 编码，正确解析中文字符"""
        path = tmp_path / "config.json"
        path.write_text(json.dumps({"driver": "web", "note": "中文配置"}, ensure_ascii=False), encoding="utf-8")
        c = ConfigManager(config_path=str(path))
        assert c.get("note") == "中文配置"

    def test_save_and_reload_roundtrip(self, tmp_path):
        """save() 写入的文件应能被重新加载，且内容（含中文）保持不变"""
        path = tmp_path / "config.json"
        c1 = ConfigManager(config_path=str(path))
        c1.set("note", "中文备注")
        c2 = ConfigManager(config_path=str(path))
        assert c2.get("note") == "中文备注"

    def test_save_creates_parent_directories_recursively(self, tmp_path):
        """save() 应递归创建多级不存在的父目录（parents=True）"""
        path = tmp_path / "a" / "b" / "c" / "config.json"
        c = ConfigManager(config_path=str(path))
        c.save()
        assert path.exists()

    def test_get_nested_dot_key(self, tmp_path):
        """get() 应支持点号分隔的嵌套 key 查找（如 recording.enabled）"""
        path = str(tmp_path / "config.json")
        c = ConfigManager(config_path=path)
        c.set("recording", {"enabled": True, "mode": "auto"})
        assert c.get("recording.enabled") is True
        assert c.get("recording.mode") == "auto"

    def test_get_nested_dot_key_missing_returns_default(self, config):
        """嵌套 key 中间某一级不存在时应返回 default"""
        assert config.get("recording.nonexistent_key", "fallback") == "fallback"
        assert config.get("nonexistent.nested", "fallback") == "fallback"

    def test_get_nested_dot_key_non_dict_intermediate(self, config):
        """嵌套 key 路径中某一级不是 dict 时应安全返回 default"""
        config.set("flat_value", "just_a_string")
        assert config.get("flat_value.sub", "fallback") == "fallback"

    def test_get_plain_key_with_no_dot_unaffected(self, config):
        """不含点号的普通 key 走非嵌套分支，行为不受嵌套逻辑影响"""
        assert config.get("driver") == "web"
        assert config.get("driver", "fallback") == "web"

    # ---- 以下用 mock 直接断言 open()/json.dump()/mkdir() 的精确调用参数 ----
    # 这类参数（encoding="utf-8" vs None、indent=2 vs None、ensure_ascii=False vs None
    # 等）对"能否正确读回值"这种黑盒断言是不可区分的（json 反序列化不关心缩进/大小写
    # 编码名，Python 的 open() 对 "utf-8"/"UTF-8" 一视同仁），必须直接检查调用参数。

    def test_load_opens_file_with_exact_utf8_encoding(self, tmp_path):
        """load() 打开配置文件时必须显式传 mode='r', encoding='utf-8'"""
        path = tmp_path / "config.json"
        path.write_text(json.dumps({"driver": "web"}), encoding="utf-8")

        with patch("builtins.open", wraps=open) as mock_file:
            ConfigManager(config_path=str(path))
            read_calls = [c for c in mock_file.call_args_list if str(path) in str(c)]
            assert read_calls, "load() 未调用 open() 读取配置文件"
            args, kwargs = read_calls[0]
            assert args[1] == "r"
            assert kwargs.get("encoding") == "utf-8"

    def test_save_opens_file_with_exact_utf8_encoding(self, tmp_path):
        """save() 打开配置文件写入时必须显式传 encoding='utf-8'"""
        path = tmp_path / "config.json"
        c = ConfigManager(config_path=str(path))

        with patch("builtins.open", wraps=open) as mock_file:
            c.save()
            write_calls = [call for call in mock_file.call_args_list if str(path) in str(call)]
            assert write_calls, "save() 未调用 open() 写入配置文件"
            args, kwargs = write_calls[0]
            assert kwargs.get("encoding") == "utf-8"

    def test_save_dumps_json_with_indent_2_and_ensure_ascii_false(self, tmp_path):
        """save() 调用 json.dump 必须显式传 indent=2, ensure_ascii=False"""
        path = tmp_path / "config.json"
        c = ConfigManager(config_path=str(path))

        with patch("core.config_manager.json.dump") as mock_dump:
            c.save()
            mock_dump.assert_called_once()
            _, kwargs = mock_dump.call_args
            assert kwargs.get("indent") == 2
            assert kwargs.get("ensure_ascii") is False

    def test_save_mkdir_uses_parents_true(self, tmp_path):
        """save() 创建父目录时必须显式传 parents=True（支持多级不存在的目录）"""
        path = tmp_path / "config.json"
        c = ConfigManager(config_path=str(path))

        with patch.object(Path, "mkdir") as mock_mkdir:
            c.save()
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
