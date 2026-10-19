"""BUG-A20：接口返回数据中 status 恒为 HTTP 状态码"""
from api.rest_helper import build_http_result


def test_body_status_does_not_override_http_status():
    r = build_http_result(200, {"status": "shipped", "id": 7})
    assert r["status"] == 200
    assert r["id"] == 7
    assert r["body"] == {"status": "shipped", "id": 7}


def test_plain_dict_body_flattened_without_body_key():
    assert build_http_result(201, {"created": True}) == {"created": True, "status": 201}


def test_non_object_and_empty_bodies():
    assert build_http_result(200, [1, 2]) == {"body": [1, 2], "status": 200}
    assert build_http_result(200, "pong") == {"body": "pong", "status": 200}
    assert build_http_result(204, None) == {"status": 204}
