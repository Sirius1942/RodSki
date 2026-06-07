"""单元测试 — RodskiLoadUser (WI-37)"""
from __future__ import annotations
from unittest.mock import MagicMock, patch, call
import pytest


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_shared_ctx(case_registry=None, model_registry=None, data_store=None, global_values=None):
    """构造轻量 SharedLoadContext mock。"""
    ctx = MagicMock()
    ctx.case_registry = case_registry or {}
    ctx.model_registry = model_registry or {}
    ctx.data_store = data_store or MagicMock()
    ctx.global_values = global_values or {}
    return ctx


def _make_user_instance(shared_ctx=None, host="http://example.com"):
    """
    创建 RodskiLoadUser 实例。
    由于 RodskiLoadUser.abstract=True，直接继承并实例化。
    不使用真实 Locust——mock 掉 client 即可。
    """
    from rodski.load.user import RodskiLoadUser

    class _TestUser(RodskiLoadUser):
        abstract = False

    user = _TestUser.__new__(_TestUser)
    user.host = host
    user.client = MagicMock()       # 模拟 Locust FastHttpUser.client
    if shared_ctx is not None:
        user._shared_ctx = shared_ctx
    return user


# ---------------------------------------------------------------------------
# test: on_start() 创建 LoadDriver 和 KeywordEngine
# ---------------------------------------------------------------------------

class TestRodskiLoadUserOnStart:

    @patch("rodski.load.user.KeywordEngine")
    @patch("rodski.load.user.LoadDriver")
    def test_on_start_creates_load_driver(self, mock_ld_cls, mock_ke_cls):
        """on_start() 用 client 和 host 创建 LoadDriver。"""
        user = _make_user_instance()
        user.on_start()

        mock_ld_cls.assert_called_once_with(
            locust_client=user.client,
            host=user.host,
        )

    @patch("rodski.load.user.KeywordEngine")
    @patch("rodski.load.user.LoadDriver")
    def test_on_start_creates_keyword_engine(self, mock_ld_cls, mock_ke_cls):
        """on_start() 创建 KeywordEngine，并传入 LoadDriver 实例。"""
        mock_ld_inst = MagicMock()
        mock_ld_cls.return_value = mock_ld_inst

        user = _make_user_instance()
        user.on_start()

        assert mock_ke_cls.call_count == 1
        call_kwargs = mock_ke_cls.call_args[1]
        assert call_kwargs.get("driver") is mock_ld_inst

    @patch("rodski.load.user.KeywordEngine")
    @patch("rodski.load.user.LoadDriver")
    def test_on_start_stores_instances(self, mock_ld_cls, mock_ke_cls):
        """on_start() 后 _load_driver 和 _keyword_engine 属性已设置。"""
        user = _make_user_instance()
        user.on_start()

        assert hasattr(user, "_load_driver")
        assert hasattr(user, "_keyword_engine")

    @patch("rodski.load.user.KeywordEngine")
    @patch("rodski.load.user.LoadDriver")
    def test_on_start_initializes_returns(self, mock_ld_cls, mock_ke_cls):
        """on_start() 后 _returns 为空列表。"""
        user = _make_user_instance()
        user.on_start()

        assert user._returns == []

    @patch("rodski.load.user.KeywordEngine")
    @patch("rodski.load.user.LoadDriver")
    def test_on_start_injects_model_parser(self, mock_ld_cls, mock_ke_cls):
        """当 _shared_ctx 存在时，KeywordEngine 接收 model_parser。"""
        model_registry = {"Login": {"__model_type__": "ui"}}
        ctx = _make_shared_ctx(model_registry=model_registry)
        user = _make_user_instance(shared_ctx=ctx)

        user.on_start()

        call_kwargs = mock_ke_cls.call_args[1]
        assert call_kwargs.get("model_parser") is not None

    @patch("rodski.load.user.KeywordEngine")
    @patch("rodski.load.user.LoadDriver")
    def test_on_start_injects_data_manager(self, mock_ld_cls, mock_ke_cls):
        """当 _shared_ctx 存在时，KeywordEngine 接收 data_manager = ctx.data_store。"""
        fake_store = MagicMock()
        ctx = _make_shared_ctx(data_store=fake_store)
        user = _make_user_instance(shared_ctx=ctx)

        user.on_start()

        call_kwargs = mock_ke_cls.call_args[1]
        assert call_kwargs.get("data_manager") is fake_store

    @patch("rodski.load.user.KeywordEngine")
    @patch("rodski.load.user.LoadDriver")
    def test_on_start_no_shared_ctx(self, mock_ld_cls, mock_ke_cls):
        """没有 _shared_ctx 时，model_parser / data_manager 为 None。"""
        user = _make_user_instance(shared_ctx=None)
        # 不设置 _shared_ctx，确保不会 AttributeError
        user.on_start()

        call_kwargs = mock_ke_cls.call_args[1]
        assert call_kwargs.get("model_parser") is None
        assert call_kwargs.get("data_manager") is None


