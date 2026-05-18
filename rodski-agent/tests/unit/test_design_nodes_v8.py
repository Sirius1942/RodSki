"""Integration tests for v8 new nodes: load_skills, gap_analysis, design_model, generate_xml."""

import sqlite3
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest

from rodski_agent.design.nodes import gap_analysis, design_model, generate_xml


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content), encoding="utf-8")


def _make_model_xml(model_names: list) -> str:
    models = "\n".join(f'  <model name="{n}" type="ui" servicename=""/>' for n in model_names)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<models>\n{models}\n</models>\n'


def _plan(steps: list) -> list:
    return [{"id": "C001", "title": "Test Case", "steps": steps}]


LOGIN_MD = textwrap.dedent("""\
    # 登录模块 业务文档

    ## 业务术语
    - **工作台**：登录成功后的主页面，URL 包含 /dashboard
    - **演示账号**：用户名 admin，密码 admin123

    ## 操作流程

    ### 登录
    打开系统首页，在登录表单输入用户名和密码，点击"登录"按钮，等待页面跳转到工作台。

    ## 测试约束
    - 每个用例执行完必须退出登录，避免影响后续用例的权限状态
""")


# ---------------------------------------------------------------------------
# load_skills
# ---------------------------------------------------------------------------

def test_load_skills_populates_skill_context(tmp_path):
    """load_skills node: given skills_dir, skill_context is correctly filled into state."""
    (tmp_path / "login.md").write_text(LOGIN_MD, encoding="utf-8")

    # Use the inline load_skills_fn from graph.py (same logic, tested directly via skill_loader)
    from rodski_agent.design.skill_loader import load_skill_docs

    ctx = load_skill_docs(str(tmp_path))
    result = {"skill_context": ctx.to_dict()}

    assert "工作台" in result["skill_context"]["terms"]
    assert any(f["name"] == "登录" for f in result["skill_context"]["flows"])
    assert len(result["skill_context"]["constraints"]) == 1


def test_load_skills_empty_dir_returns_empty(tmp_path):
    """load_skills node: empty skills_dir yields empty skill_context."""
    from rodski_agent.design.skill_loader import load_skill_docs

    ctx = load_skill_docs(str(tmp_path))
    d = ctx.to_dict()
    assert d["terms"] == {}
    assert d["flows"] == []
    assert d["constraints"] == []


# ---------------------------------------------------------------------------
# gap_analysis
# ---------------------------------------------------------------------------

def test_gap_analysis_with_existing_model(tmp_path):
    """gap_analysis: given output_dir with model.xml, gap_report is correct."""
    _write(tmp_path / "model" / "model.xml", _make_model_xml(["LoginPage"]))

    state = {
        "output_dir": str(tmp_path),
        "case_plan": _plan([
            {"model": "LoginPage", "data": ""},
            {"model": "HomePage", "data": ""},
        ]),
    }
    result = gap_analysis(state)
    report = result["gap_report"]

    assert report["missing_models"] == ["HomePage"]
    assert report["reusable_models"] == ["LoginPage"]


def test_gap_analysis_no_output_dir_all_missing(tmp_path):
    """gap_analysis: missing output_dir means all referenced assets are in missing."""
    state = {
        "output_dir": str(tmp_path / "nonexistent"),
        "case_plan": _plan([{"model": "Foo", "data": "FooData.R001"}]),
    }
    result = gap_analysis(state)
    report = result["gap_report"]

    assert "Foo" in report["missing_models"]
    assert "FooData" in report["missing_data"]


# ---------------------------------------------------------------------------
# design_model
# ---------------------------------------------------------------------------

DESIGN_MODEL_RESPONSE = '[{"name": "LoginPage", "elements": [{"name": "username", "type": "web", "locators": [{"type": "id", "value": "username"}]}]}]'


def test_design_model_fills_designed_models():
    """design_model: mock call_llm_text, verifies designed_models is populated."""
    state = {
        "case_plan": _plan([{"model": "LoginPage", "action": "type", "data": ""}]),
    }
    with patch("rodski_agent.common.llm_bridge.call_llm_text", return_value=DESIGN_MODEL_RESPONSE):
        result = design_model(state)

    assert "designed_models" in result
    assert "LoginPage" in result["designed_models"]
    assert result["designed_models"]["LoginPage"][0]["name"] == "username"


def test_design_model_preserves_mobile_model_metadata():
    response = (
        '[{"name": "LoginScreen", "model_type": "ui", "driver_type": "android", '
        '"elements": [{"name": "phone", "type": "input", '
        '"locators": [{"type": "id", "value": "com.example:id/phone"}]}]}]'
    )
    state = {
        "case_plan": _plan([{"model": "LoginScreen", "action": "type", "data": "L001"}]),
    }

    with patch("rodski_agent.common.llm_bridge.call_llm_text", return_value=response):
        result = design_model(state)

    model = result["designed_models"]["LoginScreen"]
    assert model["driver_type"] == "android"
    assert model["model_type"] == "ui"
    assert model["elements"][0]["name"] == "phone"


def test_design_model_empty_plan_returns_empty():
    """design_model: empty case_plan returns empty designed_models."""
    result = design_model({"case_plan": []})
    assert result == {"designed_models": {}}


