"""Mobile App generation contract tests for RodSki Agent.

These tests pin the v7 mobile generation constraints without changing
production code in this task. The positive tests validate the intended
artifact shape. The xfail test documents the current generator gap.
"""
from __future__ import annotations

import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from rodski_agent.design.nodes import _validate_case_plan_actions, generate_xml


ALLOWED_LOCATORS = {
    "id",
    "class",
    "css",
    "xpath",
    "text",
    "tag",
    "name",
    "static",
    "field",
    "vision",
    "ocr",
    "vision_bbox",
}

MOBILE_FORBIDDEN_ACTIONS = {
    "swipe",
    "tap",
    "long_press",
    "press_keycode",
    "hide_keyboard",
    "click",
    "double_click",
    "right_click",
    "hover",
    "select",
    "key_press",
    "drag",
    "scroll",
}


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def _build_data_sqlite(db_path: Path, platform: str) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(db_path)) as conn:
        conn.executescript(
            """
            CREATE TABLE rs_datatable (
                table_name TEXT PRIMARY KEY,
                model_name TEXT NOT NULL,
                table_kind TEXT NOT NULL,
                row_mode TEXT NOT NULL,
                remark TEXT DEFAULT '',
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE rs_datatable_field (
                table_name TEXT NOT NULL,
                field_name TEXT NOT NULL,
                field_order INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (table_name, field_name)
            );
            CREATE TABLE rs_row (
                table_name TEXT NOT NULL,
                data_id TEXT NOT NULL,
                remark TEXT DEFAULT '',
                PRIMARY KEY (table_name, data_id)
            );
            CREATE TABLE rs_field (
                table_name TEXT NOT NULL,
                data_id TEXT NOT NULL,
                field_name TEXT NOT NULL,
                field_value TEXT NOT NULL,
                PRIMARY KEY (table_name, data_id, field_name)
            );
            """
        )
        conn.execute(
            """
            INSERT INTO rs_datatable(table_name, model_name, table_kind, row_mode, remark)
            VALUES ('LoginScreen', 'LoginScreen', 'data', 'standard', ?)
            """,
            (f"{platform} login input",),
        )
        conn.executemany(
            """
            INSERT INTO rs_datatable_field(table_name, field_name, field_order)
            VALUES ('LoginScreen', ?, ?)
            """,
            [("phone", 0), ("password", 1), ("loginBtn", 2)],
        )
        conn.execute(
            "INSERT INTO rs_row(table_name, data_id, remark) VALUES ('LoginScreen', 'L001', 'normal login')"
        )
        conn.executemany(
            """
            INSERT INTO rs_field(table_name, data_id, field_name, field_value)
            VALUES ('LoginScreen', 'L001', ?, ?)
            """,
            [
                ("phone", "13800000000"),
                ("password", "demo123.Password"),
                ("loginBtn", "click"),
            ],
        )

        conn.execute(
            """
            INSERT INTO rs_datatable(table_name, model_name, table_kind, row_mode, remark)
            VALUES ('HomeScreen_verify', 'HomeScreen', 'verify', 'standard', ?)
            """,
            (f"{platform} home verify",),
        )
        conn.executemany(
            """
            INSERT INTO rs_datatable_field(table_name, field_name, field_order)
            VALUES ('HomeScreen_verify', ?, ?)
            """,
            [("welcomeText", 0), ("signedInPhone", 1)],
        )
        conn.execute(
            "INSERT INTO rs_row(table_name, data_id, remark) VALUES ('HomeScreen_verify', 'V001', 'login success')"
        )
        conn.executemany(
            """
            INSERT INTO rs_field(table_name, data_id, field_name, field_value)
            VALUES ('HomeScreen_verify', 'V001', ?, ?)
            """,
            [
                ("welcomeText", "欢迎使用 RodSki Mobile Demo"),
                ("signedInPhone", "13800000000"),
            ],
        )


