from pathlib import Path
from typing import Tuple

import pytest

from rodski_cli.run import _needs_browser


def _write_module_case(tmp_path: Path, case_xml: str, model_xml: str) -> Tuple[Path, Path]:
    case_dir = tmp_path / "case"
    model_dir = tmp_path / "model"
    case_dir.mkdir()
    model_dir.mkdir()

    case_path = case_dir / "tc001.xml"
    model_path = model_dir / "model.xml"
    case_path.write_text(case_xml, encoding="utf-8")
    model_path.write_text(model_xml, encoding="utf-8")

    return case_path, model_path


@pytest.mark.parametrize("driver_type", ["android", "ios"])
def test_mobile_model_driver_type_does_not_need_browser(tmp_path, driver_type):
    case_path, model_path = _write_module_case(
        tmp_path,
        """
<case>
  <test_step action="type" model="LoginScreen" data="L001" />
  <test_step action="verify" model="LoginScreen" data="L001" />
</case>
""",
        f"""
<models>
  <model name="LoginScreen" type="ui" driver_type="{driver_type}">
    <element name="Username">
      <location type="id">username</location>
    </element>
  </model>
</models>
""",
    )

    assert _needs_browser(case_path, model_path) is False


def test_globalvalue_mobile_app_uri_navigate_does_not_need_browser(tmp_path):
    case_path, model_path = _write_module_case(
        tmp_path,
        """
<case>
  <test_step action="navigate" model="" data="GlobalValue.Mobile.AppURI" />
</case>
""",
        """
<models>
  <model name="WebPage" type="ui">
    <element name="Title">
      <location type="css">h1</location>
    </element>
  </model>
</models>
""",
    )
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "globalvalue.xml").write_text(
        """
<globalvalue>
  <group name="Mobile">
    <var name="AppURI" value="app://android/com.example/.MainActivity" />
  </group>
</globalvalue>
""",
        encoding="utf-8",
    )

    assert _needs_browser(case_path, model_path) is False


def test_web_url_navigate_needs_browser(tmp_path):
    case_path, model_path = _write_module_case(
        tmp_path,
        """
<case>
  <test_step action="navigate" model="" data="https://example.com/login" />
</case>
""",
        """
<models>
  <model name="WebPage" type="ui">
    <element name="Title">
      <location type="css">h1</location>
    </element>
  </model>
</models>
""",
    )

    assert _needs_browser(case_path, model_path) is True


def test_ui_verify_only_case_needs_browser(tmp_path):
    """只有 verify 步骤的 UI 用例仍需要浏览器。

    回归：verify 曾缺席 _BROWSER_ACTIONS，导致纯 verify 用例被判为不需要
    浏览器、driver 为 None，verify 抛
    ``'NoneType' object has no attribute 'get_text'``；
    demo_pause_takeover 的 part2_continue.xml 就是这种形态。
    """
    case_path, model_path = _write_module_case(
        tmp_path,
        """
<case>
  <test_step action="verify" model="Dashboard" data="V001" />
</case>
""",
        """
<models>
  <model name="Dashboard" type="ui">
    <element name="totalOrders">
      <location type="id">totalOrders</location>
    </element>
  </model>
</models>
""",
    )

    assert _needs_browser(case_path, model_path) is True


def test_interface_verify_only_case_does_not_need_browser(tmp_path):
    """接口模型的 verify 不走浏览器（driver_type 判定优先于 verify 入集）。"""
    case_path, model_path = _write_module_case(
        tmp_path,
        """
<case>
  <test_step action="verify" model="UserApi" data="V001" />
</case>
""",
        """
<models>
  <model name="UserApi" type="interface">
    <element name="code">
      <location type="jsonpath">$.code</location>
    </element>
  </model>
</models>
""",
    )

    assert _needs_browser(case_path, model_path) is False


def test_database_verify_only_case_does_not_need_browser(tmp_path):
    case_path, model_path = _write_module_case(
        tmp_path,
        """
<case>
  <test_step action="verify" model="UserTable" data="V001" />
</case>
""",
        """
<models>
  <model name="UserTable" type="database">
    <element name="name">
      <location type="sql">select name from t</location>
    </element>
  </model>
</models>
""",
    )

    assert _needs_browser(case_path, model_path) is False
