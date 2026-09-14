"""设备发现单元测试 — adb / simctl 解析与平台推导

全部 hermetic：runner 可注入，不调用真的 adb / xcrun。
"""
from unittest.mock import MagicMock

import pytest

try:
    from rodski.core.device_scheduler import (
        Device, _parse_adb_devices, _parse_devicectl_devices, _parse_simctl_devices,
        discover_devices, resolve_platform,
    )
except ImportError:
    from core.device_scheduler import (
        Device, _parse_adb_devices, _parse_devicectl_devices, _parse_simctl_devices,
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
    ],
    "com.apple.CoreSimulator.SimRuntime.watchOS-11-5": [
      {"name": "Apple Watch Ultra 3 (49mm)", "udid": "A8A1E1AC-EEEE",
       "state": "Shutdown", "isAvailable": true}
    ]
  }
}
"""

# 真机样例 —— 取自 `xcrun devicectl list devices --json-output` 的真实结构（已裁剪）。
# 三个条目分别覆盖：可用的 iOS 真机、Apple Watch、以及**配对但未连接**的 iOS 真机。
DEVICECTL_OUTPUT = """{
  "result": {
    "devices": [
      {
        "identifier": "6725A022-7CE2-5DD1-AAF5-600FC381D484",
        "connectionProperties": {
          "pairingState": "paired",
          "transportType": "wired",
          "tunnelState": "disconnected"
        },
        "deviceProperties": {
          "name": "Tars2",
          "osVersionNumber": "26.6.1",
          "developerModeStatus": "enabled"
        },
        "hardwareProperties": {
          "platform": "iOS",
          "reality": "physical",
          "productType": "iPhone16,1",
          "udid": "00008130-001979EE3CF3803A"
        }
      },
      {
        "identifier": "B3ECB119-C017-55E1-835A-23DC5D02DF0F",
        "connectionProperties": {
          "pairingState": "paired",
          "transportType": null,
          "tunnelState": "unavailable"
        },
        "deviceProperties": {"name": "jiusi Apple Watch"},
        "hardwareProperties": {
          "platform": "watchOS",
          "reality": "physical",
          "productType": "Watch7,5",
          "udid": "00008310-001B053C0A3A601E"
        }
      },
      {
        "identifier": "7F50D9B0-2190-51F7-96D3-765726DDF950",
        "connectionProperties": {
          "pairingState": "paired",
          "transportType": null,
          "tunnelState": "unavailable"
        },
        "deviceProperties": {"name": "kaisi iPhone"},
        "hardwareProperties": {
          "platform": "iOS",
          "reality": "physical",
          "productType": "iPhone17,1",
          "udid": "00008140-001A5966213B001C"
        }
      }
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

    def test_emulator_and_real_device_are_distinguished(self):
        """adb 对模拟器与真机用同一套通道，但两者在混跑里是**不同类别**。

        早期实现把每台 adb 设备都标成 kind="real"，于是 AVD 显示成 [真机]，
        DeviceMix=real,simulator 也凑不出「一台真机 + 一台模拟器」。
        """
        devices = _parse_adb_devices(ADB_OUTPUT)

        assert devices[0].udid == "emulator-5554"
        assert devices[0].kind == "simulator"
        assert devices[0].is_real is False
        assert devices[1].udid == "AKRSUT1618000209"
        assert devices[1].kind == "real"
        assert devices[1].is_real is True

    def test_emulator_detected_by_serial_prefix_even_without_qualifiers(self):
        """判据是 adb 生成的 serial 前缀，不依赖设备端上报的 product:/device: 限定符
        （那些换镜像/改名就没了，而 serial 形式由 adb 保证）。"""
        devices = _parse_adb_devices("List of devices attached\nemulator-5556\tdevice\n")

        assert devices[0].kind == "simulator"

    def test_tcp_device_is_treated_as_real(self):
        """走 TCP 的实体设备（serial 是 host:port）不是模拟器，不能误判。"""
        devices = _parse_adb_devices(
            "List of devices attached\n192.168.1.9:5555\tdevice\n")

        assert devices[0].kind == "real"

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

    def test_filters_non_ios_runtimes(self):
        """watchOS/tvOS 模拟器装不了 iOS app，混进设备池会让 DeviceMix 选中死设备。"""
        udids = [d.udid for d in _parse_simctl_devices(SIMCTL_OUTPUT)]

        assert "A8A1E1AC-EEEE" not in udids

    def test_kind_is_simulator(self):
        assert all(d.kind == "simulator" for d in _parse_simctl_devices(SIMCTL_OUTPUT))

    def test_rejects_invalid_json(self):
        assert _parse_simctl_devices("not json") == []

    def test_empty_json(self):
        assert _parse_simctl_devices("{}") == []


class TestDiscoverDevices:
    def test_android_uses_adb_runner(self):
        devices = discover_devices("android", adb_runner=lambda: ADB_OUTPUT)
        assert len(devices) == 2

    def test_ios_uses_simctl_runner(self):
        """iOS 枚举 = 模拟器(simctl) + 真机(devicectl)：真机与模拟器混跑是常规用法。"""
        devices = discover_devices("ios", simctl_runner=lambda: SIMCTL_OUTPUT,
                                   devicectl_runner=lambda: DEVICECTL_OUTPUT)

        assert len(devices) == 4
        assert [d.udid for d in devices][:3] == [
            "AC199BB6-AAAA", "015EA67B-BBBB", "F1F8BAB6-DDDD"]

    def test_ios_simulator_only_when_no_real_device(self):
        """devicectl 不可用（未装 / 无真机）时静默降级，不影响只跑模拟器的既有行为。"""
        devices = discover_devices("ios", simctl_runner=lambda: SIMCTL_OUTPUT,
                                   devicectl_runner=lambda: "")

        assert len(devices) == 3
        assert all(d.state in {"Booted", "Shutdown"} for d in devices)

    def test_unknown_platform_raises(self):
        with pytest.raises(ValueError, match="不支持的平台"):
            discover_devices("windows")


class TestParseDevicectlDevices:
    """真机枚举必须走 devicectl（simctl 看不到 USB 真机）。"""

    def test_keeps_only_connected_ios_real_devices(self):
        devices = _parse_devicectl_devices(DEVICECTL_OUTPUT)

        assert [d.udid for d in devices] == ["00008130-001979EE3CF3803A"]
        assert devices[0].name == "Tars2"
        assert devices[0].platform == "ios"

    def test_filters_watch_and_disconnected_ios(self):
        """watchOS 与未连接（transportType 为 null）的 iOS 真机都不算可用设备。"""
        devices = _parse_devicectl_devices(DEVICECTL_OUTPUT)
        udids = {d.udid for d in devices}

        assert "00008310-001B053C0A3A601E" not in udids      # Apple Watch
        assert "00008140-001A5966213B001C" not in udids      # iOS 真机但未连接

    def test_disconnected_tunnel_is_not_a_filter(self):
        """开发者模式刚开、隧道未建时 tunnelState=disconnected，不能据此误杀设备。

        Tars2 在样例里正是 disconnected —— 它必须出现在结果里。
        """
        devices = _parse_devicectl_devices(DEVICECTL_OUTPUT)

        assert [d.udid for d in devices] == ["00008130-001979EE3CF3803A"]

    def test_rejects_invalid_json(self):
        assert _parse_devicectl_devices("not json") == []

    def test_empty_json(self):
        assert _parse_devicectl_devices("{}") == []


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
