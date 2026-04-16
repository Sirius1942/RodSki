# rodski-agent

**rodski-agent** is the AI Agent layer for the [RodSki](https://github.com/RodSki/rodski) test automation framework.

```
Harness Agent (Claude Code / CI/CD)
        | CLI + JSON stdout
        v
  rodski-agent (this project)     <-- test design + execution + smart repair
        | CLI call
        v
    rodski (execution engine)     <-- XML parse -> keyword execution -> result
```

## Installation

```bash
# From PyPI
pip install rodski-agent

# Development (editable + test tools)
pip install -e "rodski-agent/[dev]"
```

### Dependencies

| Package | Purpose | Required |
|---------|---------|----------|
| langgraph | Workflow orchestration (StateGraph) | Yes |
| langchain-anthropic | Claude LLM integration | Yes |
| langchain-openai | OpenAI LLM integration | Yes |
| click | CLI framework | Yes |
| pyyaml | Configuration files | Yes |
| requests | OmniParser HTTP client | Yes |
| pillow | Image processing | Yes |

## Quick Start

### 1. Execute a test case

```bash
# Run a test module directory
rodski-agent run --case path/to/test_module/ --format json

# Specify browser and headed mode
rodski-agent run --case path/to/test_module/ --browser firefox --no-headless

# Set max retry count
rodski-agent run --case path/to/test_module/ --max-retry 5
```

### 2. Design a test case from requirements

```bash
# Generate test case from natural language
rodski-agent design \
  --requirement "Test login with username/password" \
  --output output/login/

# Enable visual exploration with a target URL
rodski-agent design \
  --requirement "Test login" \
  --url "https://app.example.com/login" \
  --output output/login/
```

### 3. Full Pipeline (design + validate + execute)

```bash
# Basic pipeline
rodski-agent pipeline \
  --requirement "Test user registration" \
  --url "https://app.example.com/register" \
  --output output/register/ \
  --format json

# Parallel execution with custom retry settings
rodski-agent pipeline \
  --requirement "Test checkout flow" \
  --url "https://app.example.com" \
  --output output/checkout/ \
  --parallel --max-workers 4 \
  --max-retry 5 --max-fix-attempts 3
```

### 4. Diagnose failed tests

```bash
# Diagnose from result directory
rodski-agent diagnose --result output/login/result/

# Diagnose from specific result file
rodski-agent diagnose --result output/login/execution_summary.json --format json
```

### 5. View configuration

```bash
rodski-agent config show
```

## Output Format

All commands support `--format json` (default: `human`). JSON output follows a unified contract:

```json
{
  "status": "success | failure | error",
  "command": "run | design | pipeline | diagnose",
  "output": { ... },
  "error": null
}
```

### run output example

```json
{
  "status": "success",
  "command": "run",
  "output": {
    "total": 3,
    "passed": 3,
    "failed": 0,
    "cases": [
      {"id": "c001", "status": "PASS", "time": 2.1},
      {"id": "c002", "status": "PASS", "time": 1.8}
    ]
  }
}
```

### design output example

```json
{
  "status": "success",
  "command": "design",
  "output": {
    "cases": ["case/c001.xml"],
    "models": ["model/model.xml"],
    "data": ["data/data.xml"],
    "summary": "Generated 3 file(s)"
  }
}
```

## Configuration

rodski-agent looks for `agent_config.yaml` in this order:

1. `$RODSKI_AGENT_CONFIG` env var
2. `./agent_config.yaml` (current directory)
3. `<project_root>/config/agent_config.yaml`
4. Built-in defaults

Environment variables override config file values: `RODSKI_AGENT_LLM__DESIGN__MODEL=gpt-4o`.

### LLM Configuration

Design and Execution agents use separate LLM configurations:

```yaml
llm:
  design:
    provider: claude
    model: claude-sonnet-4-20250514
    base_url: "http://code.casstime.ai"
    api_key_env: ANTHROPIC_API_KEY
    temperature: 0.7
    max_tokens: 4096
  execution:
    provider: claude
    model: claude-sonnet-4-20250514
    base_url: "http://code.casstime.ai"
    api_key_env: ANTHROPIC_API_KEY
    temperature: 0.1
    max_tokens: 2048
```

## Architecture

### Design Agent (LangGraph)

```
analyze_req -> explore_page -> identify_elem -> plan_cases -> design_data -> generate_xml -> validate_xml
                                                                                  ^              |
                                                                                  +-- (fail) ----+
```

| Node | Description |
|------|-------------|
| analyze_req | LLM extracts test scenarios from requirements |
| explore_page | Playwright screenshot + OmniParser element detection |
| identify_elem | LLM Vision adds semantic labels to detected elements |
| plan_cases | Plans test case structure (phases, steps, models) |
| design_data | Designs test data tables |
| generate_xml | Generates case/model/data XML files |
| validate_xml | Validates with `rodski validate`, retries on failure |

### Execution Agent (LangGraph)

```
pre_check -> execute -> parse_result -[pass]-> report
                                     -[fail]-> diagnose -> retry_decide -[retry]-> apply_fix -> execute
                                                                        -[give_up]-> report
```

| Node | Description |
|------|-------------|
| pre_check | Validate case path, directory structure, rodski version |
| execute | Call `rodski run` to execute tests |
| parse_result | Parse execution results |
| diagnose | LLM diagnoses failure root cause |
| retry_decide | Decide retry based on diagnosis confidence |
| apply_fix | Smart repair (wait/locator/data strategies) |
| report | Generate final report |

### Smart Repair Strategies

| Strategy | Trigger | Fix Action |
|----------|---------|-----------|
| Wait | Timeout / element not ready | Insert wait step before failing step |
| Locator | Element not found | LLM suggests new locator, update model XML |
| Data | Data mismatch | LLM suggests new data value, update data XML |

### Pipeline Orchestrator

The `pipeline` command chains Design -> Validation Gate -> Execution:

1. **Design Phase**: Generate test case XML from requirements
2. **Validation Gate**: Run `rodski validate` on all generated XML; fail-fast if invalid
3. **Execution Phase**: Execute generated cases (sequential or parallel with `--parallel`)

## Development

```bash
# Install dev dependencies
pip install -e "rodski-agent/[dev]"

# Run tests (424 tests)
cd rodski-agent
PYTHONPATH=src python3 -m pytest tests/ -v

# Run with coverage
PYTHONPATH=src python3 -m pytest tests/ --cov=rodski_agent
```

## Project Structure

```
rodski-agent/
├── pyproject.toml
├── README.md
├── config/
│   └── agent_config.yaml     # Default configuration
├── schemas/
│   └── output_schema.json    # JSON output schema
├── src/rodski_agent/
│   ├── cli.py                # CLI entry point (Click)
│   ├── common/
│   │   ├── config.py         # Configuration management
│   │   ├── contracts.py      # JSON output contract
│   │   ├── errors.py         # Error classification
│   │   ├── formatters.py     # Output formatting
│   │   ├── llm_bridge.py     # LLM abstraction (langchain)
│   │   ├── omniparser_client.py  # OmniParser HTTP client
│   │   ├── result_parser.py  # Result parser
│   │   ├── rodski_knowledge.py   # RodSki constraint KB
│   │   ├── rodski_tools.py   # RodSki CLI wrappers
│   │   ├── state.py          # LangGraph state definitions
│   │   └── xml_builder.py    # XML generator
│   ├── design/
│   │   ├── graph.py          # Design Agent graph
│   │   ├── nodes.py          # Design workflow nodes
│   │   ├── prompts.py        # LLM prompts
│   │   └── visual.py         # Visual exploration
│   ├── execution/
│   │   ├── graph.py          # Execution Agent graph
│   │   ├── nodes.py          # Execution workflow nodes
│   │   ├── prompts.py        # Diagnosis prompts
│   │   └── fixer.py          # Smart repair strategies
│   └── pipeline/
│       └── orchestrator.py   # Design -> Execution pipeline
└── tests/                    # 424 unit tests
```

## License

MIT
