"""CLI entry point for rodski-agent."""

from __future__ import annotations

import json
import os
from typing import Any

import click

from rodski_agent import __version__
from rodski_agent.common.contracts import AgentOutput
from rodski_agent.common.errors import AgentError, InternalError
from rodski_agent.common.formatters import format_run_result, format_error
from rodski_agent.execution.graph import build_execution_graph


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


def _handle_agent_error(ctx: click.Context, err: AgentError, command: str) -> None:
    """Handle an AgentError: output structured error and set exit code 2."""
    error_meta = {
        "error_code": err.code,
        "error_category": err.category.value,
    }
    if err.details:
        error_meta["details"] = err.details

    agent_out = AgentOutput(
        status="error",
        command=command,
        output={},
        error=err.message,
        metadata=error_meta,
    )

    fmt = ctx.obj.get("format", "human") if ctx.obj else "human"
    if fmt == "json":
        click.echo(agent_out.to_json())
    else:
        click.echo(format_error(err.to_dict()))

    ctx.exit(2)


def _handle_unexpected_error(ctx: click.Context, exc: Exception, command: str) -> None:
    """Wrap an unexpected exception in InternalError and output it."""
    internal = InternalError(
        message=f"Unexpected error: {exc}",
        details={"exception_type": type(exc).__name__},
        suggestion="This is likely a bug. Please report it.",
    )
    _handle_agent_error(ctx, internal, command)


def _load_result_data(path: str) -> list[dict[str, Any]] | None:
    """Load test result data from a directory or file path.

    Supports:
      - Directory containing execution_summary.json or result_*.xml
      - Direct path to execution_summary.json
      - Direct path to result_*.xml

    Returns
    -------
    list[dict] | None
        List of case result dicts, or None if loading fails.
    """
    from rodski_agent.common.result_parser import (
        parse_execution_summary,
        extract_cases_from_summary,
        parse_result_xml,
        find_latest_result,
    )

    if os.path.isdir(path):
        # Try execution_summary.json first
        summary = parse_execution_summary(path)
        if summary:
            cases = extract_cases_from_summary(summary)
            if cases:
                return cases
        # Try result_*.xml
        latest = find_latest_result(path)
        if latest:
            cases = parse_result_xml(latest)
            if cases:
                return cases
        return None

    if not os.path.isfile(path):
        return None

    # Direct file path
    if path.endswith(".json"):
        summary = parse_execution_summary(path)
        if summary:
            return extract_cases_from_summary(summary)
        return None

    if path.endswith(".xml"):
        cases = parse_result_xml(path)
        return cases if cases else None

    return None


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
@click.option("--max-retry", default=3, show_default=True, type=int, help="Max retry count on failure.")
@click.option("--headless/--no-headless", default=True, show_default=True, help="Run browser in headless mode.")
@click.option("--browser", default="chromium", show_default=True, help="Browser engine to use.")
@click.pass_context
def run(ctx: click.Context, case: str, max_retry: int, headless: bool, browser: str) -> None:
    """Execute a test case."""
    try:
        case_path = os.path.abspath(case)
        state = {
            "case_path": case_path,
            "max_retry": max_retry,
            "headless": headless,
            "browser": browser,
        }

        graph = build_execution_graph()
        result = graph.invoke(state)

        status = result.get("status", "error")
        report_data = result.get("report", {})
        error = result.get("error", "")

        # Include retry info in output
        retry_count = result.get("retry_count", 0)
        fixes_applied = result.get("fixes_applied", [])
        if retry_count > 0:
            report_data["retry_count"] = retry_count
            report_data["fixes_applied"] = fixes_applied

        agent_status = (
            "success" if status in ("pass",)
            else "failure" if status in ("fail", "partial")
            else "error"
        )

        agent_out = AgentOutput(
            status=agent_status,
            command="run",
            output=report_data,
            error=error if error else None,
        )

        fmt = ctx.obj.get("format", "human") if ctx.obj else "human"
        if fmt == "json":
            click.echo(agent_out.to_json())
        else:
            if agent_status == "error":
                click.echo(agent_out.to_human())
            else:
                human_text = format_run_result(report_data)
                if retry_count > 0:
                    human_text += f"\nRetries: {retry_count}/{max_retry}"
                    if fixes_applied:
                        human_text += f"\nFixes applied: {', '.join(fixes_applied)}"
                click.echo(human_text)

        # Exit with non-zero for failures
        if status not in ("pass",):
            ctx.exit(1 if status in ("fail", "partial") else 2)

    except AgentError as err:
        _handle_agent_error(ctx, err, "run")
    except (SystemExit, click.exceptions.Exit):
        raise  # ctx.exit() raises click.exceptions.Exit — let it propagate
    except Exception as exc:
        _handle_unexpected_error(ctx, exc, "run")


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
    try:
        from rodski_agent.design.graph import build_design_graph
        from rodski_agent.common.contracts import DesignOutput

        output_dir = os.path.abspath(output)
        state: dict[str, Any] = {
            "requirement": requirement,
            "output_dir": output_dir,
        }
        if url:
            state["target_url"] = url

        graph = build_design_graph()
        result = graph.invoke(state)

        status = result.get("status", "error")
        generated_files = result.get("generated_files", [])
        error = result.get("error", "")
        validation_errors = result.get("validation_errors", [])

        # Classify generated files
        case_files = [f for f in generated_files if "/case/" in f]
        model_files = [f for f in generated_files if "/model/" in f]
        data_files = [f for f in generated_files if "/data/" in f]

        design_output = DesignOutput(
            cases=case_files,
            models=model_files,
            data=data_files,
            summary=f"Generated {len(generated_files)} file(s)",
        )

        agent_status = "success" if status == "success" else "error"

        agent_out = AgentOutput(
            status=agent_status,
            command="design",
            output=design_output.to_dict(),
            error=error if error else None,
        )

        fmt = ctx.obj.get("format", "human") if ctx.obj else "human"
        if fmt == "json":
            click.echo(agent_out.to_json())
        else:
            if agent_status == "error":
                click.echo(agent_out.to_human())
                if validation_errors:
                    click.echo("Validation errors:")
                    for ve in validation_errors:
                        click.echo(f"  - {ve}")
            else:
                click.echo(agent_out.to_human())

        if status != "success":
            ctx.exit(2)

    except AgentError as err:
        _handle_agent_error(ctx, err, "design")
    except (SystemExit, click.exceptions.Exit):
        raise
    except Exception as exc:
        _handle_unexpected_error(ctx, exc, "design")


