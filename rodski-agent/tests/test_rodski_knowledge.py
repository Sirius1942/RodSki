"""rodski_knowledge 约束知识库单元测试。

测试 src/rodski_agent/common/rodski_knowledge.py 中的常量和校验函数。
覆盖：
  - SUPPORTED_KEYWORDS 数量与内容
  - LOCATOR_TYPES 数量与内容
  - validate_action() 合法/非法 action 判断
  - validate_locator_type() 合法/非法定位器类型判断
  - validate_directory_structure() 缺失目录检测
  - validate_element_data_consistency() 字段不一致检测
  - validate_verify_table_name() 验证表名规范
  - is_ui_atomic_action() UI 原子动作识别
  - RODSKI_CONSTRAINT_SUMMARY 非空且包含关键内容
无外部依赖，无需 mock。
"""
from __future__ import annotations

import os

import pytest

from rodski_agent.common.rodski_knowledge import (
    ALL_VALID_ACTIONS,
    LOCATOR_TYPES,
    RODSKI_CONSTRAINT_SUMMARY,
    RODSKI_KEYWORD_REFERENCE,
    SUPPORTED_KEYWORDS,
    UI_ATOMIC_ACTIONS,
    VERIFY_TABLE_SUFFIX,
    is_ui_atomic_action,
    validate_action,
    validate_directory_structure,
    validate_element_data_consistency,
    validate_locator_type,
    validate_verify_table_name,
)


class TestSupportedKeywords:
    """SUPPORTED_KEYWORDS 常量校验"""

    def test_supported_keywords_数量为15(self):
        """SUPPORTED_KEYWORDS 应包含恰好 15 个关键字。"""
        assert len(SUPPORTED_KEYWORDS) == 15

    def test_supported_keywords_包含核心关键字(self):
        """SUPPORTED_KEYWORDS 应包含 type / verify / send / navigate 等核心关键字。"""
        for kw in ("type", "verify", "send", "navigate", "close", "launch", "run", "DB"):
            assert kw in SUPPORTED_KEYWORDS, f"关键字 '{kw}' 应在 SUPPORTED_KEYWORDS 中"

    def test_supported_keywords_不包含UI原子动作(self):
        """click 等 UI 原子动作不应出现在 SUPPORTED_KEYWORDS 中。"""
        for action in ("click", "double_click", "right_click", "hover"):
            assert action not in SUPPORTED_KEYWORDS, f"'{action}' 不应作为独立关键字"

    def test_supported_keywords_所有元素为字符串(self):
        """SUPPORTED_KEYWORDS 中的每个元素应为非空字符串。"""
        for kw in SUPPORTED_KEYWORDS:
            assert isinstance(kw, str) and len(kw) > 0


class TestLocatorTypes:
    """LOCATOR_TYPES 常量校验"""

    def test_locator_types_数量为12(self):
        """LOCATOR_TYPES 应包含恰好 12 种定位器类型。"""
        assert len(LOCATOR_TYPES) == 12

    def test_locator_types_包含传统定位器(self):
        """LOCATOR_TYPES 应包含 id / css / xpath / text 等传统定位器。"""
        for loc in ("id", "class", "css", "xpath", "text", "tag", "name", "static", "field"):
            assert loc in LOCATOR_TYPES, f"定位器 '{loc}' 应在 LOCATOR_TYPES 中"

    def test_locator_types_包含视觉定位器(self):
        """LOCATOR_TYPES 应包含 vision / ocr / vision_bbox 三种视觉定位器。"""
        for loc in ("vision", "ocr", "vision_bbox"):
            assert loc in LOCATOR_TYPES, f"视觉定位器 '{loc}' 应在 LOCATOR_TYPES 中"

    def test_locator_types_所有元素为字符串(self):
        """LOCATOR_TYPES 中的每个元素应为非空字符串。"""
        for lt in LOCATOR_TYPES:
            assert isinstance(lt, str) and len(lt) > 0


