"""单元测试 — VLMAgent.locate / locate_many（mock OllamaClient）。"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from rodski_perception.agent import LocateResult, VLMAgent
from rodski_perception.errors import InvalidResponseError


def _mock_client(content: str):
    """构造一个返回固定 content 的 fake OllamaClient。"""
    client = MagicMock()
    client.chat.return_value = {
        "model": "qwen3-vl:2b",
        "message": {"content": content},
        "done": True,
    }
    return client


# ----------------------------------------------------------------------
# locate (single)
# ----------------------------------------------------------------------


class TestLocate:
    def test_single_success(self, tiny_png):
        client = _mock_client('[{"bbox_2d":[100,200,300,400],"label":"login"}]')
        agent = VLMAgent(client=client)
        result = agent.locate(prompt="登录按钮", image=tiny_png)
        assert isinstance(result, LocateResult)
        assert result.bbox == (100, 200, 300, 400)
        assert result.target_description == "登录按钮"
        assert result.label == "login"
        assert result.image_size == (100, 100)
        # 100x100 像素图，bbox (100/1000, 200/1000, 300/1000, 400/1000) 对应像素
        # (10, 20, 30, 40)，中心 (20, 30)
        assert result.coordinates == (20, 30)
        # latency 应该 >= 0
        assert result.latency_ms >= 0

    def test_empty_array_returns_none(self, tiny_png):
        client = _mock_client("[]")
        agent = VLMAgent(client=client)
        assert agent.locate(prompt="不存在", image=tiny_png) is None

    def test_empty_array_with_fence_returns_none(self, tiny_png):
        client = _mock_client("```json\n[]\n```")
        agent = VLMAgent(client=client)
        assert agent.locate(prompt="x", image=tiny_png) is None

    def test_invalid_response_raises(self, tiny_png):
        client = _mock_client("this is just prose, no bbox at all")
        agent = VLMAgent(client=client)
        with pytest.raises(InvalidResponseError):
            agent.locate(prompt="x", image=tiny_png)

    def test_missing_image_raises(self, tmp_path):
        agent = VLMAgent(client=_mock_client("[]"))
        with pytest.raises(FileNotFoundError):
            agent.locate(prompt="x", image=tmp_path / "nope.png")

    def test_element_type_in_prompt(self, tiny_png):
        client = _mock_client('[{"bbox_2d":[0,0,100,100]}]')
        agent = VLMAgent(client=client)
        agent.locate(prompt="登录", image=tiny_png, element_type="button")
        sent_prompt = client.chat.call_args.kwargs["prompt"]
        assert "button" in sent_prompt.lower()


# ----------------------------------------------------------------------
# locate_many
# ----------------------------------------------------------------------


class TestLocateMany:
    def test_single_inference_with_index(self, tiny_png):
        # 模型一次返回三个目标
        client = _mock_client(
            "["
            '{"index":0,"bbox_2d":[10,20,30,40],"label":"a"},'
            '{"index":1,"bbox_2d":[50,60,70,80],"label":"b"},'
            '{"index":2,"bbox_2d":[90,100,110,120],"label":"c"}'
            "]"
        )
        agent = VLMAgent(client=client)
        results = agent.locate_many(
            prompts=["A目标", "B目标", "C目标"], image=tiny_png
        )
        assert len(results) == 3
        assert all(r is not None for r in results)
        assert results[0].target_description == "A目标"
        assert results[1].target_description == "B目标"
        assert results[2].target_description == "C目标"
        # 验证只调用一次 chat（单次推理）
        assert client.chat.call_count == 1

    def test_partial_missing_filled_with_none(self, tiny_png):
        # 模型只返回 index 0 和 2
        client = _mock_client(
            "["
            '{"index":0,"bbox_2d":[10,20,30,40]},'
            '{"index":2,"bbox_2d":[90,100,110,120]}'
            "]"
        )
        agent = VLMAgent(client=client)
        results = agent.locate_many(prompts=["a", "b", "c"], image=tiny_png)
        assert results[0] is not None
        assert results[1] is None
        assert results[2] is not None

    def test_empty_array_all_none(self, tiny_png):
        client = _mock_client("[]")
        agent = VLMAgent(client=client)
        results = agent.locate_many(prompts=["a", "b"], image=tiny_png)
        assert results == [None, None]

    def test_fallback_on_invalid_response(self, tiny_png):
        """单次推理无法解析时 → 退回 N 次串行 locate。"""
        client = MagicMock()
        # 1st call (locate_many 单次推理) — 不可解析
        # 2nd call (fallback locate "a") — 命中
        # 3rd call (fallback locate "b") — 空数组
        client.chat.side_effect = [
            {"message": {"content": "garbage no bbox here"}},
            {"message": {"content": '[{"bbox_2d":[1,2,3,4]}]'}},
            {"message": {"content": "[]"}},
        ]
        agent = VLMAgent(client=client)
        results = agent.locate_many(prompts=["a", "b"], image=tiny_png)
        assert client.chat.call_count == 3
        assert results[0] is not None
        assert results[1] is None

    def test_empty_prompts_returns_empty(self, tiny_png):
        agent = VLMAgent(client=_mock_client("[]"))
        assert agent.locate_many(prompts=[], image=tiny_png) == []

    def test_match_by_label_when_index_missing(self, tiny_png):
        """模型没给 index，但 label 可以模糊匹配回 prompt。"""
        client = _mock_client(
            "["
            '{"bbox_2d":[1,2,3,4],"label":"username field"},'
            '{"bbox_2d":[5,6,7,8],"label":"password field"}'
            "]"
        )
        agent = VLMAgent(client=client)
        results = agent.locate_many(
            prompts=["username input", "password input"],
            image=tiny_png,
        )
        # 至少其中一个被回填（label 包含 prompt 子串）
        non_none = [r for r in results if r is not None]
        assert len(non_none) == 2
