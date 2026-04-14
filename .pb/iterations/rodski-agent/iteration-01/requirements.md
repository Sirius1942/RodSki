# Iteration 01: 项目骨架 + CLI 框架 + 知识库

## 目标

搭建 rodski-agent 项目结构，实现 `rodski-agent --version` 可运行，构建 rodski 框架约束知识库。

## 前置依赖

无（首个迭代）

## 任务列表

### T01-001: 创建项目目录结构 (30min)

- **文件**:
  - `rodski-agent/pyproject.toml`
  - `rodski-agent/README.md`
  - `rodski-agent/src/rodski_agent/__init__.py`
  - `rodski-agent/src/rodski_agent/common/__init__.py`
  - `rodski-agent/src/rodski_agent/design/__init__.py`
  - `rodski-agent/src/rodski_agent/execution/__init__.py`
  - `rodski-agent/src/rodski_agent/pipeline/__init__.py`
  - `rodski-agent/config/agent_config.yaml`
- **描述**: 按设计方案 SS5 创建完整目录结构。编写 `pyproject.toml` 声明依赖（langgraph, click, pyyaml, requests, pillow）。配置 `[project.scripts]` 使 `rodski-agent` 命令可用。在 `__init__.py` 中定义 `__version__ = "0.1.0"`。
- **验收标准**:
  - [ ] `pip install -e ".[dev]"` 成功
  - [ ] `python -c "import rodski_agent"` 不报错

### T01-002: 实现 CLI 入口框架 (60min)

- **文件**: `rodski-agent/src/rodski_agent/cli.py`
- **描述**: 使用 Click 创建 CLI 入口 `main()`。实现 `--version` 选项和 `--format` 全局选项（human/json，默认 human）。注册子命令占位符：`run`、`design`、`pipeline`、`diagnose`、`config`，每个子命令先返回 "Not implemented yet"。
- **验收标准**:
  - [ ] `rodski-agent --version` 输出版本号
  - [ ] `rodski-agent run --help` 显示帮助信息
  - [ ] `rodski-agent --format json run` 以 JSON 格式输出（即使是占位内容）

### T01-003: 配置加载器 (45min)

- **文件**:
  - `rodski-agent/src/rodski_agent/common/config.py`
  - `rodski-agent/config/agent_config.yaml`
- **描述**: 实现 `AgentConfig` 类，加载 YAML 配置。支持配置文件路径查找（当前目录 > 项目根 > 默认）。支持环境变量覆盖（`RODSKI_AGENT_*`）。编写默认配置文件 `agent_config.yaml`（含 rodski 路径、LLM 配置、Agent 行为配置）。
- **验收标准**:
  - [ ] `AgentConfig().rodski.cli_path` 返回正确路径
  - [ ] 环境变量 `RODSKI_AGENT_LLM_MODEL` 可覆盖配置

### T01-004: rodski 框架约束知识库 -- rodski_knowledge.py (60min)

- **文件**:
  - `rodski-agent/src/rodski_agent/common/rodski_knowledge.py`
  - `rodski-agent/tests/test_rodski_knowledge.py`
- **描述**: 从 `CORE_DESIGN_CONSTRAINTS.md` 提取硬性约束，编码为 Python 常量（`SUPPORTED_KEYWORDS`、`UI_ATOMIC_ACTIONS`、`LOCATOR_TYPES`、`DRIVER_TYPES`、`CASE_PHASES`、`COMPONENT_TYPES`、`SPECIAL_VALUES`、`VERIFY_TABLE_SUFFIX`）。从 `TEST_CASE_WRITING_GUIDE.md` 提取目录结构约束（`REQUIRED_DIRS`、`FIXED_FILES`）。实现校验函数（`validate_action`、`validate_locator_type`、`validate_element_data_consistency`、`validate_directory_structure`、`validate_verify_table_name`）。编写 `RODSKI_CONSTRAINT_SUMMARY` 字符串常量供 LLM 提示词嵌入。
- **rodski 知识依赖**:
  - `rodski/docs/CORE_DESIGN_CONSTRAINTS.md` -- 关键字清单(SS5)、定位器类型(SS2.5)、数据表规则(SS2)、目录结构(SS6)
  - `rodski/docs/TEST_CASE_WRITING_GUIDE.md` -- Case/Model/Data XML 格式
- **验收标准**:
  - [ ] 所有常量与 `CORE_DESIGN_CONSTRAINTS.md` 一致
  - [ ] 校验函数能正确识别合法/非法输入
  - [ ] `RODSKI_CONSTRAINT_SUMMARY` 涵盖关键字、Case XML、Model XML、Data XML、目录结构五大类约束
  - [ ] 单元测试验证约束与 rodski 源码同步

### T01-005: 单元测试基础设施 (30min)

- **文件**:
  - `rodski-agent/tests/__init__.py`
  - `rodski-agent/tests/conftest.py`
  - `rodski-agent/tests/test_cli.py`
  - `rodski-agent/tests/test_config.py`
- **描述**: 编写 `conftest.py`，提供 `cli_runner` fixture（Click CliRunner）。编写 CLI 版本号测试和配置加载测试。
- **验收标准**:
  - [ ] `cd rodski-agent && pytest tests/ -v` 全部通过
  - [ ] 至少 5 个测试用例

### T01-006: CI 配置 (15min)

- **文件**: `rodski-agent/Makefile`
- **描述**: 编写 `make test`（运行 pytest）、`make lint`（运行 ruff 或 flake8）、`make install`（pip install -e .）。
- **验收标准**:
  - [ ] `make test` 可运行
  - [ ] `make install && rodski-agent --version` 成功

## 交付物

- 可安装的 Python 包 `rodski-agent`
- `rodski-agent --version` 可运行
- `rodski_knowledge.py` 框架约束知识库（含常量 + 校验函数 + LLM 约束摘要）
- 8+ 个单元测试通过
- 完整的项目目录结构

## 约束检查

- [ ] `SUPPORTED_KEYWORDS` 与 `CORE_DESIGN_CONSTRAINTS.md` SS5 一致（15 个关键字）
- [ ] `UI_ATOMIC_ACTIONS` 不在 SUPPORTED 中（SS1.2）
- [ ] `LOCATOR_TYPES` 包含全部 12 种定位器类型（SS2.5）
- [ ] `REQUIRED_DIRS` 包含 case/model/data（SS6）
- [ ] `RODSKI_CONSTRAINT_SUMMARY` 内容不违反任何核心约束条款
