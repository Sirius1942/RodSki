"""Unit tests for rodski_agent.narrator.nodes"""
import pytest
from pathlib import Path
from textwrap import dedent
from unittest.mock import MagicMock, patch


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def demo_project(tmp_path):
    case_dir = tmp_path / "case"
    model_dir = tmp_path / "model"
    data_dir = tmp_path / "data"
    case_dir.mkdir()
    model_dir.mkdir()
    data_dir.mkdir()

    (data_dir / "globalvalue.xml").write_text(dedent("""\
        <?xml version="1.0" encoding="UTF-8"?>
        <globalvalue>
            <group name="DefaultValue">
                <var name="URL" value="http://localhost:8000"/>
            </group>
        </globalvalue>
    """), encoding="utf-8")

    (model_dir / "model.xml").write_text(dedent("""\
        <?xml version="1.0" encoding="UTF-8"?>
        <models>
            <model name="LoginForm" type="ui">
                <element name="username" type="input">
                    <location type="id">loginUsername</location>
                    <desc>用户名输入框</desc>
                </element>
            </model>
        </models>
    """), encoding="utf-8")

    (data_dir / "data.xml").write_text(dedent("""\
        <?xml version="1.0" encoding="UTF-8"?>
        <datatables>
            <datatable name="LoginForm">
                <row id="L001">
                    <field name="username">admin</field>
                    <field name="password">123456</field>
                </row>
            </datatable>
        </datatables>
    """), encoding="utf-8")

    case_file = case_dir / "tc_test.xml"
    case_file.write_text(dedent("""\
        <?xml version="1.0" encoding="UTF-8"?>
        <cases>
            <case execute="是" id="TC001" title="正常登录" description="使用正确账号登录" component_type="界面">
                <pre_process>
                    <test_step action="navigate" model="" data="http://localhost:8000"/>
                </pre_process>
                <test_case>
                    <test_step action="type" model="LoginForm" data="L001"/>
                </test_case>
                <post_process>
                    <test_step action="close" model="" data=""/>
                </post_process>
            </case>
        </cases>
    """), encoding="utf-8")

    return tmp_path, case_file


# ============================================================
# resolve_case 节点
# ============================================================

def test_resolve_case_success(demo_project):
    from rodski_agent.narrator.nodes import resolve_case

    _, case_file = demo_project
    state = {"case_path": str(case_file)}
    result = resolve_case(state)

    assert result.get("status") != "error"
    assert len(result["resolved_cases"]) == 1
    assert result["resolved_cases"][0]["id"] == "TC001"


def test_resolve_case_sets_output_dir(demo_project):
    from rodski_agent.narrator.nodes import resolve_case

    project_root, case_file = demo_project
    state = {"case_path": str(case_file)}
    result = resolve_case(state)

    expected = str(project_root / "narrative")
    assert result["output_dir"] == expected


def test_resolve_case_missing_file():
    from rodski_agent.narrator.nodes import resolve_case

    state = {"case_path": "/nonexistent/path/tc.xml"}
    result = resolve_case(state)

    assert result["status"] == "error"
    assert "不存在" in result["error"]


def test_resolve_case_with_id_filter(demo_project):
    from rodski_agent.narrator.nodes import resolve_case

    _, case_file = demo_project
    state = {"case_path": str(case_file), "case_ids": ["TC999"]}
    result = resolve_case(state)

    assert result.get("resolved_cases") == []


def test_resolve_case_no_log(demo_project):
    """无日志路径时正常工作，log_info 为 None。"""
    from rodski_agent.narrator.nodes import resolve_case

    _, case_file = demo_project
    state = {"case_path": str(case_file), "log_path": None}
    result = resolve_case(state)

    steps = result["resolved_cases"][0]["steps"]
    for step in steps:
        assert step.get("log_info") is None


# ============================================================
# narrate 节点（mock LLM）
# ============================================================

