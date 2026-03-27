"""Screenshot utilities for RodSki vision layer.

Provides two capture backends:

* **Web** – delegates to a Selenium ``WebDriver`` instance.
* **Desktop** – uses ``pyautogui`` to take a full-screen screenshot on
  Windows or macOS.

Also includes ``auto_cleanup`` for keeping screenshot directories tidy.
"""

from __future__ import annotations

import logging
import os
import platform
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Web screenshot
# ---------------------------------------------------------------------------

def capture_web(driver: Any, output_path: str) -> str:
    """Take a screenshot via a Selenium WebDriver and save it to *output_path*.

    Args:
        driver: A ``selenium.webdriver.*`` instance that supports
            ``save_screenshot``.
        output_path: Destination file path (PNG recommended).

    Returns:
        The resolved absolute path of the saved screenshot.

    Raises:
        RuntimeError: If the driver fails to save the screenshot.
    """
    path = Path(output_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)

    success = driver.save_screenshot(str(path))
    if not success:
        raise RuntimeError(f"Selenium save_screenshot returned False for {path}")

    logger.debug("Web screenshot saved: %s", path)
    return str(path)


# ---------------------------------------------------------------------------
# Desktop screenshot
# ---------------------------------------------------------------------------

def capture_desktop(output_path: str) -> str:
    """Take a full-screen screenshot and save it to *output_path*.

    Supports Windows and macOS via ``pyautogui``.  The output directory is
    created automatically if it does not exist.

    Args:
        output_path: Destination file path (PNG recommended).

    Returns:
        The resolved absolute path of the saved screenshot.

    Raises:
        ImportError: If ``pyautogui`` is not installed.
        RuntimeError: If the screenshot capture fails.
    """
    try:
        import pyautogui  # type: ignore[import]
    except ImportError as exc:
        raise ImportError(
            "pyautogui is required for desktop screenshots. "
            "Install it with: pip install pyautogui"
        ) from exc

    path = Path(output_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)

    system = platform.system()
    logger.debug("Capturing desktop screenshot on %s -> %s", system, path)

    screenshot = pyautogui.screenshot()
    screenshot.save(str(path))

    if not path.exists():
        raise RuntimeError(f"Screenshot file was not created at {path}")

    logger.debug("Desktop screenshot saved: %s", path)
    return str(path)


# ---------------------------------------------------------------------------
# Auto-cleanup
# ---------------------------------------------------------------------------

def auto_cleanup(directory: str, max_files: int = 20) -> int:
    """Remove old screenshot files from *directory* keeping at most *max_files*.

    Files are sorted by modification time (oldest first) and the oldest
    ones beyond the *max_files* limit are deleted.

    Args:
        directory: Path to the directory to clean up.
        max_files: Maximum number of files to retain (default 20).

    Returns:
        Number of files deleted.

    Raises:
        ValueError: If *max_files* is less than 1.
    """
    if max_files < 1:
        raise ValueError(f"max_files must be >= 1, got {max_files}")

    dir_path = Path(directory)
    if not dir_path.is_dir():
        logger.debug("auto_cleanup: directory does not exist: %s", dir_path)
        return 0

    # Collect image files only
    extensions = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
    files = [
        f for f in dir_path.iterdir()
        if f.is_file() and f.suffix.lower() in extensions
    ]

    if len(files) <= max_files:
        return 0

    # Sort oldest-first
    files.sort(key=lambda f: f.stat().st_mtime)
    to_delete = files[: len(files) - max_files]

    deleted = 0
    for f in to_delete:
        try:
            f.unlink()
            deleted += 1
            logger.debug("Deleted old screenshot: %s", f)
        except OSError as exc:
            logger.warning("Could not delete %s: %s", f, exc)

    logger.info("auto_cleanup: deleted %d file(s) from %s", deleted, dir_path)
    return deleted