class TestValidateAction:
    """validate_action() 合法性校验"""

    def test_validate_action_type_返回True(self):
        """type 是 SUPPORTED_KEYWORDS 中的关键字，应返回 True。"""
        assert validate_action("type") is True

    def test_validate_action_verify_返回True(self):
        """verify 是 SUPPORTED_KEYWORDS 中的关键字，应返回 True。"""
        assert validate_action("verify") is True

    def test_validate_action_send_返回True(self):
        """send 是 SUPPORTED_KEYWORDS 中的关键字，应返回 True。"""
        assert validate_action("send") is True

    def test_validate_action_check兼容关键字_返回True(self):
        """check 是 COMPAT_KEYWORDS 中的兼容关键字，应返回 True。"""
        assert validate_action("check") is True

    def test_validate_action_screenshot补充类型_返回True(self):
        """screenshot 是 ADDITIONAL_ACTION_TYPES 中的补充 action，应返回 True。"""
        assert validate_action("screenshot") is True

    def test_validate_action_evaluate补充类型_返回True(self):
        """evaluate 是 ADDITIONAL_ACTION_TYPES 中的补充 action，应返回 True。"""
        assert validate_action("evaluate") is True

    def test_validate_action_click_返回False(self):
        """click 是 UI 原子动作，不是独立关键字，应返回 False。"""
        assert validate_action("click") is False

    def test_validate_action_double_click_返回False(self):
        """double_click 是 UI 原子动作，不是独立关键字，应返回 False。"""
        assert validate_action("double_click") is False

    def test_validate_action_hover_返回False(self):
        """hover 是 UI 原子动作，不是独立关键字，应返回 False。"""
        assert validate_action("hover") is False

    def test_validate_action_非法字符串_返回False(self):
        """完全非法的字符串应返回 False。"""
        assert validate_action("invalid_action") is False
        assert validate_action("") is False
        assert validate_action("CLICK") is False  # 大小写敏感


class TestValidateLocatorType:
    """validate_locator_type() 合法性校验"""

    def test_validate_locator_type_css_返回True(self):
        """css 是合法定位器类型，应返回 True。"""
        assert validate_locator_type("css") is True

    def test_validate_locator_type_xpath_返回True(self):
        """xpath 是合法定位器类型，应返回 True。"""
        assert validate_locator_type("xpath") is True

    def test_validate_locator_type_id_返回True(self):
        """id 是合法定位器类型，应返回 True。"""
        assert validate_locator_type("id") is True

    def test_validate_locator_type_vision_返回True(self):
        """vision 是合法视觉定位器类型，应返回 True。"""
        assert validate_locator_type("vision") is True

    def test_validate_locator_type_ocr_返回True(self):
        """ocr 是合法视觉定位器类型，应返回 True。"""
        assert validate_locator_type("ocr") is True

    def test_validate_locator_type_invalid_返回False(self):
        """非法定位器类型字符串应返回 False。"""
        assert validate_locator_type("invalid") is False

    def test_validate_locator_type_空字符串_返回False(self):
        """空字符串应返回 False。"""
        assert validate_locator_type("") is False

    def test_validate_locator_type_大写_返回False(self):
        """大写定位器类型（如 CSS）应返回 False（区分大小写）。"""
        assert validate_locator_type("CSS") is False
        assert validate_locator_type("ID") is False


class TestValidateDirectoryStructure:
    """validate_directory_structure() 目录结构校验"""

    def test_完整结构_返回空列表(self, sample_project_dir):
        """case/model/data 三个目录都存在时应返回空列表。"""
        missing = validate_directory_structure(str(sample_project_dir))
        assert missing == []

    def test_缺少case目录_返回case(self, tmp_path):
        """只有 model/data 时应返回缺失的 'case'。"""
        (tmp_path / "model").mkdir()
        (tmp_path / "data").mkdir()
        missing = validate_directory_structure(str(tmp_path))
        assert "case" in missing
        assert "model" not in missing
        assert "data" not in missing

    def test_缺少model目录_返回model(self, tmp_path):
        """只有 case/data 时应返回缺失的 'model'。"""
        (tmp_path / "case").mkdir()
        (tmp_path / "data").mkdir()
        missing = validate_directory_structure(str(tmp_path))
        assert "model" in missing

    def test_缺少所有目录_返回全部三个(self, tmp_path):
        """三个目录都缺失时应返回包含全部三个名称的列表。"""
        missing = validate_directory_structure(str(tmp_path))
        assert set(missing) == {"case", "model", "data"}

    def test_不存在路径_返回全部三个(self):
        """传入不存在的路径时三个目录都缺失，返回包含全部三个名称。"""
        missing = validate_directory_structure("/tmp/__nonexistent_dir_xyz__")
        assert set(missing) == {"case", "model", "data"}


