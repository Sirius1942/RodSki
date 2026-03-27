"""OmniParser HTTP client.

Sends a base64-encoded screenshot to the OmniParser REST service and returns
a list of parsed UI elements with normalised bounding boxes.
"""

from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)

_DEFAULT_URL = "http://14.103.175.167:7862/parse/"
_DEFAULT_TIMEOUT = 5  # seconds
_DEFAULT_BOX_THRESHOLD = 0.18
_DEFAULT_IOU_THRESHOLD = 0.7


class OmniParserError(Exception):
    """Raised when the OmniParser service returns an unexpected response."""


class OmniClient:
    """Thin HTTP wrapper around the OmniParser inference endpoint.

    Args:
        url: Full URL of the /parse/ endpoint.
        timeout: Request timeout in seconds (default 5).
    """

    def __init__(
        self,
        url: str = _DEFAULT_URL,
        timeout: int = _DEFAULT_TIMEOUT,
    ) -> None:
        self.url = url
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(
        self,
        screenshot_path: str,
        box_threshold: float = _DEFAULT_BOX_THRESHOLD,
        iou_threshold: float = _DEFAULT_IOU_THRESHOLD,
    ) -> list[dict[str, Any]]:
        """Send *screenshot_path* to OmniParser and return parsed elements.

        Args:
            screenshot_path: Absolute or relative path to the PNG/JPEG file.
            box_threshold: Confidence threshold for bounding-box detection.
            iou_threshold: IoU threshold used for NMS.

        Returns:
            A list of dicts, each with keys:
            ``type``, ``content``, ``bbox`` (normalised [x1,y1,x2,y2]),
            ``interactivity``.

        Raises:
            FileNotFoundError: If *screenshot_path* does not exist.
            OmniParserError: If the service returns a non-200 status or an
                unexpected response schema.
            requests.Timeout: If the request exceeds *self.timeout* seconds.
        """
        path = Path(screenshot_path)
        if not path.exists():
            raise FileNotFoundError(f"Screenshot not found: {screenshot_path}")

        b64 = self._encode_image(path)
        payload = {
            "base64_image": b64,
            "box_threshold": box_threshold,
            "iou_threshold": iou_threshold,
        }

        logger.debug("POST %s (timeout=%ss)", self.url, self.timeout)
        response = requests.post(self.url, json=payload, timeout=self.timeout)

        if response.status_code != 200:
            raise OmniParserError(
                f"OmniParser returned HTTP {response.status_code}: {response.text[:200]}"
            )

        data = response.json()
        parsed = data.get("parsed_content_list")
        if parsed is None:
            raise OmniParserError(
                f"Response missing 'parsed_content_list' key. Keys: {list(data.keys())}"
            )

        logger.debug(
            "OmniParser latency=%.3fs, elements=%d",
            data.get("latency", 0.0),
            len(parsed),
        )
        return parsed

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _encode_image(path: Path) -> str:
        """Read *path* and return a base64-encoded string."""
        with open(path, "rb") as fh:
            return base64.b64encode(fh.read()).decode("utf-8")
