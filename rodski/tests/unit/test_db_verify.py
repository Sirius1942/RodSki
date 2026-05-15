"""T42-004: DB verify 由 _verify 数据行字段驱动比较

核心逻辑：
- DB 模型只存 __queries__，无普通 element 字段
- verify 应遍历 _verify 数据行字段（排除 __* 元字段）
- 实际值来自 Return[-1]（查询结果）
- 若 Return[-1] 是 list，自动取第一项（设计决策 D2）
- 失败条件：查询结果为空、字段缺失、0 字段比较
"""
import pytest
from unittest.mock import MagicMock
from core.keyword_engine import KeywordEngine
from core.exceptions import AssertionFailedError, InvalidParameterError
from core.model_parser import MODEL_TYPE_DATABASE


def _make_db_engine(data_row, return_value):
    """构造 DB 模型的 verify 引擎

    Args:
        data_row: _verify 数据行（期望值）
        return_value: 模拟的 Return[-1]（查询结果）
    """
    mock_driver = MagicMock()
    mock_model_parser = MagicMock()
    mock_model_parser.get_model.return_value = {
        '__model_type__': MODEL_TYPE_DATABASE,
        '__driver_type__': None,
        '__connection__': 'test_db',
        '__queries__': {'select_user': 'SELECT * FROM users WHERE id=1'},
    }
    mock_model_parser.get_model_type.return_value = MODEL_TYPE_DATABASE
    mock_model_parser.get_model_driver_type.return_value = 'database'

    mock_data_manager = MagicMock()
    mock_data_manager.get_data.return_value = data_row

    engine = KeywordEngine(
        mock_driver,
        model_parser=mock_model_parser,
        data_manager=mock_data_manager,
    )
    # 模拟上一步 DB 查询返回
    if return_value is not None:
        engine.store_return(return_value)
    return engine


# ── 正常匹配 ──────────────────────────────────────────────────────

class TestDbVerifyNormalMatch:
    """字段值匹配 → 验证通过"""

    def test_single_field_match(self):
        data_row = {'username': 'alice'}
        result = {'username': 'alice', 'age': '30'}
        engine = _make_db_engine(data_row, result)

        assert engine._batch_verify_db(data_row, 'UserDB') is True

    def test_multiple_fields_match(self):
        data_row = {'username': 'alice', 'status': 'active'}
        result = {'username': 'alice', 'status': 'active', 'id': '1'}
        engine = _make_db_engine(data_row, result)

        assert engine._batch_verify_db(data_row, 'UserDB') is True

    def test_skips_dunder_fields_in_data_row(self):
        """data_row 中的 __* 字段应被跳过"""
        data_row = {'__data_id__': 'V001', 'username': 'alice'}
        result = {'username': 'alice'}
        engine = _make_db_engine(data_row, result)

        assert engine._batch_verify_db(data_row, 'UserDB') is True


# ── 值不匹配 ──────────────────────────────────────────────────────

class TestDbVerifyMismatch:
    """字段值不匹配 → 抛出 AssertionFailedError"""

    def test_single_field_mismatch(self):
        data_row = {'username': 'alice'}
        result = {'username': 'bob'}
        engine = _make_db_engine(data_row, result)

        with pytest.raises(AssertionFailedError) as exc_info:
            engine._batch_verify_db(data_row, 'UserDB')
        assert '批量验证失败' in str(exc_info.value)
        assert 'username' in str(exc_info.value)

    def test_mismatch_shows_expected_and_actual(self):
        data_row = {'age': '25'}
        result = {'age': '30'}
        engine = _make_db_engine(data_row, result)

        with pytest.raises(AssertionFailedError) as exc_info:
            engine._batch_verify_db(data_row, 'UserDB')
        msg = str(exc_info.value)
        assert "期望='25'" in msg
        assert "实际='30'" in msg


# ── 字段缺失 ──────────────────────────────────────────────────────

class TestDbVerifyMissingField:
    """查询结果中缺少期望字段 → 立即失败"""

    def test_missing_field_raises(self):
        data_row = {'email': 'alice@test.com'}
        result = {'username': 'alice'}  # 没有 email 字段
        engine = _make_db_engine(data_row, result)

        with pytest.raises(AssertionFailedError) as exc_info:
            engine._batch_verify_db(data_row, 'UserDB')
        assert "缺少字段 'email'" in str(exc_info.value)


# ── 查询结果为空 ──────────────────────────────────────────────────

class TestDbVerifyEmptyResult:
    """查询结果为空 → 立即失败"""

    def test_none_result_raises(self):
        data_row = {'username': 'alice'}
        engine = _make_db_engine(data_row, None)
        # Return stack is empty, get_return(-1) returns None
        engine._return_stack = []

        with pytest.raises(AssertionFailedError) as exc_info:
            engine._batch_verify_db(data_row, 'UserDB')
        assert "查询结果为空" in str(exc_info.value)

    def test_empty_list_result_raises(self):
        data_row = {'username': 'alice'}
        engine = _make_db_engine(data_row, [])

        with pytest.raises(AssertionFailedError) as exc_info:
            engine._batch_verify_db(data_row, 'UserDB')
        assert "查询结果为空" in str(exc_info.value)


# ── 0 字段比较 ────────────────────────────────────────────────────

class TestDbVerifyZeroFields:
    """所有字段都是 __* 或 BLANK → 0 字段比较 → 失败"""

    def test_all_dunder_fields_raises(self):
        data_row = {'__data_id__': 'V001', '__table__': 'users'}
        result = {'username': 'alice'}
        engine = _make_db_engine(data_row, result)

        with pytest.raises(AssertionFailedError) as exc_info:
            engine._batch_verify_db(data_row, 'UserDB')
        assert "比较字段数为 0" in str(exc_info.value)

    def test_all_blank_fields_raises(self):
        data_row = {'username': 'BLANK', 'status': 'BLANK'}
        result = {'username': 'alice', 'status': 'active'}
        engine = _make_db_engine(data_row, result)

        with pytest.raises(AssertionFailedError) as exc_info:
            engine._batch_verify_db(data_row, 'UserDB')
        assert "比较字段数为 0" in str(exc_info.value)


# ── list 结果自动取第一项 ─────────────────────────────────────────

class TestDbVerifyListAutoFirst:
    """Return[-1] 是 list 时，自动取 [0]（设计决策 D2）"""

    def test_list_result_takes_first_item(self):
        data_row = {'username': 'alice'}
        result = [{'username': 'alice', 'id': '1'}, {'username': 'bob', 'id': '2'}]
        engine = _make_db_engine(data_row, result)

        assert engine._batch_verify_db(data_row, 'UserDB') is True

    def test_list_result_mismatch_uses_first_item(self):
        data_row = {'username': 'bob'}
        result = [{'username': 'alice'}, {'username': 'bob'}]
        engine = _make_db_engine(data_row, result)

        with pytest.raises(AssertionFailedError) as exc_info:
            engine._batch_verify_db(data_row, 'UserDB')
        # 应该用第一项 alice 比较，而非第二项 bob
        msg = str(exc_info.value)
        assert "实际='alice'" in msg
