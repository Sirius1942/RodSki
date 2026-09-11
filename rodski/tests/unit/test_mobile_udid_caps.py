"""--udid / Mobile.UDID 链路单元测试

覆盖三跳：
    globalvalue.Mobile.UDID → KeywordEngine.mobile_caps → DriverFactory → 驱动 options

以及最关键的一条顺序约束：`--udid` 必须**晚于** `--platform` 的平台 globalvalue
合并生效，否则会被 globalvalue_ios.xml 里自带的 UDID 静默覆盖（不报错但打错机器）。
"""
import sys
from pathlib import Path

import pytest
from unittest.mock import MagicMock, patch

try:
    from rodski.core.keyword_engine import KeywordEngine
    from rodski.core.driver_factory import DriverFactory
    from rodski.rodski_cli.run import _apply_mobile_cli_overrides
except ImportError:
    from core.keyword_engine import KeywordEngine
    from core.driver_factory import DriverFactory
    from rodski_cli.run import _apply_mobile_cli_overrides


class TestMobileCapsUdid:
    """KeywordEngine 必须把 Mobile.UDID 透传进 mobile_caps。"""

    def _engine(self, global_vars, factory):
        return KeywordEngine(driver=MagicMock(), global_vars=global_vars,
                             driver_factory=factory)

    def test_mobile_caps_includes_udid_from_globalvalue(self):
        factory = MagicMock()
        engine = self._engine({"Mobile": {"Platform": "ios", "UDID": "ABC-123",
                                          "DeviceName": "iPhone 16"}}, factory)
        engine._get_driver_for_type("ios")

        assert factory.call_args.kwargs["udid"] == "ABC-123"

    def test_mobile_caps_udid_absent_when_unconfigured(self):
        factory = MagicMock()
        engine = self._engine({"Mobile": {"Platform": "android"}}, factory)
        engine._get_driver_for_type("android")

        # 无 UDID 时必须为 None（而不是空串或缺失的键），并保持既有 caps 不变
        kwargs = factory.call_args.kwargs
        assert kwargs["udid"] is None
        assert kwargs["device_name"] == "Android"
        assert kwargs["server_url"] == "http://localhost:4723"
        assert kwargs["no_reset"] is False


class TestMobilePortCaps:
    """并发端口：不区分端口时同机第二个 XCUITest 会话会复用第一台设备的 WDA。"""

    def _caps(self, global_vars):
        factory = MagicMock()
        engine = KeywordEngine(driver=MagicMock(), global_vars=global_vars,
                               driver_factory=factory)
        engine._get_driver_for_type(global_vars["Mobile"].get("Platform", "ios"))
        return factory.call_args.kwargs

    def test_ports_injected_when_udid_present(self):
        caps = self._caps({"Mobile": {"Platform": "ios", "UDID": "SIM-A"}})

        assert caps["wda_local_port"] >= 8100
        assert caps["mjpeg_server_port"] >= 9100
        assert caps["system_port"] >= 8200

    def test_ports_omitted_without_udid(self):
        """单设备路径（无 UDID）行为必须逐字节不变：继续用 Appium 默认端口。"""
        caps = self._caps({"Mobile": {"Platform": "android"}})

        assert "wda_local_port" not in caps
        assert "mjpeg_server_port" not in caps
        assert "system_port" not in caps

    def test_two_devices_get_different_port_bands(self):
        """两个真机 UDID 必须落到不同槽位，否则并发时仍然互撞。"""
        a = self._caps({"Mobile": {"Platform": "ios", "UDID": "AC199BB6-54B6-424A-9D3C-B8CEA8DF89BC"}})
        b = self._caps({"Mobile": {"Platform": "ios", "UDID": "015EA67B-C996-48DE-A5F3-576B2BED409B"}})

        assert a["wda_local_port"] != b["wda_local_port"]
        assert a["mjpeg_server_port"] != b["mjpeg_server_port"]

    def test_same_udid_yields_same_ports_across_processes(self):
        """按 UDID 哈希而非下标分配 —— 独立进程（run / queue 子进程）才能一致。"""
        from core.keyword_engine import mobile_port_slot

        udid = "AC199BB6-54B6-424A-9D3C-B8CEA8DF89BC"
        assert mobile_port_slot(udid) == mobile_port_slot(udid)
        assert 0 <= mobile_port_slot(udid) < 100


