"""单元测试 — CLI 入口（subprocess + mock OllamaClient）。"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from rodski_perception.cli import (
    EXIT_ARG_ERROR,
    EXIT_INFERENCE_FAILED,
    EXIT_MODEL_NOT_FOUND,
    EXIT_OK,
    EXIT_OLLAMA_UNREACHABLE,
    main,
)


# ----------------------------------------------------------------------
# 通过 main() 直接调用（in-process），避免每次起子进程的开销
# ----------------------------------------------------------------------


def _mock_chat(content: str):
    """patch OllamaClient.chat 让 ollama_client 直接返回 fake content。"""
    payload = {"model": "qwen3-vl:2b", "message": {"content": content}, "done": True}
    return patch(
        "rodski_perception.ollama_client.OllamaClient.chat",
        return_value=payload,
    )


def _mock_list_models(names):
    return patch(
        "rodski_perception.ollama_client.OllamaClient.list_models",
        return_value=names,
    )


class TestNoCommand:
    def test_help_when_no_args(self, capsys):
        rc = main([])
        # 现在返回 ARG_ERROR + 输出帮助
        assert rc == EXIT_ARG_ERROR


class TestLocateSingle:
    def test_success(self, tiny_png, capsys):
        with _mock_chat('[{"bbox_2d":[100,200,300,400],"label":"login"}]'):
            rc = main([
                "locate",
                "--image", str(tiny_png),
                "--prompt", "登录按钮",
                "--output", "json",
            ])
        assert rc == EXIT_OK
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["target_description"] == "登录按钮"
        assert data["bbox"] == [100, 200, 300, 400]
        assert "coordinates" in data
        assert data["model"] == "qwen3-vl:2b"
        assert data["image_size"] == [100, 100]

    def test_not_found(self, tiny_png, capsys):
        with _mock_chat("[]"):
            rc = main([
                "locate",
                "--image", str(tiny_png),
                "--prompt", "不存在",
                "--output", "json",
            ])
        assert rc == EXIT_OK  # 找不到也算成功完成
        data = json.loads(capsys.readouterr().out)
        assert data["bbox"] is None
        assert data["error"] == "not found"

    def test_missing_image(self, capsys, tmp_path):
        rc = main([
            "locate",
            "--image", str(tmp_path / "missing.png"),
            "--prompt", "x",
        ])
        assert rc == EXIT_ARG_ERROR

    def test_no_prompt(self, capsys, tiny_png):
        rc = main(["locate", "--image", str(tiny_png)])
        assert rc == EXIT_ARG_ERROR


class TestLocateMany:
    def test_multiple_prompts(self, tiny_png, capsys):
        # 单次推理返回 2 个
        content = (
            "["
            '{"index":0,"bbox_2d":[10,20,30,40],"label":"a"},'
            '{"index":1,"bbox_2d":[50,60,70,80],"label":"b"}'
            "]"
        )
        with _mock_chat(content):
            rc = main([
                "locate",
                "--image", str(tiny_png),
                "--prompt", "用户名",
                "--prompt", "密码",
                "--output", "json",
            ])
        assert rc == EXIT_OK
        data = json.loads(capsys.readouterr().out)
        assert "results" in data
        assert len(data["results"]) == 2
        assert data["results"][0]["target_description"] == "用户名"
        assert data["results"][1]["target_description"] == "密码"

    def test_prompts_file(self, tiny_png, tmp_path, capsys):
        pf = tmp_path / "prompts.txt"
        pf.write_text("用户名\n密码\n# comment\n\n登录\n", encoding="utf-8")
        content = "["
        for i in range(3):
            if i:
                content += ","
            content += f'{{"index":{i},"bbox_2d":[{i*10},{i*10},{i*10+5},{i*10+5}]}}'
        content += "]"
        with _mock_chat(content):
            rc = main([
                "locate",
                "--image", str(tiny_png),
                "--prompts-file", str(pf),
                "--output", "json",
            ])
        assert rc == EXIT_OK
        data = json.loads(capsys.readouterr().out)
        assert len(data["results"]) == 3

    def test_prompt_and_prompts_file_mutex(self, tiny_png, tmp_path):
        pf = tmp_path / "p.txt"
        pf.write_text("a")
        rc = main([
            "locate",
            "--image", str(tiny_png),
            "--prompt", "x",
            "--prompts-file", str(pf),
        ])
        assert rc == EXIT_ARG_ERROR


class TestErrorExitCodes:
    def test_unreachable_3(self, tiny_png):
        from rodski_perception.errors import OllamaUnreachableError
        with patch(
            "rodski_perception.ollama_client.OllamaClient.chat",
            side_effect=OllamaUnreachableError("nope"),
        ):
            rc = main([
                "locate",
                "--image", str(tiny_png),
                "--prompt", "x",
            ])
        assert rc == EXIT_OLLAMA_UNREACHABLE

    def test_model_not_found_4(self, tiny_png):
        from rodski_perception.errors import ModelNotFoundError
        with patch(
            "rodski_perception.ollama_client.OllamaClient.chat",
            side_effect=ModelNotFoundError("missing"),
        ):
            rc = main([
                "locate",
                "--image", str(tiny_png),
                "--prompt", "x",
            ])
        assert rc == EXIT_MODEL_NOT_FOUND

    def test_inference_failed_1(self, tiny_png):
        # 模型返回不可解析（且不是空数组）
        with _mock_chat("totally not parseable junk text"):
            rc = main([
                "locate",
                "--image", str(tiny_png),
                "--prompt", "x",
            ])
        assert rc == EXIT_INFERENCE_FAILED


class TestModels:
    def test_filters_vl_only(self, capsys):
        with _mock_list_models(["qwen3-vl:2b", "qwen3-vl:8b", "llama3:8b"]):
            rc = main(["models", "--output", "text"])
        assert rc == EXIT_OK
        out = capsys.readouterr().out
        assert "qwen3-vl:2b" in out
        assert "llama3:8b" not in out

    def test_all_flag(self, capsys):
        with _mock_list_models(["qwen3-vl:2b", "llama3:8b"]):
            rc = main(["models", "--all", "--output", "json"])
        out = capsys.readouterr().out
        data = json.loads(out)
        assert "llama3:8b" in data["models"]

    def test_unreachable(self, capsys):
        from rodski_perception.errors import OllamaUnreachableError
        with patch(
            "rodski_perception.ollama_client.OllamaClient.list_models",
            side_effect=OllamaUnreachableError("nope"),
        ):
            rc = main(["models"])
        assert rc == EXIT_OLLAMA_UNREACHABLE


class TestEvalStub:
    def test_returns_arg_error(self, capsys):
        rc = main(["eval", "--dataset", "/tmp/x"])
        # dataset not found → EXIT_ARG_ERROR
        assert rc == EXIT_ARG_ERROR
        assert "not found" in capsys.readouterr().err


# ----------------------------------------------------------------------
# 真正起 subprocess 验证一次（也覆盖 console_script entry）
# 仅测 --version 和 --help，避免依赖网络/模型
# ----------------------------------------------------------------------


class TestSubprocessSmoke:
    def test_version(self):
        r = subprocess.run(
            [sys.executable, "-m", "rodski_perception.cli", "--version"],
            capture_output=True, text=True, timeout=10,
        )
        assert r.returncode == 0
        assert "rodski-perception" in r.stdout

    def test_help(self):
        r = subprocess.run(
            [sys.executable, "-m", "rodski_perception.cli", "--help"],
            capture_output=True, text=True, timeout=10,
        )
        assert r.returncode == 0
        assert "locate" in r.stdout
        assert "parse" in r.stdout
        assert "models" in r.stdout
