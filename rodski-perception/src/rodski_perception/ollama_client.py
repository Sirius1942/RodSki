"""ollama HTTP 客户端封装。

仅实现 rodski-perception 用到的两个端点：

- ``POST /api/chat`` — 多模态对话（VLM 推理）
- ``GET  /api/tags`` — 列出已安装模型

错误统一抛 :class:`OllamaUnreachableError` / :class:`ModelNotFoundError`，
让 CLI 与 backend 转换为合适的退出码 / 异常类。
"""

from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import requests

from .errors import ModelNotFoundError, OllamaUnreachableError

logger = logging.getLogger(__name__)


DEFAULT_OLLAMA_HOST = "http://localhost:11434"

#: 单次推理默认超时（秒）。Qwen3-VL 2B 在 M4 Pro 上约 5-8s，留 60s 给 8B/cold start。
DEFAULT_TIMEOUT_SECONDS = 60

#: list_models / health check 的轻量超时。
DEFAULT_TAGS_TIMEOUT_SECONDS = 3


class OllamaClient:
    """对 ollama HTTP API 的精简包装。

    Parameters
    ----------
    host:
        ollama 服务地址，默认 ``http://localhost:11434``。**不** 包含 ``/v1``
        前缀——本类直接调用原生 ``/api/*`` 端点（Qwen3-VL 的 bbox 输出在
        OpenAI 兼容层会被过滤）。
    timeout:
        chat 推理超时秒数。
    session:
        可选注入 ``requests.Session``，主要用于测试。
    """

    def __init__(
        self,
        host: str = DEFAULT_OLLAMA_HOST,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        session: Optional[requests.Session] = None,
    ) -> None:
        # 去掉尾部斜杠，避免拼接出 ``http://localhost:11434//api/chat``
        self._host = host.rstrip("/")
        self._timeout = timeout
        self._session = session or requests.Session()

    # ------------------------------------------------------------------
    # 公开 API
    # ------------------------------------------------------------------

    @property
    def host(self) -> str:
        return self._host

    def is_reachable(self, timeout: float = DEFAULT_TAGS_TIMEOUT_SECONDS) -> bool:
        """轻量 health check：``GET /api/tags`` 返回 200 即视为可达。

        不抛异常，永远返回 bool；适合 backend.is_available 这种探针场景。
        """
        try:
            r = self._session.get(f"{self._host}/api/tags", timeout=timeout)
            return r.status_code == 200
        except Exception:  # noqa: BLE001
            return False

    def list_models(self, timeout: float = DEFAULT_TAGS_TIMEOUT_SECONDS) -> List[str]:
        """``GET /api/tags`` 返回所有已安装模型名（含 ``:tag`` 后缀）。"""
        try:
            r = self._session.get(f"{self._host}/api/tags", timeout=timeout)
        except requests.exceptions.RequestException as exc:
            raise OllamaUnreachableError(
                f"无法连接 ollama 服务 {self._host}：{exc}\n"
                f"请确认：brew services start ollama  /  ollama serve"
            ) from exc

        if r.status_code != 200:
            raise OllamaUnreachableError(
                f"ollama {self._host} 返回 HTTP {r.status_code}: {r.text[:200]}"
            )

        try:
            payload = r.json()
        except ValueError as exc:
            raise OllamaUnreachableError(
                f"ollama 返回的不是合法 JSON：{r.text[:200]}"
            ) from exc
        models = payload.get("models") or []
        return [m.get("name", "") for m in models if m.get("name")]

    def chat(
        self,
        model: str,
        prompt: str,
        images: Optional[List[Union[str, Path, bytes]]] = None,
        system: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """同步调用 ``POST /api/chat``。

        Parameters
        ----------
        model:
            如 ``qwen3-vl:2b``。
        prompt:
            user 消息正文。
        images:
            列表，每项可以是图片路径（``str`` / ``Path``）或已经是 ``bytes``。
            内部统一编码为 base64。
        system:
            可选 system 消息。
        options:
            透传给 ollama 的 ``options`` 字段，常用 ``{"num_predict": 300,
            "temperature": 0}``。
        timeout:
            覆盖默认 ``self._timeout``。

        Returns
        -------
        ollama 的原始响应字典；最重要的字段是 ``response["message"]["content"]``。

        Raises
        ------
        OllamaUnreachableError:
            网络错误 / 服务不可达 / 非 200 响应。
        ModelNotFoundError:
            响应内容含 ``model.*not found`` / ``unknown model`` 字样
            （ollama 在 HTTP 200 里也可能返回 error 字段）。
        """
        messages: List[Dict[str, Any]] = []
        if system:
            messages.append({"role": "system", "content": system})
        user_msg: Dict[str, Any] = {"role": "user", "content": prompt}
        if images:
            user_msg["images"] = [_encode_image_as_b64(img) for img in images]
        messages.append(user_msg)

        body: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        if options:
            body["options"] = options

        try:
            r = self._session.post(
                f"{self._host}/api/chat",
                json=body,
                timeout=timeout if timeout is not None else self._timeout,
            )
        except requests.exceptions.RequestException as exc:
            raise OllamaUnreachableError(
                f"调用 ollama {self._host}/api/chat 失败：{exc}"
            ) from exc

        if r.status_code == 404:
            raise ModelNotFoundError(
                f"模型 {model!r} 未安装。请运行：ollama pull {model}"
            )
        if r.status_code != 200:
            text = r.text[:300]
            # ollama 把"model not found"在某些版本下用非 200 返回
            if "not found" in text.lower() or "unknown model" in text.lower():
                raise ModelNotFoundError(
                    f"模型 {model!r} 未安装：{text}\n"
                    f"请运行：ollama pull {model}"
                )
            raise OllamaUnreachableError(
                f"ollama {self._host} 返回 HTTP {r.status_code}: {text}"
            )

        try:
            payload = r.json()
        except ValueError as exc:
            raise OllamaUnreachableError(
                f"ollama 返回的不是合法 JSON：{r.text[:200]}"
            ) from exc

        # ollama 偶尔在 200 里塞 error 字段
        if isinstance(payload, dict) and payload.get("error"):
            err = str(payload["error"])
            if "not found" in err.lower() or "unknown model" in err.lower():
                raise ModelNotFoundError(
                    f"模型 {model!r} 未安装：{err}\n"
                    f"请运行：ollama pull {model}"
                )
            raise OllamaUnreachableError(f"ollama 报错：{err}")

        return payload


# ----------------------------------------------------------------------
# 内部工具
# ----------------------------------------------------------------------


def _encode_image_as_b64(image: Union[str, Path, bytes]) -> str:
    """把图片转成 ollama 接受的 base64 字符串。"""
    if isinstance(image, (bytes, bytearray)):
        return base64.b64encode(bytes(image)).decode("ascii")
    path = Path(image)
    if not path.exists():
        raise FileNotFoundError(f"image not found: {path}")
    return base64.b64encode(path.read_bytes()).decode("ascii")


__all__ = [
    "OllamaClient",
    "DEFAULT_OLLAMA_HOST",
    "DEFAULT_TIMEOUT_SECONDS",
]
