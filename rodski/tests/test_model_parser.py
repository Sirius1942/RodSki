import pytest
from pathlib import Path
from core.model_parser import ModelParser


@pytest.fixture
def model_parser():
    xml_path = Path(__file__).parent.parent / "examples" / "product" / "model.xml"
    return ModelParser(str(xml_path))


def test_get_element_with_id(model_parser):
    result = model_parser.get_element("LoginPage.UsernameInput")
    assert result == {'locator_type': 'id', 'locator_value': 'username'}


def test_get_element_with_name(model_parser):
    result = model_parser.get_element("LoginPage.PasswordInput")
    assert result == {'locator_type': 'name', 'locator_value': 'password'}


def test_get_element_with_xpath(model_parser):
    result = model_parser.get_element("LoginPage.LoginButton")
    assert result == {'locator_type': 'xpath', 'locator_value': "//button[@type='submit']"}


def test_get_element_with_css(model_parser):
    result = model_parser.get_element("LoginPage.ErrorMessage")
    assert result == {'locator_type': 'css', 'locator_value': '.error-msg'}


def test_get_element_from_different_model(model_parser):
    result = model_parser.get_element("HomePage.WelcomeText")
    assert result == {'locator_type': 'id', 'locator_value': 'welcome'}


def test_get_element_not_found(model_parser):
    result = model_parser.get_element("LoginPage.NonExistent")
    assert result is None


def test_get_element_model_not_found(model_parser):
    result = model_parser.get_element("NonExistentPage.Element")
    assert result is None


def test_get_element_invalid_format(model_parser):
    result = model_parser.get_element("InvalidFormat")
    assert result is None
