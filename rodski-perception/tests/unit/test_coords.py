"""单元测试 — coords.py 坐标转换 + Qwen 响应解析。"""

from __future__ import annotations

import pytest

from rodski_perception.coords import (
    bbox_center,
    bbox_to_pixels,
    clamp_bbox_normalized,
    parse_qwen_response,
)
from rodski_perception.errors import InvalidResponseError


# ----------------------------------------------------------------------
# parse_qwen_response
# ----------------------------------------------------------------------


class TestParseQwenResponse:
    def test_plain_json_array(self):
        items = parse_qwen_response('[{"bbox_2d":[10,20,30,40],"label":"btn"}]')
        assert len(items) == 1
        assert items[0]["bbox_2d"] == [10, 20, 30, 40]
        assert items[0]["label"] == "btn"

    def test_markdown_fence(self):
        text = '```json\n[{"bbox_2d":[1,2,3,4],"label":"x"}]\n```'
        items = parse_qwen_response(text)
        assert len(items) == 1
        assert items[0]["bbox_2d"] == [1, 2, 3, 4]

    def test_with_prose_around(self):
        text = (
            "Sure! Here is the JSON:\n"
            '[{"bbox_2d":[100,200,300,400],"label":"login"}]\n'
            "Hope this helps."
        )
        items = parse_qwen_response(text)
        assert items[0]["bbox_2d"] == [100, 200, 300, 400]

    def test_results_key_wrapper(self):
        text = '{"results":[{"bbox_2d":[5,6,7,8],"label":"a"}]}'
        items = parse_qwen_response(text)
        assert items[0]["bbox_2d"] == [5, 6, 7, 8]

    def test_single_object(self):
        text = '{"bbox_2d":[1,1,2,2],"label":"only"}'
        items = parse_qwen_response(text)
        assert items[0]["label"] == "only"

    def test_multiple_items_with_index(self):
        text = (
            '[{"index":0,"bbox_2d":[1,2,3,4],"label":"a"},'
            '{"index":1,"bbox_2d":[5,6,7,8],"label":"b"}]'
        )
        items = parse_qwen_response(text)
        assert len(items) == 2
        # index 透传到 raw
        assert items[0]["raw"]["index"] == 0
        assert items[1]["raw"]["index"] == 1

    def test_float_coords_rounded(self):
        items = parse_qwen_response('[{"bbox_2d":[1.4, 2.6, 3.5, 4.5]}]')
        assert items[0]["bbox_2d"] == [1, 3, 4, 4]

    def test_missing_bbox_filtered(self):
        with pytest.raises(InvalidResponseError):
            parse_qwen_response('[{"label":"no bbox"}]')

    def test_empty_string_raises(self):
        with pytest.raises(InvalidResponseError):
            parse_qwen_response("")

    def test_unparseable_text(self):
        with pytest.raises(InvalidResponseError):
            parse_qwen_response("nothing parseable here at all")

    def test_confidence_field_optional(self):
        items = parse_qwen_response('[{"bbox_2d":[1,2,3,4],"confidence":0.87}]')
        assert items[0]["confidence"] == 0.87


# ----------------------------------------------------------------------
# clamp_bbox_normalized
# ----------------------------------------------------------------------


class TestClamp:
    def test_within_range(self):
        assert clamp_bbox_normalized((10, 20, 30, 40)) == (10, 20, 30, 40)

    def test_out_of_upper_bound(self):
        assert clamp_bbox_normalized((1200, 50, 1500, 200)) == (1000, 50, 1000, 200)

    def test_negative_clamped(self):
        assert clamp_bbox_normalized((-10, -5, 100, 100)) == (0, 0, 100, 100)

    def test_swap_when_inverted(self):
        # x1>x2 / y1>y2 应被换序
        assert clamp_bbox_normalized((300, 400, 100, 200)) == (100, 200, 300, 400)


# ----------------------------------------------------------------------
# bbox_to_pixels
# ----------------------------------------------------------------------


class TestBboxToPixels:
    def test_full_canvas(self):
        # 0-1000 千分比 → 0-(w,h) 像素
        assert bbox_to_pixels((0, 0, 1000, 1000), (800, 600)) == (0, 0, 800, 600)

    def test_quarter(self):
        # 500/1000 = 0.5
        assert bbox_to_pixels((500, 500, 750, 750), (800, 600)) == (400, 300, 600, 450)

    def test_rounding(self):
        # 333/1000 * 800 = 266.4 → 266
        bbox = bbox_to_pixels((333, 333, 666, 666), (800, 600))
        assert bbox == (266, 200, 533, 400)


# ----------------------------------------------------------------------
# bbox_center
# ----------------------------------------------------------------------


class TestBboxCenter:
    def test_simple(self):
        assert bbox_center((0, 0, 100, 100)) == (50, 50)

    def test_uneven(self):
        assert bbox_center((10, 20, 30, 40)) == (20, 30)

    def test_integer_division(self):
        # (1+4)/2 = 2 (整数除法)
        assert bbox_center((1, 2, 4, 6)) == (2, 4)
