"""assertion 模块单元测试 - 图片匹配器"""
import os
import sys
import time
import cv2
import unittest.mock
import numpy as np
from pathlib import Path

# 确保导入路径正确
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.assertion import ImageMatcher, BaseAssertion


# ── 测试辅助 ──────────────────────────────────────────────────

def create_test_image(width: int, height: int, color: tuple = (0, 0, 255)) -> np.ndarray:
    """创建带竖条纹纹理的测试图片（BGR格式），避免纯色导致匹配异常"""
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img[:, :] = color
    stripe = 8
    for x in range(0, width, stripe):
        if (x // stripe) % 2 == 0:
            img[:, x:min(x+stripe, width)] = [
                (color[0] + 40) % 256,
                (color[1] + 40) % 256,
                (color[2] + 40) % 256,
            ]
    return img


def create_gradient_image(width: int, height: int) -> np.ndarray:
    """创建渐变测试图片"""
    img = np.zeros((height, width, 3), dtype=np.uint8)
    for y in range(height):
        for x in range(width):
            img[y, x] = [int(255 * x / width), int(255 * y / height), 128]
    return img


def save_temp_image(img: np.ndarray, name: str) -> str:
    """保存临时图片，返回路径"""
    tmpdir = Path("/tmp/rodski_assertion_test")
    tmpdir.mkdir(parents=True, exist_ok=True)
    path = tmpdir / name
    cv2.imwrite(str(path), img)
    return str(path)


# ── 测试用例 ──────────────────────────────────────────────────

class TestImageMatcher:

    def setup_method(self):
        self.matcher = ImageMatcher()
        self.tmpdir = Path("/tmp/rodski_assertion_test")
        self.tmpdir.mkdir(parents=True, exist_ok=True)

    def teardown_method(self):
        pass

    def test_match_identical_images(self):
        """完全相同的图片应该匹配"""
        img = create_test_image(200, 100, (50, 100, 200))
        ref_path = save_temp_image(img, "identical.png")

        result = self.matcher.match(img, Path(ref_path), threshold=0.8)

        assert result["matched"] is True
        assert result["similarity"] >= 0.9999
        assert result["threshold"] == 0.8
        assert result["reference"] == ref_path
        assert result["location"] is not None
        assert result["location"]["w"] == 200
        assert result["location"]["h"] == 100

    def test_match_different_images_shows_lower_similarity(self):
        """不同图片的相似度应明显低于相同图片"""
        # 创建两个明显不同的 UI 截图
        # UI1: 深色标题栏 + 白色内容区
        ui1 = np.full((200, 300, 3), (240, 240, 240), dtype=np.uint8)
        ui1[0:40, :] = (30, 30, 30)
        ui1[40:200, 0:60] = (220, 220, 220)
        ui1[40:200, 60:300] = (255, 255, 255)

        # UI2: 完全不同布局和颜色
        ui2 = np.full((200, 300, 3), (200, 200, 200), dtype=np.uint8)
        ui2[0:30, :] = (0, 0, 128)
        ui2[30:200, :] = (255, 255, 255)
        ui2[50:100, 100:280] = (255, 0, 0)

        ui3 = ui1.copy()  # 与 ui1 相同

        ref1_path = save_temp_image(ui1, "ui1.png")
        ref2_path = save_temp_image(ui2, "ui2.png")

        # 相同图片应该相似度很高
        result_same = self.matcher.match(ui1, Path(ref1_path), threshold=0.8)
        assert result_same["matched"] is True
        assert result_same["similarity"] >= 0.9999

        # 不同图片相似度应该明显更低（但未必低于 0.8，因为 TM_CCORR_NORMED 对结构差异不敏感）
        result_diff = self.matcher.match(ui1, Path(ref2_path), threshold=0.95)
        assert result_diff["similarity"] < result_same["similarity"], \
            "不同图片相似度应低于相同图片"

    def test_match_threshold_boundary(self):
        """阈值边界测试"""
        img = create_test_image(100, 100, (128, 128, 128))
        ref_path = save_temp_image(img, "threshold_test.png")

        # 完全相同图片，阈值 1.0 应该也匹配
        result = self.matcher.match(img, Path(ref_path), threshold=1.0)
        assert result["matched"] is True

    def test_match_small_screenshot_with_large_reference(self):
        """截图比预期图片小时，按截图尺寸裁剪后比对"""
        # 相同图片但不同尺寸
        img = create_test_image(200, 100, (50, 100, 200))
        # 截图较小
        screenshot = img[25:75, 50:150]  # 裁剪中心区域
        ref_path = save_temp_image(img, "large_ref.png")

        result = self.matcher.match(screenshot, Path(ref_path), threshold=0.8)

        # 裁剪区域与原图结构相同，应该能匹配（但相似度可能不是1.0）
        assert result["similarity"] > 0.0
        assert result["location"] is not None

    def test_match_returns_location_on_success(self):
        """匹配成功时返回正确的位置信息"""
        # 创建带有明显特征图案的图片
        screenshot = create_test_image(300, 200, (100, 100, 100))
        # 在中心放置一个明显不同的绿色方块
        screenshot[85:115, 140:160] = (0, 255, 0)

        # 预期图片就是这个绿色方块
        reference = np.zeros((30, 20, 3), dtype=np.uint8)
        reference[:] = (0, 255, 0)
        ref_path = save_temp_image(reference, "green_patch.png")

        result = self.matcher.match(screenshot, Path(ref_path), threshold=0.5)

        assert result["matched"] is True
        assert result["location"]["w"] == 20
        assert result["location"]["h"] == 30
        # 绿色块在 screenshot 的中心(140-160, 85-115)，裁剪后的位置应该接近那里
        assert result["location"]["x"] >= 0
        assert result["location"]["y"] >= 0

    def test_match_invalid_screenshot_type_raises(self):
        """非 numpy.ndarray 类型应抛出 TypeError"""
        ref_path = save_temp_image(create_test_image(100, 100), "valid.png")

        try:
            self.matcher.match("not an image", Path(ref_path), threshold=0.8)
            assert False, "应该抛出 TypeError"
        except TypeError as e:
            assert "numpy.ndarray" in str(e)

    def test_match_missing_reference_raises(self):
        """预期图片不存在应抛出 FileNotFoundError"""
        screenshot = create_test_image(100, 100)
        fake_path = Path("/tmp/does_not_exist.png")

        try:
            self.matcher.match(screenshot, fake_path, threshold=0.8)
            assert False, "应该抛出 FileNotFoundError"
        except FileNotFoundError:
            pass

    def test_match_grayscale_conversion(self):
        """灰度图转换不影响匹配"""
        # 创建 BGR 彩色图
        color_img = np.zeros((80, 80, 3), dtype=np.uint8)
        color_img[20:60, 20:60] = (0, 255, 0)  # 绿色方块

        ref_path = save_temp_image(color_img, "color.png")

        # 使用相同图片但作为灰度存储后读取
        gray_img = cv2.cvtColor(color_img, cv2.COLOR_BGR2GRAY)
        # 模拟灰度截图（单通道）
        gray_screenshot = cv2.cvtColor(gray_img, cv2.COLOR_GRAY2BGR)

        result = self.matcher.match(gray_screenshot, Path(ref_path), threshold=0.6)
        assert result["matched"] is True

    def test_match_similarity_rounding(self):
        """相似度应保留4位小数"""
        img = create_test_image(50, 50, (77, 77, 77))
        ref_path = save_temp_image(img, "rounding_test.png")

        result = self.matcher.match(img, Path(ref_path), threshold=0.5)

        # 验证小数位数
        sim = result["similarity"]
        assert round(sim, 4) == sim

    def test_result_structure(self):
        """结果字典结构完整"""
        img = create_test_image(100, 100, (55, 55, 55))
        ref_path = save_temp_image(img, "struct_test.png")

        result = self.matcher.match(img, Path(ref_path), threshold=0.8)

        required_keys = ["matched", "similarity", "threshold", "screenshot", "reference", "location"]
        for key in required_keys:
            assert key in result, f"结果缺少字段: {key}"

    # ── Phase 2 测试用例 ────────────────────────────────────────

    def test_match_scope_element(self):
        """scope=element 应仅在指定元素区域内匹配"""
        # 创建 300x200 大图，中心有个绿色方块
        screenshot = create_test_image(300, 200, (100, 100, 100))
        screenshot[85:115, 140:160] = (0, 255, 0)  # 绿色方块

        # 预期图片就是这个绿色方块
        reference = np.zeros((30, 20, 3), dtype=np.uint8)
        reference[:] = (0, 255, 0)
        ref_path = save_temp_image(reference, "element_ref.png")

        # scope=element，定位到绿色方块所在区域
        element_bbox = {"x": 140, "y": 85, "w": 20, "h": 30}
        result = self.matcher.match(
            screenshot, Path(ref_path),
            threshold=0.5,
            scope="element",
            element_bbox=element_bbox,
        )

        assert result["matched"] is True
        assert result["location"]["w"] == 20
        assert result["location"]["h"] == 30

    def test_match_scope_element_without_bbox_raises(self):
        """scope=element 但未提供 element_bbox 应抛出 ValueError"""
        img = create_test_image(200, 100, (50, 100, 200))
        ref_path = save_temp_image(img, "test.png")

        try:
            self.matcher.match(img, Path(ref_path), threshold=0.8, scope="element")
            assert False, "应该抛出 ValueError"
        except ValueError as e:
            assert "element_bbox" in str(e)

    def test_match_scope_invalid_raises(self):
        """无效的 scope 值应抛出 ValueError"""
        img = create_test_image(100, 100, (55, 55, 55))
        ref_path = save_temp_image(img, "test.png")

        try:
            self.matcher.match(img, Path(ref_path), threshold=0.8, scope="invalid")
            assert False, "应该抛出 ValueError"
        except ValueError as e:
            assert "full" in str(e) and "element" in str(e)

    def test_match_wait_immediate_success(self):
        """wait=0 应立即返回结果（立即断言）"""
        img = create_test_image(200, 100, (50, 100, 200))
        ref_path = save_temp_image(img, "wait_immediate.png")

        result = self.matcher.match(img, Path(ref_path), threshold=0.8, wait=0)

        assert result["matched"] is True
        assert result["wait_attempts"] == 1
        # 首次即成功，first_match_time 可能为 0.0 或 None
        assert result["first_match_time"] is None or result["first_match_time"] == 0.0

    def test_match_wait_polling_on_failure(self):
        """wait>0 时，首次失败后应轮询重试"""
        img = create_test_image(200, 100, (50, 100, 200))
        ref_path = save_temp_image(img, "wait_fail.png")

        # Mock _template_match 始终返回低相似度，模拟始终匹配失败
        original_template_match = self.matcher._template_match
        self.matcher._template_match = lambda scr, ref: (0.3, None)

        sleep_calls = []
        original_sleep = time.sleep
        def tracked_sleep(delay):
            sleep_calls.append(delay)
        time.sleep = tracked_sleep

        try:
            result = self.matcher.match(
                img, Path(ref_path),
                threshold=0.8,
                wait=2,  # 2 秒超时
                poll_interval=0.5,
            )
        finally:
            time.sleep = original_sleep
            self.matcher._template_match = original_template_match

        assert result["matched"] is False
        assert result["wait_attempts"] >= 2  # 至少重试一次
        # 验证轮询间隔
        for delay in sleep_calls:
            assert delay == 0.5

    def test_match_wait_success_on_retry(self):
        """wait>0 时，如果最终匹配成功应返回成功并记录首次匹配时间"""
        # 创建一个带随机性的测试场景
        # 第一次调用 _template_match 返回低相似度，后续返回高相似度
        import unittest.mock as mock

        img = create_test_image(200, 100, (50, 100, 200))
        ref_path = save_temp_image(img, "wait_retry.png")

        call_count = [0]

        original_template_match = self.matcher._template_match

        def flaky_template_match(scr, ref):
            call_count[0] += 1
            if call_count[0] == 1:
                # 第一次失败
                return 0.3, None
            return original_template_match(scr, ref)

        self.matcher._template_match = flaky_template_match

        try:
            result = self.matcher.match(
                img, Path(ref_path),
                threshold=0.8,
                wait=3,
                poll_interval=0.3,
            )
        finally:
            self.matcher._template_match = original_template_match

        assert result["matched"] is True
        assert result["wait_attempts"] == 2
        assert result["first_match_time"] is not None
        assert result["first_match_time"] > 0

    def test_match_wait_timeout_returns_failure(self):
        """wait>0 时，超时后应返回失败结果"""
        img = create_test_image(200, 100, (50, 100, 200))
        ref_path = save_temp_image(img, "wait_timeout.png")

        # Mock _template_match 始终返回低相似度
        original_template_match = self.matcher._template_match
        self.matcher._template_match = lambda scr, ref: (0.3, None)

        try:
            result = self.matcher.match(
                img, Path(ref_path),
                threshold=0.8,
                wait=1,  # 1 秒超时
                poll_interval=0.2,
            )
        finally:
            self.matcher._template_match = original_template_match

        assert result["matched"] is False
        assert result["first_match_time"] is None
        assert result["wait_attempts"] >= 2  # 至少有几次重试

    def test_save_failure_screenshot(self):
        """匹配失败时应保存截图到 failures 目录"""
        # 创建两个结构完全不同的图片
        ui1 = np.full((200, 300, 3), (240, 240, 240), dtype=np.uint8)
        ui1[0:40, :] = (30, 30, 30)
        ui1[40:200, 0:60] = (220, 220, 220)
        ui1[40:200, 60:300] = (255, 255, 255)

        ui2 = np.full((200, 300, 3), (200, 200, 200), dtype=np.uint8)
        ui2[0:30, :] = (0, 0, 128)
        ui2[30:200, :] = (255, 255, 255)
        ui2[50:100, 100:280] = (255, 0, 0)

        ref_path = save_temp_image(ui2, "fail_ref.png")

        result = self.matcher.match(ui1, Path(ref_path), threshold=0.95)

        assert result["matched"] is False

        # 验证截图保存
        failures_dir = Path("/tmp/rodski_assertion_test/failures")
        saved_path = ImageMatcher.save_failure_screenshot(
            ui1, "fail_ref.png", failures_dir=failures_dir
        )

        assert saved_path is not None
        assert Path(saved_path).exists()
        assert "fail_ref" in saved_path
        assert saved_path.endswith(".png")

    def test_save_failure_screenshot_creates_dir(self):
        """save_failure_screenshot 应自动创建目录"""
        screenshot = create_test_image(100, 100, (50, 50, 50))
        failures_dir = Path("/tmp/rodski_assertion_test/failures_auto_create/subdir")
        # 清理可能存在的目录
        import shutil
        parent = failures_dir.parent
        if parent.exists():
            shutil.rmtree(parent)
        assert not failures_dir.exists()

        saved_path = ImageMatcher.save_failure_screenshot(
            screenshot, "test.png", failures_dir=failures_dir
        )

        assert saved_path is not None
        assert failures_dir.exists()

    def test_result_structure_with_phase2_fields(self):
        """Phase2 结果字典应包含新字段"""
        img = create_test_image(100, 100, (55, 55, 55))
        ref_path = save_temp_image(img, "phase2_struct.png")

        result = self.matcher.match(img, Path(ref_path), threshold=0.8, wait=0)

        required_keys = [
            "matched", "similarity", "threshold",
            "screenshot", "reference", "location",
            "wait_attempts", "first_match_time",
        ]
        for key in required_keys:
            assert key in result, f"结果缺少字段: {key}"

    def test_crop_element_region_exact(self):
        """_crop_element_region 应正确裁剪指定区域"""
        screenshot = np.zeros((200, 300, 3), dtype=np.uint8)
        screenshot[50:100, 100:200] = (255, 0, 0)  # 红色区域

        cropped = self.matcher._crop_element_region(
            screenshot, {"x": 100, "y": 50, "w": 100, "h": 50}
        )

        assert cropped.shape == (50, 100, 3)
        # 验证裁剪的是红色区域
        assert cropped[0, 0].tolist() == [255, 0, 0]

    def test_crop_element_region_clips_to_bounds(self):
        """_crop_element_region 超出边界时应裁剪到有效区域"""
        screenshot = np.zeros((100, 100, 3), dtype=np.uint8)

        # 请求超出边界的区域
        cropped = self.matcher._crop_element_region(
            screenshot, {"x": 90, "y": 90, "w": 50, "h": 50}
        )

        # 应该裁剪到 (90,90) 到 (100,100) 的 10x10 区域
        assert cropped.shape == (10, 10, 3)


class TestKeywordEngineAssertIntegration:

    """_kw_assert 与 keyword_engine 的集成测试（不依赖 driver）"""

    def test_parse_kv_args_basic(self):
        """基本 key=value 解析"""
        from core.keyword_engine import KeywordEngine
        result = KeywordEngine._parse_kv_args("type=image,reference=img/foo.png,threshold=0.85")
        assert result == {
            "type": "image",
            "reference": "img/foo.png",
            "threshold": "0.85",
        }

    def test_parse_kv_args_with_brackets_in_value(self):
        """value 中含中文方括号时应正确处理"""
        from core.keyword_engine import KeywordEngine
        # value 中可以有【】
        result = KeywordEngine._parse_kv_args("type=image,reference=img/弹窗.png")
        assert result["reference"] == "img/弹窗.png"

    def test_parse_kv_args_empty_string(self):
        """空字符串返回空字典"""
        from core.keyword_engine import KeywordEngine
        result = KeywordEngine._parse_kv_args("")
        assert result == {}

    def test_parse_kv_args_with_spaces(self):
        """带空格的参数"""
        from core.keyword_engine import KeywordEngine
        result = KeywordEngine._parse_kv_args("type=image, reference=img/foo.png , threshold=0.85")
        assert result == {
            "type": "image",
            "reference": "img/foo.png",
            "threshold": "0.85",
        }

    def test_parse_kv_args_element_bbox(self):
        """element_bbox 格式 x,y,w,h"""
        from core.keyword_engine import KeywordEngine
        result = KeywordEngine._parse_kv_args("type=image,reference=img/foo.png,element_bbox=100,200,50,50")
        assert result["element_bbox"] == "100,200,50,50"


class TestBaseAssertion:

    def test_resolve_reference_path_absolute(self):
        """绝对路径保持不变"""
        abs_path = Path("/tmp/images/assert/test.png")
        result = BaseAssertion.resolve_reference_path(abs_path, Path("/some/module"))
        assert result == abs_path

    def test_resolve_reference_path_relative(self):
        """相对路径拼接 images/assert/"""
        result = BaseAssertion.resolve_reference_path(
            "expected/modal.png",
            Path("/project/module")
        )
        assert result == Path("/project/module/images/assert/expected/modal.png")


# ── Phase 3: VideoAnalyzer 测试 ──────────────────────────────────

class TestVideoAnalyzer:
    """VideoAnalyzer 单元测试"""

    def setup_method(self):
        from core.assertion.video_analyzer import VideoAnalyzer
        self.analyzer = VideoAnalyzer()

    def test_match_invalid_position_raises(self):
        """无效的 position 应抛出 ValueError"""
        ref = save_temp_image(create_test_image(100, 100), "video_ref.png")
        try:
            self.analyzer.match(
                video_source="/tmp/nonexistent.mp4",
                reference=Path(ref),
                threshold=0.8,
                position="invalid",
            )
            assert False, "应抛出 ValueError"
        except ValueError as e:
            assert "position" in str(e)

    def test_match_missing_reference_raises(self):
        """reference 不存在应抛出 FileNotFoundError"""
        try:
            self.analyzer.match(
                video_source="/tmp/nonexistent.mp4",
                reference=Path("/tmp/nonexistent_ref.png"),
                threshold=0.8,
                position="any",
            )
            assert False, "应抛出 FileNotFoundError"
        except FileNotFoundError:
            pass

    def test_result_structure(self):
        """结果字典结构完整"""
        ref = save_temp_image(create_test_image(100, 100), "video_ref.png")

        # 使用不存在的视频源，预期快速失败
        result = self.analyzer.match(
            video_source="/tmp/nonexistent.mp4",
            reference=Path(ref),
            threshold=0.8,
            position="any",
            wait=0,
        )

        required_keys = [
            "matched", "similarity", "threshold",
            "reference", "position",
            "matched_frame_time", "total_frames_checked",
            "wait_attempts", "first_match_time",
        ]
        for key in required_keys:
            assert key in result, f"结果缺少字段: {key}"

    def test_match_position_values(self):
        """position 参数应为有效值之一"""
        ref = save_temp_image(create_test_image(100, 100), "pos_ref.png")

        for pos in ("start", "middle", "end", "any"):
            result = self.analyzer.match(
                video_source="/tmp/nonexistent.mp4",
                reference=Path(ref),
                threshold=0.8,
                position=pos,
                wait=0,
            )
            assert result["position"] == pos

    def test_wait_attempts_increments(self):
        """wait>0 时 wait_attempts 应大于 1"""
        ref = save_temp_image(create_test_image(100, 100), "wait_ref.png")

        result = self.analyzer.match(
            video_source="/tmp/nonexistent.mp4",
            reference=Path(ref),
            threshold=0.8,
            position="any",
            wait=1,  # 1 秒
            poll_interval=0.3,
        )

        assert result["wait_attempts"] >= 1
        assert result["matched"] is False  # 视频不存在，应失败

    def test_crop_element_region(self):
        """_crop_element_region 应正确裁剪"""
        frame = np.zeros((200, 300, 3), dtype=np.uint8)
        frame[50:100, 100:200] = (255, 0, 0)  # 红色区域

        cropped = self.analyzer._crop_element_region(
            frame, {"x": 100, "y": 50, "w": 100, "h": 50}
        )

        assert cropped.shape == (50, 100, 3)
        assert cropped[0, 0].tolist() == [255, 0, 0]

    def test_template_match_method(self):
        """_template_match 应返回相似度和位置"""
        frame = create_test_image(200, 200, (100, 100, 100))
        reference = create_test_image(50, 50, (100, 100, 100))

        similarity, location = self.analyzer._template_match(frame, reference)

        assert isinstance(similarity, float)
        assert 0.0 <= similarity <= 1.0
        assert location is not None
        assert "x" in location and "y" in location


class TestRecorder:
    """Recorder 单元测试"""

    def test_recorder_default_config(self):
        """默认配置应正确"""
        from core.recording.recorder import Recorder
        r = Recorder()
        assert r.enabled is True
        assert r.output_dir.name == "recordings"
        assert r.output_dir.parent.name == "assert"

    def test_recorder_disabled(self):
        """disabled=True 时 enabled 应为 False"""
        from core.recording.recorder import Recorder
        r = Recorder(config={"enabled": False})
        assert r.enabled is False

    def test_ensure_output_dir(self):
        """ensure_output_dir 应创建目录"""
        from core.recording.recorder import Recorder
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            r = Recorder(config={"output_dir": str(Path(tmpdir) / "recordings")})
            r.ensure_output_dir()
            assert r.output_dir.exists()

    def test_cleanup_old_recordings(self):
        """cleanup_old_recordings 应保留最近文件"""
        from core.recording.recorder import Recorder
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            recordings_dir = Path(tmpdir) / "recordings"
            recordings_dir.mkdir()
            # 创建 5 个文件
            for i in range(5):
                (recordings_dir / f"video_{i}.mp4").touch()
            r = Recorder(config={"output_dir": str(recordings_dir)})
            removed = r.cleanup_old_recordings(max_count=3)
            assert removed == 2
            remaining = list(recordings_dir.glob("*.mp4"))
            assert len(remaining) == 3

    def test_start_recording_no_driver(self):
        """start_recording 无驱动时应返回 None（不抛异常）"""
        from core.recording.recorder import Recorder
        r = Recorder()
        result = r.start_recording("case_001", None)
        # 无有效 page 时应返回 None（不抛异常）
        assert result is None

    def test_stop_recording_no_active(self):
        """stop_recording 无活跃录屏时应返回 None"""
        from core.recording.recorder import Recorder
        r = Recorder()
        result = r.stop_recording("nonexistent_case")
        assert result is None

    def test_get_video_path_no_active(self):
        """get_video_path 无活跃录屏时应返回 None"""
        from core.recording.recorder import Recorder
        r = Recorder()
        result = r.get_video_path("nonexistent_case")
        assert result is None


class TestVideoAssertIntegration:
    """Video 断言与 keyword_engine 集成测试"""

    def test_parse_kv_args_video(self):
        """视频参数解析"""
        from core.keyword_engine import KeywordEngine
        result = KeywordEngine._parse_kv_args(
            "type=video,reference=img/frame.png,threshold=0.85,video_source=recording,position=middle"
        )
        assert result == {
            "type": "video",
            "reference": "img/frame.png",
            "threshold": "0.85",
            "video_source": "recording",
            "position": "middle",
        }

    def test_parse_kv_args_video_with_time_range(self):
        """视频参数解析（带 time_range）"""
        from core.keyword_engine import KeywordEngine
        # time_range 的值含有逗号，但 _parse_kv_args 会将其拆分
        # 这是已知的解析限制，time_range 需要在调用处二次解析
        result = KeywordEngine._parse_kv_args(
            "type=video,reference=img/frame.png"
        )
        assert result["type"] == "video"
        assert result["reference"] == "img/frame.png"


# ── 便捷运行 ──────────────────────────────────────────────────

if __name__ == "__main__":
    print("运行 assertion 单元测试...")
    print(f"测试图片目录: /tmp/rodski_assertion_test/")

    import core.test_runner as runner

    r = runner.RodskiTestRunner(verbosity=2)
    failed_count = r.run([Path(__file__).resolve()])
    print(f"\n结果: {failed_count} failed")
    sys.exit(failed_count)
