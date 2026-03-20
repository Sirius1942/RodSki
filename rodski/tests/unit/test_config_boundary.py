"""config_manager 边界和异常测试"""
import pytest
import os
from core.config_manager import ConfigManager


class TestConfigManagerBoundary:
    """配置管理器边界测试"""
    
    def test_missing_config_file(self):
        """测试配置文件不存在"""
        manager = ConfigManager("nonexistent.yaml")
        # 应该使用默认配置
        assert manager.get('timeout', 30) == 30
    
    def test_invalid_yaml(self, tmp_path):
        """测试无效的 YAML"""
        config_file = tmp_path / "bad.yaml"
        config_file.write_text("invalid: yaml: content:")
        
        manager = ConfigManager(str(config_file))
        # 应该回退到默认值
        assert manager.get('timeout', 30) == 30
    
    def test_nested_config_get(self):
        """测试嵌套配置获取"""
        manager = ConfigManager()
        manager.config = {'db': {'host': 'localhost', 'port': 3306}}
        
        assert manager.get('db.host') == 'localhost'
        assert manager.get('db.port') == 3306
        assert manager.get('db.user', 'root') == 'root'
    
    def test_config_override(self):
        """测试配置覆盖"""
        manager = ConfigManager()
        manager.set('timeout', 60)
        assert manager.get('timeout') == 60