# ---------------------------------------------------------------------------
# test: _execute_case()
# ---------------------------------------------------------------------------

class TestRodskiLoadUserExecuteCase:

    def _user_with_engine(self, case_registry, steps):
        """构造一个注入了 mock engine 的 user，context 包含 case_registry。"""
        from rodski.load.user import RodskiLoadUser

        ctx = _make_shared_ctx(case_registry=case_registry)

        class _TestUser(RodskiLoadUser):
            abstract = False

        user = _TestUser.__new__(_TestUser)
        user.host = "http://example.com"
        user.client = MagicMock()
        user._shared_ctx = ctx

        # 构造带 mock engine 的 user：跳过 on_start()，直接注入
        mock_engine = MagicMock()
        mock_engine._context = MagicMock()
        mock_engine._context.history = []
        user._keyword_engine = mock_engine
        user._returns = []
        return user, mock_engine

    def test_execute_case_raises_for_unknown_case_id(self):
        """不存在的 case_id 应抛 ValueError。"""
        user, _ = self._user_with_engine(case_registry={}, steps=[])
        with pytest.raises(ValueError, match="case_id 'NONEXIST' 不在 case_registry 中"):
            user._execute_case("NONEXIST")

    def test_execute_case_calls_execute_for_each_step(self):
        """_execute_case 对 pre_process + test_case 中的每个 step 调用 engine.execute()。"""
        pre_steps = [{"action": "navigate", "model": "", "data": "http://a.com"}]
        tc_steps  = [{"action": "wait", "model": "", "data": "1"}]
        case = {
            "case_id": "TC001",
            "pre_process": pre_steps,
            "test_case": tc_steps,
            "post_process": [],
        }
        user, mock_engine = self._user_with_engine(
            case_registry={"TC001": case}, steps=[]
        )
        # engine.execute 不真实执行，直接 return True
        mock_engine.execute.return_value = True
        mock_engine._context.history = []

        user._execute_case("TC001")

        assert mock_engine.execute.call_count == 2
        # 第一个调用应是 navigate
        first_call_args = mock_engine.execute.call_args_list[0]
        assert first_call_args[0][0] == "navigate"

    def test_execute_case_skips_post_process(self):
        """post_process 中的步骤不应执行。"""
        case = {
            "case_id": "TC002",
            "pre_process": [],
            "test_case": [{"action": "wait", "model": "", "data": "0.1"}],
            "post_process": [{"action": "close", "model": "", "data": ""}],
        }
        user, mock_engine = self._user_with_engine(
            case_registry={"TC002": case}, steps=[]
        )
        mock_engine.execute.return_value = True
        mock_engine._context.history = []

        user._execute_case("TC002")

        # 只有 test_case 中的 wait 被执行，close（post_process）不执行
        assert mock_engine.execute.call_count == 1
        assert mock_engine.execute.call_args[0][0] == "wait"

    def test_execute_case_resets_returns(self):
        """_execute_case 每次调用都重置 _returns 列表。"""
        case = {
            "case_id": "TC003",
            "pre_process": [],
            "test_case": [],
            "post_process": [],
        }
        user, mock_engine = self._user_with_engine(
            case_registry={"TC003": case}, steps=[]
        )
        user._returns = ["old_value"]
        mock_engine._context.history = []

        user._execute_case("TC003")
        assert user._returns == []

    def test_execute_case_no_ctx(self):
        """_shared_ctx 为 None 时，_execute_case 直接返回，不抛异常。"""
        from rodski.load.user import RodskiLoadUser

        class _TestUser(RodskiLoadUser):
            abstract = False

        user = _TestUser.__new__(_TestUser)
        # 不设置 _shared_ctx
        # 调用应静默返回
        result = user._execute_case("ANYTHING")
        assert result is None

    def test_execute_step_collects_return_value(self):
        """engine.execute() 向 history 追加内容时，_returns 会收集该值。"""
        case = {
            "case_id": "TC004",
            "pre_process": [],
            "test_case": [{"action": "send", "model": "ApiModel", "data": "D001"}],
            "post_process": [],
        }
        user, mock_engine = self._user_with_engine(
            case_registry={"TC004": case}, steps=[]
        )

        # 模拟 engine.execute() 追加 history
        def _fake_execute(action, params):
            mock_engine._context.history.append({"status": 200})
            return True

        mock_engine.execute.side_effect = _fake_execute
        mock_engine._context.history = []

        user._execute_case("TC004")

        assert len(user._returns) == 1
        assert user._returns[0] == {"status": 200}