def test_narrate_calls_llm(demo_project):
    from rodski_agent.narrator.nodes import narrate

    _, case_file = demo_project
    mock_response = MagicMock()
    mock_response.content = "## TC001: 正常登录\n\n**测试目标**: 验证正常登录流程\n"

    with patch("rodski_agent.common.llm_bridge.get_chat_model") as mock_get:
        mock_model = MagicMock()
        mock_model.invoke.return_value = mock_response
        mock_get.return_value = mock_model

        state = {
            "case_path": str(case_file),
            "resolved_cases": [
                {
                    "id": "TC001",
                    "title": "正常登录",
                    "description": "使用正确账号登录",
                    "component_type": "界面",
                    "steps": [],
                }
            ],
        }
        result = narrate(state)

    assert len(result["narratives"]) == 1
    assert result["narratives"][0]["case_id"] == "TC001"
    assert "TC001" in result["narratives"][0]["markdown"]


def test_narrate_llm_failure_graceful(demo_project):
    """LLM 调用失败时，生成错误占位内容，不抛出异常。"""
    from rodski_agent.narrator.nodes import narrate

    _, case_file = demo_project

    with patch("rodski_agent.common.llm_bridge.get_chat_model") as mock_get:
        mock_model = MagicMock()
        mock_model.invoke.side_effect = RuntimeError("LLM timeout")
        mock_get.return_value = mock_model

        state = {
            "case_path": str(case_file),
            "resolved_cases": [
                {"id": "TC001", "title": "正常登录", "description": "", "component_type": "", "steps": []}
            ],
        }
        result = narrate(state)

    assert len(result["narratives"]) == 1
    assert "生成失败" in result["narratives"][0]["markdown"]


# ============================================================
# write_files 节点
# ============================================================

def test_write_files_creates_directory(tmp_path):
    from rodski_agent.narrator.nodes import write_files

    output_dir = str(tmp_path / "narrative")
    state = {
        "output_dir": output_dir,
        "narratives": [
            {"case_id": "TC001", "title": "正常登录", "markdown": "## TC001\n\n内容"},
        ],
    }
    result = write_files(state)

    assert result["status"] == "success"
    assert len(result["written_files"]) == 1
    assert Path(result["written_files"][0]).exists()


def test_write_files_naming(tmp_path):
    from rodski_agent.narrator.nodes import write_files

    output_dir = str(tmp_path / "narrative")
    state = {
        "output_dir": output_dir,
        "narratives": [
            {"case_id": "TC032", "title": "clear清空输入框", "markdown": "内容"},
        ],
    }
    result = write_files(state)

    filename = Path(result["written_files"][0]).name
    assert filename == "TC032_clear清空输入框.md"


def test_write_files_sanitizes_special_chars(tmp_path):
    from rodski_agent.narrator.nodes import write_files

    output_dir = str(tmp_path / "narrative")
    state = {
        "output_dir": output_dir,
        "narratives": [
            {"case_id": "TC001", "title": "登录/注销 测试", "markdown": "内容"},
        ],
    }
    result = write_files(state)

    filename = Path(result["written_files"][0]).name
    assert "/" not in filename
    assert " " not in filename


def test_write_files_content(tmp_path):
    from rodski_agent.narrator.nodes import write_files

    output_dir = str(tmp_path / "narrative")
    content = "## TC001: 正常登录\n\n**测试目标**: 验证登录"
    state = {
        "output_dir": output_dir,
        "narratives": [
            {"case_id": "TC001", "title": "正常登录", "markdown": content},
        ],
    }
    result = write_files(state)

    written = Path(result["written_files"][0]).read_text(encoding="utf-8")
    assert written == content


def test_write_files_no_narratives(tmp_path):
    from rodski_agent.narrator.nodes import write_files

    state = {"output_dir": str(tmp_path / "narrative"), "narratives": []}
    result = write_files(state)

    assert result["status"] == "success"
    assert result["written_files"] == []


# ============================================================
# _safe_filename
# ============================================================

def test_safe_filename_basic():
    from rodski_agent.narrator.nodes import _safe_filename

    assert _safe_filename("TC001_正常登录") == "TC001_正常登录"


def test_safe_filename_slash():
    from rodski_agent.narrator.nodes import _safe_filename

    assert "/" not in _safe_filename("TC001/登录")


def test_safe_filename_space():
    from rodski_agent.narrator.nodes import _safe_filename

    assert " " not in _safe_filename("TC001 登录 测试")


def test_safe_filename_consecutive_underscores():
    from rodski_agent.narrator.nodes import _safe_filename

    result = _safe_filename("TC001  登录")
    assert "__" not in result
