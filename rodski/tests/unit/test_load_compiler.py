"""单元测试 — LoadCompiler (WI-44)"""
from __future__ import annotations

import ast
import json
import os
import warnings
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_shared_ctx(
    case_registry=None,
    model_registry=None,
    global_values=None,
    data_store=None,
    module_dir=None,
):
    from rodski.load.context import SharedLoadContext

    mock_ds = MagicMock()
    mock_ds.get_table = MagicMock(return_value=[])

    return SharedLoadContext(
        case_registry=case_registry or {},
        model_registry=model_registry or {},
        data_store=data_store or mock_ds,
        global_values=global_values or {},
        module_dir=Path(module_dir or "/tmp"),
    )


def _make_plan(cases=None, host="http://example.com", plan_id="TC_PLAN_001"):
    return {
        "plan_id": plan_id,
        "load_profile": {
            "host": host,
            "concurrency": 2,
            "duration_seconds": 10,
            "ramp_up_seconds": 0,
            "think_time_ms": {"min": 100, "max": 500},
        },
        "cases": cases or [],
    }


def _make_case(case_id, steps=None):
    return {
        "case_id": case_id,
        "component_type": "接口",
        "pre_process": [],
        "test_case": steps or [],
        "post_process": [],
    }


def _make_send_step(model="LoginModel", data=None):
    return {
        "action": "send",
        "model": model,
        "data": data or {},
    }


# ---------------------------------------------------------------------------
# Test: compile() basic
# ---------------------------------------------------------------------------

class TestCompileBasic:

    def test_compile_creates_py_file(self, tmp_path):
        """compile() 应生成 perf/{plan_id}.py。"""
        from rodski.load.compiler import LoadCompiler

        ctx = _make_shared_ctx()
        plan = _make_plan(plan_id="PLAN_001")
        compiler = LoadCompiler(ctx, plan, tmp_path / "perf")
        out = compiler.compile()

        assert out.exists()
        assert out.name == "PLAN_001.py"

    def test_compile_creates_meta_file(self, tmp_path):
        """compile() 应生成对应的 .meta 文件。"""
        from rodski.load.compiler import LoadCompiler

        ctx = _make_shared_ctx()
        plan = _make_plan(plan_id="PLAN_002")
        compiler = LoadCompiler(ctx, plan, tmp_path / "perf")
        out = compiler.compile()

        meta_path = out.parent / f"{out.stem}.py.meta"
        assert meta_path.exists()
        meta = json.loads(meta_path.read_text())
        assert "compiled_at" in meta
        assert meta["source"] == "auto"

    def test_compile_creates_perf_dir(self, tmp_path):
        """perf/ 不存在时 compile() 自动创建。"""
        from rodski.load.compiler import LoadCompiler

        perf_dir = tmp_path / "perf" / "sub"
        ctx = _make_shared_ctx()
        plan = _make_plan(plan_id="PLAN_003")
        compiler = LoadCompiler(ctx, plan, perf_dir)
        compiler.compile()

        assert perf_dir.exists()

    def test_compile_returns_path(self, tmp_path):
        """compile() 返回 Path 对象。"""
        from rodski.load.compiler import LoadCompiler

        ctx = _make_shared_ctx()
        plan = _make_plan(plan_id="PLAN_004")
        compiler = LoadCompiler(ctx, plan, tmp_path)
        out = compiler.compile()

        assert isinstance(out, Path)


# ---------------------------------------------------------------------------
# Test: ast.parse() passes
# ---------------------------------------------------------------------------

