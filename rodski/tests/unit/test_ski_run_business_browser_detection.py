from pathlib import Path

import pytest

try:
    from rodski.ski_run import _needs_browser
except ImportError:  # Running pytest with rodski/ as the working directory.
    from ski_run import _needs_browser


def _write_case_module(tmp_path: Path, case_xml: str, model_xml: str = "<models />") -> Path:
    module_dir = tmp_path / "module"
    case_dir = module_dir / "case"
    case_dir.mkdir(parents=True)
    (module_dir / "model").mkdir()
    (module_dir / "model" / "model.xml").write_text(model_xml, encoding="utf-8")
    case_path = case_dir / "case.xml"
    case_path.write_text(case_xml, encoding="utf-8")
    return case_path


def _write_business_model(case_path: Path, ref: str, business_model_xml: str, filename: str | None = None) -> Path:
    business_dir = case_path.parent.parent / "business"
    business_dir.mkdir(exist_ok=True)
    business_path = business_dir / (filename or f"{ref}.xml")
    business_path.write_text(business_model_xml, encoding="utf-8")
    return business_path


def test_business_call_interface_only_model_does_not_need_browser(tmp_path):
    case_path = _write_case_module(
        tmp_path,
        '<case><business_call ref="account_api" /></case>',
        '<models><model name="AccountAPI" type="interface" /></models>',
    )
    _write_business_model(
        case_path,
        "account_api",
        """<business_models version="0.1">
          <business_model id="account_api" name="Account API" version="1">
            <nodes><node id="request"><steps>
              <test_step action="send" model="AccountAPI" />
              <test_step action="assert" model="AccountAPI" />
            </steps></node></nodes>
            <edges><edge from="request" to="request" /></edges>
            <flows><flow id="all" type="basic" path="request&gt;request" /></flows>
          </business_model>
        </business_models>""",
    )

    assert _needs_browser(case_path) is False


@pytest.mark.parametrize("action", ["navigate", "click"])
def test_business_call_browser_action_in_referenced_model_needs_browser(tmp_path, action):
    case_path = _write_case_module(
        tmp_path,
        '<case><business_call ref="checkout" /></case>',
        '<models><model name="Checkout" type="interface" /></models>',
    )
    _write_business_model(
        case_path,
        "checkout",
        f"""<business_models version="0.1">
          <business_model id="checkout" name="Checkout" version="1">
            <nodes><node id="start"><steps>
              <test_step action="{action}" model="Checkout" />
            </steps></node></nodes>
            <edges><edge from="start" to="start" /></edges>
            <flows><flow id="all" type="basic" path="start&gt;start" /></flows>
          </business_model>
        </business_models>""",
    )

    assert _needs_browser(case_path) is True


def test_business_call_ref_matches_model_id_in_shared_business_xml(tmp_path):
    case_path = _write_case_module(
        tmp_path,
        '<case><business_call ref="login_flow" /></case>',
        '<models><model name="LoginAPI" type="interface" /></models>',
    )
    _write_business_model(
        case_path,
        "login_flow",
        """<business_models version="0.1">
          <business_model id="other_flow" name="Other" version="1">
            <nodes><node id="start"><steps><test_step action="send" model="LoginAPI" /></steps></node></nodes>
            <edges><edge from="start" to="start" /></edges>
            <flows><flow id="all" type="basic" path="start&gt;start" /></flows>
          </business_model>
          <business_model id="login_flow" name="Login" version="1">
            <nodes><node id="open"><steps><test_step action="navigate" model="LoginAPI" /></steps></node></nodes>
            <edges><edge from="open" to="open" /></edges>
            <flows><flow id="all" type="basic" path="open&gt;open" /></flows>
          </business_model>
        </business_models>""",
        filename="business.xml",
    )

    assert _needs_browser(case_path) is True


@pytest.mark.parametrize("business_xml", [None, "<business_models>"])
def test_missing_or_invalid_business_reference_does_not_raise(tmp_path, business_xml):
    case_path = _write_case_module(
        tmp_path,
        '<case><business_call ref="missing_flow" /></case>',
    )
    if business_xml is not None:
        _write_business_model(case_path, "missing_flow", business_xml)

    assert _needs_browser(case_path) is False


def test_ordinary_test_step_browser_detection_is_unchanged(tmp_path):
    case_path = _write_case_module(
        tmp_path,
        '<case><test_step action="navigate" model="AccountAPI" /></case>',
        '<models><model name="AccountAPI" type="interface" /></models>',
    )

    # The business-call-specific interface handling must not change the legacy
    # unconditional browser-action scan for ordinary case test_step elements.
    assert _needs_browser(case_path) is True
