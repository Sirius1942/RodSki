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
