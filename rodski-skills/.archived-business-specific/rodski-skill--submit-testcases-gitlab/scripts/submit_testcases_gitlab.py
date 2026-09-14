#!/usr/bin/env python3
"""Sync selected RodSki testcase directories from 00 Pass to GitLab.

The submitter-owned directory is treated as a publish artifact: every push
rebuilds only that owner directory, then copies the selected testcase asset
directories into it. Sibling submitter
directories and repository-root legacy-looking paths are never cleaned by this
script.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import fnmatch
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import quote, urlparse, urlunparse


DEFAULT_SOURCE = Path(os.getenv("RODSKI_TESTCASE_SOURCE", str(Path.home() / "TestCase/00 Pass")))
DEFAULT_REPO_URL = "https://gitlab.casstime.net/qa/RodSki-AutoTest"
DEFAULT_BRANCHES_URL = "https://gitlab.casstime.net/qa/RodSki-AutoTest/-/branches"
DEFAULT_WORKDIR = Path.home() / ".codex/cache/submit-testcases-gitlab/RodSki-AutoTest"
DEFAULT_PASSWORD_FILE = (
    Path(os.environ["RODSKI_GITLAB_PASSWORD_FILE"]).expanduser()
    if os.getenv("RODSKI_GITLAB_PASSWORD_FILE")
    else None
)
DEFAULT_RODSKI_BIN = Path("/opt/homebrew/bin/rodski")
ALLOWED_DIRS = {"case", "data", "fun", "model", "plan"}
COPY_DIRS = {"case", "data", "fun", "model"}
MODULE_HINT_DIRS = {"case", "data", "model", "plan"}
SKIP_SCAN_DIRS = {
    ".git",
    ".svn",
    ".hg",
    "node_modules",
    "result",
    "results",
    "__pycache__",
    ".idea",
    ".vscode",
    "dist",
    "build",
    "coverage",
}
SKIP_COPY_NAMES = {
    ".DS_Store",
    "Thumbs.db",
}
SKIP_COPY_DIRS = {
    ".git",
    ".svn",
    ".hg",
    "__pycache__",
    "node_modules",
    "result",
    "results",
}
SKIP_COPY_PATTERNS = ["*.pyc", "*.pyo", "*.log", "*.tmp", "*.bak", "*~"]
FORBIDDEN_ROOT_GITLINKS = {"repo"}
# Shared mainline branches that this personal submit flow must never touch.
# Compared case-insensitively. There is intentionally no override flag.
PROTECTED_BRANCHES = {"main", "master", "head"}


class SubmitError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Submit only case/data/fun/model from 00 Pass to GitLab."
    )
    parser.add_argument(
        "--source",
        type=Path,
        action="append",
        default=None,
        help=(
            "Source root to scan for RodSki modules. Repeat to merge several "
            "roots into one submission (e.g. --source '00 Pass' --source "
            "'00 落地项目'). Defaults to the single 00 Pass root."
        ),
    )
    parser.add_argument("--repo-url", default=DEFAULT_REPO_URL)
    parser.add_argument("--workdir", type=Path, default=DEFAULT_WORKDIR)
    parser.add_argument("--username", default=os.getenv("RODSKI_GITLAB_USERNAME"))
    parser.add_argument(
        "--owner-dir",
        default=os.getenv("RODSKI_GITLAB_OWNER_DIR"),
        help="Single repository directory that owns this submitter's payload.",
    )
    parser.add_argument(
        "--branch",
        default=os.getenv("RODSKI_GITLAB_BRANCH"),
        help="Personal branch to commit and push to. Defaults to --username; never defaults to main.",
    )
    parser.add_argument(
        "--password-file",
        type=Path,
        default=DEFAULT_PASSWORD_FILE,
        help="Optional local private password/token file. Prefer Keychain or RODSKI_GITLAB_PASSWORD.",
    )
    parser.add_argument("--message", default=None, help="Commit message.")
    parser.add_argument(
        "--rodski-bin",
        type=Path,
        default=Path(os.getenv("RODSKI_BIN", str(DEFAULT_RODSKI_BIN))),
        help="RodSki executable used to add the current version to the commit message.",
    )
    parser.add_argument(
        "--rodski-version",
        default=os.getenv("RODSKI_VERSION"),
        help="Explicit RodSki version string for the commit message. Overrides --rodski-bin.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scan and print what would be copied without cloning, committing, or pushing.",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Clone/update the worktree, sync selected directories, commit, and push.",
    )
    parser.add_argument(
        "--allow-dirty-workdir",
        action="store_true",
        help="Allow continuing when the cached Git worktree already has local changes.",
    )
    return parser.parse_args()


def relpath(path: Path, base: Path) -> str:
    return path.relative_to(base).as_posix()


def is_skip_copy(path: Path) -> bool:
    name = path.name
    if name in SKIP_COPY_NAMES:
        return True
    if path.is_dir() and name in SKIP_COPY_DIRS:
        return True
    return any(fnmatch.fnmatch(name, pattern) for pattern in SKIP_COPY_PATTERNS)


def is_rodski_module(child_dirs: set[str]) -> bool:
    allowed = child_dirs & ALLOWED_DIRS
    if len(allowed) >= 3:
        return True
    return "case" in allowed and bool(allowed & {"data", "model", "plan"})


def discover_module_roots(source: Path) -> list[Path]:
    if not source.exists():
        raise SubmitError(f"Source path does not exist: {source}")
    if not source.is_dir():
        raise SubmitError(f"Source path is not a directory: {source}")

    module_roots: list[Path] = []
    for current, dirnames, _filenames in os.walk(source):
        current_path = Path(current)
        dirnames[:] = [
            dirname
            for dirname in sorted(dirnames)
            if dirname not in SKIP_SCAN_DIRS and not dirname.startswith(".")
        ]
        child_dirs = set(dirnames)
        if is_rodski_module(child_dirs):
            module_roots.append(current_path)
            dirnames[:] = []
    return sorted(module_roots, key=lambda path: relpath(path, source))


def selected_directories(source: Path, module_roots: list[Path]) -> list[tuple[Path, str]]:
    selected: list[tuple[Path, str]] = []
    for module_root in module_roots:
        for name in sorted(COPY_DIRS):
            src = module_root / name
            if src.is_dir():
                dst_rel = f"{relpath(module_root, source)}/{name}"
                selected.append((src, dst_rel))
    return selected


def aggregate_sources(
    sources: list[Path],
) -> tuple[list[str], list[tuple[Path, str]]]:
    """Scan each source and merge results, refusing destination collisions.

    Returns the sorted module-root labels (relative to their own source) and the
    combined selection. Two sources that map to the same `owner_dir/<rel>` path
    would silently overwrite each other on copy, so that is a hard error.
    """
    module_root_labels: list[str] = []
    selected: list[tuple[Path, str]] = []
    seen_dst: dict[str, Path] = {}
    for source in sources:
        module_roots = discover_module_roots(source)
        for module_root in module_roots:
            module_root_labels.append(relpath(module_root, source))
        for src, dst_rel in selected_directories(source, module_roots):
            previous = seen_dst.get(dst_rel)
            if previous is not None:
                raise SubmitError(
                    f"Destination collision for {dst_rel!r}: both {previous} and "
                    f"{src} map to the same repository path. Rename one module "
                    "root so submissions do not overwrite each other."
                )
            seen_dst[dst_rel] = src
            selected.append((src, dst_rel))
    return sorted(module_root_labels), sorted(selected, key=lambda item: item[1])


def print_scan(
    sources: list[Path],
    module_root_labels: list[str],
    selected: list[tuple[Path, str]],
    repo_url: str,
    owner_dir: str,
    branch: str | None,
) -> None:
    if len(sources) == 1:
        print(f"Source: {sources[0]}")
    else:
        print("Sources:")
        for source in sources:
            print(f"  - {source}")
    print(f"Repository owner directory: {owner_dir}")
    print(f"Target branch: {branch or '(current checkout)'}")
    print(f"GitLab branches page: {DEFAULT_BRANCHES_URL}")
    print(f"GitLab owner tree page: {display_owner_tree_url(repo_url, branch, owner_dir)}")
    print(f"Detected RodSki module roots: {len(module_root_labels)}")
    for label in module_root_labels:
        print(f"  - {label}")
    print(f"Selected directories to copy: {len(selected)}")
    for _src, dst_rel in selected:
        print(f"  - {owner_dir}/{dst_rel}")


def copy_tree_filtered(src: Path, dst: Path) -> int:
    copied_files = 0
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True, exist_ok=True)

    for current, dirnames, filenames in os.walk(src):
        current_path = Path(current)
        dirnames[:] = sorted(
            dirname for dirname in dirnames if not is_skip_copy(current_path / dirname)
        )
        rel_current = current_path.relative_to(src)
        dst_current = dst / rel_current
        dst_current.mkdir(parents=True, exist_ok=True)
        for filename in sorted(filenames):
            src_file = current_path / filename
            if is_skip_copy(src_file):
                continue
            dst_file = dst_current / filename
            shutil.copy2(src_file, dst_file)
            copied_files += 1
    return copied_files


def candidate_repo_urls(repo_url: str) -> list[str]:
    cleaned = repo_url.rstrip("/")
    candidates = [repo_url]
    if not cleaned.endswith(".git"):
        candidates.append(cleaned + ".git")
    deduped: list[str] = []
    for candidate in candidates:
        if candidate not in deduped:
            deduped.append(candidate)
    return deduped


def repo_url_with_username(repo_url: str, username: str) -> str:
    parsed = urlparse(repo_url)
    if parsed.username:
        return repo_url
    host = parsed.hostname
    if not host:
        return repo_url
    port = f":{parsed.port}" if parsed.port else ""
    netloc = f"{quote(username, safe='')}@{host}{port}"
    return urlunparse(parsed._replace(netloc=netloc))


def display_repo_url(repo_url: str) -> str:
    parsed = urlparse(repo_url)
    if not parsed.username and not parsed.password:
        return repo_url
    host = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    return urlunparse(parsed._replace(netloc=f"{host}{port}"))


def display_owner_tree_url(repo_url: str, branch: str | None, owner_dir: str) -> str:
    base = display_repo_url(repo_url).rstrip("/")
    ref = branch or "HEAD"
    return f"{base}/tree/{quote(ref, safe='')}/{quote(owner_dir, safe='')}"


def validate_owner_dir(owner_dir: str) -> str:
    if owner_dir is None:
        raise SubmitError("Owner directory is required. Pass --owner-dir or set RODSKI_GITLAB_OWNER_DIR.")
    normalized = owner_dir.strip()
    candidate = Path(normalized)
    if (
        not normalized
        or candidate.is_absolute()
        or len(candidate.parts) != 1
        or normalized in {".", "..", ".git"}
    ):
        raise SubmitError(f"Owner directory must be one safe repository folder name: {owner_dir!r}")
    return normalized


def validate_branch(branch: str | None) -> str | None:
    if branch is None:
        return None
    normalized = branch.strip()
    if not normalized:
        raise SubmitError("Branch must not be empty; this script never falls back to main.")
    if normalized.lower() in PROTECTED_BRANCHES:
        raise SubmitError(
            f"Refusing to target protected mainline branch {normalized!r}.\n"
            f"This personal submit flow only pushes to a submitter branch listed at "
            f"{DEFAULT_BRANCHES_URL}. Pick a personal --branch."
        )
    return normalized


def validate_username(username: str | None) -> str:
    if username is None or not username.strip():
        raise SubmitError("GitLab username is required. Pass --username or set RODSKI_GITLAB_USERNAME.")
    return username.strip()


def git_prefix() -> list[str]:
    args = ["git"]
    if shutil.which("git-credential-osxkeychain"):
        args += ["-c", "credential.helper=osxkeychain"]
    return args


def git_args(env: dict[str, str] | None = None) -> list[str]:
    args = ["git"]
    if env and env.get("GIT_ASKPASS") and env.get("RODSKI_GITLAB_PASSWORD"):
        args += ["-c", "credential.helper="]
    elif shutil.which("git-credential-osxkeychain"):
        args += ["-c", "credential.helper=osxkeychain"]
    return args


def git_env(username: str, password_file: Path | None, tempdir: Path | None = None) -> dict[str, str]:
    env = os.environ.copy()
    env["RODSKI_GITLAB_USERNAME"] = username
    password = (
        env.get("RODSKI_GITLAB_PASSWORD")
        or env.get("GITLAB_PASSWORD")
        or read_password_file(password_file)
    )
    if password:
        if tempdir is None:
            raise SubmitError("Internal error: tempdir is required for askpass authentication.")
        askpass = tempdir / "git-askpass.sh"
        askpass.write_text(
            "#!/bin/sh\n"
            "case \"$1\" in\n"
            "*Username*) printf '%s\\n' \"$RODSKI_GITLAB_USERNAME\" ;;\n"
            "*Password*) printf '%s\\n' \"$RODSKI_GITLAB_PASSWORD\" ;;\n"
            "*) printf '\\n' ;;\n"
            "esac\n",
            encoding="utf-8",
        )
        askpass.chmod(0o700)
        env["RODSKI_GITLAB_PASSWORD"] = password
        env["GIT_ASKPASS"] = str(askpass)
        env["GIT_TERMINAL_PROMPT"] = "0"
    else:
        env.setdefault("GIT_TERMINAL_PROMPT", "0")
    return env


def read_password_file(path: Path | None) -> str | None:
    if path is None:
        return None
    if not path.exists():
        return None
    if not path.is_file():
        raise SubmitError(f"GitLab password path is not a regular file: {path}")
    return path.read_text(encoding="utf-8").strip() or None


def run(args: list[str], env: dict[str, str] | None = None, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        rendered = " ".join(args)
        detail = (proc.stderr or proc.stdout).strip()
        raise SubmitError(f"Command failed: {rendered}\n{detail}")
    return proc


def run_git(args: list[str], env: dict[str, str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return run(git_args(env) + args, env=env, cwd=cwd)


def indexed_gitlinks(workdir: Path, env: dict[str, str]) -> list[str]:
    output = run_git(["-C", str(workdir), "ls-files", "--stage"], env=env).stdout
    gitlinks: list[str] = []
    for line in output.splitlines():
        meta, path = line.split("\t", 1)
        mode = meta.split(" ", 1)[0]
        if mode == "160000":
            gitlinks.append(path)
    return gitlinks


def is_nested_git_repo(path: Path) -> bool:
    return path.is_dir() and (path / ".git").exists()


def remove_path(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()


def remove_forbidden_root_gitlinks(workdir: Path, env: dict[str, str]) -> list[str]:
    removed: list[str] = []
    indexed = set(indexed_gitlinks(workdir, env))
    for name in sorted(FORBIDDEN_ROOT_GITLINKS):
        root_path = workdir / name
        if name in indexed:
            run_git(["-C", str(workdir), "update-index", "--force-remove", name], env=env)
            removed.append(name)
        if root_path.exists() and is_nested_git_repo(root_path):
            remove_path(root_path)
            if name not in removed:
                removed.append(name)
    return removed


def ensure_no_forbidden_root_gitlinks(workdir: Path, env: dict[str, str]) -> None:
    forbidden = sorted(
        path
        for path in indexed_gitlinks(workdir, env)
        if Path(path).parts and Path(path).parts[0] in FORBIDDEN_ROOT_GITLINKS
    )
    if forbidden:
        rendered = ", ".join(forbidden)
        raise SubmitError(
            f"Refusing to submit repository-root gitlink(s): {rendered}.\n"
            "Remove the accidental nested Git repository reference before pushing."
        )


def unquote_git_path(token: str) -> str:
    """Decode a path token from `git status --porcelain`.

    When core.quotePath is on (the default), Git wraps paths containing
    non-ASCII or special bytes in double quotes and C-escapes them, e.g.
    "\\346\\263\\275..." for UTF-8 bytes. Decode those escapes back to bytes and
    interpret as UTF-8. Unquoted tokens are returned unchanged.
    """
    token = token.strip()
    if not (len(token) >= 2 and token.startswith('"') and token.endswith('"')):
        return token
    inner = token[1:-1]
    simple = {
        "a": 0x07, "b": 0x08, "t": 0x09, "n": 0x0A,
        "v": 0x0B, "f": 0x0C, "r": 0x0D, '"': 0x22, "\\": 0x5C,
    }
    out = bytearray()
    i = 0
    while i < len(inner):
        ch = inner[i]
        if ch != "\\":
            out.extend(ch.encode("utf-8"))
            i += 1
            continue
        nxt = inner[i + 1]
        if nxt in simple:
            out.append(simple[nxt])
            i += 2
        elif nxt.isdigit():
            out.append(int(inner[i + 1 : i + 4], 8))
            i += 4
        else:
            out.extend(nxt.encode("utf-8"))
            i += 2
    return out.decode("utf-8", errors="replace")


def parse_porcelain_paths(status_output: str) -> list[str]:
    """Extract repository paths from `git status --porcelain` output.

    Handles renames (`R  old -> new`) by taking the destination path and decodes
    the C-style quoting Git applies to non-ASCII names (core.quotePath).
    """
    paths: list[str] = []
    for line in status_output.splitlines():
        if not line.strip():
            continue
        entry = line[3:]
        if " -> " in entry:
            entry = entry.split(" -> ", 1)[1]
        decoded = unquote_git_path(entry)
        if decoded:
            paths.append(decoded)
    return paths


def ensure_changes_within_owner_dir(
    workdir: Path, owner_dir: str, env: dict[str, str]
) -> None:
    """Hard guard: every staged change must live under the owner directory.

    Sibling submitter folders and repository-root paths must never be modified
    by a personal submission. If anything outside `owner_dir/` changed, refuse to
    commit so we cannot clobber another submitter's work.
    """
    status = run_git(["-C", str(workdir), "status", "--porcelain"], env=env).stdout
    owner_prefix = f"{owner_dir}/"
    stray = sorted(
        path
        for path in parse_porcelain_paths(status)
        if not path.startswith(owner_prefix)
    )
    if stray:
        rendered = "\n  ".join(stray)
        raise SubmitError(
            "Refusing to commit changes outside the owner directory "
            f"{owner_dir!r}:\n  {rendered}\n"
            "A personal submission must only touch its own folder. Inspect the "
            "cached worktree before retrying."
        )


def read_rodski_version(args: argparse.Namespace) -> str:
    if args.rodski_version:
        return args.rodski_version.strip()

    candidates: list[str] = []
    rodski_bin = args.rodski_bin.expanduser()
    if rodski_bin.exists():
        candidates.append(str(rodski_bin))
    path_rodski = shutil.which("rodski")
    if path_rodski and path_rodski not in candidates:
        candidates.append(path_rodski)

    errors: list[str] = []
    for candidate in candidates:
        proc = subprocess.run(
            [candidate, "--version"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        output = (proc.stdout or proc.stderr).strip()
        if proc.returncode == 0 and output:
            return output.splitlines()[0].strip()
        detail = output or f"exit code {proc.returncode}"
        errors.append(f"{candidate}: {detail}")

    detail = "; ".join(errors) if errors else "no rodski executable found"
    raise SubmitError(f"Unable to determine RodSki version for commit message: {detail}")


def commit_message_with_rodski_version(message: str | None, rodski_version: str) -> str:
    base = message or f"提交测试用例: {_dt.datetime.now().strftime('%Y-%m-%d %H:%M')}"
    if rodski_version in base:
        return base
    return f"{base} ({rodski_version})"


def git_ref_exists(workdir: Path, ref: str, env: dict[str, str]) -> bool:
    proc = subprocess.run(
        git_args(env) + ["-C", str(workdir), "rev-parse", "--verify", "--quiet", ref],
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return proc.returncode == 0


def ensure_submit_branch(workdir: Path, branch: str | None, env: dict[str, str]) -> None:
    if not branch:
        return

    remote_branch = git_ref_exists(workdir, f"refs/remotes/origin/{branch}", env)
    local_branch = git_ref_exists(workdir, f"refs/heads/{branch}", env)

    if local_branch:
        run_git(["-C", str(workdir), "checkout", branch], env=env)
        if not remote_branch:
            raise SubmitError(
                f"Local branch {branch!r} exists but remote origin/{branch} does not.\n"
                f"Open {DEFAULT_BRANCHES_URL} to confirm the personal submission branch exists, "
                f"or choose the correct --branch."
            )
        run_git(["-C", str(workdir), "pull", "--ff-only", "origin", branch], env=env)
        return

    if remote_branch:
        run_git(["-C", str(workdir), "checkout", "-B", branch, f"origin/{branch}"], env=env)
    else:
        raise SubmitError(
            f"Remote branch origin/{branch} does not exist.\n"
            f"Open {DEFAULT_BRANCHES_URL} and choose an existing personal submission branch; "
            f"this script does not submit to main."
        )


def ensure_worktree(args: argparse.Namespace, env: dict[str, str]) -> None:
    workdir = args.workdir
    repo_url = repo_url_with_username(args.repo_url, args.username)
    if (workdir / ".git").is_dir():
        run_git(["-C", str(workdir), "remote", "set-url", "origin", repo_url], env=env)
        status = run_git(["-C", str(workdir), "status", "--porcelain"], env=env).stdout.strip()
        if status and not args.allow_dirty_workdir:
            raise SubmitError(
                f"Cached Git worktree has local changes: {workdir}\n"
                "Inspect it or rerun with --allow-dirty-workdir if those changes are intentional."
            )
        run_git(["-C", str(workdir), "fetch", "origin"], env=env)
        ensure_submit_branch(workdir, args.branch, env)
        return

    if workdir.exists() and any(workdir.iterdir()):
        raise SubmitError(f"Workdir exists but is not an empty Git checkout: {workdir}")

    workdir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="clone-", dir=str(workdir.parent)) as tmp:
        tmp_path = Path(tmp)
        last_error: Exception | None = None
        for repo_url in candidate_repo_urls(repo_url):
            try:
                run_git(["clone", repo_url, str(tmp_path / "repo")], env=env)
                shutil.move(str(tmp_path / "repo"), str(workdir))
                run_git(["-C", str(workdir), "fetch", "origin"], env=env)
                ensure_submit_branch(workdir, args.branch, env)
                return
            except SubmitError as exc:
                last_error = exc
                if (tmp_path / "repo").exists():
                    shutil.rmtree(tmp_path / "repo")
        assert last_error is not None
        raise last_error


def ensure_git_identity(workdir: Path, username: str, env: dict[str, str]) -> None:
    name = subprocess.run(
        git_prefix() + ["-C", str(workdir), "config", "--get", "user.name"],
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.strip()
    email = subprocess.run(
        git_prefix() + ["-C", str(workdir), "config", "--get", "user.email"],
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.strip()
    if not name:
        run_git(["-C", str(workdir), "config", "user.name", username], env=env)
    if not email:
        run_git(["-C", str(workdir), "config", "user.email", f"{username}@gitlab.casstime.net"], env=env)


def sync_payload(
    workdir: Path,
    selected: list[tuple[Path, str]],
    owner_dir: str,
) -> int:
    copied_files = 0
    publish_root = clean_owner_payload(workdir, owner_dir)
    for src, dst_rel in selected:
        copied_files += copy_tree_filtered(src, publish_root / dst_rel)
    return copied_files


def clean_owner_payload(
    workdir: Path,
    owner_dir: str,
) -> Path:
    publish_root = workdir / owner_dir
    if publish_root.exists():
        if publish_root.is_dir() and not publish_root.is_symlink():
            shutil.rmtree(publish_root)
        else:
            publish_root.unlink()

    publish_root.mkdir(parents=True, exist_ok=True)
    return publish_root


def commit_and_push(args: argparse.Namespace, env: dict[str, str]) -> tuple[str | None, str | None]:
    workdir = args.workdir
    ensure_git_identity(workdir, args.username, env)
    removed_gitlinks = remove_forbidden_root_gitlinks(workdir, env)
    if removed_gitlinks:
        print(
            "Removed accidental repository-root gitlink(s): "
            + ", ".join(removed_gitlinks)
        )
    run_git(["-C", str(workdir), "add", "-A"], env=env)
    ensure_no_forbidden_root_gitlinks(workdir, env)
    ensure_changes_within_owner_dir(workdir, args.owner_dir, env)
    status = run_git(["-C", str(workdir), "status", "--porcelain"], env=env).stdout.strip()
    if not status:
        print("No changes detected after cleaning and syncing selected testcase directories.")
        return None, None

    rodski_version = read_rodski_version(args)
    message = commit_message_with_rodski_version(args.message, rodski_version)
    run_git(["-C", str(workdir), "commit", "-m", message], env=env)
    commit_hash = run_git(["-C", str(workdir), "rev-parse", "--short", "HEAD"], env=env).stdout.strip()
    if args.branch:
        run_git(["-C", str(workdir), "push", "-u", "origin", args.branch], env=env)
    else:
        run_git(["-C", str(workdir), "push"], env=env)
    return commit_hash, rodski_version


def validate_repo_url(repo_url: str) -> None:
    parsed = urlparse(repo_url)
    if parsed.scheme != "https" or parsed.hostname != "gitlab.casstime.net":
        raise SubmitError(f"Unexpected GitLab repository URL: {repo_url}")


def main() -> int:
    args = parse_args()
    if not args.dry_run and not args.push:
        args.dry_run = True
    if args.dry_run and args.push:
        raise SubmitError("Use either --dry-run or --push, not both.")

    raw_sources = args.source if args.source else [DEFAULT_SOURCE]
    sources: list[Path] = []
    for raw in raw_sources:
        resolved = raw.expanduser().resolve()
        if resolved not in sources:
            sources.append(resolved)
    args.username = validate_username(args.username)
    if args.branch is None:
        args.branch = args.username
    args.owner_dir = validate_owner_dir(args.owner_dir)
    args.branch = validate_branch(args.branch)
    validate_repo_url(args.repo_url)
    module_root_labels, selected = aggregate_sources(sources)
    print_scan(
        sources,
        module_root_labels,
        selected,
        args.repo_url,
        args.owner_dir,
        args.branch,
    )

    if not selected:
        raise SubmitError("No case/data/fun/model directories were detected.")
    if args.dry_run:
        print(
            "Push mode cleanup: only the target owner directory will be rebuilt "
            "before copying selected testcase assets."
        )
        print(
            "Cleanup boundary: sibling submitter folders and repository-root "
            "legacy-looking folders will not be cleaned."
        )
        print("Dry run only: no Git clone, commit, or push was performed.")
        return 0

    with tempfile.TemporaryDirectory(prefix="submit-testcases-gitlab-") as tmp:
        env = git_env(args.username, args.password_file.expanduser() if args.password_file else None, Path(tmp))
        ensure_worktree(args, env)
        copied_files = sync_payload(
            args.workdir,
            selected,
            args.owner_dir,
        )
        commit_hash, rodski_version = commit_and_push(args, env)

    print(f"Worktree: {args.workdir}")
    print(f"Repository: {display_repo_url(args.repo_url)}")
    print(f"GitLab branches page: {DEFAULT_BRANCHES_URL}")
    print(f"GitLab owner tree page: {display_owner_tree_url(args.repo_url, args.branch, args.owner_dir)}")
    print(f"Owner directory: {args.owner_dir}")
    print(f"Branch: {args.branch or '(current checkout)'}")
    if rodski_version:
        print(f"RodSki version in commit message: {rodski_version}")
    print(
        "Cleanup: rebuilt only the owner directory; sibling submitter folders "
        "and repository-root legacy-looking folders were not cleaned."
    )
    print(f"Copied files: {copied_files}")
    if commit_hash:
        print(f"Pushed commit: {commit_hash}")
    else:
        print("Push skipped because there was nothing to commit.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SubmitError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
