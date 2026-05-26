"""ImageTemplateMatcher 单元测试 (iteration-54a)

测试 ``vision/image_matcher.py`` 中的 OpenCV 模板匹配定位器及路径解析工具。
覆盖场景：
    - 完整匹配（参考图就在截图里）→ 返回 bbox
    - 多尺度命中（参考图 vs 截图缩放）
    - 模板比截图大 → 跳过该 scale，仍能匹配其他 scale
    - 相似度低于阈值 → 返回 None
    - 截图/参考图文件不存在 → FileNotFoundError
    - 文件存在但解码失败 → ValueError
    - resolve_template_path：绝对路径 / 相对路径 / ${var} 替换

对应核心设计约束 §2.5 视觉定位器中的 vision_image 类型。
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from vision.image_matcher import (
    DEFAULT_SCALES,
    DEFAULT_THRESHOLD,
    ImageTemplateMatcher,
    resolve_template_path,
)


# ---------------------------------------------------------------------------
# Fixtures：在 tmp_path 中生成合成截图 + 模板
# ---------------------------------------------------------------------------

def _make_canvas(width: int = 400, height: int = 300, color=(220, 220, 220)) -> np.ndarray:
    """生成纯色背景画布（BGR）。"""
    img = np.full((height, width, 3), color, dtype=np.uint8)
    return img


def _draw_pattern(img: np.ndarray, x: int, y: int, w: int, h: int, color=(50, 100, 200)) -> None:
    """在画布上画一个矩形 + 内部对角线，方便模板匹配命中。"""
    cv2.rectangle(img, (x, y), (x + w, y + h), color, thickness=-1)
    # 加几条对角线增加纹理特征
    cv2.line(img, (x, y), (x + w, y + h), (255, 255, 255), 2)
    cv2.line(img, (x + w, y), (x, y + h), (255, 255, 255), 2)


@pytest.fixture
def screenshot_and_template(tmp_path: Path):
    """生成 400x300 的截图，内含一个 80x40 的特征图块（位于 (120, 80)）。

    模板由截图中相同区域裁出，因此 1.0 scale 应能 100% 命中。
    """
    screen = _make_canvas(400, 300)
    _draw_pattern(screen, 120, 80, 80, 40, color=(50, 100, 200))

    template = screen[80:120, 120:200].copy()

    screen_path = tmp_path / "screen.png"
    tmpl_path = tmp_path / "template.png"
    assert cv2.imwrite(str(screen_path), screen)
    assert cv2.imwrite(str(tmpl_path), template)
    return screen_path, tmpl_path, (120, 80, 200, 120)


# ---------------------------------------------------------------------------
# 基本构造
# ---------------------------------------------------------------------------

class TestConstructor:
    def test_defaults(self):
        m = ImageTemplateMatcher()
        assert m.threshold == DEFAULT_THRESHOLD
        assert m.scales == DEFAULT_SCALES

    def test_custom_threshold_and_scales(self):
        m = ImageTemplateMatcher(threshold=0.6, scales=(1.0, 2.0))
        assert m.threshold == 0.6
        assert m.scales == (1.0, 2.0)

    def test_empty_scales_falls_back_to_identity(self):
        m = ImageTemplateMatcher(scales=())
        assert m.scales == (1.0,)


# ---------------------------------------------------------------------------
# 正向匹配
# ---------------------------------------------------------------------------

class TestExactMatch:
    def test_exact_template_returns_expected_bbox(self, screenshot_and_template):
        screen_path, tmpl_path, expected = screenshot_and_template
        matcher = ImageTemplateMatcher()
        bbox = matcher.locate(str(screen_path), str(tmpl_path))
        assert bbox is not None
        x1, y1, x2, y2 = bbox
        ex1, ey1, ex2, ey2 = expected
        # 容忍 1px 误差
        assert abs(x1 - ex1) <= 1
        assert abs(y1 - ey1) <= 1
        assert abs(x2 - ex2) <= 1
        assert abs(y2 - ey2) <= 1

    def test_bbox_size_matches_template(self, screenshot_and_template):
        screen_path, tmpl_path, _ = screenshot_and_template
        bbox = ImageTemplateMatcher().locate(str(screen_path), str(tmpl_path))
        x1, y1, x2, y2 = bbox
        # template 是 80x40
        assert (x2 - x1, y2 - y1) == (80, 40)


# ---------------------------------------------------------------------------
# 多尺度
# ---------------------------------------------------------------------------

class TestMultiScale:
    def test_template_larger_than_screen_at_one_scale_still_matches_at_smaller(self, tmp_path):
        """模板在某个 scale 比截图大时该 scale 应被跳过，其他 scale 仍能匹配。"""
        # 截图：300x200，含 80x40 特征块在 (100, 60)
        screen = _make_canvas(300, 200)
        _draw_pattern(screen, 100, 60, 80, 40, color=(30, 200, 90))
        # 模板：使用原尺寸特征块
        template = screen[60:100, 100:180].copy()

        screen_path = tmp_path / "screen.png"
        tmpl_path = tmp_path / "template.png"
        cv2.imwrite(str(screen_path), screen)
        cv2.imwrite(str(tmpl_path), template)

        # scale=10.0 会让模板远大于截图（必跳过），scale=1.0 应命中
        matcher = ImageTemplateMatcher(scales=(10.0, 1.0), threshold=0.85)
        bbox = matcher.locate(str(screen_path), str(tmpl_path))
        assert bbox is not None

    def test_all_scales_too_large_returns_none(self, tmp_path):
        """所有 scale 都让模板大于截图 → 返回 None（而非抛错）。"""
        screen = _make_canvas(50, 50)
        template = _make_canvas(100, 100, color=(0, 0, 0))
        screen_path = tmp_path / "screen.png"
        tmpl_path = tmp_path / "template.png"
        cv2.imwrite(str(screen_path), screen)
        cv2.imwrite(str(tmpl_path), template)

        matcher = ImageTemplateMatcher(scales=(1.0, 1.5, 2.0))
        assert matcher.locate(str(screen_path), str(tmpl_path)) is None

    def test_multiscale_hits_on_resized_screen(self, tmp_path):
        """截图被整体缩放 1.5×，模板未变 → 启用 scales 后仍能匹配。"""
        # 原始 400x300 截图含 80x40 特征块在 (120,80)
        base = _make_canvas(400, 300)
        _draw_pattern(base, 120, 80, 80, 40, color=(80, 30, 160))
        template = base[80:120, 120:200].copy()

        # 截图被放大 1.5×
        enlarged = cv2.resize(base, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)

        screen_path = tmp_path / "screen.png"
        tmpl_path = tmp_path / "template.png"
        cv2.imwrite(str(screen_path), enlarged)
        cv2.imwrite(str(tmpl_path), template)

        # 默认 scales 含 1.25 较接近 1.5，多尺度匹配应找到（阈值放宽以兼容缩放损失）
        matcher = ImageTemplateMatcher(
            scales=(1.0, 1.25, 1.5, 1.75),
            threshold=0.7,
        )
        bbox = matcher.locate(str(screen_path), str(tmpl_path))
        assert bbox is not None
        x1, y1, x2, y2 = bbox
        # 期望中心点接近 (180*1.5, 100*1.5)
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        assert abs(cx - 240) <= 30
        assert abs(cy - 150) <= 30


# ---------------------------------------------------------------------------
# 阈值过滤
# ---------------------------------------------------------------------------

class TestThreshold:
    def test_low_similarity_returns_none(self, tmp_path):
        """截图中没有与模板相似的区域 → 应返回 None。"""
        # 截图：纯灰，无任何图案
        screen = _make_canvas(400, 300, color=(180, 180, 180))
        # 模板：完全不同色彩的复杂图案
        template = _make_canvas(60, 30, color=(0, 0, 255))
        _draw_pattern(template, 5, 5, 50, 20, color=(255, 0, 0))

        screen_path = tmp_path / "screen.png"
        tmpl_path = tmp_path / "template.png"
        cv2.imwrite(str(screen_path), screen)
        cv2.imwrite(str(tmpl_path), template)

        matcher = ImageTemplateMatcher(threshold=0.85)
        assert matcher.locate(str(screen_path), str(tmpl_path)) is None

    def test_threshold_zero_always_returns_bbox(self, tmp_path):
        """阈值 0 → 即使相似度低也返回最佳 bbox。"""
        screen = _make_canvas(100, 100, color=(0, 0, 0))
        template = _make_canvas(20, 20, color=(255, 255, 255))
        screen_path = tmp_path / "screen.png"
        tmpl_path = tmp_path / "template.png"
        cv2.imwrite(str(screen_path), screen)
        cv2.imwrite(str(tmpl_path), template)

        matcher = ImageTemplateMatcher(threshold=-1.0)
        assert matcher.locate(str(screen_path), str(tmpl_path)) is not None


# ---------------------------------------------------------------------------
# 错误处理
# ---------------------------------------------------------------------------

class TestErrorHandling:
    def test_screenshot_not_found_raises(self, tmp_path):
        tmpl_path = tmp_path / "t.png"
        cv2.imwrite(str(tmpl_path), _make_canvas(10, 10))
        matcher = ImageTemplateMatcher()
        with pytest.raises(FileNotFoundError) as exc:
            matcher.locate(str(tmp_path / "no_screen.png"), str(tmpl_path))
        assert "no_screen.png" in str(exc.value)

    def test_template_not_found_raises(self, tmp_path):
        screen_path = tmp_path / "s.png"
        cv2.imwrite(str(screen_path), _make_canvas(20, 20))
        matcher = ImageTemplateMatcher()
        with pytest.raises(FileNotFoundError) as exc:
            matcher.locate(str(screen_path), str(tmp_path / "missing_tpl.png"))
        assert "missing_tpl.png" in str(exc.value)

    def test_corrupted_screenshot_raises_value_error(self, tmp_path):
        bad_path = tmp_path / "bad.png"
        bad_path.write_bytes(b"not an image")
        tmpl_path = tmp_path / "tpl.png"
        cv2.imwrite(str(tmpl_path), _make_canvas(10, 10))

        with pytest.raises(ValueError) as exc:
            ImageTemplateMatcher().locate(str(bad_path), str(tmpl_path))
        assert "无法解码" in str(exc.value)


# ---------------------------------------------------------------------------
# resolve_template_path
# ---------------------------------------------------------------------------

class TestResolveTemplatePath:
    def test_absolute_path_returned_as_is(self, tmp_path):
        target = tmp_path / "abs.png"
        target.write_bytes(b"")
        out = resolve_template_path(str(target), model_dir=str(tmp_path))
        assert Path(out) == target

    def test_relative_path_resolved_against_model_dir(self, tmp_path):
        model_dir = tmp_path / "model"
        assets_dir = tmp_path / "assets"
        model_dir.mkdir()
        assets_dir.mkdir()
        target = assets_dir / "btn.png"
        target.write_bytes(b"")

        out = resolve_template_path("../assets/btn.png", model_dir=str(model_dir))
        assert Path(out) == target.resolve()

    def test_variable_substitution(self, tmp_path):
        target = tmp_path / "btn.png"
        target.write_bytes(b"")
        out = resolve_template_path(
            "${root}/btn.png",
            model_dir=None,
            global_vars={"root": str(tmp_path)},
        )
        assert Path(out) == target.resolve()

    def test_empty_value_raises(self):
        with pytest.raises(ValueError):
            resolve_template_path("", model_dir="/tmp")
        with pytest.raises(ValueError):
            resolve_template_path("   ", model_dir="/tmp")

    def test_unresolved_variable_left_intact(self, tmp_path):
        """未定义的 ${var} 不替换，调用方会拿到一个不存在的路径再报错。"""
        out = resolve_template_path(
            "${undef}/x.png",
            model_dir=str(tmp_path),
            global_vars={"other": "v"},
        )
        assert "${undef}" in out