def _write_mobile_module(root: Path, platform: str) -> None:
    app_target = (
        "app://android/com.rodski.demoapp/.MainActivity"
        if platform == "android"
        else "app://ios/com.rodski.demoapp"
    )
    model_locators = (
        """
        <location type="id" priority="1">com.rodski.demoapp:id/phoneInput</location>
        <location type="ocr" priority="2">手机号</location>
        """
        if platform == "android"
        else """
        <location type="name" priority="1">phoneInput</location>
        <location type="ocr" priority="2">手机号</location>
        """
    )

    _write(
        root / "case" / "mobile_login.xml",
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <cases tags="mobile,app,smoke">
          <case execute="否" id="MOB-001" title="Mobile login" component_type="界面">
            <pre_process>
              <test_step action="navigate" model="" data="GlobalValue.Mobile.AppTarget"/>
            </pre_process>
            <test_case>
              <test_step action="type" model="LoginScreen" data="L001"/>
              <test_step action="verify" model="HomeScreen" data="V001"/>
            </test_case>
            <post_process>
              <test_step action="close" model="" data=""/>
            </post_process>
          </case>
        </cases>
        """,
    )
    _write(
        root / "model" / "model.xml",
        f"""
        <?xml version="1.0" encoding="UTF-8"?>
        <models>
          <model name="LoginScreen" type="ui" driver_type="{platform}">
            <element name="phone">
              <type>input</type>
              {model_locators}
            </element>
            <element name="password">
              <type>input</type>
              <location type="id" priority="1">com.rodski.demoapp:id/passwordInput</location>
              <location type="ocr" priority="2">密码</location>
            </element>
            <element name="loginBtn">
              <type>button</type>
              <location type="id" priority="1">com.rodski.demoapp:id/loginButton</location>
              <location type="text" priority="2">登录</location>
              <location type="vision_bbox" priority="3">80,420,640,500</location>
            </element>
          </model>
          <model name="HomeScreen" type="ui" driver_type="{platform}">
            <element name="welcomeText">
              <type>text</type>
              <location type="ocr">欢迎使用 RodSki Mobile Demo</location>
            </element>
            <element name="signedInPhone">
              <type>text</type>
              <location type="id">com.rodski.demoapp:id/signedInPhone</location>
            </element>
          </model>
        </models>
        """,
    )
    _write(
        root / "data" / "globalvalue.xml",
        f"""
        <?xml version="1.0" encoding="UTF-8"?>
        <globalvalue>
          <group name="Mobile">
            <var name="Platform" value="{platform}"/>
            <var name="AppiumServer" value="http://127.0.0.1:4723"/>
            <var name="DeviceName" value="Mobile Device"/>
            <var name="AppTarget" value="{app_target}"/>
          </group>
        </globalvalue>
        """,
    )
    _build_data_sqlite(root / "data" / "data.sqlite", platform)
    (root / "fun").mkdir(parents=True, exist_ok=True)
    (root / "result").mkdir(parents=True, exist_ok=True)


def _assert_mobile_generation_contract(root: Path, expected_driver_type: str) -> None:
    case_files = sorted((root / "case").glob("*.xml"))
    assert case_files, "mobile generation must create case XML"

    for case_file in case_files:
        case_root = ET.parse(case_file).getroot()
        for step in case_root.findall(".//test_step"):
            action = step.get("action", "")
            assert action not in MOBILE_FORBIDDEN_ACTIONS
            assert action in {"navigate", "type", "verify", "close", "run", "wait", "screenshot"}

            data = step.get("data", "")
            if action in {"type", "verify", "send", "DB"} and data:
                assert "." not in data
                assert not data.startswith("GlobalValue.")

    model_file = root / "model" / "model.xml"
    assert model_file.exists(), "mobile generation must create model/model.xml"
    model_root = ET.parse(model_file).getroot()
    mobile_models = model_root.findall("model")
    assert mobile_models, "model.xml must contain mobile models"
    for model in mobile_models:
        assert model.get("type", "ui") == "ui"
        assert model.get("driver_type") == expected_driver_type
        for element in model.findall("element"):
            assert "locator" not in element.attrib
            assert "value" not in element.attrib
            locations = element.findall("location")
            assert locations, "each mobile element must use <location type=\"...\">"
            for location in locations:
                assert location.get("type") in ALLOWED_LOCATORS
                assert (location.text or "").strip()

    data_dir = root / "data"
    assert (data_dir / "globalvalue.xml").exists()
    assert (data_dir / "data.sqlite").exists()
    assert not (data_dir / "data.xml").exists()
    assert not (data_dir / "data_verify.xml").exists()

    gv_root = ET.parse(data_dir / "globalvalue.xml").getroot()
    mobile_group = gv_root.find("./group[@name='Mobile']")
    assert mobile_group is not None
    vars_by_name = {var.get("name"): var.get("value") for var in mobile_group.findall("var")}
    assert vars_by_name["Platform"] == expected_driver_type
    assert vars_by_name["AppTarget"].startswith(f"app://{expected_driver_type}/")

    with sqlite3.connect(str(data_dir / "data.sqlite")) as conn:
        rows = conn.execute(
            "SELECT table_name, model_name, table_kind FROM rs_datatable ORDER BY table_name"
        ).fetchall()
        assert ("LoginScreen", "LoginScreen", "data") in rows
        assert ("HomeScreen_verify", "HomeScreen", "verify") in rows

        login_fields = {
            row[0]
            for row in conn.execute(
                """
                SELECT field_name
                FROM rs_datatable_field
                WHERE table_name = 'LoginScreen'
                """
            )
        }
        assert login_fields == {"phone", "password", "loginBtn"}


@pytest.mark.parametrize("platform", ["android", "ios"])
def test_mobile_module_artifacts_follow_v7_contract(tmp_path: Path, platform: str) -> None:
    """A compliant mobile module uses v7 driver/data/locator contracts."""
    _write_mobile_module(tmp_path, platform)

    _assert_mobile_generation_contract(tmp_path, expected_driver_type=platform)


def test_mobile_case_plan_validator_removes_mobile_specific_actions() -> None:
    """Mobile gestures must not survive as Case XML actions."""
    case_plan = [
        {
            "id": "MOB-001",
            "title": "Bad mobile gestures",
            "steps": [
                {"phase": "test_case", "action": "navigate", "model": "", "data": "GlobalValue.Mobile.AppTarget"},
                {"phase": "test_case", "action": "swipe", "model": "LoginScreen", "data": "S001"},
                {"phase": "test_case", "action": "long_press", "model": "LoginScreen", "data": "L001"},
                {"phase": "test_case", "action": "hide_keyboard", "model": "", "data": ""},
                {"phase": "test_case", "action": "type", "model": "LoginScreen", "data": "L001"},
                {"phase": "test_case", "action": "verify", "model": "HomeScreen", "data": "V001"},
            ],
        }
    ]

    validated = _validate_case_plan_actions(case_plan)

    actions = [step["action"] for step in validated[0]["steps"]]
    assert actions == ["navigate", "type", "verify"]


def test_mobile_contract_detects_model_prefixed_case_data(tmp_path: Path) -> None:
    """Case data must be plain DataID, never ModelName.DataID."""
    _write_mobile_module(tmp_path, "android")
    case_file = tmp_path / "case" / "mobile_login.xml"
    case_xml = case_file.read_text(encoding="utf-8")
    case_file.write_text(case_xml.replace('data="L001"', 'data="LoginScreen.L001"'), encoding="utf-8")

    with pytest.raises(AssertionError):
        _assert_mobile_generation_contract(tmp_path, expected_driver_type="android")


def test_generate_xml_mobile_output_meets_v7_contract(tmp_path: Path) -> None:
    """P4 generator output should satisfy the mobile module contract."""
    state = {
        "output_dir": str(tmp_path),
        "case_plan": [
            {
                "id": "MOB-001",
                "title": "Android login",
                "execute": "否",
                "component_type": "界面",
                "steps": [
                    {"phase": "pre_process", "action": "navigate", "model": "", "data": "GlobalValue.Mobile.AppTarget"},
                    {"phase": "test_case", "action": "type", "model": "LoginScreen", "data": "L001"},
                    {"phase": "test_case", "action": "verify", "model": "HomeScreen", "data": "V001"},
                    {"phase": "post_process", "action": "close", "model": "", "data": ""},
                ],
            }
        ],
        "designed_models": {
            "LoginScreen": [
                {"name": "phone", "type": "android", "locators": [{"type": "id", "value": "com.rodski:id/phone"}]},
                {
                    "name": "password",
                    "type": "android",
                    "locators": [{"type": "id", "value": "com.rodski:id/password"}],
                },
                {"name": "loginBtn", "type": "android", "locators": [{"type": "text", "value": "登录"}]},
            ],
            "HomeScreen": [
                {"name": "welcomeText", "type": "android", "locators": [{"type": "ocr", "value": "欢迎"}]},
                {
                    "name": "signedInPhone",
                    "type": "android",
                    "locators": [{"type": "id", "value": "com.rodski:id/phone"}],
                },
            ],
        },
        "test_data": {
            "datatables": [
                {
                    "name": "LoginScreen",
                    "rows": [
                        {
                            "id": "L001",
                            "fields": [
                                {"name": "phone", "value": "13800000000"},
                                {"name": "password", "value": "demo123.Password"},
                                {"name": "loginBtn", "value": "click"},
                            ],
                        }
                    ],
                }
            ],
            "verify_tables": [
                {
                    "name": "HomeScreen_verify",
                    "rows": [
                        {
                            "id": "V001",
                            "fields": [
                                {"name": "welcomeText", "value": "欢迎使用 RodSki Mobile Demo"},
                                {"name": "signedInPhone", "value": "13800000000"},
                            ],
                        }
                    ],
                }
            ],
            "globalvalue": [
                {
                    "name": "Mobile",
                    "vars": [
                        {"name": "Platform", "value": "android"},
                        {"name": "AppTarget", "value": "app://android/com.rodski.demoapp/.MainActivity"},
                    ],
                }
            ],
        },
    }

    result = generate_xml(state)

    assert result["status"] == "running"
    _assert_mobile_generation_contract(tmp_path, expected_driver_type="android")
    assert (tmp_path / "plan" / "project_full.xml").exists()
    assert (tmp_path / "fun").is_dir()
    assert (tmp_path / "result").is_dir()


def test_generate_xml_mobile_mode_requires_explicit_platform(tmp_path: Path) -> None:
    """Mobile/App intent must not silently default to Android when platform is absent."""
    result = generate_xml({
        "output_dir": str(tmp_path),
        "requirement": "生成移动端 App 登录测试",
        "case_plan": [
            {
                "id": "MOB-001",
                "title": "Mobile login",
                "steps": [
                    {"phase": "test_case", "action": "type", "model": "LoginScreen", "data": "L001"},
                ],
            }
        ],
        "test_data": {},
    })

    assert result["status"] == "error"
    assert "requires explicit platform" in result["error"]
    assert not (tmp_path / "case" / "test_case.xml").exists()
