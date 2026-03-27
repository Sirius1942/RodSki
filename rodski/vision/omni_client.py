"""OmniParser HTTP client.

Sends a base64-encoded screenshot to the OmniParser REST service and returns
a list of parsed UI elements with normalised bounding boxes.
"""

from __future__ import annotations

import base64
import logging
import time
from io import BytesIO
from pathlib import Path
from typing import Any, Union

import requests

from .exceptions import OmniParserError

logger = logging.getLogger(__name__)

_DEFAULT_URL = "http://localhost:8001/parse/"
_DEFAULT_TIMEOUT = 10  # seconds
_DEFAULT_RETRY = 2
_DEFAULT_BOX_THRESHOLD = 0.18
_DEFAULT_IOU_THRESHOLD = 0.7

# Type alias for screenshot input
ScreenshotInput = Union[str, Path, bytes, Any]  # Any for PIL Image


class OmniClient:
    """Thin HTTP wrapper around the OmniParser inference endpoint.

    Args:
        url: Full URL of the OmniParser service (default: http://localhost:8001/parse/).
        timeout: Request timeout in seconds (default: 10).
        retry: Number of retry attempts on failure (default: 2).
    """

    def __init__(
        self,
        url: str = _DEFAULT_URL,
        timeout: int = _DEFAULT_TIMEOUT,
        retry: int = _DEFAULT_RETRY,
    ) -> None:
        self.url = url.rstrip('/') if not url.endswith('/parse/') else url
        self.timeout = timeout
        self.retry = retry

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(
        self,
        screenshot: ScreenshotInput,
        box_threshold: float = _DEFAULT_BOX_THRESHOLD,
        iou_threshold: float = _DEFAULT_IOU_THRESHOLD,
    ) -> list[dict[str, Any]]:
        """Send screenshot to OmniParser and return parsed elements.

        Args:
            screenshot: Screenshot input, can be:
                - str or Path: file path to PNG/JPEG image
                - bytes: raw image bytes
                - PIL.Image.Image: PIL Image object
            box_threshold: Confidence threshold for bounding-box detection.
            iou_threshold: IoU threshold used for NMS.

        Returns:
            A list of dicts, each with keys:
            ``type``, ``content``, ``bbox`` (normalised [x1,y1,x2,y2]),
            ``interactivity``.

        Raises:
            FileNotFoundError: If screenshot is a path and file does not exist.
            OmniParserError: If the service returns a non-200 status or an
                unexpected response schema.
            requests.Timeout: If all retry attempts exceed timeout.
        """
        b64 = self._encode_image(screenshot)
        payload = {
            "base64_image": b64,
            "box_threshold": box_threshold,
            "iou_threshold": iou_threshold,
        }

        last_exception: Exception | None = None
        for attempt in range(self.retry + 1):
            try:
                logger.debug("POST %s (timeout=%ss, attempt=%d/%d)",
                           self.url, self.timeout, attempt + 1, self.retry + 1)
                response = requests.post(self.url, json=payload, timeout=self.timeout)

                if response.status_code != 200:
                    raise OmniParserError(
                        url=self.url,
                        status_code=response.status_code,
                        message=f"OmniParser returned HTTP {response.status_code}: {response.text[:200]}"
                    )

                data = response.json()
                parsed = data.get("parsed_content_list")
                if parsed is None:
                    raise OmniParserError(
                        url=self.url,
                        message=f"Response missing 'parsed_content_list' key. Keys: {list(data.keys())}"
                    )

                logger.debug(
                    "OmniParser latency=%.3fs, elements=%d",
                    data.get("latency", 0.0),
                    len(parsed),
                )
                return parsed

            except requests.Timeout as e:
                last_exception = e
                logger.warning(
                    "OmniParser request timed out (attempt %d/%d): %s",
                    attempt + 1, self.retry + 1, e
                )
                if attempt < self.retry:
                    time.sleep(0.5 * (attempt + 1))  # Exponential backoff
                continue

            except OmniParserError:
                raise

            except requests.RequestException as e:
                last_exception = e
                logger.warning(
                    "OmniParser request failed (attempt %d/%d): %s",
                    attempt + 1, self.retry + 1, e
                )
                if attempt < self.retry:
                    time.sleep(0.5 * (attempt + 1))
                continue

        # All retries exhausted
        if isinstance(last_exception, requests.Timeout):
            raise last_exception
        raise OmniParserError(
            url=self.url,
            message=f"All {self.retry + 1} attempts failed. Last error: {last_exception}"
        )

    def health_check(self) -> bool:
        """Check if the OmniParser service is available.

        Returns:
            True if service is healthy, False otherwise.
        """
        # Try to hit the base URL or a health endpoint
        base_url = self.url.rsplit('/parse/', 1)[0] if '/parse/' in self.url else self.url
        health_url = f"{base_url}/health"

        try:
            response = requests.get(health_url, timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            # Try the parse endpoint with minimal data
            try:
                # Create a minimal 1x1 PNG for health check
                tiny_png = base64.b64decode(
                    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8"
                    "z8BQDwADhQGAWjR9awAAAABJRU5ErkJggg=="
                )
                payload = {"base64_image": base64.b64encode(tiny_png).decode("utf-8")}
                response = requests.post(self.url, json=payload, timeout=5)
                return response.status_code == 200
            except requests.RequestException:
                return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _encode_image(screenshot: ScreenshotInput) -> str:
        """Convert screenshot input to base64-encoded string.

        Args:
            screenshot: File path (str/Path), bytes, or PIL Image.

        Returns:
            Base64-encoded string.

        Raises:
            FileNotFoundError: If file path does not exist.
            TypeError: If input type is not supported.
        """
        if isinstance(screenshot, (str, Path)):
            path = Path(screenshot)
            if not path.exists():
                raise FileNotFoundError(f"Screenshot not found: {screenshot}")
            with open(path, "rb") as fh:
                return base64.b64encode(fh.read()).decode("utf-8")

        elif isinstance(screenshot, bytes):
            return base64.b64encode(screenshot).decode("utf-8")

        else:
            # Try PIL Image
            try:
                from PIL import Image
                if isinstance(screenshot, Image.Image):
                    buffer = BytesIO()
                    # Preserve original format or default to PNG
                    fmt = screenshot.format or "PNG"
                    screenshot.save(buffer, format=fmt)
                    return base64.b64encode(buffer.getvalue()).decode("utf-8")
            except ImportError:
                pass

            raise TypeError(
                f"Unsupported screenshot type: {type(screenshot).__name__}. "
                "Expected str/Path (file path), bytes, or PIL.Image.Image."
            )