def test_design_model_no_model_in_steps_returns_empty():
    """design_model: steps with no model field returns empty designed_models."""
    state = {"case_plan": _plan([{"action": "open", "data": ""}])}
    result = design_model(state)
    assert result == {"designed_models": {}}


# ---------------------------------------------------------------------------
# generate_xml — designed_models path
# ---------------------------------------------------------------------------

def test_generate_xml_uses_designed_models_not_stub(tmp_path):
    """generate_xml: when designed_models exists, does not fall back to stub path."""
    from rodski_agent.common.xml_builder import build_model_xml

    designed_models = {
        "LoginPage": [{"name": "username", "type": "web", "locators": [{"type": "id", "value": "username"}]}]
    }
    state = {
        "output_dir": str(tmp_path),
        "case_plan": _plan([{"model": "LoginPage", "action": "type", "data": ""}]),
        "test_data": {},
        "designed_models": designed_models,
    }

    result = generate_xml(state)

    model_file = tmp_path / "model" / "model.xml"
    assert model_file.exists(), "model.xml should be generated"
    content = model_file.read_text(encoding="utf-8")
    # LLM-designed model name should appear; stub would use css locator with #username
    assert "LoginPage" in content
    # LLM-designed: locator type=id, value=username; stub would use css:#field1
    assert 'type="id"' in content
    assert "username" in content


def test_generate_xml_mobile_app_mode_writes_sqlite_and_globalvalue(tmp_path):
    state = {
        "requirement": "Android 移动端 App 登录",
        "target_url": "app://android/com.example/.MainActivity",
        "output_dir": str(tmp_path),
        "case_plan": _plan([
            {"phase": "pre_process", "action": "navigate", "model": "", "data": "GlobalValue.Mobile.AppTarget"},
            {"phase": "test_case", "action": "type", "model": "LoginScreen", "data": "L001"},
            {"phase": "test_case", "action": "swipe", "model": "LoginScreen", "data": "S001"},
            {"phase": "test_case", "action": "verify", "model": "LoginScreen", "data": "V001"},
            {"phase": "post_process", "action": "close", "model": "", "data": ""},
        ]),
        "test_data": {
            "datatables": [{
                "name": "LoginScreen",
                "rows": [{"id": "L001", "fields": [
                    {"name": "username", "value": "admin"},
                    {"name": "password", "value": "123456"},
                    {"name": "login_button", "value": "click"},
                ]}],
            }],
            "verify_tables": [{
                "name": "LoginScreen_verify",
                "rows": [{"id": "V001", "fields": [
                    {"name": "welcome_text", "value": "Welcome"},
                ]}],
            }],
        },
        "designed_models": {
            "LoginScreen": {
                "driver_type": "android",
                "elements": [
                    {"name": "username", "type": "input", "locators": [{"type": "id", "value": "com.example:id/username"}]},
                    {"name": "password", "type": "input", "locators": [{"type": "id", "value": "com.example:id/password"}]},
                    {"name": "login_button", "type": "button", "locators": [{"type": "text", "value": "登录"}]},
                    {"name": "welcome_text", "type": "text", "locators": [{"type": "text", "value": "Welcome"}]},
                ],
            }
        },
    }

    result = generate_xml(state)

    assert result["status"] == "running"
    assert not (tmp_path / "data" / "data.xml").exists()
    assert not (tmp_path / "data" / "data_verify.xml").exists()
    assert (tmp_path / "data" / "data.sqlite").exists()
    assert (tmp_path / "data" / "globalvalue.xml").exists()

    case_xml = (tmp_path / "case" / "test_case.xml").read_text(encoding="utf-8")
    assert 'action="swipe"' not in case_xml
    assert 'action="navigate"' in case_xml
    assert 'action="type"' in case_xml
    assert 'action="verify"' in case_xml
    assert 'action="close"' in case_xml

    model_xml = (tmp_path / "model" / "model.xml").read_text(encoding="utf-8")
    assert 'driver_type="android"' in model_xml
    assert '<location type="id">com.example:id/username</location>' in model_xml
    assert 'value="com.example:id/username"' not in model_xml

    globalvalue_xml = (tmp_path / "data" / "globalvalue.xml").read_text(encoding="utf-8")
    assert 'name="Mobile"' in globalvalue_xml
    assert 'name="AppTarget"' in globalvalue_xml
    assert 'app://android/com.example/.MainActivity' in globalvalue_xml

    conn = sqlite3.connect(str(tmp_path / "data" / "data.sqlite"))
    try:
        tables = {
            row[0]: row[1]
            for row in conn.execute("SELECT table_name, table_kind FROM rs_datatable")
        }
        assert tables == {"LoginScreen": "data", "LoginScreen_verify": "verify"}
        fields = [
            row[0]
            for row in conn.execute(
                "SELECT field_name FROM rs_datatable_field WHERE table_name='LoginScreen' ORDER BY field_order"
            )
        ]
        assert fields == ["username", "password", "login_button", "welcome_text"]
        verify_blank = conn.execute(
            "SELECT field_value FROM rs_field "
            "WHERE table_name='LoginScreen_verify' AND data_id='V001' AND field_name='username'"
        ).fetchone()[0]
        assert verify_blank == "BLANK"
    finally:
        conn.close()
