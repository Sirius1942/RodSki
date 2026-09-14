"""移动端 navigate App URI 测试 — Iteration 47"""
import pytest
from unittest.mock import Mock, MagicMock, patch


def _make_engine_with_mobile_driver(mock_mobile_driver, platform="android"):
    """创建注入了移动端驱动的 KeywordEngine"""
    from core.keyword_engine import KeywordEngine
    engine = KeywordEngine.__new__(KeywordEngine)
    engine.driver = MagicMock()  # 主驱动（PlaywrightDriver）
    engine._desktop_drivers = {platform: mock_mobile_driver}
    engine._global_vars = {
        "Mobile": {
            "Platform": platform,
            "AppiumServer": "http://127.0.0.1:4723",
            "DeviceName": "test_device",
        }
    }
    engine._driver_factory = None
    engine.model_parser = None
    engine.data_manager = None
    engine._return_values = []
    engine.store_return = Mock()
    return engine


class TestNavigateAppUri:

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_navigate_android_app_uri(self, mock_remote):
        """navigate app://android/... 调用 AppiumDriver.start_app"""
        mock_mobile = MagicMock()
        mock_mobile.start_app = Mock(return_value=True)
        engine = _make_engine_with_mobile_driver(mock_mobile, "android")

        engine._kw_navigate({"data": "app://android/com.rodski.demo/com.rodski.demo.LoginActivity"})

        mock_mobile.start_app.assert_called_once_with(
            "com.rodski.demo", "com.rodski.demo.LoginActivity"
        )

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_navigate_ios_app_uri(self, mock_remote):
        """navigate app://ios/... 调用 AppiumDriver.start_app"""
        mock_mobile = MagicMock()
        mock_mobile.start_app = Mock(return_value=True)
        engine = _make_engine_with_mobile_driver(mock_mobile, "ios")

        engine._kw_navigate({"data": "app://ios/com.rodski.demo"})

        mock_mobile.start_app.assert_called_once_with("com.rodski.demo")

    def test_navigate_http_url_uses_main_driver(self):
        """navigate https://... 仍走主驱动（PlaywrightDriver），不受影响"""
        mock_mobile = MagicMock()
        engine = _make_engine_with_mobile_driver(mock_mobile, "android")
        engine.driver.navigate = Mock(return_value=True)
        engine._ensure_driver = Mock()

        engine._kw_navigate({"data": "https://example.com"})

        engine.driver.navigate.assert_called_once_with("https://example.com")
        mock_mobile.start_app.assert_not_called()

    def test_navigate_android_uri_no_activity(self):
        """app://android/{package} 不含 activity 时，start_app 只传 package"""
        mock_mobile = MagicMock()
        mock_mobile.start_app = Mock(return_value=True)
        engine = _make_engine_with_mobile_driver(mock_mobile, "android")

        engine._kw_navigate({"data": "app://android/com.rodski.demo"})

        mock_mobile.start_app.assert_called_once_with("com.rodski.demo", None)


class TestNavigateAppUriFailure:
    """启动失败必须让步骤失败 —— 否则报告记 OK，而 App 根本不在目标页面。

    实测起因：多设备在线时 adb am start 报 `more than one device/emulator`
    （见 appium_driver.start_app 的 -s 修复）。修好之后仍需保证这条失败不被吞：
    否则后续元素定位失败的报错指向「找不到元素」，真正的起因在几百行之前。
    """

    def test_android_start_failure_raises(self):
        from core.keyword_engine import DriverError

        mock_mobile = MagicMock()
        mock_mobile.start_app = Mock(return_value=False)
        engine = _make_engine_with_mobile_driver(mock_mobile, "android")

        with pytest.raises(DriverError):
            engine._kw_navigate({"data": "app://android/com.rodski.demo/.LoginActivity"})

        engine.store_return.assert_not_called()

    def test_ios_start_failure_raises(self):
        from core.keyword_engine import DriverError

        mock_mobile = MagicMock()
        mock_mobile.start_app = Mock(return_value=False)
        engine = _make_engine_with_mobile_driver(mock_mobile, "ios")

        with pytest.raises(DriverError):
            engine._kw_navigate({"data": "app://ios/com.rodski.demo"})

        engine.store_return.assert_not_called()

    def test_android_success_stores_return(self):
        """成功路径不受影响：返回值照常入 history（供 ${Return[-1]} 引用）。"""
        mock_mobile = MagicMock()
        mock_mobile.start_app = Mock(return_value=True)
        engine = _make_engine_with_mobile_driver(mock_mobile, "android")

        assert engine._kw_navigate(
            {"data": "app://android/com.rodski.demo/.LoginActivity"}) is True
        engine.store_return.assert_called_once()