class TestDriverOptionsCarryUdid:
    """驱动层已经就绪：udid 直达 appium:udid（本用例锁定该契约）。"""
    @patch('drivers.appium_driver.webdriver.Remote')
    def test_android_options_carry_udid(self, mock_remote):
        from drivers.android_driver import AndroidDriver
        AndroidDriver(udid="XYZ")

        options = mock_remote.call_args.kwargs.get('options')
        caps = options.to_capabilities() if options else mock_remote.call_args[0][1]
        assert caps.get('appium:udid') == 'XYZ' or caps.get('udid') == 'XYZ'

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_ios_options_carry_udid(self, mock_remote):
        from drivers.ios_driver import IOSDriver
        IOSDriver(udid="XYZ")

        options = mock_remote.call_args.kwargs.get('options')
        caps = options.to_capabilities() if options else mock_remote.call_args[0][1]
        assert caps.get('appium:udid') == 'XYZ' or caps.get('udid') == 'XYZ'

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_ios_options_carry_concurrency_ports(self, mock_remote):
        """不设 wdaLocalPort 时，同机第二个会话会复用第一台设备的 WDA（默认 8100）。"""
        from drivers.ios_driver import IOSDriver
        IOSDriver(udid="XYZ", wda_local_port=8630, mjpeg_server_port=9630)

        caps = mock_remote.call_args.kwargs['options'].to_capabilities()
        assert caps['appium:wdaLocalPort'] == 8630
        assert caps['appium:mjpegServerPort'] == 9630

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_ios_options_omit_ports_by_default(self, mock_remote):
        """未指定时不得写入端口 cap —— 单设备路径沿用 Appium 默认值。"""
        from drivers.ios_driver import IOSDriver
        IOSDriver(udid="XYZ")

        caps = mock_remote.call_args.kwargs['options'].to_capabilities()
        assert 'appium:wdaLocalPort' not in caps

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_android_options_carry_system_port(self, mock_remote):
        from drivers.android_driver import AndroidDriver
        AndroidDriver(udid="XYZ", system_port=8210, mjpeg_server_port=9210)

        caps = mock_remote.call_args.kwargs['options'].to_capabilities()
        assert caps['appium:systemPort'] == 8210
        assert caps['appium:mjpegServerPort'] == 9210

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_driver_factory_forwards_udid_to_android(self, mock_remote):
        DriverFactory.release_all()
        try:
            DriverFactory.get_driver("android", udid="DEV-A", device_name="Pixel",
                                     server_url="http://localhost:4723")
            options = mock_remote.call_args.kwargs.get('options')
            caps = options.to_capabilities()
            assert caps.get('appium:udid') == "DEV-A"
        finally:
            DriverFactory.release_all()

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_driver_factory_forwards_udid_to_ios(self, mock_remote):
        DriverFactory.release_all()
        try:
            DriverFactory.get_driver("ios", udid="SIM-A", device_name="iPhone 16",
                                     server_url="http://localhost:4723")
            options = mock_remote.call_args.kwargs.get('options')
            caps = options.to_capabilities()
            assert caps.get('appium:udid') == "SIM-A"
        finally:
            DriverFactory.release_all()


class _StubExecutor:
    """_apply_mobile_cli_overrides 只碰 executor.global_vars。"""

    def __init__(self, global_vars):
        self.global_vars = global_vars


class _Args:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class TestUdidOverrideOrder:
    """顺序回归：--udid 必须在 --platform 的平台 globalvalue 合并之后写入。"""

    @pytest.fixture
    def module_dir(self, tmp_path):
        data = tmp_path / "data"
        data.mkdir()
        (data / "globalvalue.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<globalvalue>\n  <group name="Mobile">\n'
            '    <var name="Platform" value="android"/>\n'
            '  </group>\n</globalvalue>\n', encoding="utf-8")
        # 平台文件自带 UDID —— 正是会静默覆盖 CLI 值的那一份
        (data / "globalvalue_ios.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<globalvalue>\n  <group name="Mobile">\n'
            '    <var name="Platform" value="ios"/>\n'
            '    <var name="UDID" value="AAA"/>\n'
            '    <var name="BundleId" value="com.rodski.demo"/>\n'
            '  </group>\n</globalvalue>\n', encoding="utf-8")
        return tmp_path

    def test_udid_applied_after_platform_merge(self, module_dir):
        """--platform ios 会合并 globalvalue_ios.xml（内含 UDID=AAA），
        CLI 的 --udid BBB 必须最终生效——写早了就会被静默改回 AAA。"""
        executor = _StubExecutor({"Mobile": {"Platform": "android"}})

        _apply_mobile_cli_overrides(
            executor, module_dir,
            _Args(platform="ios", udid="BBB"))

        mobile = executor.global_vars["Mobile"]
        assert mobile["Platform"] == "ios"
        assert mobile["UDID"] == "BBB"          # 不是 "AAA"
        assert mobile["BundleId"] == "com.rodski.demo"   # 平台合并仍然生效

    def test_udid_alone_does_not_touch_platform(self, module_dir):
        executor = _StubExecutor({"Mobile": {"Platform": "ios"}})

        _apply_mobile_cli_overrides(executor, module_dir, _Args(udid="BBB"))

        mobile = executor.global_vars["Mobile"]
        assert mobile["UDID"] == "BBB"
        assert mobile["Platform"] == "ios"
        assert "BundleId" not in mobile          # 没给 --platform 就不合并平台文件

    def test_resolved_device_name_aligns_with_udid(self, module_dir):
        """XCUITest 支持 udid 或 deviceName+platformVersion，两者对齐消除歧义。"""
        executor = _StubExecutor({"Mobile": {}})

        _apply_mobile_cli_overrides(
            executor, module_dir,
            _Args(platform="ios", udid="BBB", _resolved_device_name="iPhone 16 Pro"))

        assert executor.global_vars["Mobile"]["DeviceName"] == "iPhone 16 Pro"

    def test_no_udid_leaves_platform_file_value(self, module_dir):
        """不传 --udid 时行为完全不变：平台文件里的 UDID 照旧。"""
        executor = _StubExecutor({"Mobile": {}})

        _apply_mobile_cli_overrides(executor, module_dir, _Args(platform="ios"))

        assert executor.global_vars["Mobile"]["UDID"] == "AAA"
