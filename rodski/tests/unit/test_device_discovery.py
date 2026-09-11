"""设备发现单元测试 — adb / simctl 解析与平台推导

全部 hermetic：runner 可注入，不调用真的 adb / xcrun。
"""
from unittest.mock import MagicMock

import pytest

try:
    from rodski.core.device_scheduler import (
        Device, _parse_adb_devices, _parse_simctl_devices,
        discover_devices, resolve_platform,
    )
except ImportError:
    from core.device_scheduler import (
        Device, _parse_adb_devices, _parse_simctl_devices,
        discover_devices, resolve_platform,
    )


ADB_OUTPUT = """List of devices attached
emulator-5554          device product:sdk model:Pixel_7 device:emu transport_id:1
AKRSUT1618000209       device product:xxx model:SM_G9910 device:yyy transport_id:2
ZY223XQ9WX             unauthorized usb:336592896X transport_id:3
192.168.1.9:5555       offline transport_id:4
"""

SIMCTL_OUTPUT = """{
  "devices": {
    "com.apple.CoreSimulator.SimRuntime.iOS-18-5": [
      {"name": "iPhone 16", "udid": "AC199BB6-AAAA", "state": "Shutdown", "isAvailable": true},
      {"name": "iPhone 16 Pro", "udid": "015EA67B-BBBB", "state": "Booted", "isAvailable": true},
      {"name": "iPhone 14 Pro", "udid": "DEADBEEF-CCCC", "state": "Shutdown", "isAvailable": false}
    ],
    "com.apple.CoreSimulator.SimRuntime.iOS-26-5": [
      {"name": "iPhone 17", "udid": "F1F8BAB6-DDDD", "state": "Shutdown", "isAvailable": true}
    ]
  }
}
"""


class TestParseAdbDevices:
    def test_keeps_only_device_state(self):
        """unauthorized / offline 会让 Appium 建会话失败，必须提前滤掉。"""
        devices = _parse_adb_devices(ADB_OUTPUT)

        assert [d.udid for d in devices] == ["emulator-5554", "AKRSUT1618000209"]
        assert all(d.platform == "android" for d in devices)
        assert all(d.state == "device" for d in devices)

    def test_extracts_model_qualifier(self):
        devices = _parse_adb_devices(ADB_OUTPUT)

        assert devices[0].name == "Pixel_7"
        assert devices[1].name == "SM_G9910"

    def test_header_only_yields_empty(self):
        assert _parse_adb_devices("List of devices attached\n\n") == []

    def test_empty_output(self):
        assert _parse_adb_devices("") == []

    def test_ignores_daemon_noise_lines(self):
        output = "List of devices attached\n* daemon not running; starting now\nemulator-5554\tdevice\n"
        assert [d.udid for d in _parse_adb_devices(output)] == ["emulator-5554"]

    def test_missing_binary_is_not_fatal(self):
        """adb 不存在时 runner 返回空串，解析层必须安静返回空列表而非抛异常。"""
        devices = discover_devices("android", adb_runner=lambda: "")
        assert devices == []


class TestParseSimctlDevices:
    def test_filters_unavailable(self):
        devices = _parse_simctl_devices(SIMCTL_OUTPUT)

        udids = [d.udid for d in devices]
        assert "DEADBEEF-CCCC" not in udids          # isAvailable=false
        assert udids == ["AC199BB6-AAAA", "015EA67B-BBBB", "F1F8BAB6-DDDD"]

    def test_extracts_name_and_state(self):
        devices = _parse_simctl_devices(SIMCTL_OUTPUT)

        assert devices[1].name == "iPhone 16 Pro"
        assert devices[1].state == "Booted"
        assert all(d.platform == "ios" for d in devices)

    def test_rejects_invalid_json(self):
        assert _parse_simctl_devices("not json") == []

    def test_empty_json(self):
        assert _parse_simctl_devices("{}") == []


class TestDiscoverDevices:
    def test_android_uses_adb_runner(self):
        devices = discover_devices("android", adb_runner=lambda: ADB_OUTPUT)
        assert len(devices) == 2

    def test_ios_uses_simctl_runner(self):
        devices = discover_devices("ios", simctl_runner=lambda: SIMCTL_OUTPUT)
        assert len(devices) == 3

    def test_unknown_platform_raises(self):
        with pytest.raises(ValueError, match="不支持的平台"):
            discover_devices("windows")


class TestResolvePlatform:
    def test_cli_platform_wins(self, tmp_path):
        assert resolve_platform(tmp_path, "ios") == "ios"

    def test_read_from_globalvalue(self, tmp_path):
        data = tmp_path / "data"
        data.mkdir()
        (data / "globalvalue.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<globalvalue>\n  <group name="Mobile">\n'
            '    <var name="Platform" value="ios"/>\n'
            '  </group>\n</globalvalue>\n', encoding="utf-8")

        assert resolve_platform(tmp_path, None) == "ios"

    def test_probe_false_returns_none_when_unknown(self, tmp_path):
        """显式给了 --devices 却不给 --platform 时，宁可为 None 让调用方报错，
        也不要探测出一个平台去猜（Android 的 UDID 给 iOS 用不报错，只会打错机器）。"""
        assert resolve_platform(tmp_path, None, probe=False) is None

    def test_probe_falls_back_to_ios(self, tmp_path):
        assert resolve_platform(tmp_path, None, adb_runner=lambda: "") == "ios"

    def test_probe_prefers_android_when_adb_has_devices(self, tmp_path):
        assert resolve_platform(tmp_path, None, adb_runner=lambda: ADB_OUTPUT) == "android"
