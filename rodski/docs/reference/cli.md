# CLI Reference

RodSki command-line interface reference.

## Commands

### rodski run

Execute test cases.

```bash
rodski run <case_path> [options]
```

**Arguments:**
- `case_path`: Path to case XML file or case directory

**Options:**
- `--browser <type>`: Browser type (chrome, firefox, edge)
- `--headless`: Run in headless mode
- `--config <path>`: Custom config file path
- `--module-dir <path>`: Test module directory
- `--debug`: Enable debug logging

**Examples:**
```bash
rodski run product/myapp/login/case/login.xml
rodski run product/myapp/login/case/ --headless
rodski run product/myapp/login/case/ --browser firefox --debug
```

### rodski explain

Explain test case execution with AI analysis.

```bash
rodski explain <case_path> [options]
```

**Arguments:**
- `case_path`: Path to case XML file

**Options:**
- `--result <path>`: Result XML file to analyze
- `--verbose`: Show detailed explanation

**Examples:**
```bash
rodski explain product/myapp/login/case/login.xml
rodski explain product/myapp/login/case/login.xml --result result/20260330_103055/result.xml
```

### rodski validate

Validate XML files against schemas.

```bash
rodski validate <file_path>
```

**Arguments:**
- `file_path`: Path to XML file (case, model, data, or result)

**Examples:**
```bash
rodski validate product/myapp/login/case/login.xml
rodski validate product/myapp/login/model/model.xml
```

### rodski init

Initialize a new test project structure.

```bash
rodski init <project_name>
```

**Arguments:**
- `project_name`: Name of the test project

**Examples:**
```bash
rodski init myapp
```

## Global Options

- `--version`: Show version information
- `--help`: Show help message
- `-v, --verbose`: Verbose output
- `-q, --quiet`: Quiet mode (errors only)

## Environment Variables

- `RODSKI_CONFIG`: Default config file path
- `RODSKI_BROWSER`: Default browser type
- `ANTHROPIC_API_KEY`: API key for AI features