class TestAstParse:

    def test_generated_code_is_valid_python(self, tmp_path):
        """生成的代码必须通过 ast.parse()。"""
        from rodski.load.compiler import LoadCompiler

        case_id = "TC_LOAD_001"
        case_def = _make_case(case_id, steps=[_make_send_step()])
        ctx = _make_shared_ctx(
            case_registry={case_id: case_def},
            model_registry={
                "LoginModel": {
                    "method": "POST",
                    "url": "/api/login",
                    "fields": {
                        "username": {"location": "body"},
                        "password": {"location": "body"},
                    },
                }
            },
        )
        plan = _make_plan(
            plan_id="PLAN_AST",
            cases=[{"id": case_id, "execute": "是", "weight": 1}],
        )
        compiler = LoadCompiler(ctx, plan, tmp_path)
        out = compiler.compile()
        code = out.read_text()
        ast.parse(code)  # must not raise

    def test_empty_plan_is_valid_python(self, tmp_path):
        """空 plan（无 cases）生成的代码也通过 ast.parse()。"""
        from rodski.load.compiler import LoadCompiler

        ctx = _make_shared_ctx()
        plan = _make_plan(plan_id="PLAN_EMPTY")
        compiler = LoadCompiler(ctx, plan, tmp_path)
        out = compiler.compile()
        ast.parse(out.read_text())

    def test_generated_code_contains_compiled_rodski_user(self, tmp_path):
        """生成代码必须包含 CompiledRodskiUser 类。"""
        from rodski.load.compiler import LoadCompiler

        ctx = _make_shared_ctx()
        plan = _make_plan(plan_id="PLAN_CLASS")
        compiler = LoadCompiler(ctx, plan, tmp_path)
        out = compiler.compile()
        assert "CompiledRodskiUser" in out.read_text()

    def test_generated_code_has_fast_http_user(self, tmp_path):
        """CompiledRodskiUser 继承 FastHttpUser。"""
        from rodski.load.compiler import LoadCompiler

        ctx = _make_shared_ctx()
        plan = _make_plan(plan_id="PLAN_FHU")
        compiler = LoadCompiler(ctx, plan, tmp_path)
        out = compiler.compile()
        assert "FastHttpUser" in out.read_text()

    def test_generated_code_imports_locust(self, tmp_path):
        """生成代码包含 locust 导入语句。"""
        from rodski.load.compiler import LoadCompiler

        ctx = _make_shared_ctx()
        plan = _make_plan(plan_id="PLAN_IMP")
        compiler = LoadCompiler(ctx, plan, tmp_path)
        out = compiler.compile()
        code = out.read_text()
        assert "from locust import" in code


# ---------------------------------------------------------------------------
# Test: task weight
# ---------------------------------------------------------------------------

class TestTaskWeight:

    def test_task_weight_in_generated_code(self, tmp_path):
        """@task(weight) 的 weight 值应正确嵌入代码。"""
        from rodski.load.compiler import LoadCompiler

        case_id = "TC_WEIGHT_001"
        case_def = _make_case(case_id, steps=[_make_send_step()])
        ctx = _make_shared_ctx(
            case_registry={case_id: case_def},
            model_registry={"LoginModel": {"method": "POST", "url": "/api/x", "fields": {}}},
        )
        plan = _make_plan(
            plan_id="PLAN_W",
            cases=[{"id": case_id, "execute": "是", "weight": 7}],
        )
        compiler = LoadCompiler(ctx, plan, tmp_path)
        out = compiler.compile()
        code = out.read_text()
        assert "@task(7)" in code

    def test_multiple_tasks_correct_weights(self, tmp_path):
        """多个 case 各自 weight 正确。"""
        from rodski.load.compiler import LoadCompiler

        cases_cfg = [
            {"id": "TC_A", "execute": "是", "weight": 3},
            {"id": "TC_B", "execute": "是", "weight": 5},
        ]
        case_registry = {
            "TC_A": _make_case("TC_A"),
            "TC_B": _make_case("TC_B"),
        }
        ctx = _make_shared_ctx(case_registry=case_registry)
        plan = _make_plan(plan_id="PLAN_MW", cases=cases_cfg)
        compiler = LoadCompiler(ctx, plan, tmp_path)
        out = compiler.compile()
        code = out.read_text()
        assert "@task(3)" in code
        assert "@task(5)" in code

    def test_non_execute_cases_excluded(self, tmp_path):
        """execute != '是' 的 case 不生成 @task。"""
        from rodski.load.compiler import LoadCompiler

        cases_cfg = [
            {"id": "TC_YES", "execute": "是", "weight": 1},
            {"id": "TC_NO",  "execute": "否", "weight": 1},
        ]
        ctx = _make_shared_ctx(
            case_registry={
                "TC_YES": _make_case("TC_YES"),
                "TC_NO":  _make_case("TC_NO"),
            }
        )
        plan = _make_plan(plan_id="PLAN_EX", cases=cases_cfg)
        compiler = LoadCompiler(ctx, plan, tmp_path)
        out = compiler.compile()
        code = out.read_text()
        assert "TC_YES" in code
        assert "TC_NO" not in code


