"""配置管理 - 加载、验证、更新、持久化"""
import json
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULTS = {
    "driver": "web",
    "browser": "chromium",
    "headless": False,
    "timeout": 30,
    "retry": 0,
    "retry_delay": 1.0,
    "retry_on_errors": ["ElementNotFound", "Timeout", "StaleElement"],
    "log_level": "INFO",
    "log_dir": "logs",
    "report_format": "html",
    "auto_screenshot_on_failure": True,
    "auto_screenshot_on_step": True,
    "screenshot_dir": "screenshots",
    "recording": {
        "enabled": True,
        "mode": "auto",
        "scope": "target",
        "output_dir": "recordings",
        "fps": 10,
        "max_duration": 600,
        "retain_on_pass": True,
        "retain_on_fail": True,
        "prefer_playwright_native_in_headless": True,
        "capture_input": False,
        "event_timeline": False,
        "monitor_id": None,
        "video_size": "screen",
    },
    "smart_wait_enabled": True,
    "smart_wait_max_retries": 30,
    "smart_wait_retry_interval": 0.3,
    "smart_wait_log_retry": True,
}

VALID_KEYS = {
    "driver": {"web", "desktop"},
    "browser": {"chromium", "firefox", "webkit"},
    "headless": {True, False},
    "log_level": {"DEBUG", "INFO", "WARNING", "ERROR"},
    "report_format": {"html", "json"},
}


class ConfigManager:
    def __init__(self, config_path: str = "config/config.json"):
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = dict(DEFAULTS)
        self.load()

    def load(self) -> None:
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.config.update(data)
            except (json.JSONDecodeError, ValueError):
                pass

    def save(self) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    def get(self, key: str, default: Any = None) -> Any:
        if '.' in key:
            keys = key.split('.')
            value = self.config
            for k in keys:
                if isinstance(value, dict):
                    value = value.get(k)
                    if value is None:
                        return default
                else:
                    return default
            return value
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.config[key] = value
        self.save()

    def delete(self, key: str) -> bool:
        if key in self.config:
            del self.config[key]
            self.save()
            return True
        return False

    def list_all(self) -> Dict[str, Any]:
        return dict(self.config)

    def to_dict(self) -> Dict[str, Any]:
        """导出为可序列化的字典配置

        用于跨进程/线程传递配置，避免对象序列化问题。
        典型场景：ExploreExecutor 传递配置给 PlaywrightDriver。

        Returns:
            完整配置字典，可 JSON 序列化
        """
        return dict(self.config)

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'ConfigManager':
        """从字典恢复 ConfigManager 实例

        Args:
            config_dict: 配置字典（通常来自 to_dict()）

        Returns:
            ConfigManager 实例
        """
        instance = cls.__new__(cls)
        instance.config_path = Path("config/config.json")  # 默认路径
        instance.config = dict(DEFAULTS)
        instance.config.update(config_dict)
        return instance

    def validate(self, key: Optional[str] = None) -> bool:
        if key:
            if key in VALID_KEYS:
                return self.config.get(key) in VALID_KEYS[key]
            return key in self.config
        for k, valid in VALID_KEYS.items():
            if k in self.config and self.config[k] not in valid:
                return False
        return True

    def reset(self) -> None:
        self.config = dict(DEFAULTS)
        self.save()
