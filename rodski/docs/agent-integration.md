# Agent Integration Guide

## Overview

RodSki serves as the execution layer for AI Agents, providing structured test automation capabilities through a CLI interface with JSON output support.

## Architecture

```
AI Agent (OpenClaw/Claude Code)
    ↓
RodSki CLI (--output-format json)
    ↓
Test Execution Engine
    ↓
JSON Result Output
```

## CLI Usage

### Basic Execution

```bash
rodski run <case_path> --output-format json
```

### Success Response

```json
{
  "status": "success",
  "exit_code": 0,
  "summary": {
    "total": 5,
    "passed": 5,
    "failed": 0,
    "skipped": 0
  },
  "steps": [
    {
      "case_id": "TC001",
      "title": "Login Test",
      "status": "PASS",
      "execution_time": 2.5,
      "error": "",
      "screenshot_path": ""
    }
  ],
  "variables": {}
}
```

### Failure Response

```json
{
  "status": "failed",
  "exit_code": 1,
  "error": {
    "type": "ExecutionError",
    "message": "Element not found: #login-button"
  },
  "failed_step": {
    "case_id": "TC001",
    "index": 3
  }
}
```

### Interrupt Response

```json
{
  "status": "interrupted",
  "exit_code": 130,
  "error": {
    "type": "UserInterrupt",
    "message": "Execution interrupted by user"
  }
}
```

## Exit Codes

- `0`: Success - all tests passed
- `1`: Failure - one or more tests failed
- `130`: User interrupt (Ctrl+C)

## Integration Examples

### OpenClaw Integration

```python
import subprocess
import json

result = subprocess.run(
    ["rodski", "run", "examples/demo_case.xml", "--output-format", "json"],
    capture_output=True,
    text=True
)

data = json.loads(result.stdout)
if data["status"] == "success":
    print(f"Tests passed: {data['summary']['passed']}/{data['summary']['total']}")
else:
    print(f"Test failed: {data['error']['message']}")
```

### Claude Code Integration

Use RodSki as a skill/tool within Claude Code workflows to execute automated tests and validate application behavior.

## Best Practices

1. Always use `--output-format json` for programmatic access
2. Check `exit_code` for quick success/failure determination
3. Parse `failed_step` to identify exact failure location
4. Use `--headless` mode for CI/CD environments
5. Capture `screenshot_path` for debugging failures
