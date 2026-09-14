#!/usr/bin/env python3
"""Store the GitLab credential without echoing or writing it into skill files."""

from __future__ import annotations

import argparse
import getpass
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlparse


DEFAULT_REPO_URL = "https://gitlab.casstime.net/qa/RodSki-AutoTest"
DEFAULT_USERNAME = os.getenv("RODSKI_GITLAB_USERNAME", "")
DEFAULT_PASSWORD_FILE = (
    Path(os.environ["RODSKI_GITLAB_PASSWORD_FILE"]).expanduser()
    if os.getenv("RODSKI_GITLAB_PASSWORD_FILE")
    else None
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Store GitLab credentials for testcase submission.")
    parser.add_argument("--repo-url", default=DEFAULT_REPO_URL)
    parser.add_argument("--username", default=DEFAULT_USERNAME)
    parser.add_argument(
        "--password-file",
        type=Path,
        default=DEFAULT_PASSWORD_FILE,
        help="Optional local private password/token file. Not written unless explicitly provided or RODSKI_GITLAB_PASSWORD_FILE is set.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    parsed = urlparse(args.repo_url)
    if parsed.scheme != "https" or not parsed.hostname:
        print(f"ERROR: unexpected repository URL: {args.repo_url}", file=sys.stderr)
        return 1

    if args.username:
        username = input(f"GitLab username [{args.username}]: ").strip() or args.username
    else:
        username = input("GitLab username: ").strip()
    if not username:
        print("ERROR: empty username", file=sys.stderr)
        return 1
    password = getpass.getpass("GitLab password/token: ")
    if not password:
        print("ERROR: empty password/token", file=sys.stderr)
        return 1

    payload = (
        f"protocol=https\n"
        f"host={parsed.hostname}\n"
        f"username={username}\n"
        f"password={password}\n\n"
    )

    proc = subprocess.run(["git", "credential", "approve"], input=payload, text=True)
    if proc.returncode != 0:
        print("ERROR: failed to store credential", file=sys.stderr)
        return proc.returncode

    password_file = args.password_file.expanduser() if args.password_file else None
    if password_file:
        password_file.parent.mkdir(parents=True, exist_ok=True)
        password_file.write_text(password + "\n", encoding="utf-8")
        password_file.chmod(0o600)

    check_payload = (
        f"protocol=https\n"
        f"host={parsed.hostname}\n"
        f"username={username}\n\n"
    )
    check = subprocess.run(
        ["git", "credential", "fill"],
        input=check_payload,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check.returncode != 0 or "password=" not in check.stdout:
        print("ERROR: stored credential could not be read back by git credential fill", file=sys.stderr)
        return 1

    print(f"Stored credential for {username}@{parsed.hostname} in the configured Git credential helper.")
    if password_file:
        print(f"Stored local testcase-submit password file: {password_file}")
    else:
        print("No local password file was written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
