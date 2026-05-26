"""单元测试 — prompts.py prompt 模板生成。"""

from __future__ import annotations

import pytest

from rodski_perception.prompts import (
    build_locate_many_prompt,
    build_locate_prompt,
    build_parse_prompt,
)


class TestLocatePrompt:
    def test_includes_description(self):
        p = build_locate_prompt("登录按钮")
        assert "登录按钮" in p

    def test_specifies_json_format(self):
        p = build_locate_prompt("submit")
        assert "JSON" in p
        assert "bbox_2d" in p

    def test_specifies_1000_scale(self):
        p = build_locate_prompt("submit")
        assert "0-1000" in p

    def test_element_type_button(self):
        p = build_locate_prompt("登录", element_type="button")
        assert "button" in p.lower()

    def test_element_type_icon(self):
        p = build_locate_prompt("搜索", element_type="icon")
        # icon 类型有 "icon-only" / "label" 的特殊 hint
        assert "icon" in p.lower()

    def test_unknown_element_type_still_injected(self):
        p = build_locate_prompt("foo", element_type="custom_widget")
        assert "custom_widget" in p

    def test_no_element_type_no_hint(self):
        p = build_locate_prompt("submit")
        assert "Hint:" not in p

    def test_empty_description_raises(self):
        with pytest.raises(ValueError):
            build_locate_prompt("")
        with pytest.raises(ValueError):
            build_locate_prompt("   ")


class TestLocateManyPrompt:
    def test_lists_all_prompts(self):
        p = build_locate_many_prompt(["a", "b", "c"])
        assert "a" in p
        assert "b" in p
        assert "c" in p

    def test_numbered_targets(self):
        p = build_locate_many_prompt(["foo", "bar"])
        assert "0. foo" in p
        assert "1. bar" in p

    def test_includes_index_field_instruction(self):
        p = build_locate_many_prompt(["x", "y"])
        assert "index" in p

    def test_with_element_type(self):
        p = build_locate_many_prompt(["a", "b"], element_type="input")
        assert "input" in p.lower()

    def test_empty_list_raises(self):
        with pytest.raises(ValueError):
            build_locate_many_prompt([])

    def test_empty_item_raises(self):
        with pytest.raises(ValueError):
            build_locate_many_prompt(["a", "", "c"])


class TestParsePrompt:
    def test_specifies_kinds(self):
        p = build_parse_prompt()
        assert "button" in p
        assert "input" in p
        assert "kind" in p

    def test_no_specific_description(self):
        p = build_parse_prompt()
        assert "ALL" in p