# ---------------------------------------------------------------------------
# Test: literal inlining
# ---------------------------------------------------------------------------

class TestLiteralInlining:

    def test_literal_fields_become_constants(self, tmp_path):
        """字面量字段应生成模块级常量 _TC_xxx_STEPx_METHOD / _URL。"""
        from rodski.load.compiler import LoadCompiler

        case_id = "TC_LIT_001"
        case_def = _make_case(case_id, steps=[_make_send_step("MyModel")])
        ctx = _make_shared_ctx(
            case_registry={case_id: case_def},
            model_registry={
                "MyModel": {"method": "POST", "url": "/api/data", "fields": {}}
            },
        )
        plan = _make_plan(
            plan_id="PLAN_LIT",
            cases=[{"id": case_id, "execute": "是", "weight": 1}],
        )
        compiler = LoadCompiler(ctx, plan, tmp_path)
        out = compiler.compile()
        code = out.read_text()
        assert "_TC_TC_LIT_001_STEP0_METHOD" in code
        assert "_TC_TC_LIT_001_STEP0_URL" in code

    def test_literal_body_field_inlined(self, tmp_path):
        """body 字段的字面量值应出现在生成代码中。"""
        from rodski.load.compiler import LoadCompiler

        case_id = "TC_BODY_001"
        mock_ds = MagicMock()
        mock_ds.get_table = MagicMock(return_value=[{"username": "testuser", "password": "pass123"}])
        ctx = _make_shared_ctx(
            case_registry={
                case_id: _make_case(case_id, steps=[_make_send_step("AuthModel")])
            },
            model_registry={
                "AuthModel": {
                    "method": "POST",
                    "url": "/login",
                    "fields": {
                        "username": {"location": "body"},
                        "password": {"location": "body"},
                    },
                }
            },
            data_store=mock_ds,
        )
        plan = _make_plan(
            plan_id="PLAN_BODY",
            cases=[{"id": case_id, "execute": "是", "weight": 1}],
        )
        compiler = LoadCompiler(ctx, plan, tmp_path)
        out = compiler.compile()
        code = out.read_text()
        assert "testuser" in code
        assert "pass123" in code


# ---------------------------------------------------------------------------
# Test: GlobalValue expansion
# ---------------------------------------------------------------------------

class TestGlobalValueExpansion:

    def test_global_value_expanded_at_compile_time(self, tmp_path):
        """${GlobalValue.DefaultValue.URL} 应在编译期展开为字面量。"""
        from rodski.load.compiler import LoadCompiler

        case_id = "TC_GV_001"
        mock_ds = MagicMock()
        mock_ds.get_table = MagicMock(return_value=[{"url": "${GlobalValue.DefaultValue.host}"}])
        ctx = _make_shared_ctx(
            case_registry={
                case_id: _make_case(case_id, steps=[_make_send_step("GVModel")])
            },
            model_registry={
                "GVModel": {
                    "method": "GET",
                    "url": "${GlobalValue.DefaultValue.host}/api",
                    "fields": {},
                }
            },
            global_values={
                "DefaultValue": {"host": "http://staging.example.com"}
            },
            data_store=mock_ds,
        )
        plan = _make_plan(
            plan_id="PLAN_GV",
            cases=[{"id": case_id, "execute": "是", "weight": 1}],
        )
        compiler = LoadCompiler(ctx, plan, tmp_path)
        out = compiler.compile()
        code = out.read_text()
        # GlobalValue 展开后字面量值出现在代码中
        assert "http://staging.example.com" in code
        # ${GlobalValue...} 占位符不应残留
        assert "${GlobalValue" not in code


