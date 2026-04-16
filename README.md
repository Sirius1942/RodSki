# RodSki

**RodSki** 是面向 AI Agent 的跨平台确定性测试执行引擎，基于 XML 活文档协议，支持 Web（Playwright）、Android（Appium）、iOS（Appium）和桌面应用（PyWinAuto）的自动化测试执行。

> Agent 负责思考，RodSki 负责稳定执行。

## 特性

- **结构化 XML 协议** — model / case / data 活文档，Agent 可读可写
- **多平台确定性执行** — Web / Android / iOS / Desktop 统一关键字
- **视觉定位能力** — OmniParser + LLM 语义定位（可选 AI 能力层）
- **Agent 友好 CLI** — run / validate / explain / dry-run，JSON 结构化输出
- **活文档模式** — Agent 写 XML → RodSki 执行 → 结果反馈 → Agent 分析
- **智能等待** — 自动处理元素加载延迟，零配置开箱即用
- **智能诊断** — AI 辅助失败分析与恢复建议（可选）

## 快速开始

### 前置条件

- Python >= 3.9
- pip >= 21.0

### 安装

```bash
# 推荐：创建虚拟环境
python3 -m venv .venv && source .venv/bin/activate

# ---- rodski 执行引擎 ----

# 基础安装（仅核心 + XML 解析）
pip install -e .

# Web 测试（Playwright）
pip install -e ".[web]"
playwright install chromium          # 安装浏览器

# 移动端测试（Appium）
pip install -e ".[mobile]"

# 全部能力（Web + Mobile + Vision + LLM + GUI）
pip install -e ".[all]"

# ---- rodski-agent（AI Agent 层）----

# 基础安装
pip install -e rodski-agent/

# 开发环境（含 pytest）
pip install -e "rodski-agent/[dev]"

# MCP Server 支持（需 Python >= 3.10）
pip install -e "rodski-agent/[mcp]"
```

### rodski 执行引擎

```bash
# 执行测试
rodski run case/ --output-format json

# 解释用例（自然语言）
rodski explain case/login.xml

# 干跑模式（仅验证不执行）
rodski run case/ --dry-run
```

### rodski-agent (AI Agent 层)

```bash
# 从需求自动生成测试用例
rodski-agent design --requirement "测试登录功能" --output output/login/

# 执行测试用例（含智能重试）
rodski-agent run --case output/login/ --format json

# 设计 + 执行一步到位
rodski-agent pipeline --requirement "测试登录" --output output/login/ --format json

# 诊断失败用例
rodski-agent diagnose --result output/login/result/
```

## 架构概览

```
Agent (探索/决策) → XML (活文档) → RodSki (执行) → JSON (结果) → Agent (分析)
```

RodSki 作为 Agent 工具链中的执行层，提供确定性、可重复的测试执行能力。Agent 通过 XML 协议描述测试意图，RodSki 负责跨平台执行并以 JSON 格式返回结构化结果，供 Agent 进一步分析和决策。

## 项目结构

```
RodSki/
├── rodski/              # Layer 1: 执行引擎
│   ├── core/            # 执行引擎（关键字、解析器、诊断）
│   ├── drivers/         # 平台驱动（Playwright/Appium/PyWinAuto）
│   ├── llm/             # LLM 能力层（可选）
│   ├── vision/          # 视觉定位（可选）
│   ├── rodski_cli/      # CLI 子命令
│   ├── config/          # 配置文件
│   └── docs/            # 框架文档
├── rodski-agent/        # Layer 2: AI Agent 层
│   ├── src/rodski_agent/
│   │   ├── design/      # Design Agent（需求→用例）
│   │   ├── execution/   # Execution Agent（执行→诊断→修复）
│   │   ├── pipeline/    # Pipeline 编排
│   │   ├── common/      # 共享工具（LLM、XML、配置）
│   │   ├── cli.py       # CLI 入口
│   │   └── mcp_server.py # MCP Server
│   └── tests/           # 453 个单元测试
├── rodski-demo/         # 官方示例
└── .pb/                 # 项目管理文档
```

## 文档

| 文档 | 说明 |
|------|------|
| [Agent 集成指南](rodski/docs/AGENT_INTEGRATION.md) | Agent 接入主入口 |
| [用例编写指南](rodski/docs/TEST_CASE_WRITING_GUIDE.md) | XML 用例编写规范 |
| [核心设计约束](rodski/docs/CORE_DESIGN_CONSTRAINTS.md) | 框架不可违反的设计约束 |
| [关键字参考](rodski/docs/SKILL_REFERENCE.md) | 全部关键字语法说明 |
| [架构说明](rodski/docs/ARCHITECTURE.md) | 框架内部架构 |
| [视觉定位](rodski/docs/VISION_LOCATION.md) | OmniParser 视觉定位能力 |

## 智能等待

RodSki 内置智能等待机制，自动处理 UI 元素的加载延迟，无需手动添加等待步骤。

- **零配置** — 默认启用，开箱即用
- **性能优化** — 元素就绪时立即执行，不浪费时间
- **自动重试** — 元素未加载时自动重试（默认 30 次 x 300ms = 9 秒）
- **可配置** — 支持自定义重试次数和间隔

配置项位于 `rodski/config/config.json`：

```json
{
  "smart_wait_enabled": true,
  "smart_wait_max_retries": 30,
  "smart_wait_retry_interval": 0.3,
  "smart_wait_log_retry": true
}
```

## License

MIT License - 详见 [LICENSE](rodski/LICENSE)
