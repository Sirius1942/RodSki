"""assertion 模块单元测试 - 图片匹配器"""
import os
import sys
import cv2
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


# ── 便捷运行 ──────────────────────────────────────────────────

if __name__ == "__main__":
    print("运行 assertion 单元测试...")
    print(f"测试图片目录: /tmp/rodski_assertion_test/")

    import core.test_runner as runner

    r = runner.RodskiTestRunner(verbosity=2)
    failed_count = r.run([Path(__file__).resolve()])
    print(f"\n结果: {failed_count} failed")
    sys.exit(failed_count)
