"""发布前安全检查门禁测试。

推送代码前必须通过此测试：
    python3 -m pytest rodski-agent/tests/release/ -v

检查项：
1. 敏感配置文件已被 gitignore
2. 源码中无硬编码密钥
3. 提交内容中无内部 URL 泄露
4. .gitignore 完整性
"""
import subprocess
import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]  # rodski-agent/tests/release/ → RodSki/
AGENT_ROOT = PROJECT_ROOT / "rodski-agent"


# ============================================================
# 1. 敏感文件 gitignore 检查
# ============================================================

MUST_BE_IGNORED = [
    "rodski-agent/config/agent_config.yaml",
]

MUST_NOT_BE_TRACKED = [
    ".env",
    "credentials.json",
    "credentials.yaml",
]


@pytest.mark.parametrize("filepath", MUST_BE_IGNORED)
def test_sensitive_file_is_gitignored(filepath):
    """关键配置文件必须在 .gitignore 中。"""
    result = subprocess.run(
        ["git", "check-ignore", "-q", filepath],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
    )
    assert result.returncode == 0, (
        f"{filepath} 未被 gitignore！请将其加入 .gitignore"
    )


@pytest.mark.parametrize("filepath", MUST_BE_IGNORED)
def test_sensitive_file_not_tracked(filepath):
    """关键配置文件不应在 git 追踪中。"""
    result = subprocess.run(
        ["git", "ls-files", filepath],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == "", (
        f"{filepath} 仍在 git 追踪中！请执行: git rm --cached {filepath}"
    )


# ============================================================
# 2. 无硬编码密钥
# ============================================================

SECRET_PATTERNS = [
    re.compile(r"sk-ant-[a-zA-Z0-9]{20,}"),       # Anthropic API key
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),            # OpenAI API key
    re.compile(r'password\s*=\s*["\'][^"\']{6,}'), # hardcoded password
    re.compile(r'token\s*=\s*["\']sk-'),           # token assignment
]

SCAN_DIRS = [
    AGENT_ROOT / "src",
    AGENT_ROOT / "config",
]

SCAN_EXTENSIONS = {".py", ".yaml", ".yml", ".toml", ".json"}

EXCLUDE_PATTERNS = {"agent_config.yaml.example", "__pycache__", ".egg-info"}


def _source_files():
    """收集需要扫描的源码文件。"""
    files = []
    for scan_dir in SCAN_DIRS:
        if not scan_dir.exists():
            continue
        for f in scan_dir.rglob("*"):
            if not f.is_file():
                continue
            if f.suffix not in SCAN_EXTENSIONS:
                continue
            if any(ex in str(f) for ex in EXCLUDE_PATTERNS):
                continue
            files.append(f)
    return files


def test_no_hardcoded_secrets():
    """源码中不应包含硬编码的 API 密钥。"""
    violations = []
    for filepath in _source_files():
        content = filepath.read_text(encoding="utf-8", errors="replace")
        for pattern in SECRET_PATTERNS:
            matches = pattern.findall(content)
            if matches:
                rel_path = filepath.relative_to(PROJECT_ROOT)
                violations.append(f"{rel_path}: {pattern.pattern} → {matches[0][:20]}...")

    assert not violations, (
        "发现硬编码密钥:\n" + "\n".join(f"  - {v}" for v in violations)
    )


# ============================================================
# 3. 无内部 URL 泄露（在 git staged/committed 文件中）
# ============================================================

INTERNAL_URL_PATTERNS = [
    re.compile(r"casstime\.ai"),
    re.compile(r"14\.103\.175\.167"),  # OmniParser 内部 IP
]


def test_no_internal_urls_in_tracked_files():
    """git 追踪的文件中不应包含公司内部 URL。"""
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
    )
    tracked_files = result.stdout.strip().splitlines()

    violations = []
    for rel_path in tracked_files:
        filepath = PROJECT_ROOT / rel_path
        if not filepath.exists() or not filepath.is_file():
            continue
        if filepath.suffix not in SCAN_EXTENSIONS:
            continue
        if any(ex in rel_path for ex in EXCLUDE_PATTERNS):
            continue

        try:
            content = filepath.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        for pattern in INTERNAL_URL_PATTERNS:
            if pattern.search(content):
                violations.append(f"{rel_path}: 包含内部 URL ({pattern.pattern})")

    assert not violations, (
        "git 追踪文件中发现内部 URL:\n" + "\n".join(f"  - {v}" for v in violations)
    )


# ============================================================
# 4. .gitignore 完整性
# ============================================================

REQUIRED_GITIGNORE_ENTRIES = [
    "rodski-agent/config/agent_config.yaml",
    ".claude/",
    ".pb/",
]


def test_gitignore_completeness():
    """检查 .gitignore 包含所有必要条目。"""
    gitignore_path = PROJECT_ROOT / ".gitignore"
    assert gitignore_path.exists(), ".gitignore 文件不存在"

    content = gitignore_path.read_text(encoding="utf-8")
    missing = []
    for entry in REQUIRED_GITIGNORE_ENTRIES:
        if entry not in content:
            missing.append(entry)

    assert not missing, (
        ".gitignore 缺少以下条目:\n" + "\n".join(f"  - {m}" for m in missing)
    )


# ============================================================
# 5. agent_config.yaml.example 存在且无敏感值
# ============================================================

def test_config_example_exists():
    """公开配置模板文件必须存在。"""
    example = AGENT_ROOT / "config" / "agent_config.yaml.example"
    assert example.exists(), "缺少 config/agent_config.yaml.example 模板文件"


def test_config_example_no_secrets():
    """配置模板中不应包含实际密钥或内部 URL。"""
    example = AGENT_ROOT / "config" / "agent_config.yaml.example"
    if not example.exists():
        pytest.skip("模板文件不存在")

    content = example.read_text(encoding="utf-8")
    for pattern in SECRET_PATTERNS + INTERNAL_URL_PATTERNS:
        assert not pattern.search(content), (
            f"agent_config.yaml.example 包含敏感内容: {pattern.pattern}"
        )
