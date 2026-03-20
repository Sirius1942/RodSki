"""共享 fixtures"""
from unittest.mock import MagicMock
import pytest
import warnings

# 过滤第三方库的 deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="openpyxl")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="dateutil")


@pytest.fixture
def make_driver():
    """创建一个正确配置的 mock driver"""
    def _make():
        driver = MagicMock()
        driver.click.return_value = True
        driver.type.return_value = True
        driver.check.return_value = True
        driver.wait.return_value = None
        driver.navigate.return_value = True
        driver.screenshot.return_value = True
        driver.select.return_value = True
        driver.hover.return_value = True
        driver.drag.return_value = True
        driver.scroll.return_value = True
        driver.assert_element = MagicMock(return_value=True)
        # New UI keywords
        driver.upload_file.return_value = True
        driver.clear.return_value = True
        driver.double_click.return_value = True
        driver.right_click.return_value = True
        driver.key_press.return_value = True
        driver.get_text.return_value = "sample text"
        # New HTTP keywords
        driver.http_get.return_value = True
        driver.http_post.return_value = True
        driver.http_put.return_value = True
        driver.http_delete.return_value = True
        return driver
    return _make
