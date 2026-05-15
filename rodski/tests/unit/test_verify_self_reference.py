"""T42-003: 非 UI 模型 _verify 禁止使用 ${Return[-1]} 自引用

核心设计约束 §4.3：接口/DB 模型的 verify 实际值自动从 Return[-1] 读取，
如果期望值也引用 ${Return[-1]}，则变成自己跟自己比较，断言永远通过（空校验）。
此测试确保这种情况直接报错，而非仅警告。

UI 模型不受影响：其实际值来自页面元素，不来自 Return[-1]。
"""
import pytest
from unittest.mock import MagicMock
from core.keyword_engine import KeywordEngine
from core.exceptions import InvalidParameterError
from core.model_parser import MODEL_TYPE_UI, MODEL_TYPE_INTERFACE, MODEL_TYPE_DATABASE


def _make_interface_engine(mock_driver, data_row):
    """构造接口模型的 verify 引擎"""
    mock_model_parser = MagicMock()
    mock_model_parser.get_model.return_value = {
        '__model_type__': MODEL_TYPE_INTERFACE,
        'status': {
            'locator_type': 'field',
            'locator_value': 'status',
            'element_type': 'field',
        },
    }
    mock_model_parser.get_model_type.return_value = MODEL_TYPE_INTERFACE
    mock_model_parser.get_model_driver_type.return_value = 'interface'
    mock_data_manager = MagicMock()
    mock_data_manager.get_data.return_value = data_row

    engine = KeywordEngine(
        mock_driver,
        model_parser=mock_model_parser,
        data_manager=mock_data_manager,
    )
    # 模拟上一步接口返回
    engine.store_return({'status': '200'})
    return engine


def _make_database_engine(mock_driver, data_row):
    """构造数据库模型的 verify 引擎"""
    mock_model_parser = MagicMock()
    mock_model_parser.get_model.return_value = {
        '__model_type__': MODEL_TYPE_DATABASE,
        'count': {
            'locator_type': 'field',
            'locator_value': 'count',
            'element_type': 'field',
        },
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
    engine.store_return({'count': '5'})
    # Mock _batch_verify_db since it's the DB-specific path (not under test here)
    engine._batch_verify_db = MagicMock(return_value=True)
    return engine


def _make_ui_engine(mock_driver, data_row):
    """构造 UI 模型的 verify 引擎"""
    mock_model_parser = MagicMock()
    mock_model_parser.get_model.return_value = {
        '__model_type__': MODEL_TYPE_UI,
        'orderNo': {
            'locator_type': 'id',
            'locator_value': 'order-id',
            'model_type': MODEL_TYPE_UI,
        },
    }
    mock_model_parser.get_model_type.return_value = MODEL_TYPE_UI
    mock_model_parser.get_model_driver_type.return_value = 'web'
    mock_data_manager = MagicMock()
    mock_data_manager.get_data.return_value = data_row

    engine = KeywordEngine(
        mock_driver,
        model_parser=mock_model_parser,
        data_manager=mock_data_manager,
    )
    engine.store_return('ORD-999')
    return engine


@pytest.fixture
def mock_driver():
    driver = MagicMock()
    driver.get_text_locator.return_value = 'ORD-999'
    return driver


# --- 接口模型：${Return[-1]} 必须报错 ---

class TestInterfaceVerifySelfReference:
    """接口模型 _verify 使用 ${Return[-1]} 应立即失败"""

    def test_interface_verify_rejects_return_ref(self, mock_driver):
        """接口 verify 期望值含 ${Return[-1]} → InvalidParameterError"""
        engine = _make_interface_engine(mock_driver, {'status': '${Return[-1]}'})
        with pytest.raises(InvalidParameterError, match="接口/DB verify"):
            engine.execute("verify", {"model": "API_Login", "data": "V001"})

    def test_interface_verify_rejects_return_ref_nested(self, mock_driver):
        """接口 verify 期望值含 ${Return[-1].field} 也应报错"""
        engine = _make_interface_engine(
            mock_driver, {'status': '${Return[-1].status}'}
        )
        with pytest.raises(InvalidParameterError, match="接口/DB verify"):
            engine.execute("verify", {"model": "API_Login", "data": "V001"})

    def test_interface_verify_literal_value_passes(self, mock_driver):
        """接口 verify 使用字面值 → 正常通过"""
        engine = _make_interface_engine(mock_driver, {'status': '200'})
        result = engine.execute("verify", {"model": "API_Login", "data": "V001"})
        assert result is True


# --- 数据库模型：${Return[-1]} 必须报错 ---

class TestDatabaseVerifySelfReference:
    """数据库模型 _verify 使用 ${Return[-1]} 应立即失败"""

    def test_database_verify_rejects_return_ref(self, mock_driver):
        """DB verify 期望值含 ${Return[-1]} → InvalidParameterError"""
        engine = _make_database_engine(mock_driver, {'count': '${Return[-1]}'})
        with pytest.raises(InvalidParameterError, match="接口/DB verify"):
            engine.execute("verify", {"model": "DB_Order", "data": "V001"})

    def test_database_verify_rejects_return_ref_with_key(self, mock_driver):
        """DB verify 期望值含 ${Return[-1].count} 也应报错"""
        engine = _make_database_engine(
            mock_driver, {'count': '${Return[-1].count}'}
        )
        with pytest.raises(InvalidParameterError, match="接口/DB verify"):
            engine.execute("verify", {"model": "DB_Order", "data": "V001"})

    def test_database_verify_literal_value_passes(self, mock_driver):
        """DB verify 使用字面值 → 正常通过"""
        engine = _make_database_engine(mock_driver, {'count': '5'})
        result = engine.execute("verify", {"model": "DB_Order", "data": "V001"})
        assert result is True


# --- UI 模型：${Return[-1]} 仍然允许 ---

class TestUIVerifyAllowsReturnRef:
    """UI 模型 _verify 使用 ${Return[-1]} 不受影响"""

    def test_ui_verify_allows_return_ref(self, mock_driver):
        """UI verify 期望值含 ${Return[-1]} → 正常执行（不报错）"""
        from data.data_resolver import DataResolver

        engine = _make_ui_engine(mock_driver, {'orderNo': '${Return[-1]}'})
        resolver = DataResolver(return_provider=engine.get_return)
        engine.data_resolver = resolver

        result = engine.execute("verify", {"model": "OrderPage", "data": "V001"})
        assert result is True
