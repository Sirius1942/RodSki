import pytest
from pathlib import Path
from core.model_parser import ModelParser


@pytest.fixture
def model_parser():
    xml_path = Path(__file__).parent.parent / "examples" / "product" / "DEMO" / "demo_site" / "model" / "model.xml"
    return ModelParser(str(xml_path))


def test_get_element_with_id(model_parser):
    result = model_parser.get_element("Login.username")
    assert result['locator_type'] == 'id'
    assert result['locator_value'] == 'username'
    assert result['driver_type'] == 'web'


def test_get_element_with_xpath(model_parser):
    result = model_parser.get_element("HomePage.logoutBtn")
    assert result['locator_type'] == 'xpath'
    assert result['locator_value'] == "//a[text()='Logout']"


def test_get_model(model_parser):
    model = model_parser.get_model("Login")
    assert model is not None
    assert "username" in model
    assert "password" in model
    assert "loginBtn" in model


def test_get_model_driver_type(model_parser):
    assert model_parser.get_model_driver_type("Login") == "web"
    assert model_parser.get_model_driver_type("LoginAPI") == "interface"


def test_get_element_not_found(model_parser):
    result = model_parser.get_element("Login.NonExistent")
    assert result is None


def test_get_element_model_not_found(model_parser):
    result = model_parser.get_element("NonExistentPage.Element")
    assert result is None


def test_get_element_invalid_format(model_parser):
    result = model_parser.get_element("InvalidFormat")
    assert result is None


def test_interface_model(model_parser):
    model = model_parser.get_model("LoginAPI")
    assert model is not None
    assert "_method" in model
    assert "_url" in model
    assert "username" in model
    assert model["_method"]["driver_type"] == "interface"
