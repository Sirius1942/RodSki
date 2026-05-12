"""Unit tests for rodski_agent.narrator.case_resolver"""
import pytest
from pathlib import Path
from textwrap import dedent


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def demo_project(tmp_path):
    """创建最小化的 demo 项目结构。"""
    case_dir = tmp_path / "case"
    model_dir = tmp_path / "model"
    data_dir = tmp_path / "data"
    case_dir.mkdir()
    model_dir.mkdir()
    data_dir.mkdir()

    # globalvalue.xml
    (data_dir / "globalvalue.xml").write_text(dedent("""\
        <?xml version="1.0" encoding="UTF-8"?>
        <globalvalue>
            <group name="DefaultValue">
                <var name="URL" value="http://localhost:8000"/>
            </group>
        </globalvalue>
    """), encoding="utf-8")

    # model.xml
    (model_dir / "model.xml").write_text(dedent("""\
        <?xml version="1.0" encoding="UTF-8"?>
        <models>
            <model name="LoginForm" type="ui">
                <element name="username" type="input">
                    <location type="id">loginUsername</location>
                    <desc>用户名输入框</desc>
                </element>
                <element name="password" type="input">
                    <location type="id">loginPassword</location>
                    <desc>密码输入框</desc>
                </element>
                <element name="loginBtn" type="button">
                    <location type="id">loginBtn</location>
                    <desc>登录按钮</desc>
                </element>
            </model>
        </models>
    """), encoding="utf-8")

    # data.xml
    (data_dir / "data.xml").write_text(dedent("""\
        <?xml version="1.0" encoding="UTF-8"?>
        <datatables>
            <datatable name="LoginForm">
                <row id="L001">
                    <field name="username">admin</field>
                    <field name="password">123456</field>
                    <field name="loginBtn">click</field>
                </row>
                <row id="L002">
                    <field name="username">GlobalValue.DefaultValue.URL</field>
                    <field name="password">wrongpass</field>
                </row>
            </datatable>
        </datatables>
    """), encoding="utf-8")

    # case XML
    case_file = case_dir / "tc_login.xml"
    case_file.write_text(dedent("""\
        <?xml version="1.0" encoding="UTF-8"?>
        <cases>
            <case execute="是" id="TC001" title="正常登录" description="使用正确账号登录" component_type="界面">
                <pre_process>
                    <test_step action="navigate" model="" data="http://localhost:8000"/>
                </pre_process>
                <test_case>
                    <test_step action="type" model="LoginForm" data="L001"/>
                    <test_step action="verify" model="LoginForm" data="L001"/>
                </test_case>
                <post_process>
                    <test_step action="close" model="" data=""/>
                </post_process>
            </case>
            <case execute="是" id="TC002" title="错误密码登录" description="使用错误密码登录" component_type="界面">
                <test_case>
                    <test_step action="type" model="LoginForm" data="L002"/>
                </test_case>
            </case>
        </cases>
    """), encoding="utf-8")

    return tmp_path, case_file


# ============================================================
# 测试：基础解析
# ============================================================

def test_resolve_all_cases(demo_project):
    from rodski_agent.narrator.case_resolver import CaseResolver

    _, case_file = demo_project
    resolver = CaseResolver(str(case_file))
    cases = resolver.resolve()

    assert len(cases) == 2
    assert cases[0].id == "TC001"
    assert cases[1].id == "TC002"


def test_resolve_filtered_by_id(demo_project):
    from rodski_agent.narrator.case_resolver import CaseResolver

    _, case_file = demo_project
    resolver = CaseResolver(str(case_file))
    cases = resolver.resolve(case_ids=["TC002"])

    assert len(cases) == 1
    assert cases[0].id == "TC002"


def test_resolve_model_elements(demo_project):
    from rodski_agent.narrator.case_resolver import CaseResolver

    _, case_file = demo_project
    resolver = CaseResolver(str(case_file))
    cases = resolver.resolve(case_ids=["TC001"])

    # test_case 中的 type 步骤应有 LoginForm 的元素
    test_steps = [s for s in cases[0].steps if s.phase == "test_case"]
    type_step = test_steps[0]
    assert type_step.model_name == "LoginForm"
    assert len(type_step.elements) == 3
    elem_names = [e.name for e in type_step.elements]
    assert "username" in elem_names
    assert "loginBtn" in elem_names


def test_resolve_data_fields(demo_project):
    from rodski_agent.narrator.case_resolver import CaseResolver

    _, case_file = demo_project
    resolver = CaseResolver(str(case_file))
    cases = resolver.resolve(case_ids=["TC001"])

    test_steps = [s for s in cases[0].steps if s.phase == "test_case"]
    type_step = test_steps[0]
    assert type_step.data_fields["username"] == "admin"
    assert type_step.data_fields["password"] == "123456"


def test_resolve_global_value(demo_project):
    from rodski_agent.narrator.case_resolver import CaseResolver

    _, case_file = demo_project
    resolver = CaseResolver(str(case_file))
    cases = resolver.resolve(case_ids=["TC002"])

    test_steps = [s for s in cases[0].steps if s.phase == "test_case"]
    # L002 的 username 是 GlobalValue.DefaultValue.URL
    assert test_steps[0].data_fields["username"] == "http://localhost:8000"


def test_resolve_no_model_step(demo_project):
    from rodski_agent.narrator.case_resolver import CaseResolver

    _, case_file = demo_project
    resolver = CaseResolver(str(case_file))
    cases = resolver.resolve(case_ids=["TC001"])

    pre_steps = [s for s in cases[0].steps if s.phase == "pre_process"]
    assert len(pre_steps) == 1
    assert pre_steps[0].action == "navigate"
    assert pre_steps[0].raw_data == "http://localhost:8000"
    assert pre_steps[0].elements == []


def test_project_root_inference(demo_project):
    from rodski_agent.narrator.case_resolver import CaseResolver

    project_root, case_file = demo_project
    resolver = CaseResolver(str(case_file))
    assert resolver.project_root == project_root.resolve()


def test_to_dict_serializable(demo_project):
    from rodski_agent.narrator.case_resolver import CaseResolver
    import json

    _, case_file = demo_project
    resolver = CaseResolver(str(case_file))
    cases = resolver.resolve()
    dicts = [CaseResolver.to_dict(c) for c in cases]
    # 应可 JSON 序列化
    json.dumps(dicts, ensure_ascii=False)


def test_missing_model_graceful(demo_project):
    """引用不存在的 model 时，elements 为空列表，不报错。"""
    from rodski_agent.narrator.case_resolver import CaseResolver
    from textwrap import dedent

    project_root, _ = demo_project
    case_file = project_root / "case" / "tc_missing.xml"
    case_file.write_text(dedent("""\
        <?xml version="1.0" encoding="UTF-8"?>
        <cases>
            <case execute="是" id="TC099" title="缺失模型" description="" component_type="">
                <test_case>
                    <test_step action="type" model="NonExistentModel" data="X001"/>
                </test_case>
            </case>
        </cases>
    """), encoding="utf-8")

    resolver = CaseResolver(str(case_file))
    cases = resolver.resolve()
    assert cases[0].steps[0].elements == []
    assert cases[0].steps[0].data_fields == {}
