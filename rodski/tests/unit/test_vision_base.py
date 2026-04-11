"""视觉定位基础层单元测试

覆盖:
  - OmniClient: 正常解析、HTTP 错误、超时、文件不存在、响应格式异常
  - coordinate_utils: normalized_to_pixel、bbox_str_to_coords、get_screen_size
  - screenshot: capture_web、capture_desktop、auto_cleanup

OmniParser 网络调用全部通过 unittest.mock.patch 隔离。
不依赖 pytest，使用 RodSki 自有 RodskiTestRunner。
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from core.test_runner import assert_raises, assert_raises_match

# ── 被测模块 ──────────────────────────────────────────────────
from vision.omni_client import OmniClient
from vision.exceptions import OmniParserError
from vision.coordinate_utils import (
    normalized_to_pixel,
    bbox_str_to_coords,
    get_screen_size,
)
from vision.screenshot import capture_web, capture_desktop, auto_cleanup


# ═══════════════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════════════

def _make_tiny_png(path: Path) -> Path:
    """写一个 1×1 白色 PNG（最小合法 PNG）供测试使用。"""
    # 最小合法 PNG bytes (1x1 white pixel)
    png_bytes = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8"
        "z8BQDwADhQGAWjR9awAAAABJRU5ErkJggg=="
    )
    path.write_bytes(png_bytes)
    return path


def _fake_response(parsed_content_list: list, latency: float = 0.1) -> Mock:
    """构造模拟的 requests.Response 对象。"""
    resp = Mock()
    resp.status_code = 200
    resp.json.return_value = {
        "latency": latency,
        "parsed_content_list": parsed_content_list,
    }
    return resp


# ═══════════════════════════════════════════════════════════════
# OmniClient 测试
# ═══════════════════════════════════════════════════════════════

class TestOmniClientParse:
    """OmniClient.parse 正常路径。"""

    def test_returns_parsed_content_list(self, tmp_path):
        img = _make_tiny_png(tmp_path / "shot.png")
        elements = [
            {"type": "text", "content": "Submit", "bbox": [0.1, 0.2, 0.3, 0.4], "interactivity": True},
        ]
        with patch("vision.omni_client.requests.post", return_value=_fake_response(elements)) as mock_post:
            client = OmniClient()
            result = client.parse(str(img))

        assert result == elements
        mock_post.assert_called_once()

    def test_post_payload_structure(self, tmp_path):
        img = _make_tiny_png(tmp_path / "shot.png")
        with patch("vision.omni_client.requests.post", return_value=_fake_response([])) as mock_post:
            OmniClient().parse(str(img), box_threshold=0.25, iou_threshold=0.5)

        _, kwargs = mock_post.call_args
        payload = kwargs["json"]
        assert "base64_image" in payload
        assert payload["box_threshold"] == 0.25
        assert payload["iou_threshold"] == 0.5

    def test_timeout_forwarded_to_requests(self, tmp_path):
        img = _make_tiny_png(tmp_path / "shot.png")
        with patch("vision.omni_client.requests.post", return_value=_fake_response([])) as mock_post:
            OmniClient(timeout=3).parse(str(img))

        _, kwargs = mock_post.call_args
        assert kwargs["timeout"] == 3

    def test_base64_image_is_valid(self, tmp_path):
        img = _make_tiny_png(tmp_path / "shot.png")
        with patch("vision.omni_client.requests.post", return_value=_fake_response([])) as mock_post:
            OmniClient().parse(str(img))

        payload = mock_post.call_args[1]["json"]
        decoded = base64.b64decode(payload["base64_image"])
        assert decoded == img.read_bytes()

class TestOmniClientErrors:
    """OmniClient.parse 异常路径。"""

    def test_file_not_found_raises(self, tmp_path):
        client = OmniClient()
        assert_raises(FileNotFoundError, client.parse, str(tmp_path / "no_such_file.png"))

    def test_http_error_raises_omni_parser_error(self, tmp_path):
        img = _make_tiny_png(tmp_path / "shot.png")
        bad_resp = Mock()
        bad_resp.status_code = 500
        bad_resp.text = "Internal Server Error"
        with patch("vision.omni_client.requests.post", return_value=bad_resp):
            assert_raises(OmniParserError, OmniClient().parse, str(img))

    def test_missing_key_raises_omni_parser_error(self, tmp_path):
        img = _make_tiny_png(tmp_path / "shot.png")
        resp = Mock()
        resp.status_code = 200
        resp.json.return_value = {"latency": 0.1}  # missing parsed_content_list
        with patch("vision.omni_client.requests.post", return_value=resp):
            assert_raises(OmniParserError, OmniClient().parse, str(img))

    def test_requests_timeout_propagates(self, tmp_path):
        import requests as _req
        img = _make_tiny_png(tmp_path / "shot.png")
        with patch("vision.omni_client.requests.post", side_effect=_req.Timeout("timed out")):
            assert_raises(_req.Timeout, OmniClient().parse, str(img))

    def test_empty_parsed_content_list_returned_as_empty_list(self, tmp_path):
        img = _make_tiny_png(tmp_path / "shot.png")
        with patch("vision.omni_client.requests.post", return_value=_fake_response([])):
            result = OmniClient().parse(str(img))
        assert result == []


class TestOmniClientInputFormats:
    """OmniClient.parse 支持多种输入格式。"""

    def test_parse_with_path_object(self, tmp_path):
        """支持 pathlib.Path 作为输入。"""
        img = _make_tiny_png(tmp_path / "shot.png")
        elements = [{"type": "button", "content": "Click", "bbox": [0.1, 0.2, 0.3, 0.4]}]
        with patch("vision.omni_client.requests.post", return_value=_fake_response(elements)):
            client = OmniClient()
            result = client.parse(img)  # Path object directly
        assert result == elements

    def test_parse_with_bytes_input(self, tmp_path):
        """支持 bytes 作为输入。"""
        img = _make_tiny_png(tmp_path / "shot.png")
        img_bytes = img.read_bytes()
        elements = [{"type": "text", "content": "Hello", "bbox": [0, 0, 0.5, 0.5]}]

        with patch("vision.omni_client.requests.post", return_value=_fake_response(elements)) as mock_post:
            client = OmniClient()
            result = client.parse(img_bytes)

        assert result == elements
        # Verify the payload contains valid base64
        payload = mock_post.call_args[1]["json"]
        decoded = base64.b64decode(payload["base64_image"])
        assert decoded == img_bytes

    def test_parse_with_pil_image(self, tmp_path):
        """支持 PIL.Image.Image 作为输入。"""
        try:
            from PIL import Image
            # 直接创建 1x1 白色 PIL 图像，避免懒加载 broken data stream 问题
            pil_img = Image.new("RGB", (1, 1), color=(255, 255, 255))
            elements = [{"type": "icon", "content": "search", "bbox": [0.2, 0.3, 0.4, 0.5]}]

            with patch("vision.omni_client.requests.post", return_value=_fake_response(elements)):
                client = OmniClient()
                result = client.parse(pil_img)

            assert result == elements
        except ImportError:
            pass  # Skip if PIL not installed

    def test_parse_with_invalid_type_raises_type_error(self):
        """不支持的输入类型抛出 TypeError。"""
        client = OmniClient()
        assert_raises(TypeError, client.parse, 12345)  # int is not supported

    def test_file_not_found_with_path_object(self, tmp_path):
        """Path 对象指向不存在的文件抛出 FileNotFoundError。"""
        client = OmniClient()
        assert_raises(FileNotFoundError, client.parse, tmp_path / "nonexistent.png")


class TestOmniClientRetry:
    """OmniClient 重试机制测试。"""

    def test_retry_on_connection_error(self, tmp_path):
        """连接错误时重试。"""
        import requests as _req
        img = _make_tiny_png(tmp_path / "shot.png")
        elements = [{"type": "text", "content": "OK", "bbox": [0, 0, 1, 1]}]

        call_count = [0]
        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] < 3:  # Fail first 2 times
                raise _req.ConnectionError("Connection failed")
            return _fake_response(elements)

        with patch("vision.omni_client.requests.post", side_effect=side_effect):
            client = OmniClient(retry=3)
            result = client.parse(str(img))

        assert result == elements
        assert call_count[0] == 3  # 2 failures + 1 success

    def test_retry_exhausted_raises_omni_parser_error(self, tmp_path):
        """重试次数耗尽后抛出 OmniParserError。"""
        import requests as _req
        img = _make_tiny_png(tmp_path / "shot.png")

        with patch("vision.omni_client.requests.post", side_effect=_req.ConnectionError("Connection failed")):
            client = OmniClient(retry=1)  # 1 retry = 2 total attempts
            assert_raises(OmniParserError, client.parse, str(img))

    def test_retry_on_timeout(self, tmp_path):
        """超时时重试。"""
        import requests as _req
        img = _make_tiny_png(tmp_path / "shot.png")
        elements = [{"type": "button", "content": "Submit", "bbox": [0.1, 0.2, 0.3, 0.4]}]

        call_count = [0]
        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] < 2:  # Fail first time
                raise _req.Timeout("Timed out")
            return _fake_response(elements)

        with patch("vision.omni_client.requests.post", side_effect=side_effect):
            client = OmniClient(retry=2)
            result = client.parse(str(img))

        assert result == elements
        assert call_count[0] == 2  # 1 timeout + 1 success

    def test_http_error_no_retry(self, tmp_path):
        """HTTP 错误（非 200）不重试，直接抛出。"""
        img = _make_tiny_png(tmp_path / "shot.png")
        bad_resp = Mock()
        bad_resp.status_code = 500
        bad_resp.text = "Internal Server Error"

        call_count = [0]
        def side_effect(*args, **kwargs):
            call_count[0] += 1
            return bad_resp

        with patch("vision.omni_client.requests.post", side_effect=side_effect):
            client = OmniClient(retry=3)
            assert_raises(OmniParserError, client.parse, str(img))

        assert call_count[0] == 1  # No retry on HTTP error


class TestOmniClientHealthCheck:
    """OmniClient.health_check 测试。"""

    def test_health_check_success_via_health_endpoint(self):
        """通过 /health 端点健康检查成功。"""
        mock_resp = Mock()
        mock_resp.status_code = 200

        with patch("vision.omni_client.requests.get", return_value=mock_resp):
            client = OmniClient(url="http://localhost:8001")
            result = client.health_check()

        assert result is True

    def test_health_check_success_via_parse_endpoint(self):
        """无 /health 端点时通过 parse 端点健康检查成功。"""
        import requests as _req

        mock_post_resp = Mock()
        mock_post_resp.status_code = 200

        def get_side_effect(*args, **kwargs):
            # 必须抛出 requests.RequestException 的子类，
            # 因为 health_check() 通过 except requests.RequestException 捕获
            raise _req.ConnectionError("Connection refused")

        def post_side_effect(*args, **kwargs):
            return mock_post_resp

        with patch("vision.omni_client.requests.get", side_effect=get_side_effect):
            with patch("vision.omni_client.requests.post", side_effect=post_side_effect):
                client = OmniClient(url="http://localhost:8001")
                result = client.health_check()

        assert result is True

    def test_health_check_failure(self):
        """健康检查失败返回 False。"""
        import requests as _req

        with patch("vision.omni_client.requests.get", side_effect=_req.ConnectionError("No connection")):
            with patch("vision.omni_client.requests.post", side_effect=_req.ConnectionError("No connection")):
                client = OmniClient(url="http://localhost:8001")
                result = client.health_check()

        assert result is False


class TestOmniClientDefaults:
    """OmniClient 默认值和行为测试。"""

    def test_default_url(self):
        """默认 URL 设置正确（含尾斜杠，因为默认值以 /parse/ 结尾）。"""
        client = OmniClient()
        assert client.url == "http://localhost:8001/parse/"

    def test_default_timeout(self):
        """默认超时设置为 10 秒。"""
        client = OmniClient()
        assert client.timeout == 10

    def test_default_retry(self):
        """默认重试次数为 2。"""
        client = OmniClient()
        assert client.retry == 2

    def test_url_trailing_slash_handling(self):
        """URL 尾部斜杠处理。"""
        client1 = OmniClient(url="http://localhost:8001/")
        assert client1.url == "http://localhost:8001"

        client2 = OmniClient(url="http://localhost:8001/parse/")
        assert client2.url == "http://localhost:8001/parse/"

class TestNormalizedToPixel:
    """normalized_to_pixel 正常路径与边界。"""

    def test_basic_conversion(self):
        cx, cy, x1, y1, x2, y2 = normalized_to_pixel([0.0, 0.0, 1.0, 1.0], 1920, 1080)
        assert x1 == 0 and y1 == 0
        assert x2 == 1920 and y2 == 1080
        assert cx == 960 and cy == 540

    def test_centre_point_is_midpoint(self):
        cx, cy, x1, y1, x2, y2 = normalized_to_pixel([0.1, 0.2, 0.3, 0.4], 1000, 1000)
        assert x1 == 100 and y1 == 200
        assert x2 == 300 and y2 == 400
        assert cx == 200 and cy == 300

    def test_fractional_truncation(self):
        # 0.333... * 300 = 99.9 → 99
        cx, cy, x1, y1, x2, y2 = normalized_to_pixel([1/3, 1/3, 2/3, 2/3], 300, 300)
        assert isinstance(cx, int)
        assert isinstance(x1, int)

    def test_wrong_length_raises_value_error(self):
        assert_raises(ValueError, normalized_to_pixel, [0.1, 0.2, 0.3], 100, 100)
        assert_raises(ValueError, normalized_to_pixel, [0.1, 0.2, 0.3, 0.4, 0.5], 100, 100)

    def test_returns_six_values(self):
        result = normalized_to_pixel([0.1, 0.1, 0.9, 0.9], 800, 600)
        assert len(result) == 6

class TestBboxStrToCoords:
    """bbox_str_to_coords 正常路径与异常。"""

    def test_basic_parsing(self):
        cx, cy = bbox_str_to_coords("100,200,300,400")
        assert cx == 200
        assert cy == 300

    def test_float_values(self):
        cx, cy = bbox_str_to_coords("10.5,20.5,30.5,40.5")
        assert cx == 20  # int((10.5+30.5)/2)
        assert cy == 30  # int((20.5+40.5)/2)

    def test_spaces_around_values(self):
        cx, cy = bbox_str_to_coords(" 0 , 0 , 200 , 100 ")
        assert cx == 100
        assert cy == 50

    def test_wrong_field_count_raises(self):
        assert_raises(ValueError, bbox_str_to_coords, "100,200,300")
        assert_raises(ValueError, bbox_str_to_coords, "100,200,300,400,500")

    def test_non_numeric_raises(self):
        assert_raises(ValueError, bbox_str_to_coords, "a,b,c,d")

    def test_returns_two_ints(self):
        result = bbox_str_to_coords("0,0,640,480")
        assert len(result) == 2
        assert all(isinstance(v, int) for v in result)


class TestGetScreenSize:
    """get_screen_size — mock pyautogui 以保证离线可运行。"""

    def test_returns_two_positive_ints(self):
        mock_pyautogui = MagicMock()
        mock_pyautogui.size.return_value = (1920, 1080)
        with patch.dict("sys.modules", {"pyautogui": mock_pyautogui}):
            # 重新导入以使 patch 生效
            import importlib
            import vision.coordinate_utils as cu
            importlib.reload(cu)
            w, h = cu.get_screen_size()
        assert isinstance(w, int) and isinstance(h, int)
        assert w > 0 and h > 0

    def test_values_match_mock(self):
        mock_pyautogui = MagicMock()
        mock_pyautogui.size.return_value = (2560, 1440)
        with patch.dict("sys.modules", {"pyautogui": mock_pyautogui}):
            import importlib
            import vision.coordinate_utils as cu
            importlib.reload(cu)
            w, h = cu.get_screen_size()
        assert w == 2560
        assert h == 1440

# ═══════════════════════════════════════════════════════════════
# screenshot 测试
# ═══════════════════════════════════════════════════════════════

class TestCaptureWeb:
    """capture_web — selenium driver mock。"""

    def test_returns_absolute_path(self, tmp_path):
        driver = Mock()
        driver.save_screenshot.return_value = True
        out = tmp_path / "web_shot.png"
        result = capture_web(driver, str(out))
        assert os.path.isabs(result)

    def test_calls_save_screenshot(self, tmp_path):
        driver = Mock()
        driver.save_screenshot.return_value = True
        out = tmp_path / "web_shot.png"
        capture_web(driver, str(out))
        driver.save_screenshot.assert_called_once()

    def test_creates_parent_directory(self, tmp_path):
        driver = Mock()
        driver.save_screenshot.return_value = True
        out = tmp_path / "nested" / "dir" / "shot.png"
        capture_web(driver, str(out))
        assert out.parent.exists()

    def test_raises_on_driver_failure(self, tmp_path):
        driver = Mock()
        driver.save_screenshot.return_value = False
        out = tmp_path / "shot.png"
        assert_raises(RuntimeError, capture_web, driver, str(out))


class TestCaptureDesktop:
    """capture_desktop — mock pyautogui.screenshot。"""

    def test_returns_absolute_path(self, tmp_path):
        mock_img = Mock()
        mock_img.save = Mock()
        mock_pyautogui = MagicMock()
        mock_pyautogui.screenshot.return_value = mock_img
        out = tmp_path / "desktop_shot.png"
        # Patch save to actually write a file so exists() check passes
        def _fake_save(path):
            Path(path).touch()
        mock_img.save.side_effect = _fake_save
        with patch.dict("sys.modules", {"pyautogui": mock_pyautogui}):
            import importlib
            import vision.screenshot as ss
            importlib.reload(ss)
            result = ss.capture_desktop(str(out))
        assert os.path.isabs(result)

    def test_calls_pyautogui_screenshot(self, tmp_path):
        mock_img = Mock()
        def _fake_save(path):
            Path(path).touch()
        mock_img.save.side_effect = _fake_save
        mock_pyautogui = MagicMock()
        mock_pyautogui.screenshot.return_value = mock_img
        out = tmp_path / "shot.png"
        with patch.dict("sys.modules", {"pyautogui": mock_pyautogui}):
            import importlib
            import vision.screenshot as ss
            importlib.reload(ss)
            ss.capture_desktop(str(out))
        mock_pyautogui.screenshot.assert_called_once()

    def test_creates_parent_directory(self, tmp_path):
        mock_img = Mock()
        def _fake_save(path):
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.touch()
        mock_img.save.side_effect = _fake_save
        mock_pyautogui = MagicMock()
        mock_pyautogui.screenshot.return_value = mock_img
        out = tmp_path / "sub" / "shot.png"
        with patch.dict("sys.modules", {"pyautogui": mock_pyautogui}):
            import importlib
            import vision.screenshot as ss
            importlib.reload(ss)
            ss.capture_desktop(str(out))
        assert out.parent.exists()

class TestAutoCleanup:
    """auto_cleanup — 文件清理逻辑。"""

    def _write_pngs(self, directory: Path, count: int) -> list:
        """在 directory 下创建 count 个 PNG 文件，返回路径列表。"""
        files = []
        for i in range(count):
            f = directory / f"shot_{i:03d}.png"
            f.write_bytes(b"fake")
            files.append(f)
        return files

    def test_no_deletion_when_under_limit(self, tmp_path):
        self._write_pngs(tmp_path, 5)
        deleted = auto_cleanup(str(tmp_path), max_files=10)
        assert deleted == 0
        assert len(list(tmp_path.iterdir())) == 5

    def test_deletes_excess_files(self, tmp_path):
        self._write_pngs(tmp_path, 25)
        deleted = auto_cleanup(str(tmp_path), max_files=20)
        assert deleted == 5
        assert len(list(tmp_path.iterdir())) == 20

    def test_exact_limit_no_deletion(self, tmp_path):
        self._write_pngs(tmp_path, 20)
        deleted = auto_cleanup(str(tmp_path), max_files=20)
        assert deleted == 0

    def test_nonexistent_directory_returns_zero(self, tmp_path):
        deleted = auto_cleanup(str(tmp_path / "no_such_dir"), max_files=10)
        assert deleted == 0

    def test_invalid_max_files_raises(self, tmp_path):
        assert_raises(ValueError, auto_cleanup, str(tmp_path), 0)
        assert_raises(ValueError, auto_cleanup, str(tmp_path), -1)

    def test_non_image_files_not_deleted(self, tmp_path):
        # create 25 PNGs and 5 .txt files; only PNGs count toward limit
        self._write_pngs(tmp_path, 25)
        for i in range(5):
            (tmp_path / f"log_{i}.txt").write_text("log")
        deleted = auto_cleanup(str(tmp_path), max_files=20)
        assert deleted == 5
        # txt files remain
        txt_files = list(tmp_path.glob("*.txt"))
        assert len(txt_files) == 5

    def test_keeps_newest_files(self, tmp_path):
        import time
        files = self._write_pngs(tmp_path, 5)
        # touch the last file to make it newest
        newest = files[-1]
        time.sleep(0.01)
        newest.write_bytes(b"newer")
        deleted = auto_cleanup(str(tmp_path), max_files=4)
        assert deleted == 1
        assert newest.exists()  # newest must survive




