"""iteration-66 BUG-A21 / BUG-A22：接口模型 verify 的字段范围

- A21：strict 不能要求 _verify 行包含请求字段与 `_method/_url` 等控制元素（GUIDE §8.2 示例照写即失败）
- A22：模型未声明 `status` 元素时，_verify 的 status 列也要按 HTTP 状态码比较，不能静默忽略
"""
import pytest
from unittest.mock import MagicMock

from core.exceptions import AssertionFailedError, InvalidParameterError
from core.keyword_engine import KeywordEngine
from core.model_parser import MODEL_TYPE_INTERFACE, MODEL_TYPE_UI


def _field(name):
    return {'locator_type': 'field', 'locator_value': name, 'element_type': 'field'}


def _engine(model, data_row, last_return, model_type=MODEL_TYPE_INTERFACE):
    parser = MagicMock()
    parser.get_model.return_value = {'__model_type__': model_type, **model}
    parser.get_model_type.return_value = model_type
    parser.get_model_driver_type.return_value = 'interface' if model_type == MODEL_TYPE_INTERFACE else 'web'
    data_manager = MagicMock()
    data_manager.get_data.return_value = data_row
    engine = KeywordEngine(MagicMock(), model_parser=parser, data_manager=data_manager)
    engine.store_return(last_return)
    return engine


# GUIDE §8.2：模型声明请求字段 + 控制元素 + 响应字段
LOGIN_MODEL = {
    '_method': _field('_method'),
    '_url': _field('_url'),
    'username': _field('username'),
    'password': _field('password'),
    'token': _field('token'),
}


class TestStrictOnlyRowFields:
    """A21：接口模型 strict 只比较行内字段"""

    def test_request_and_control_fields_not_required(self):
        engine = _engine(LOGIN_MODEL, {'status': '200', 'token': 'abc'},
                         {'status': 200, 'token': 'abc'})
        assert engine._batch_verify('Login', 'V001') is True

    def test_row_field_mismatch_still_fails(self):
        engine = _engine(LOGIN_MODEL, {'status': '200', 'token': 'abc'},
                         {'status': 200, 'token': 'xyz'})
        with pytest.raises(AssertionFailedError, match='token'):
            engine._batch_verify('Login', 'V001')

    def test_control_column_in_row_is_not_compared(self):
        engine = _engine(LOGIN_MODEL, {'_method': 'DELETE', 'token': 'abc'},
                         {'status': 200, 'token': 'abc'})
        assert engine._batch_verify('Login', 'V001') is True

    def test_ui_model_strict_still_requires_all_fields(self):
        model = {'a': {'locator_type': 'id', 'locator_value': 'a'},
                 'b': {'locator_type': 'id', 'locator_value': 'b'}}
        engine = _engine(model, {'a': 'x'}, None, model_type=MODEL_TYPE_UI)
        engine._auto_wait_ms = lambda: 0.0
        with pytest.raises(InvalidParameterError, match="'b'"):
            engine._batch_verify('Page', 'V001')


class TestStatusWithoutModelElement:
    """A22：status 列不依赖模型声明 status 元素"""

    @pytest.mark.parametrize('match_mode', ['strict', 'subset'])
    def test_wrong_status_fails(self, match_mode):
        engine = _engine({'token': _field('token')}, {'status': '201', 'token': 'abc'},
                         {'status': 200, 'token': 'abc'})
        with pytest.raises(AssertionFailedError, match='status'):
            engine._batch_verify('Login', 'V001', match_mode)

    @pytest.mark.parametrize('match_mode', ['strict', 'subset'])
    def test_matching_status_passes(self, match_mode):
        engine = _engine({'token': _field('token')}, {'status': '200', 'token': 'abc'},
                         {'status': 200, 'token': 'abc'})
        assert engine._batch_verify('Login', 'V001', match_mode) is True

    def test_undeclared_non_status_column_skipped(self):
        """CORE §4.7.4：未在模型中声明的其他列跳过"""
        engine = _engine({'token': _field('token')}, {'token': 'abc', 'ghost': 'x'},
                         {'status': 200, 'token': 'abc'})
        assert engine._batch_verify('Login', 'V001', 'subset') is True


class TestNoneSkipsVerify:
    """A15：接口 / DB verify 中 NONE 跳过该字段（CORE §4.1），不当作期望字符串 "none" """

    def test_interface_none_skipped(self):
        engine = _engine({'token': _field('token'), 'text': _field('text')},
                         {'token': 'abc', 'text': 'NONE'}, {'status': 200, 'token': 'abc', 'text': 'hello'})
        assert engine._batch_verify('Login', 'V001') is True

    def test_interface_null_still_expects_null(self):
        engine = _engine({'text': _field('text')}, {'text': 'NULL'}, {'status': 200, 'text': 'hello'})
        with pytest.raises(AssertionFailedError, match='text'):
            engine._batch_verify('Login', 'V001')

    def test_db_none_skipped_even_if_column_missing(self):
        from core.model_parser import MODEL_TYPE_DATABASE
        engine = _engine({'n': _field('n')}, {'n': '1', 'remark': 'NONE', 'other': 'none'},
                         {'n': 1, 'other': 'none'}, model_type=MODEL_TYPE_DATABASE)
        assert engine._batch_verify('Q', 'V001') is True
