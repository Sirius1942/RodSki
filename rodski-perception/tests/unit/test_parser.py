"""单元测试 — ImageParser.parse（mock OllamaClient）。"""

from __future__ import annotations

from unittest.mock import MagicMock

from rodski_perception.parser import ImageParser


def _mock_client(content):
    client = MagicMock()
    client.chat.return_value = {"message": {"content": content}}
    return client


class TestImageParser:
    def test_parses_multiple_elements(self, tiny_png):
        client = _mock_client(
            "["
            '{"bbox_2d":[10,20,30,40],"label":"username","kind":"input"},'
            '{"bbox_2d":[10,60,30,80],"label":"password","kind":"input"},'
            '{"bbox_2d":[10,100,30,120],"label":"login","kind":"button"}'
            "]"
        )
        parser = ImageParser(client=client)
        result = parser.parse(tiny_png)
        assert len(result.elements) == 3
        assert result.elements[0].label == "username"
        assert result.elements[0].kind == "input"
        assert result.elements[2].kind == "button"
        assert result.image_size == (100, 100)
        assert result.latency_ms >= 0
        # 像素坐标转换检查
        # (10/1000)*100=1, (20/1000)*100=2
        assert result.elements[0].bbox == (10, 20, 30, 40)
        assert result.elements[0].coordinates == (2, 3)  # center of (1,2,3,4)

    def test_empty_array_yields_zero_elements(self, tiny_png):
        client = _mock_client("[]")
        parser = ImageParser(client=client)
        result = parser.parse(tiny_png)
        assert result.elements == []
        assert result.image_size == (100, 100)

    def test_unknown_kind_defaults_to_other(self, tiny_png):
        client = _mock_client('[{"bbox_2d":[1,2,3,4],"label":"x"}]')
        parser = ImageParser(client=client)
        result = parser.parse(tiny_png)
        assert result.elements[0].kind == "other"
