"""Tests for static business-model CLI tooling."""
from pathlib import Path

import pytest

try:
    from rodski.core.business_model import BusinessModelParser, BusinessModelValidationError, BusinessModelValidator
    from rodski.rodski_cli.business import handle
except ImportError:  # pytest launched from rodski/ with legacy import path
    from core.business_model import BusinessModelParser, BusinessModelValidationError, BusinessModelValidator
    from rodski_cli.business import handle


DEMO = Path(__file__).parents[3] / "rodski-demo" / "DEMO" / "demo_business_model"
XML = DEMO / "business" / "business.xml"


def test_static_graph_projection_and_flow_mermaid():
    model = BusinessModelParser().parse_file(XML)["login_flow"]
    graph = BusinessModelValidator.graph_dict(model)
    assert graph["input_table"] == "login_flow"
    assert len(graph["edges"]) == 5
    mermaid = BusinessModelValidator.mermaid(model, "F_LOGIN_INVALID")
    assert "flowchart TD" in mermaid
    assert "validate_login" in mermaid
    assert "locked" not in mermaid


def test_validator_rejects_cycle_and_unreachable_node():
    parser = BusinessModelParser()
    cyclic = parser.parse_string('''<business_models version="0.1"><business_model id="m" name="M" version="1">
      <nodes><node id="a"/><node id="b"/></nodes>
      <edges><edge from="a" to="b"/><edge from="b" to="a"/></edges>
      <flows><flow id="f" type="basic" path="a&gt;b"/></flows>
    </business_model></business_models>''')["m"]
    with pytest.raises(BusinessModelValidationError, match="start|cycle"):
        BusinessModelValidator.validate(cyclic)

    unreachable = parser.parse_string('''<business_models version="0.1"><business_model id="m" name="M" version="1">
      <nodes><node id="a"/><node id="b"/><node id="unused"/></nodes>
      <edges><edge from="a" to="b"/><edge from="unused" to="unused"/></edges>
      <flows><flow id="f" type="basic" path="a&gt;b"/></flows>
    </business_model></business_models>''' )["m"]
    with pytest.raises(BusinessModelValidationError, match="unreachable"):
        BusinessModelValidator.validate(unreachable)


def test_business_cli_list_validate_and_graph(capsys):
    from argparse import Namespace

    assert handle(Namespace(business_cmd="list", module=str(DEMO))) == 0
    assert "login_flow" in capsys.readouterr().out

    assert handle(Namespace(business_cmd="validate", module=str(DEMO), ref=None)) == 0
    assert "[OK] login_flow" in capsys.readouterr().out

    assert handle(Namespace(business_cmd="graph", module=str(DEMO), ref="login_flow",
                            format="json", flow=None)) == 0
    assert '"input_table": "login_flow"' in capsys.readouterr().out


def test_business_cli_coverage_json(tmp_path, capsys):
    from argparse import Namespace

    result = tmp_path / "result.xml"
    result.write_text('''<results><result case_id="TC1" status="PASS"><steps><step action="business_call">
      <business_result ref="login_flow" flow="F_LOGIN_SUCCESS" passed="true">
        <actual_path><node id="open_login"/><node id="submit_login"/><node id="validate_login"/><node id="home"/></actual_path>
      </business_result>
    </step></steps></result></results>''', encoding="utf-8")
    assert handle(Namespace(business_cmd="coverage", module=str(DEMO), ref="login_flow",
                            result=str(result), format="json")) == 0
    output = capsys.readouterr().out
    assert '"covered": 4' in output
    assert '"covered": 1' in output
