"""T42-002: type/verify 缺失字段必须报错，不允许静默跳过

测试场景：
- type 批量输入时，模型元素在数据行中缺失 → 报错
- type 批量输入时，字段值为 BLANK → 跳过（不报错）
- verify 批量验证时，字段在验证数据行中缺失 → 报错
- verify 批量验证时，所有字段都被跳过导致比较数为 0 → 报错
- verify 批量验证时，字段值为 NONE → 跳过（不报错）
"""
import pytest
from unittest.mock import MagicMock
from core.keyword_engine import KeywordEngine
from core.exceptions import InvalidParameterError, AssertionFailedError
from core.model_parser import MODEL_TYPE_UI


def _make_engine_with_model_and_data(model_dict, data_dict, model_type=MODEL_TYPE_UI):
    """构建带 mock model_parser 和 data_manager 的 KeywordEngine"""
    driver = MagicMock()
    driver.type_locator.return_value = True
    driver.get_text_locator.return_value = ""

    model_parser = MagicMock()
    model_parser.get_model.return_value = model_dict
    model_parser.get_model_type.return_value = model_type
    model_parser.get_model_driver_type.return_value = "web"

    data_manager = MagicMock()
    data_manager.get_data.return_value = data_dict

    engine = KeywordEngine(driver, model_parser=model_parser, data_manager=data_manager)
    return engine


class TestTypeMissingField:
    """type 批量输入 - 缺失字段报错"""

    def test_missing_field_raises_error(self):
        """模型有 username 和 password，数据行只有 username → 报错"""
        model = {
            'username': {'locator_type': 'id', 'locator_value': 'user', 'locations': []},
            'password': {'locator_type': 'id', 'locator_value': 'pass', 'locations': []},
        }
        data_row = {'username': 'admin'}  # password 缺失

        engine = _make_engine_with_model_and_data(model, data_row)

        with pytest.raises(InvalidParameterError, match="模型元素 'password' 在数据行 'L001' 中缺少对应字段"):
            engine.execute("type", {"model": "LoginPage", "data": "L001"})

    def test_blank_field_skips_no_error(self):
        """字段值为 BLANK → 跳过输入，不报错"""
        model = {
            'username': {'locator_type': 'id', 'locator_value': 'user', 'locations': []},
            'password': {'locator_type': 'id', 'locator_value': 'pass', 'locations': []},
        }
        data_row = {'username': 'admin', 'password': 'BLANK'}

        engine = _make_engine_with_model_and_data(model, data_row)

        # BLANK 字段不应报错，type 正常完成
        result = engine.execute("type", {"model": "LoginPage", "data": "L001"})
        assert result is True


class TestVerifyMissingField:
    """verify 批量验证 - 缺失字段报错"""

    def test_missing_field_raises_error(self):
        """模型有 status 和 message，验证数据行只有 status → 报错"""
        model = {
            'status': {'locator_type': 'id', 'locator_value': 'status', 'locations': []},
            'message': {'locator_type': 'id', 'locator_value': 'msg', 'locations': []},
        }
        data_row = {'status': 'OK'}  # message 缺失

        engine = _make_engine_with_model_and_data(model, data_row)

        with pytest.raises(InvalidParameterError, match="字段 'message' 在验证数据行 'V001' 中缺失"):
            engine.execute("verify", {"model": "ResultPage", "data": "V001"})

    def test_zero_compared_fields_raises_error(self):
        """所有字段值为 BLANK（UI 模式跳过验证），导致比较数为 0 → 报错"""
        model = {
            'status': {'locator_type': 'id', 'locator_value': 'status', 'locations': []},
            'message': {'locator_type': 'id', 'locator_value': 'msg', 'locations': []},
        }
        # 所有字段都是 BLANK，UI 模式下全部跳过
        data_row = {'status': 'BLANK', 'message': 'BLANK'}

        engine = _make_engine_with_model_and_data(model, data_row)

        with pytest.raises(AssertionFailedError, match="比较字段数为 0，不允许空校验通过"):
            engine.execute("verify", {"model": "ResultPage", "data": "V001"})

    def test_none_field_skips_no_error(self):
        """字段值为 NONE（UI 模式）→ 跳过验证，但其他字段正常比较则不报错"""
        model = {
            'status': {'locator_type': 'id', 'locator_value': 'status', 'locations': []},
            'message': {'locator_type': 'id', 'locator_value': 'msg', 'locations': []},
        }
        data_row = {'status': 'OK', 'message': 'NONE'}

        driver = MagicMock()
        driver.get_text_locator.return_value = "OK"

        model_parser = MagicMock()
        model_parser.get_model.return_value = model
        model_parser.get_model_type.return_value = MODEL_TYPE_UI
        model_parser.get_model_driver_type.return_value = "web"

        data_manager = MagicMock()
        data_manager.get_data.return_value = data_row

        engine = KeywordEngine(driver, model_parser=model_parser, data_manager=data_manager)

        # NONE 字段跳过，status 正常比较 → 通过
        result = engine.execute("verify", {"model": "ResultPage", "data": "V001"})
        assert result is True