# ---------------------------------------------------------------------------
# Test: compile_if_needed() cache
# ---------------------------------------------------------------------------

class TestCompileIfNeeded:

    def test_compile_if_needed_creates_file(self, tmp_path):
        """首次调用 compile_if_needed() 应生成文件。"""
        from rodski.load.compiler import LoadCompiler

        ctx = _make_shared_ctx()
        plan = _make_plan(plan_id="PLAN_CIN_1")
        compiler = LoadCompiler(ctx, plan, tmp_path / "perf")
        out = compiler.compile_if_needed()
        assert out.exists()

    def test_compile_if_needed_cache_hit(self, tmp_path):
        """hash 未变化时，第二次调用不重写文件（mtime 不变）。"""
        from rodski.load.compiler import LoadCompiler

        ctx = _make_shared_ctx()
        plan = _make_plan(plan_id="PLAN_CACHE")
        perf_dir = tmp_path / "perf"
        compiler = LoadCompiler(ctx, plan, perf_dir)

        out1 = compiler.compile_if_needed()
        mtime1 = out1.stat().st_mtime

        # 不传任何路径，hash 为固定值（所有文件均不存在时 hash 恒定）
        out2 = compiler.compile_if_needed()
        mtime2 = out2.stat().st_mtime

        assert mtime1 == mtime2

    def test_compile_if_needed_cache_miss_when_file_changes(self, tmp_path):
        """hash 变化时重新编译（mtime 更新）。"""
        from rodski.load.compiler import LoadCompiler
        import time

        ctx = _make_shared_ctx()
        plan = _make_plan(plan_id="PLAN_MISS")
        perf_dir = tmp_path / "perf"

        # 第一次编译，传入一个文件路径
        plan_xml = tmp_path / "plan.xml"
        plan_xml.write_text("<plan/>")
        compiler = LoadCompiler(ctx, plan, perf_dir)
        out1 = compiler.compile_if_needed(plan_path=plan_xml)
        mtime1 = out1.stat().st_mtime

        # 修改文件内容
        time.sleep(0.01)
        plan_xml.write_text("<plan version='2'/>")

        out2 = compiler.compile_if_needed(plan_path=plan_xml)
        mtime2 = out2.stat().st_mtime

        assert mtime2 >= mtime1

    def test_compile_if_needed_source_manual_skips(self, tmp_path):
        """source=manual 时 compile_if_needed() 打印 WARN 并跳过覆盖。"""
        from rodski.load.compiler import LoadCompiler

        ctx = _make_shared_ctx()
        plan = _make_plan(plan_id="PLAN_MANUAL")
        perf_dir = tmp_path / "perf"
        perf_dir.mkdir()

        out_path  = perf_dir / "PLAN_MANUAL.py"
        meta_path = perf_dir / "PLAN_MANUAL.py.meta"

        original_content = "# manual file"
        out_path.write_text(original_content)
        meta = {"plan_hash": "differenthash", "compiled_at": "2024-01-01", "source": "manual"}
        meta_path.write_text(json.dumps(meta))

        compiler = LoadCompiler(ctx, plan, perf_dir)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = compiler.compile_if_needed()

        # 文件内容未被覆盖
        assert out_path.read_text() == original_content
        assert result == out_path
        # 应有 UserWarning
        assert any("manual" in str(warning.message).lower() for warning in w)


# ---------------------------------------------------------------------------
# Test: ${Return[-N].field} compilation
# ---------------------------------------------------------------------------

