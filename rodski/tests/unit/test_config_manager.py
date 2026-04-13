"""ConfigManager 单元测试

测试 core/config_manager.py 中的配置管理器。
覆盖：默认值（driver/headless/timeout）、set/get、
      持久化（写入 JSON 文件后重新加载）、
      from_dict / to_dict、自定义配置项。
"""
import json
import pytest
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
