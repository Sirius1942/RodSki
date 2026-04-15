"""Configuration loader for rodski-agent.

Loads YAML configuration with environment variable overrides.
Search order:
  1. Path from env var RODSKI_AGENT_CONFIG
  2. ./agent_config.yaml (current working directory)
  3. <project_root>/config/agent_config.yaml
  4. Built-in defaults
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, TypeVar

import yaml

# ---------------------------------------------------------------------------
# Section dataclasses
# ---------------------------------------------------------------------------

@dataclass
class RodskiConfig:
    cli_path: str = "python rodski/ski_run.py"
    validate_cmd: str = "rodski validate"
    default_browser: str = "chromium"
    headless: bool = True


@dataclass
class LLMProviderConfig:
    """Single LLM provider configuration."""
    provider: str = "claude"
    model: str = "claude-sonnet-4-20250514"
    base_url: str = ""
    api_key_env: str = "ANTHROPIC_API_KEY"
    temperature: float = 0.7
    max_tokens: int = 4096


@dataclass
class LLMConfig:
    """LLM configuration with per-agent provider settings."""
    design: LLMProviderConfig = field(default_factory=LLMProviderConfig)
    execution: LLMProviderConfig = field(
        default_factory=lambda: LLMProviderConfig(temperature=0.1, max_tokens=2048)
    )


@dataclass
class OmniParserConfig:
    url: str = "http://localhost:8000"
    timeout: int = 30


@dataclass
class DesignConfig:
    max_scenarios: int = 10
    max_fix_attempts: int = 3


@dataclass
class ExecutionConfig:
    max_retry: int = 3
    screenshot_on_fail: bool = True
    diagnosis_enabled: bool = True


@dataclass
class OutputConfig:
    format: str = "human"
    verbose: bool = False


# ---------------------------------------------------------------------------
# Main config
# ---------------------------------------------------------------------------

_ENV_PREFIX = "RODSKI_AGENT_"
_ENV_SEP = "__"


def _project_root() -> Path:
    """Return the rodski-agent project root (directory containing ``config/``)."""
    return Path(__file__).resolve().parents[3]  # src/rodski_agent/common/config.py -> rodski-agent/


def _find_config_file() -> Path | None:
    """Locate the configuration file following the documented search order."""
    # 1. Environment variable
    env_path = os.environ.get("RODSKI_AGENT_CONFIG")
    if env_path:
        p = Path(env_path).expanduser()
        if p.is_file():
            return p

    # 2. Current working directory
    cwd_path = Path.cwd() / "agent_config.yaml"
    if cwd_path.is_file():
        return cwd_path

    # 3. Project root config/
    project_path = _project_root() / "config" / "agent_config.yaml"
    if project_path.is_file():
        return project_path

    # 4. No file found — use built-in defaults
    return None


def _load_yaml(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return data if isinstance(data, dict) else {}


def _apply_env_overrides(data: dict[str, Any]) -> dict[str, Any]:
    """Override config values with ``RODSKI_AGENT_*`` environment variables.

    ``RODSKI_AGENT_LLM__DESIGN__MODEL`` sets ``data["llm"]["design"]["model"]``.
    """
    for key, value in os.environ.items():
        if not key.startswith(_ENV_PREFIX):
            continue
        # Strip prefix and split by separator
        suffix = key[len(_ENV_PREFIX):]
        parts = [p.lower() for p in suffix.split(_ENV_SEP)]

        # Walk / create nested dict
        node = data
        for part in parts[:-1]:
            if part not in node or not isinstance(node[part], dict):
                node[part] = {}
            node = node[part]

        # Coerce simple types
        node[parts[-1]] = _coerce(value)
    return data


def _coerce(value: str) -> str | int | float | bool:
    """Best-effort coercion of string env values to Python types."""
    low = value.lower()
    if low in ("true", "1", "yes"):
        return True
    if low in ("false", "0", "no"):
        return False
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value


_T = TypeVar("_T")


def _build_section(cls: type[_T], raw: dict[str, Any] | None) -> _T:
    """Instantiate a dataclass *cls* from *raw* dict, ignoring unknown keys."""
    if not raw:
        return cls()
    known = {f.name for f in cls.__dataclass_fields__.values()}
    return cls(**{k: v for k, v in raw.items() if k in known})


def _build_llm_config(raw: dict[str, Any] | None) -> LLMConfig:
    """Build LLMConfig with nested per-agent provider configs."""
    if not raw:
        return LLMConfig()
    return LLMConfig(
        design=_build_section(LLMProviderConfig, raw.get("design")),
        execution=_build_section(LLMProviderConfig, raw.get("execution")),
    )


@dataclass
class AgentConfig:
    """Top-level configuration for rodski-agent."""

    rodski: RodskiConfig = field(default_factory=RodskiConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    omniparser: OmniParserConfig = field(default_factory=OmniParserConfig)
    design: DesignConfig = field(default_factory=DesignConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    output: OutputConfig = field(default_factory=OutputConfig)

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def load(cls, path: str | Path | None = None) -> AgentConfig:
        """Load configuration.

        Parameters
        ----------
        path:
            Explicit path to a YAML file.  When *None*, the standard search
            order is used.
        """
        if path is not None:
            config_path = Path(path).expanduser()
            if not config_path.is_file():
                raise FileNotFoundError(f"Config file not found: {config_path}")
        else:
            config_path = _find_config_file()

        raw: dict[str, Any] = _load_yaml(config_path) if config_path else {}
        raw = _apply_env_overrides(raw)

        return cls(
            rodski=_build_section(RodskiConfig, raw.get("rodski")),
            llm=_build_llm_config(raw.get("llm")),
            omniparser=_build_section(OmniParserConfig, raw.get("omniparser")),
            design=_build_section(DesignConfig, raw.get("design")),
            execution=_build_section(ExecutionConfig, raw.get("execution")),
            output=_build_section(OutputConfig, raw.get("output")),
        )

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialize the full configuration to a plain dict."""
        return asdict(self)