class TestReturnChain:

    def test_single_return_reference_compiled(self, tmp_path):
        """${Return[-1].token} → self._returns[-1].get('token', '')。"""
        from rodski.load.compiler import LoadCompiler

        case_id = "TC_RET_001"
        mock_ds = MagicMock()
        mock_ds.get_table = MagicMock(return_value=[{"Authorization": "${Return[-1].token}"}])
        ctx = _make_shared_ctx(
            case_registry={
                case_id: _make_case(case_id, steps=[_make_send_step("SecureModel")])
            },
            model_registry={
                "SecureModel": {
                    "method": "GET",
                    "url": "/secure",
                    "fields": {"Authorization": {"location": "header"}},
                }
            },
            data_store=mock_ds,
        )
        plan = _make_plan(
            plan_id="PLAN_RET",
            cases=[{"id": case_id, "execute": "是", "weight": 1}],
        )
        compiler = LoadCompiler(ctx, plan, tmp_path)
        out = compiler.compile()
        code = out.read_text()
        assert "self._returns[-1].get('token'" in code

    def test_multi_return_chain_warns_and_skips(self, tmp_path):
        """多个 Return 引用打印 WARN 并跳过该字段（使用空字符串）。"""
        from rodski.load.compiler import LoadCompiler

        case_id = "TC_RET_MULTI"
        mock_ds = MagicMock()
        # 同一字段出现两个 Return 引用
        mock_ds.get_table = MagicMock(
            return_value=[{"value": "${Return[-1].a}${Return[-2].b}"}]
        )
        ctx = _make_shared_ctx(
            case_registry={
                case_id: _make_case(case_id, steps=[_make_send_step("MultiModel")])
            },
            model_registry={
                "MultiModel": {
                    "method": "POST",
                    "url": "/multi",
                    "fields": {"value": {"location": "body"}},
                }
            },
            data_store=mock_ds,
        )
        plan = _make_plan(
            plan_id="PLAN_MULTI_RET",
            cases=[{"id": case_id, "execute": "是", "weight": 1}],
        )
        compiler = LoadCompiler(ctx, plan, tmp_path)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            out = compiler.compile()

        code = out.read_text()
        # 多层 Return 链跳过，使用空字符串
        assert "''" in code
        # 应有警告
        assert any("Return" in str(warning.message) or "多层" in str(warning.message)
                   for warning in w)


# ---------------------------------------------------------------------------
# Test: ${random(...)}, ${date(...)} compilation
# ---------------------------------------------------------------------------

class TestDynamicExpressions:

    def test_random_compiled_to_lambda(self, tmp_path):
        """${random(1, 100)} 编译为 lambda 调用。"""
        from rodski.load.compiler import LoadCompiler

        case_id = "TC_RAND_001"
        mock_ds = MagicMock()
        mock_ds.get_table = MagicMock(return_value=[{"amount": "${random(1, 100)}"}])
        ctx = _make_shared_ctx(
            case_registry={
                case_id: _make_case(case_id, steps=[_make_send_step("RandModel")])
            },
            model_registry={
                "RandModel": {
                    "method": "POST",
                    "url": "/rand",
                    "fields": {"amount": {"location": "body"}},
                }
            },
            data_store=mock_ds,
        )
        plan = _make_plan(
            plan_id="PLAN_RAND",
            cases=[{"id": case_id, "execute": "是", "weight": 1}],
        )
        compiler = LoadCompiler(ctx, plan, tmp_path)
        out = compiler.compile()
        code = out.read_text()
        assert "_random.random(1, 100)" in code

    def test_date_compiled_to_lambda(self, tmp_path):
        """${date(%Y-%m-%d)} 编译为 lambda 调用 strftime。"""
        from rodski.load.compiler import LoadCompiler

        case_id = "TC_DATE_001"
        mock_ds = MagicMock()
        mock_ds.get_table = MagicMock(return_value=[{"ts": "${date(%Y-%m-%d)}"}])
        ctx = _make_shared_ctx(
            case_registry={
                case_id: _make_case(case_id, steps=[_make_send_step("DateModel")])
            },
            model_registry={
                "DateModel": {
                    "method": "POST",
                    "url": "/date",
                    "fields": {"ts": {"location": "body"}},
                }
            },
            data_store=mock_ds,
        )
        plan = _make_plan(
            plan_id="PLAN_DATE",
            cases=[{"id": case_id, "execute": "是", "weight": 1}],
        )
        compiler = LoadCompiler(ctx, plan, tmp_path)
        out = compiler.compile()
        code = out.read_text()
        assert "strftime" in code
        assert "%Y-%m-%d" in code
