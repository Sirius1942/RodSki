"""RestHelper 单元测试

测试 api/rest_helper.py 中的 HTTP 请求辅助类。
覆盖：send_request（GET/POST/PUT/DELETE）、请求头组装、
      JSON body 序列化、响应解析、超时处理、重试机制。
所有 HTTP 请求通过 mock 隔离。
"""
import pytest
from unittest.mock import MagicMock, patch, Mock
from datetime import timedelta
import requests
from api.rest_helper import RestHelper


class TestValidateJsonSchema:
    def test_valid_schema(self):
        data = {"name": "Alice", "age": 30}
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
            },
            "required": ["name", "age"],
        }
        assert RestHelper.validate_json_schema(data, schema) is True

    def test_invalid_schema(self):
        data = {"name": 123}
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
        }
        assert RestHelper.validate_json_schema(data, schema) is False


class TestJsonpathExtract:
    def test_simple_path(self):
        data = {"user": {"name": "Alice"}}
        assert RestHelper.jsonpath_extract(data, "$.user.name") == "Alice"

    def test_nested_path(self):
        data = {"a": {"b": {"c": 42}}}
        assert RestHelper.jsonpath_extract(data, "$.a.b.c") == 42

    def test_missing_key(self):
        data = {"user": {"name": "Alice"}}
        assert RestHelper.jsonpath_extract(data, "$.user.email") is None

    def test_root_level(self):
        data = {"status": "ok"}
        assert RestHelper.jsonpath_extract(data, "$.status") == "ok"

    def test_non_dict_intermediate(self):
        data = {"user": "just a string"}
        assert RestHelper.jsonpath_extract(data, "$.user.name") is None


class TestSendRequest:
    @patch("api.rest_helper.RestHelper._get_session")
    def test_get_request(self, mock_get_session):
        mock_session = Mock()
        mock_resp = MagicMock(status_code=200, elapsed=timedelta(milliseconds=100))
        mock_session.request.return_value = mock_resp
        mock_get_session.return_value = mock_session

        resp = RestHelper.send_request("GET", "https://api.example.com/users")
        mock_session.request.assert_called_once_with(
            "GET",
            "https://api.example.com/users",
            headers=None,
            timeout=30.0,
        )
        assert resp.status_code == 200

    @patch("api.rest_helper.RestHelper._get_session")
    def test_post_request_with_body(self, mock_get_session):
        mock_session = Mock()
        mock_resp = MagicMock(status_code=201, elapsed=timedelta(milliseconds=100))
        mock_session.request.return_value = mock_resp
        mock_get_session.return_value = mock_session

        body = {"name": "test"}
        resp = RestHelper.send_request(
            "POST", "https://api.example.com/users", body=body
        )
        mock_session.request.assert_called_once_with(
            "POST",
            "https://api.example.com/users",
            headers=None,
            timeout=30.0,
            json=body,
        )
        assert resp.status_code == 201

    @patch("api.rest_helper.RestHelper._get_session")
    def test_put_with_headers(self, mock_get_session):
        mock_session = Mock()
        mock_session.request.return_value = MagicMock(status_code=200, elapsed=timedelta(milliseconds=100))
        mock_get_session.return_value = mock_session

        headers = {"Authorization": "Bearer xyz"}
        RestHelper.send_request(
            "put", "https://api.example.com/users/1",
            headers=headers, body={"name": "updated"}
        )
        mock_session.request.assert_called_once_with(
            "PUT",
            "https://api.example.com/users/1",
            headers=headers,
            timeout=30.0,
            json={"name": "updated"},
        )

    @patch("api.rest_helper.RestHelper._get_session")
    def test_delete_request(self, mock_get_session):
        mock_session = Mock()
        mock_session.request.return_value = MagicMock(status_code=204, elapsed=timedelta(milliseconds=100))
        mock_get_session.return_value = mock_session

        resp = RestHelper.send_request("DELETE", "https://api.example.com/users/1")
        mock_session.request.assert_called_once_with(
            "DELETE",
            "https://api.example.com/users/1",
            headers=None,
            timeout=30.0,
        )

    @patch("api.rest_helper.RestHelper._get_session")
    def test_custom_timeout(self, mock_get_session):
        mock_session = Mock()
        mock_session.request.return_value = MagicMock(elapsed=timedelta(milliseconds=100))
        mock_get_session.return_value = mock_session

        RestHelper.send_request("GET", "https://api.example.com", timeout=5.0)
        mock_session.request.assert_called_once_with(
            "GET",
            "https://api.example.com",
            headers=None,
            timeout=5.0,
        )


class TestAssertResponseTime:
    def test_fast_response(self):
        resp = MagicMock()
        resp.elapsed = timedelta(milliseconds=50)
        assert RestHelper.assert_response_time(resp, 100) is True

    def test_slow_response(self):
        resp = MagicMock()
        resp.elapsed = timedelta(milliseconds=500)
        assert RestHelper.assert_response_time(resp, 100) is False

    def test_exact_boundary(self):
        resp = MagicMock()
        resp.elapsed = timedelta(milliseconds=100)
        assert RestHelper.assert_response_time(resp, 100) is True


class TestExtractHeaders:
    def test_existing_header(self):
        resp = MagicMock()
        resp.headers = {"Content-Type": "application/json", "X-Request-Id": "abc123"}
        assert RestHelper.extract_headers(resp, "Content-Type") == "application/json"

    def test_missing_header(self):
        resp = MagicMock()
        resp.headers = {"Content-Type": "application/json"}
        assert RestHelper.extract_headers(resp, "X-Missing") is None

    def test_custom_header(self):
        resp = MagicMock()
        resp.headers = {"X-Custom": "value123"}
        assert RestHelper.extract_headers(resp, "X-Custom") == "value123"