class TestStartAppTargetsDevice:
    """adb 是独立于 Appium session 的第二条通道，必须自己带 -s <serial>。

    不带时多设备（真机 + 模拟器）在线会直接失败：`adb: more than one device/emulator`
    —— Appium 会话建得好好的，只有这一个跳转静默失效。
    """

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_android_start_app_passes_serial(self, mock_remote):
        import subprocess
        from drivers.android_driver import AndroidDriver

        driver = AndroidDriver(udid="emulator-5554")
        driver.driver = Mock()

        with patch.object(subprocess, "run") as run:
            run.return_value = Mock(returncode=0, stdout="Starting: Intent {...}", stderr="")
            assert driver.start_app("com.rodski.demo", ".LoginActivity") is True

        cmd = run.call_args[0][0]
        # 尾部命令形状固定；adb 可执行文件路径随环境（PATH / 回退路径），故只校验其后半段
        assert cmd[1:] == ["-s", "emulator-5554", "shell", "am", "start",
                           "-n", "com.rodski.demo/.LoginActivity"]

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_android_start_app_without_udid_omits_serial(self, mock_remote):
        """单设备路径不变：无 udid 时不得凭空写入 -s。"""
        import subprocess
        from drivers.android_driver import AndroidDriver

        driver = AndroidDriver()
        driver.driver = Mock()

        with patch.object(subprocess, "run") as run:
            run.return_value = Mock(returncode=0, stdout="", stderr="")
            driver.start_app("com.rodski.demo", ".LoginActivity")

        assert "-s" not in run.call_args[0][0]

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_android_start_app_error_in_stderr_fails(self, mock_remote):
        """`am start` 的退出码不可靠：Activity 不存在时它照样返回 0，只打 stderr。"""
        import subprocess
        from drivers.android_driver import AndroidDriver

        driver = AndroidDriver(udid="emulator-5554")
        driver.driver = Mock()

        with patch.object(subprocess, "run") as run:
            run.return_value = Mock(
                returncode=0,
                stdout="Starting: Intent { cmp=com.rodski.demo/.NoSuchActivity }",
                stderr="Error type 3\nError: Activity class {...} does not exist.",
            )
            assert driver.start_app("com.rodski.demo", ".NoSuchActivity") is False

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_android_start_app_warning_is_not_a_failure(self, mock_remote):
        """「目标 Activity 已在最前」会打 Warning 但 exit=0 —— 那是正常情况。

        回归锁：判据若写成裸的 `"Error" in stderr`，这条会误判成启动失败，
        于是正常的重复导航会变成用例失败。
        """
        import subprocess
        from drivers.android_driver import AndroidDriver

        driver = AndroidDriver(udid="emulator-5554")
        driver.driver = Mock()

        with patch.object(subprocess, "run") as run:
            run.return_value = Mock(
                returncode=0,
                stdout="Starting: Intent { cmp=com.rodski.demo/.LoginActivity }",
                stderr="Warning: Activity not started, intent has been delivered to "
                       "currently top Activity",
            )
            assert driver.start_app("com.rodski.demo", ".LoginActivity") is True

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_android_start_app_permission_denial_fails(self, mock_remote):
        """非 exported 的 Activity：exit=255 + SecurityException。"""
        import subprocess
        from drivers.android_driver import AndroidDriver

        driver = AndroidDriver(udid="emulator-5554")
        driver.driver = Mock()

        with patch.object(subprocess, "run") as run:
            run.return_value = Mock(
                returncode=255,
                stdout="Starting: Intent { cmp=com.rodski.demo/.HomeActivity }",
                stderr="\nException occurred while executing 'start':\n"
                       "java.lang.SecurityException: Permission Denial: starting Intent "
                       "{...} from null (pid=9511, uid=2000) not exported from uid 10192",
            )
            assert driver.start_app("com.rodski.demo", ".HomeActivity") is False

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_ios_driver_keeps_udid_for_activate_path(self, mock_remote):
        """iOS 走 activate_app，不碰 adb；udid 仍须留在驱动上供诊断/后续使用。"""
        from drivers.ios_driver import IOSDriver

        driver = IOSDriver(udid="00008130-001979EE3CF3803A")
        assert driver.udid == "00008130-001979EE3CF3803A"
