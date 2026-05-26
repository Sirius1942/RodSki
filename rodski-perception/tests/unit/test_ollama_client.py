"""单元测试 — ollama_client.py HTTP mock。"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import requests

from rodski_perception.errors import ModelNotFoundError, OllamaUnreachableError
from rodski_perception.ollama_client import OllamaClient, _encode_image_as_b64


# ----------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------


def _mock_session(*, get_json=None, get_status=200, post_json=None, post_status=200,
                  raise_get=None, raise_post=None):
    session = MagicMock()

    if raise_get is not None:
        session.get.side_effect = raise_get
    else:
        get_resp = MagicMock()
        get_resp.status_code = get_status
        get_resp.json.return_value = get_json or {}
        get_resp.text = str(get_json or "")
        session.get.return_value = get_resp

    if raise_post is not None:
        session.post.side_effect = raise_post
    else:
        post_resp = MagicMock()
        post_resp.status_code = post_status
        post_resp.json.return_value = post_json or {}
        post_resp.text = str(post_json or "")
        session.post.return_value = post_resp

    return session


# ----------------------------------------------------------------------
# is_reachable
# ----------------------------------------------------------------------


class TestIsReachable:
    def test_ok(self):
        session = _mock_session(get_json={"models": []})
        client = OllamaClient(session=session)
        assert client.is_reachable() is True

    def test_connection_error(self):
        session = _mock_session(raise_get=requests.exceptions.ConnectionError())
        client = OllamaClient(session=session)
        assert client.is_reachable() is False

    def test_non_200(self):
        session = _mock_session(get_status=500)
        client = OllamaClient(session=session)
        assert client.is_reachable() is False


# ----------------------------------------------------------------------
# list_models
# ----------------------------------------------------------------------


class TestListModels:
    def test_ok(self, fake_ollama_tags_payload):
        session = _mock_session(get_json=fake_ollama_tags_payload)
        client = OllamaClient(session=session)
        names = client.list_models()
        assert "qwen3-vl:2b" in names
        assert "qwen3-vl:8b" in names
        assert "llama3:8b" in names

    def test_unreachable(self):
        session = _mock_session(raise_get=requests.exceptions.ConnectionError("nope"))
        client = OllamaClient(session=session)
        with pytest.raises(OllamaUnreachableError):
            client.list_models()

    def test_non_200(self):
        session = _mock_session(get_status=503)
        client = OllamaClient(session=session)
        with pytest.raises(OllamaUnreachableError):
            client.list_models()


# ----------------------------------------------------------------------
# chat
# ----------------------------------------------------------------------


class TestChat:
    def test_success(self, fake_ollama_chat_payload):
        session = _mock_session(post_json=fake_ollama_chat_payload)
        client = OllamaClient(session=session)
        out = client.chat(model="qwen3-vl:2b", prompt="hi")
        assert out["message"]["content"].startswith("[")
        # 验证发出的 body
        call_args = session.post.call_args
        assert call_args.kwargs["json"]["model"] == "qwen3-vl:2b"
        assert call_args.kwargs["json"]["stream"] is False
        assert call_args.kwargs["json"]["messages"][0]["content"] == "hi"

    def test_with_images_b64(self, tmp_path, fake_ollama_chat_payload):
        img = tmp_path / "t.png"
        img.write_bytes(b"fake-png-bytes")
        session = _mock_session(post_json=fake_ollama_chat_payload)
        client = OllamaClient(session=session)
        client.chat(model="m", prompt="p", images=[img])
        body = session.post.call_args.kwargs["json"]
        # base64 编码后非空
        assert body["messages"][0]["images"]
        assert isinstance(body["messages"][0]["images"][0], str)

    def test_unreachable(self):
        session = _mock_session(raise_post=requests.exceptions.ConnectionError())
        client = OllamaClient(session=session)
        with pytest.raises(OllamaUnreachableError):
            client.chat(model="m", prompt="p")

    def test_model_not_found_404(self):
        session = _mock_session(post_status=404)
        client = OllamaClient(session=session)
        with pytest.raises(ModelNotFoundError):
            client.chat(model="missing", prompt="p")

    def test_model_not_found_in_text(self):
        session = MagicMock()
        post_resp = MagicMock()
        post_resp.status_code = 500
        post_resp.text = "model 'foo:7b' not found, try pulling it"
        post_resp.json.return_value = {}
        session.post.return_value = post_resp
        client = OllamaClient(session=session)
        with pytest.raises(ModelNotFoundError):
            client.chat(model="foo:7b", prompt="p")

    def test_error_field_in_200(self):
        session = _mock_session(
            post_status=200,
            post_json={"error": "model 'bar' not found"},
        )
        client = OllamaClient(session=session)
        with pytest.raises(ModelNotFoundError):
            client.chat(model="bar", prompt="p")

    def test_options_passed_through(self, fake_ollama_chat_payload):
        session = _mock_session(post_json=fake_ollama_chat_payload)
        client = OllamaClient(session=session)
        client.chat(
            model="m", prompt="p",
            options={"temperature": 0, "num_predict": 99},
        )
        body = session.post.call_args.kwargs["json"]
        assert body["options"] == {"temperature": 0, "num_predict": 99}


# ----------------------------------------------------------------------
# _encode_image_as_b64
# ----------------------------------------------------------------------


class TestEncodeImage:
    def test_bytes(self):
        assert _encode_image_as_b64(b"abc") == "YWJj"

    def test_path(self, tmp_path):
        p = tmp_path / "x.bin"
        p.write_bytes(b"abc")
        assert _encode_image_as_b64(p) == "YWJj"

    def test_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            _encode_image_as_b64(tmp_path / "nope.png")
