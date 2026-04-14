"""CLI entry point for rodski-agent."""

from __future__ import annotations

import json
from typing import Any

import click

from rodski_agent import __version__


def _output(ctx: click.Context, data: dict[str, Any], human_message: str) -> None:
    """Unified output helper: JSON dict or human-readable text."""
    fmt = ctx.obj.get("format", "human") if ctx.obj else "human"
    if fmt == "json":
        click.echo(json.dumps(data, ensure_ascii=False))
    else:
        click.echo(human_message)


def _placeholder(ctx: click.Context, command: str) -> None:
    """Emit a standard 'not implemented' placeholder for a command."""
    _output(
        ctx,
        {"status": "not_implemented", "command": command, "message": "Command not implemented yet"},
        f"[{command}] Command not implemented yet.",
    )


# ---------------------------------------------------------------------------
# Main group
# ---------------------------------------------------------------------------

@click.group()
@click.version_option(version=__version__, prog_name="rodski-agent")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["human", "json"], case_sensitive=False),
    default="human",
    show_default=True,
    help="Output format.",
)
@click.pass_context
def main(ctx: click.Context, output_format: str) -> None:
    """rodski-agent -- AI Agent layer for RodSki test automation."""
    ctx.ensure_object(dict)
    ctx.obj["format"] = output_format


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------

@main.command()
@click.option("--case", required=True, type=click.Path(exists=False), help="Path to the test case file.")
@click.option("--max-retry", default=0, show_default=True, type=int, help="Max retry count on failure.")
@click.option("--headless/--no-headless", default=True, show_default=True, help="Run browser in headless mode.")
@click.option("--browser", default="chromium", show_default=True, help="Browser engine to use.")
@click.pass_context
def run(ctx: click.Context, case: str, max_retry: int, headless: bool, browser: str) -> None:
    """Execute a test case."""
    _placeholder(ctx, "run")


# ---------------------------------------------------------------------------
# design
# ---------------------------------------------------------------------------

@main.command()
@click.option("--requirement", required=True, type=str, help="Natural-language requirement description.")
@click.option("--url", default=None, type=str, help="Target URL for the test.")
@click.option("--output", required=True, type=click.Path(), help="Output path for generated test case.")
@click.pass_context
def design(ctx: click.Context, requirement: str, url: str | None, output: str) -> None:
    """Design a test case from a requirement."""
    _placeholder(ctx, "design")


# ---------------------------------------------------------------------------
# pipeline
# ---------------------------------------------------------------------------

@main.command()
@click.option("--requirement", required=True, type=str, help="Natural-language requirement description.")
@click.option("--url", default=None, type=str, help="Target URL for the test.")
@click.option("--output", required=True, type=click.Path(), help="Output path for generated test case.")
@click.option("--max-retry", default=0, show_default=True, type=int, help="Max retry count on failure.")
@click.pass_context
def pipeline(ctx: click.Context, requirement: str, url: str | None, output: str, max_retry: int) -> None:
    """Run the full design-then-execute pipeline."""
    _placeholder(ctx, "pipeline")


# ---------------------------------------------------------------------------
# diagnose
# ---------------------------------------------------------------------------

@main.command()
@click.option("--result", required=True, type=click.Path(exists=False), help="Path to the test result file.")
@click.pass_context
def diagnose(ctx: click.Context, result: str) -> None:
    """Diagnose a failed test result."""
    _placeholder(ctx, "diagnose")


# ---------------------------------------------------------------------------
# config (sub-group)
# ---------------------------------------------------------------------------

@main.group()
@click.pass_context
def config(ctx: click.Context) -> None:
    """Manage rodski-agent configuration."""


@config.command()
@click.pass_context
def show(ctx: click.Context) -> None:
    """Show current configuration."""
    _placeholder(ctx, "config show")