class TestValidateElementDataConsistency:
    """validate_element_data_consistency() 字段一致性校验"""

    def test_完全一致_返回空列表(self):
        """模型元素与数据字段完全一致时应返回空列表。"""
        model = ["username", "password", "loginBtn"]
        data = ["username", "password", "loginBtn"]
        result = validate_element_data_consistency(model, data)
        assert result == []

    def test_数据多出字段_返回多余字段(self):
        """数据表中有模型不存在的字段时应返回该字段名。"""
        model = ["username", "password"]
        data = ["username", "password", "extra_field"]
        result = validate_element_data_consistency(model, data)
        assert "extra_field" in result

    def test_模型多出字段_不报错(self):
        """模型中有数据表不存在的字段时不视为错误（模型可以有可选元素）。"""
        model = ["username", "password", "optional_field"]
        data = ["username", "password"]
        result = validate_element_data_consistency(model, data)
        assert result == []

    def test_接口保留元素_被跳过(self):
        """_method / _url 接口保留元素应被自动排除，不报错。"""
        model = ["username", "password"]
        data = ["_method", "_url", "username", "password"]
        result = validate_element_data_consistency(model, data)
        assert result == []

    def test_接口header前缀_被跳过(self):
        """_header_Authorization 等以 _header_ 开头的字段应被自动排除。"""
        model = ["username"]
        data = ["_header_Authorization", "_header_Content-Type", "username"]
        result = validate_element_data_consistency(model, data)
        assert result == []

    def test_空列表_返回空列表(self):
        """两个列表均为空时应返回空列表。"""
        assert validate_element_data_consistency([], []) == []

    def test_多个不一致字段_全部返回(self):
        """数据表中多个字段在模型中不存在时应全部返回。"""
        model = ["username"]
        data = ["username", "ghost1", "ghost2"]
        result = validate_element_data_consistency(model, data)
        assert "ghost1" in result
        assert "ghost2" in result


class TestValidateVerifyTableName:
    """validate_verify_table_name() 验证表名规范"""

    def test_合法验证表名_返回True(self):
        """LoginForm_verify 是 LoginForm 的合法验证表名，应返回 True。"""
        assert validate_verify_table_name("LoginForm", "LoginForm_verify") is True

    def test_缺少后缀_返回False(self):
        """没有 _verify 后缀的表名应返回 False。"""
        assert validate_verify_table_name("LoginForm", "LoginForm") is False

    def test_后缀不符_返回False(self):
        """_check 后缀不合规，应返回 False。"""
        assert validate_verify_table_name("LoginForm", "LoginForm_check") is False

    def test_错误前缀_返回False(self):
        """使用错误的模型名作为前缀应返回 False。"""
        assert validate_verify_table_name("LoginForm", "OtherForm_verify") is False

    def test_空字符串_返回False(self):
        """空字符串表名应返回 False。"""
        assert validate_verify_table_name("LoginForm", "") is False

    def test_不同模型名_各自合法(self):
        """对不同模型名，各自对应的 _verify 后缀均合法。"""
        assert validate_verify_table_name("UserTable", "UserTable_verify") is True
        assert validate_verify_table_name("ProductModel", "ProductModel_verify") is True


