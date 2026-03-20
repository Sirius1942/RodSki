"""集成测试：API 工作流程"""
import pytest
from api.rest_helper import RestHelper


@pytest.fixture
def api():
    """API 关键字实例"""
    return RestHelper()


def test_api_request_get(api):
    """测试 GET 请求"""
    response = api.send_request("GET", "https://httpbin.org/get")
    assert response.status_code == 200
    assert "url" in response.json()


def test_api_request_post(api):
    """测试 POST 请求"""
    body = {"name": "test", "value": 123}
    response = api.send_request("POST", "https://httpbin.org/post", body=body)
    assert response.status_code == 200
    data = response.json()
    assert data["json"]["name"] == "test"


def test_api_headers(api):
    """测试请求头"""
    headers = {"X-Custom-Header": "test-value"}
    response = api.send_request("GET", "https://httpbin.org/headers", headers=headers)
    assert response.status_code == 200
    assert "X-Custom-Header" in response.json()["headers"]


def test_jsonpath_extract(api):
    """测试 JSONPath 提取"""
    data = {"user": {"name": "Alice", "age": 30}}
    assert api.jsonpath_extract(data, "$.user.name") == "Alice"
    assert api.jsonpath_extract(data, "$.user.age") == 30


def test_json_schema_validation(api):
    """测试 JSON Schema 验证"""
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"]
    }
    assert api.validate_json_schema({"name": "test"}, schema) is True
    assert api.validate_json_schema({}, schema) is False


def test_response_time_assertion(api):
    """测试响应时间断言"""
    response = api.send_request("GET", "https://httpbin.org/get")
    # 正常请求应该在 5 秒内完成
    assert api.assert_response_time(response, 5000) is True
    # 但不应该在 1 毫秒内完成
    assert api.assert_response_time(response, 1) is False
