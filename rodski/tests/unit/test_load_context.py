"""单元测试 — SharedLoadContext (WI-37)"""
from __future__ import annotations
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_module_dir(tmp_path: Path) -> Path:
    """在 tmp_path 下创建最小模块目录骨架。"""
    module_dir = tmp_path / "product" / "proj" / "mod"
    (module_dir / "case").mkdir(parents=True)
    (module_dir / "model").mkdir(parents=True)
    (module_dir / "data").mkdir(parents=True)
    (module_dir / "fun").mkdir(parents=True)
    (module_dir / "plan").mkdir(parents=True)
    (module_dir / "result").mkdir(parents=True)
    return module_dir


# ---------------------------------------------------------------------------
# test: build() 正常路径（case / model / data / globalvalue 均不存在时走空路径）
# ---------------------------------------------------------------------------

class TestSharedLoadContextBuild:

    def test_build_empty_module_dir(self, tmp_path):
        """case/model/data/globalvalue 均不存在 → 返回空 SharedLoadContext。"""
        module_dir = _make_module_dir(tmp_path)
        from rodski.load.context import SharedLoadContext

        ctx = SharedLoadContext.build(module_dir)
        assert ctx.case_registry == {}
        assert ctx.model_registry == {}
        assert ctx.global_values == {}
        assert ctx.module_dir == Path(module_dir)

    def test_build_returns_correct_type(self, tmp_path):
        """build() 返回 SharedLoadContext 实例。"""
        module_dir = _make_module_dir(tmp_path)
        from rodski.load.context import SharedLoadContext

        ctx = SharedLoadContext.build(module_dir)
        assert isinstance(ctx, SharedLoadContext)

    @patch("rodski.load.context.CaseParser")
    @patch("rodski.load.context.ModelParser")
    @patch("rodski.load.context.DataTableParser")
    @patch("rodski.load.context.GlobalValueParser")
    def test_build_with_case_dir(
        self,
        mock_gv_cls,
        mock_dt_cls,
        mock_mp_cls,
        mock_cp_cls,
        tmp_path,
    ):
        """case/ 目录存在时，CaseParser 被调用，case_registry 包含解析结果。"""
        module_dir = _make_module_dir(tmp_path)
        # 创建一个假 xml 文件，使 case_dir.exists() 为 True
        (module_dir / "case" / "tc001.xml").touch()

        mock_case = {"case_id": "TC001", "pre_process": [], "test_case": []}
        mock_cp_inst = MagicMock()
        mock_cp_inst.parse_cases.return_value = [mock_case]
        mock_cp_cls.return_value = mock_cp_inst

        mock_mp_inst = MagicMock()
        mock_mp_inst.models = {}
        mock_mp_cls.return_value = mock_mp_inst

        mock_dt_inst = MagicMock()
        mock_dt_cls.return_value = mock_dt_inst

        mock_gv_inst = MagicMock()
        mock_gv_inst.parse.return_value = {}
        mock_gv_cls.return_value = mock_gv_inst

        from rodski.load.context import SharedLoadContext

        ctx = SharedLoadContext.build(module_dir)

        mock_cp_cls.assert_called_once_with(str(module_dir / "case"))
        mock_cp_inst.parse_cases.assert_called_once()
        assert "TC001" in ctx.case_registry
        assert ctx.case_registry["TC001"] is mock_case

    @patch("rodski.load.context.CaseParser")
    @patch("rodski.load.context.ModelParser")
    @patch("rodski.load.context.DataTableParser")
    @patch("rodski.load.context.GlobalValueParser")
    def test_build_with_model_file(
        self,
        mock_gv_cls,
        mock_dt_cls,
        mock_mp_cls,
        mock_cp_cls,
        tmp_path,
    ):
        """model/model.xml 存在时，ModelParser 被调用，model_registry 填充。"""
        module_dir = _make_module_dir(tmp_path)
        (module_dir / "model" / "model.xml").touch()

        mock_cp_inst = MagicMock()
        mock_cp_inst.parse_cases.return_value = []
        mock_cp_cls.return_value = mock_cp_inst

        fake_models = {"Login": {"__model_type__": "ui", "username": {}}}
        mock_mp_inst = MagicMock()
        mock_mp_inst.models = fake_models
        mock_mp_cls.return_value = mock_mp_inst

        mock_dt_inst = MagicMock()
        mock_dt_cls.return_value = mock_dt_inst

        mock_gv_inst = MagicMock()
        mock_gv_inst.parse.return_value = {}
        mock_gv_cls.return_value = mock_gv_inst

        from rodski.load.context import SharedLoadContext

        ctx = SharedLoadContext.build(module_dir)

        mock_mp_cls.assert_called_once_with(str(module_dir / "model" / "model.xml"))
        assert ctx.model_registry is fake_models

    @patch("rodski.load.context.CaseParser")
    @patch("rodski.load.context.ModelParser")
    @patch("rodski.load.context.DataTableParser")
    @patch("rodski.load.context.GlobalValueParser")
    def test_build_with_sqlite(
        self,
        mock_gv_cls,
        mock_dt_cls,
        mock_mp_cls,
        mock_cp_cls,
        tmp_path,
    ):
        """data.sqlite 存在时，DataTableParser.parse_all_tables() 被调用。"""
        module_dir = _make_module_dir(tmp_path)
        (module_dir / "data" / "data.sqlite").touch()

        mock_cp_inst = MagicMock()
        mock_cp_inst.parse_cases.return_value = []
        mock_cp_cls.return_value = mock_cp_inst

        mock_mp_inst = MagicMock()
        mock_mp_inst.models = {}
        mock_mp_cls.return_value = mock_mp_inst

        mock_dt_inst = MagicMock()
        mock_dt_cls.return_value = mock_dt_inst

        mock_gv_inst = MagicMock()
        mock_gv_inst.parse.return_value = {}
        mock_gv_cls.return_value = mock_gv_inst

        from rodski.load.context import SharedLoadContext

        ctx = SharedLoadContext.build(module_dir)

        mock_dt_cls.assert_called_once_with(str(module_dir / "data"))
        mock_dt_inst.parse_all_tables.assert_called_once()
        assert ctx.data_store is mock_dt_inst

    @patch("rodski.load.context.CaseParser")
    @patch("rodski.load.context.ModelParser")
    @patch("rodski.load.context.DataTableParser")
    @patch("rodski.load.context.GlobalValueParser")
    def test_build_with_globalvalue(
        self,
        mock_gv_cls,
        mock_dt_cls,
        mock_mp_cls,
        mock_cp_cls,
        tmp_path,
    ):
        """globalvalue.xml 存在时，GlobalValueParser.parse() 被调用。"""
        module_dir = _make_module_dir(tmp_path)
        (module_dir / "data" / "globalvalue.xml").touch()

        mock_cp_inst = MagicMock()
        mock_cp_inst.parse_cases.return_value = []
        mock_cp_cls.return_value = mock_cp_inst

        mock_mp_inst = MagicMock()
        mock_mp_inst.models = {}
        mock_mp_cls.return_value = mock_mp_inst

        mock_dt_inst = MagicMock()
        mock_dt_cls.return_value = mock_dt_inst

        fake_gv = {"Env": {"Host": "https://example.com"}}
        mock_gv_inst = MagicMock()
        mock_gv_inst.parse.return_value = fake_gv
        mock_gv_cls.return_value = mock_gv_inst

        from rodski.load.context import SharedLoadContext

        ctx = SharedLoadContext.build(module_dir)

        mock_gv_cls.assert_called_once_with(str(module_dir / "data" / "globalvalue.xml"))
        mock_gv_inst.parse.assert_called_once()
        assert ctx.global_values is fake_gv


