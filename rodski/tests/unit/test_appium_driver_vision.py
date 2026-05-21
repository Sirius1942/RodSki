"""AppiumDriver vision locator 和 get_text 单元测试

覆盖：
- vision/ocr/vision_bbox 类型路由到 _locate_with_vision
- Accessibility Tree 匹配优先于 OmniParser
- get_text 坐标反查逻辑
"""
import pytest
from unittest.mock import Mock, patch, MagicMock


class TestAppiumDriverVision:

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_locate_element_routes_vision_type(self, mock_remote):
        from drivers.appium_driver import AppiumDriver
        driver = AppiumDriver({"platformName": "Android"})
        driver._locate_with_vision = Mock(return_value=(100, 200, 300, 400))

        result = driver.locate_element("vision", "登录按钮")
        driver._locate_with_vision.assert_called_once_with("vision", "登录按钮")
        assert result == (100, 200, 300, 400)

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_locate_element_routes_ocr_type(self, mock_remote):
        from drivers.appium_driver import AppiumDriver
        driver = AppiumDriver({"platformName": "Android"})
        driver._locate_with_vision = Mock(return_value=(50, 60, 70, 80))

        result = driver.locate_element("ocr", "搜索")
        driver._locate_with_vision.assert_called_once_with("ocr", "搜索")
        assert result == (50, 60, 70, 80)

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_locate_element_normal_type_unchanged(self, mock_remote):
        from drivers.appium_driver import AppiumDriver
        driver = AppiumDriver({"platformName": "Android"})
        element = Mock()
        element.rect = {'x': 10, 'y': 20, 'width': 100, 'height': 50}
        driver.driver = Mock()
        driver.driver.find_element.return_value = element

        result = driver.locate_element("id", "com.example:id/btn")
        assert result == (10, 20, 110, 70)

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_accessibility_tree_match(self, mock_remote):
        from drivers.appium_driver import AppiumDriver
        driver = AppiumDriver({"platformName": "Android"})

        xml_source = '''<?xml version="1.0" encoding="UTF-8"?>
        <hierarchy>
          <node class="android.widget.FrameLayout" bounds="[0,0][1080,1920]">
            <node class="android.widget.Button" text="登录" clickable="true" bounds="[100,200][300,260]"/>
            <node class="android.widget.EditText" text="用户名" clickable="true" bounds="[50,300][400,360]"/>
            <node class="android.widget.Button" text="注册" clickable="true" bounds="[100,400][300,460]"/>
            <node class="android.widget.TextView" text="忘记密码" clickable="true" bounds="[100,500][300,540]"/>
            <node class="android.widget.Button" text="微信登录" clickable="true" bounds="[100,600][300,660]"/>
            <node class="android.widget.Button" text="QQ登录" clickable="true" bounds="[100,700][300,760]"/>
            <node class="android.widget.TextView" text="服务协议" clickable="true" bounds="[100,800][300,840]"/>
            <node class="android.widget.TextView" text="隐私政策" clickable="true" bounds="[100,900][300,940]"/>
            <node class="android.widget.ImageView" resource-id="logo" clickable="false" bounds="[400,100][600,200]"/>
            <node class="android.widget.Button" text="跳过" clickable="true" bounds="[900,50][1000,100]"/>
            <node class="android.widget.TextView" text="版本号" clickable="false" bounds="[400,1800][600,1850]"/>
          </node>
        </hierarchy>'''
        driver.driver = Mock()
        driver.driver.page_source = xml_source

        result = driver._locate_by_accessibility_tree("登录")
        assert result == (100, 200, 300, 260)

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_accessibility_tree_skip_when_few_nodes(self, mock_remote):
        from drivers.appium_driver import AppiumDriver
        driver = AppiumDriver({"platformName": "Android"})

        xml_source = '''<?xml version="1.0" encoding="UTF-8"?>
        <hierarchy>
          <node class="android.widget.FrameLayout" bounds="[0,0][1080,1920]">
            <node class="android.widget.Button" text="OK" clickable="true" bounds="[100,200][300,260]"/>
          </node>
        </hierarchy>'''
        driver.driver = Mock()
        driver.driver.page_source = xml_source

        result = driver._locate_by_accessibility_tree("OK")
        assert result is None  # 节点不足 10 个，跳过


class TestAppiumDriverGetText:

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_get_text_finds_element(self, mock_remote):
        from drivers.appium_driver import AppiumDriver
        driver = AppiumDriver({"platformName": "Android"})

        elem = Mock()
        elem.rect = {'x': 50, 'y': 100, 'width': 200, 'height': 60}
        elem.text = "Hello World"
        elem.get_attribute = Mock(return_value="")

        driver.driver = Mock()
        driver.driver.find_elements.return_value = [elem]

        result = driver.get_text(50, 100, 250, 160)
        assert result == "Hello World"

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_get_text_returns_empty_when_no_match(self, mock_remote):
        from drivers.appium_driver import AppiumDriver
        driver = AppiumDriver({"platformName": "Android"})

        elem = Mock()
        elem.rect = {'x': 500, 'y': 500, 'width': 100, 'height': 50}
        elem.text = "Far away"

        driver.driver = Mock()
        driver.driver.find_elements.return_value = [elem]

        result = driver.get_text(0, 0, 50, 50)
        assert result == ''

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_get_text_fallback_content_desc(self, mock_remote):
        from drivers.appium_driver import AppiumDriver
        driver = AppiumDriver({"platformName": "Android"})

        elem = Mock()
        elem.rect = {'x': 10, 'y': 10, 'width': 100, 'height': 50}
        elem.text = ""
        elem.get_attribute = Mock(return_value="描述文字")

        driver.driver = Mock()
        driver.driver.find_elements.return_value = [elem]

        result = driver.get_text(10, 10, 110, 60)
        assert result == "描述文字"