class TestCompareResponses:
    def test_identical_responses(self):
        r1 = {"id": 1, "name": "Alice"}
        r2 = {"id": 1, "name": "Alice"}
        assert RestHelper.compare_responses(r1, r2) is True

    def test_different_responses(self):
        r1 = {"id": 1, "name": "Alice"}
        r2 = {"id": 1, "name": "Bob"}
        assert RestHelper.compare_responses(r1, r2) is False

    def test_ignore_fields(self):
        r1 = {"id": 1, "name": "Alice", "timestamp": "2026-01-01"}
        r2 = {"id": 1, "name": "Alice", "timestamp": "2026-03-17"}
        assert RestHelper.compare_responses(r1, r2, ignore_fields=["timestamp"]) is True

    def test_ignore_multiple_fields(self):
        r1 = {"id": 1, "name": "Alice", "ts": "a", "version": 1}
        r2 = {"id": 1, "name": "Alice", "ts": "b", "version": 2}
        assert RestHelper.compare_responses(r1, r2, ignore_fields=["ts", "version"]) is True

    def test_nested_comparison(self):
        r1 = {"user": {"id": 1, "name": "Alice"}}
        r2 = {"user": {"id": 1, "name": "Alice"}}
        assert RestHelper.compare_responses(r1, r2) is True

    def test_nested_ignore_fields(self):
        r1 = {"user": {"id": 1, "created": "a"}}
        r2 = {"user": {"id": 1, "created": "b"}}
        assert RestHelper.compare_responses(r1, r2, ignore_fields=["created"]) is True

    def test_list_values(self):
        r1 = {"items": [1, 2, 3]}
        r2 = {"items": [1, 2, 3]}
        assert RestHelper.compare_responses(r1, r2) is True

    def test_different_list_values(self):
        r1 = {"items": [1, 2, 3]}
        r2 = {"items": [1, 2, 4]}
        assert RestHelper.compare_responses(r1, r2) is False

    def test_empty_ignore_fields(self):
        r1 = {"a": 1}
        r2 = {"a": 2}
        assert RestHelper.compare_responses(r1, r2, ignore_fields=[]) is False


class TestEdgeCases:
    def test_empty_data_schema_validation(self):
        assert RestHelper.validate_json_schema({}, {"type": "object"}) is True

    def test_jsonpath_empty_string(self):
        assert RestHelper.jsonpath_extract({"a": ""}, "$.a") == ""

    def test_jsonpath_zero_value(self):
        assert RestHelper.jsonpath_extract({"count": 0}, "$.count") == 0

    @patch("api.rest_helper.requests.request")
    def test_request_exception_handling(self, mock_request):
        mock_request.side_effect = Exception("Network error")
        with pytest.raises(Exception):
            RestHelper.send_request("GET", "https://api.example.com")

    def test_response_time_zero(self):
        resp = MagicMock()
        resp.elapsed = timedelta(milliseconds=0)
        assert RestHelper.assert_response_time(resp, 100) is True

    def test_compare_empty_dicts(self):
        assert RestHelper.compare_responses({}, {}) is True


class TestSessionAndRetry:
    def test_get_session_default(self):
        session = RestHelper._get_session()
        assert isinstance(session, requests.Session)
        assert "http://" in session.adapters
        assert "https://" in session.adapters

    def test_get_session_custom_retries(self):
        session = RestHelper._get_session(max_retries=5)
        assert isinstance(session, requests.Session)

    @patch("api.rest_helper.RestHelper._get_session")
    @patch("api.rest_helper.requests.Session.request")
    def test_send_request_with_session(self, mock_request, mock_get_session):
        mock_session = Mock()
        mock_resp = MagicMock(status_code=200, elapsed=timedelta(milliseconds=100))
        mock_session.request.return_value = mock_resp
        mock_get_session.return_value = mock_session

        resp = RestHelper.send_request("GET", "https://api.example.com", use_session=True)
        mock_get_session.assert_called_once()
        assert resp.status_code == 200

    @patch("api.rest_helper.requests.request")
    def test_send_request_without_session(self, mock_request):
        mock_resp = MagicMock(status_code=200, elapsed=timedelta(milliseconds=100))
        mock_request.return_value = mock_resp

        resp = RestHelper.send_request("GET", "https://api.example.com", use_session=False)
        mock_request.assert_called_once()
        assert resp.status_code == 200

    @patch("api.rest_helper.RestHelper._get_session")
    def test_timeout_error(self, mock_get_session):
        mock_session = Mock()
        mock_session.request.side_effect = requests.exceptions.Timeout("Timeout")
        mock_get_session.return_value = mock_session

        with pytest.raises(requests.exceptions.Timeout):
            RestHelper.send_request("GET", "https://api.example.com")

    @patch("api.rest_helper.RestHelper._get_session")
    def test_connection_error(self, mock_get_session):
        mock_session = Mock()
        mock_session.request.side_effect = requests.exceptions.ConnectionError("Connection failed")
        mock_get_session.return_value = mock_session

        with pytest.raises(requests.exceptions.ConnectionError):
            RestHelper.send_request("GET", "https://api.example.com")

    @patch("api.rest_helper.RestHelper._get_session")
    def test_request_exception(self, mock_get_session):
        mock_session = Mock()
        mock_session.request.side_effect = requests.exceptions.RequestException("Request failed")
        mock_get_session.return_value = mock_session

        with pytest.raises(requests.exceptions.RequestException):
            RestHelper.send_request("GET", "https://api.example.com")