class TestIsUiAtomicAction:
    """is_ui_atomic_action() UI 原子动作识别"""

    def test_click_返回True(self):
        """'click' 是标准 UI 原子动作，应返回 True。"""
        assert is_ui_atomic_action("click") is True

    def test_double_click_返回True(self):
        """'double_click' 是标准 UI 原子动作，应返回 True。"""
        assert is_ui_atomic_action("double_click") is True

    def test_right_click_返回True(self):
        """'right_click' 是标准 UI 原子动作，应返回 True。"""
        assert is_ui_atomic_action("right_click") is True

    def test_hover_返回True(self):
        """'hover' 是标准 UI 原子动作，应返回 True。"""
        assert is_ui_atomic_action("hover") is True

    def test_scroll_返回True(self):
        """'scroll' 是标准 UI 原子动作，应返回 True。"""
        assert is_ui_atomic_action("scroll") is True

    def test_select带参_返回True(self):
        """'select【管理员】' 模式应返回 True。"""
        assert is_ui_atomic_action("select【管理员】") is True

    def test_key_press带参_返回True(self):
        """'key_press【Tab】' 模式应返回 True。"""
        assert is_ui_atomic_action("key_press【Tab】") is True

    def test_drag带参_返回True(self):
        """'drag【#drop-zone】' 模式应返回 True。"""
        assert is_ui_atomic_action("drag【#drop-zone】") is True

    def test_scroll带坐标_返回True(self):
        """'scroll【0,500】' 模式应返回 True。"""
        assert is_ui_atomic_action("scroll【0,500】") is True

    def test_普通文本_返回False(self):
        """普通文本（如用户名、密码）应返回 False。"""
        assert is_ui_atomic_action("admin") is False
        assert is_ui_atomic_action("123456") is False
        assert is_ui_atomic_action("hello world") is False

    def test_空字符串_返回False(self):
        """空字符串应返回 False。"""
        assert is_ui_atomic_action("") is False

    def test_类型关键字_返回False(self):
        """'type' 等关键字不是 UI 原子动作，应返回 False。"""
        assert is_ui_atomic_action("type") is False
        assert is_ui_atomic_action("verify") is False

    def test_含空白字符_trim后识别(self):
        """前后有空格的 'click' 在 strip 后应被识别为 UI 原子动作。"""
        assert is_ui_atomic_action("  click  ") is True


class TestRodskiConstraintSummary:
    """RODSKI_CONSTRAINT_SUMMARY 常量校验"""

    def test_constraint_summary_非空(self):
        """RODSKI_CONSTRAINT_SUMMARY 应为非空字符串。"""
        assert isinstance(RODSKI_CONSTRAINT_SUMMARY, str)
        assert len(RODSKI_CONSTRAINT_SUMMARY) > 0

    def test_constraint_summary_包含关键字规则(self):
        """RODSKI_CONSTRAINT_SUMMARY 应包含关键字规则相关内容。"""
        assert "关键字" in RODSKI_CONSTRAINT_SUMMARY

    def test_constraint_summary_包含定位器信息(self):
        """RODSKI_CONSTRAINT_SUMMARY 应包含定位器类型相关内容。"""
        assert "css" in RODSKI_CONSTRAINT_SUMMARY or "xpath" in RODSKI_CONSTRAINT_SUMMARY

    def test_constraint_summary_包含目录结构(self):
        """RODSKI_CONSTRAINT_SUMMARY 应包含目录结构约束内容。"""
        assert "case" in RODSKI_CONSTRAINT_SUMMARY
        assert "model" in RODSKI_CONSTRAINT_SUMMARY
        assert "data" in RODSKI_CONSTRAINT_SUMMARY

    def test_constraint_summary_包含15个关键字说明(self):
        """RODSKI_CONSTRAINT_SUMMARY 应提及 15 个关键字。"""
        assert "15" in RODSKI_CONSTRAINT_SUMMARY

    def test_constraint_summary_包含verify表后缀说明(self):
        """RODSKI_CONSTRAINT_SUMMARY 应包含 _verify 后缀说明。"""
        assert "_verify" in RODSKI_CONSTRAINT_SUMMARY

    def test_keyword_reference_非空(self):
        """RODSKI_KEYWORD_REFERENCE 应为非空字符串。"""
        assert isinstance(RODSKI_KEYWORD_REFERENCE, str)
        assert len(RODSKI_KEYWORD_REFERENCE) > 0
