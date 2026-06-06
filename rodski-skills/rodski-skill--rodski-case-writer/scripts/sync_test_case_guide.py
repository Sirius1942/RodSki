#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path


DEFAULT_URL = os.environ.get(
    "RODSKI_TEST_CASE_GUIDE_URL",
    "https://raw.githubusercontent.com/Sirius1942/RodSki/main/"
    "rodski/docs/TEST_CASE_WRITING_GUIDE.md",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="在 RodSki 版本检查后同步 TEST_CASE_WRITING_GUIDE.md。"
    )
    parser.add_argument("--repo", default=str(Path.home() / "TestCase"), help="RodSki 测试仓库根目录。")
    parser.add_argument(
        "--rodski",
        default="/opt/homebrew/bin/rodski",
        help="用于兼容性检查的本地 RodSki CLI。",
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help="原始 guide URL。默认使用 RODSKI_TEST_CASE_GUIDE_URL 或已知 GitHub 路径。",
    )
    parser.add_argument("--dry-run", action="store_true", help="仅检查，不写入文件。")
    return parser.parse_args()


def fail(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def run_rodski_version(rodski: Path) -> str:
    if not rodski.exists() or not rodski.is_file():
        raise RuntimeError(f"未找到 RodSki CLI：{rodski}")
    result = subprocess.run(
        [str(rodski), "--version"],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise RuntimeError(f"`{rodski} --version` 失败：{stderr or result.stdout.strip()}")
    version = result.stdout.strip()
    if not version:
        raise RuntimeError(f"`{rodski} --version` 返回空输出")
    return version


def fetch_guide(url: str) -> str:
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "rodski-skill-sync/1.0"})
        with urllib.request.urlopen(request, timeout=30) as response:
            content_type = response.headers.get("Content-Type", "")
            data = response.read()
    except urllib.error.URLError as exc:
        raise RuntimeError(f"下载 guide 失败：{exc}") from exc
    text = data.decode("utf-8", errors="replace")
    if "markdown" not in content_type and "text/plain" not in content_type:
        if not text.lstrip().startswith("# RodSki"):
            raise RuntimeError(f"下载内容不像 markdown；Content-Type={content_type!r}")
    if re.search(r"<html[\s>]|<!DOCTYPE", text[:500], re.I):
        raise RuntimeError("下载内容看起来是 HTML 或跳转页，不是原始 guide")
    if not text.lstrip().startswith("# RodSki"):
        raise RuntimeError("下载内容不是以 RodSki guide 标题开头")
    return text


def metadata(text: str) -> dict[str, str]:
    keys = {
        "version": r"(?:\*\*)?版本(?:\*\*)?\s*[:：]\s*([^\n]+)",
        "date": r"(?:\*\*)?日期(?:\*\*)?\s*[:：]\s*([^\n]+)",
        "framework": r"(?:\*\*)?适用框架(?:\*\*)?\s*[:：]\s*([^\n]+)",
    }
    result: dict[str, str] = {}
    for key, pattern in keys.items():
        match = re.search(pattern, text)
        if match:
            result[key] = match.group(1).strip().strip("* ")
    return result


def version_tuple(value: str) -> tuple[int, int] | None:
    match = re.search(r"v?(\d+)\.(\d+)", value, re.I)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def compatible(local_version: str, framework: str) -> tuple[bool, str]:
    local = version_tuple(local_version)
    required = version_tuple(framework)
    if local is None:
        return False, f"无法从 {local_version!r} 解析本地 RodSki 版本"
    if required is None:
        return False, f"无法从 {framework!r} 解析 guide 适用框架版本"
    if "+" in framework:
        ok = local[0] == required[0] and local[1] >= required[1]
        return ok, f"要求 {required[0]}.{required[1]}+，本地为 {local[0]}.{local[1]}"
    ok = local == required
    return ok, f"要求 {required[0]}.{required[1]}，本地为 {local[0]}.{local[1]}"


def strip_sync_header(text: str) -> str:
    """去掉文件开头的 RodSki-* 同步 header，只留 guide 正文。"""
    return re.sub(r"^(<!-- RodSki-[^\n]*-->\n)+\n?", "", text.lstrip())


def with_sync_header(text: str, local_version: str, source_url: str) -> str:
    stripped = strip_sync_header(text)
    today = dt.date.today().isoformat()
    header = (
        f"<!-- RodSki-Local-Version: {local_version} -->\n"
        f"<!-- RodSki-Guide-Source: {source_url} -->\n"
        f"<!-- RodSki-Guide-Synced-At: {today} -->\n\n"
    )
    return header + stripped


def main() -> int:
    args = parse_args()
    repo = Path(args.repo).expanduser().resolve()
    rodski = Path(args.rodski).expanduser().resolve()
    guide_path = repo / "TEST_CASE_WRITING_GUIDE.md"

    if not repo.exists():
        return fail(f"repo 不存在：{repo}")

    try:
        local_version = run_rodski_version(rodski)
        remote_text = fetch_guide(args.url)
    except RuntimeError as exc:
        return fail(str(exc))

    remote_meta = metadata(remote_text)
    missing = [key for key in ("version", "date", "framework") if key not in remote_meta]
    if missing:
        return fail(f"下载的 guide 缺少元数据：{', '.join(missing)}")

    is_compatible, reason = compatible(local_version, remote_meta["framework"])
    if not is_compatible:
        return fail(
            "guide 与本地 RodSki CLI 不兼容："
            f"{reason}；guide metadata={remote_meta}"
        )

    new_text = with_sync_header(remote_text, local_version, args.url)
    old_text = guide_path.read_text(encoding="utf-8", errors="replace") if guide_path.exists() else ""

    print(f"RodSki CLI：{local_version}")
    print(
        "远端 guide："
        f"{remote_meta['version']} ({remote_meta['date']}), {remote_meta['framework']}"
    )
    print(f"兼容性：OK（{reason}）")

    if strip_sync_header(old_text) == strip_sync_header(new_text):
        print(f"无需变更：{guide_path}")
        return 0

    if args.dry_run:
        print(f"Dry run：将会更新 {guide_path}")
        return 0

    if guide_path.exists():
        timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = guide_path.with_name(f"{guide_path.name}.bak-{timestamp}")
        shutil.copy2(guide_path, backup)
        print(f"已写入备份：{backup}")

    guide_path.write_text(new_text, encoding="utf-8")
    print(f"已更新：{guide_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