# ---------------------------------------------------------------------------
# test: frozen=True 约束
# ---------------------------------------------------------------------------

class TestSharedLoadContextFrozen:

    def _build_empty(self, tmp_path: Path):
        module_dir = _make_module_dir(tmp_path)
        from rodski.load.context import SharedLoadContext
        return SharedLoadContext.build(module_dir)

    def test_frozen_instance_raises_on_set(self, tmp_path):
        """尝试修改 frozen dataclass 属性应抛 FrozenInstanceError。"""
        ctx = self._build_empty(tmp_path)
        with pytest.raises(FrozenInstanceError):
            ctx.case_registry = {}  # type: ignore[misc]

    def test_frozen_instance_raises_on_model_registry_set(self, tmp_path):
        ctx = self._build_empty(tmp_path)
        with pytest.raises(FrozenInstanceError):
            ctx.model_registry = {}  # type: ignore[misc]

    def test_frozen_instance_raises_on_module_dir_set(self, tmp_path):
        ctx = self._build_empty(tmp_path)
        with pytest.raises(FrozenInstanceError):
            ctx.module_dir = Path("/other")  # type: ignore[misc]

    def test_case_registry_is_dict(self, tmp_path):
        ctx = self._build_empty(tmp_path)
        assert isinstance(ctx.case_registry, dict)

    def test_model_registry_is_dict(self, tmp_path):
        ctx = self._build_empty(tmp_path)
        assert isinstance(ctx.model_registry, dict)