# ---------------------------------------------------------------------------
# pipeline
# ---------------------------------------------------------------------------

@main.command()
@click.option("--requirement", required=True, type=str, help="Natural-language requirement description.")
@click.option("--url", default=None, type=str, help="Target URL for the test.")
@click.option("--output", required=True, type=click.Path(), help="Output path for generated test case.")
@click.option("--max-retry", default=3, show_default=True, type=int, help="Max retry count on failure.")
@click.option("--headless/--no-headless", default=True, show_default=True, help="Run browser in headless mode.")
@click.option("--browser", default="chromium", show_default=True, help="Browser engine to use.")
@click.pass_context
def pipeline(ctx: click.Context, requirement: str, url: str | None, output: str,
             max_retry: int, headless: bool, browser: str) -> None:
    """Run the full design-then-execute pipeline."""
    try:
        from rodski_agent.pipeline.orchestrator import run_pipeline

        output_dir = os.path.abspath(output)
        result = run_pipeline(
            requirement=requirement,
            output_dir=output_dir,
            target_url=url,
            max_retry=max_retry,
            headless=headless,
            browser=browser,
        )

        status = result.get("status", "error")
        design_data = result.get("design", {})
        exec_data = result.get("execution", {})
        error = result.get("error", "")

        agent_out = AgentOutput(
            status=status,
            command="pipeline",
            output={
                "design": design_data,
                "execution": exec_data,
            },
            error=error if error else None,
        )

        fmt = ctx.obj.get("format", "human") if ctx.obj else "human"
        if fmt == "json":
            click.echo(agent_out.to_json())
        else:
            if status == "success":
                report = exec_data.get("report", {})
                total = report.get("total", 0)
                passed = report.get("passed", 0)
                files = design_data.get("generated_files", [])
                click.echo(
                    f"Pipeline complete: designed {len(files)} file(s), "
                    f"executed {total} case(s), {passed} passed."
                )
            elif status == "error":
                click.echo(f"Pipeline error: {error}")
            else:
                report = exec_data.get("report", {})
                click.echo(
                    f"Pipeline finished with failures: "
                    f"{report.get('passed', 0)}/{report.get('total', 0)} passed."
                )

        if status != "success":
            ctx.exit(1 if status == "failure" else 2)

    except AgentError as err:
        _handle_agent_error(ctx, err, "pipeline")
    except (SystemExit, click.exceptions.Exit):
        raise
    except Exception as exc:
        _handle_unexpected_error(ctx, exc, "pipeline")


# ---------------------------------------------------------------------------
# diagnose
# ---------------------------------------------------------------------------

@main.command()
@click.option("--result", required=True, type=click.Path(exists=False), help="Path to test result (directory or file).")
@click.pass_context
def diagnose(ctx: click.Context, result: str) -> None:
    """Diagnose a failed test result."""
    result_path = os.path.abspath(result)

    # Load result data
    case_results = _load_result_data(result_path)
    if case_results is None:
        _output(
            ctx,
            {"status": "error", "command": "diagnose", "error": f"Cannot load result from {result_path}"},
            f"Error: Cannot load result from {result_path}",
        )
        ctx.exit(2)
        return

    # Build state and call diagnose node directly
    from rodski_agent.execution.nodes import diagnose as diagnose_node

    state: dict[str, Any] = {
        "case_results": case_results,
        "screenshots": [],
    }
    diagnosis_update = diagnose_node(state)
    diagnosis = diagnosis_update.get("diagnosis", {})

    output_data = {
        "status": "success",
        "command": "diagnose",
        "output": diagnosis,
    }

    # Human-readable output
    if diagnosis.get("skipped"):
        human_msg = f"Diagnosis skipped: {diagnosis.get('reason', 'unknown')}"
    else:
        cases = diagnosis.get("cases", [])
        lines = [f"Diagnosed {len(cases)} failed case(s):"]
        for d in cases:
            lines.append(
                f"  [{d.get('case_id', '?')}] {d.get('category', 'UNKNOWN')} "
                f"(confidence={d.get('confidence', 0):.2f}): {d.get('root_cause', '?')}"
            )
            lines.append(f"    Suggestion: {d.get('suggestion', '-')}")
            lines.append(f"    Action: {d.get('recommended_action', '-')}")
        human_msg = "\n".join(lines)

    _output(ctx, output_data, human_msg)


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
    from rodski_agent.common.config import AgentConfig

    try:
        cfg = AgentConfig.load()
        data = {"status": "success", "command": "config show", "output": cfg.to_dict()}
        import yaml as _yaml
        human_msg = _yaml.dump(cfg.to_dict(), allow_unicode=True, default_flow_style=False)
    except Exception as e:
        data = {"status": "error", "command": "config show", "error": str(e)}
        human_msg = f"Error loading config: {e}"

    _output(ctx, data, human_msg)
