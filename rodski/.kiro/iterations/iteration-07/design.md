# Iteration 07 设计文档

## 概述

Iteration 07 的目标是重构 RodSki 文档体系，建立清晰的文档分类和完善的 Agent 集成指南。

## 文档分类设计

### 四层文档架构

```
RodSki 文档
├── user-guides/     ← 测试工程师视角：如何使用
├── agent-guides/    ← AI Agent 视角：如何集成
├── developer-guides/ ← 框架开发者视角：如何贡献
└── design/          ← 架构决策视角：为何这样设计
```

### 用户指南 (user-guides/)

**目标读者**: 使用 RodSki 编写和执行测试用例的测试工程师

**核心文档**:
- `QUICKSTART.md` — 5 分钟快速入门
- `CASE_WRITING.md` — 完整的用例编写指南（最核心）
- `BEST_PRACTICES.md` — 用例编写最佳实践
- `EXCEPTION_HANDLING.md` — 异常处理与恢复
- `DYNAMIC_EXECUTION.md` — 动态执行（Iteration-06 后）

**文档风格**:
- 面向操作步骤
- 大量示例代码
- 包含截图和流程图

### Agent 集成指南 (agent-guides/)

**目标读者**: AI Agent 开发者（OpenClaw / Claude Code / 自定义 Agent）

**核心文档**:
- `README.md` — Agent 集成总览（快速导航）
- `OPENCLAW_INTEGRATION.md` — OpenClaw Skill 完整集成
- `CLAUDE_CODE_INTEGRATION.md` — Claude Code 集成
- `DIRECT_API.md` — Python API 直接调用
- `SKILL_REFERENCE.md` — Skill 定义标准格式
- `EXAMPLES.md` — 完整集成示例
- `PROTOCOL.md` — JSON 通信协议规范

**文档风格**:
- 面向 API 和协议
- 包含完整的请求/响应示例
- 强调确定性输出（JSON）

### 开发者指南 (developer-guides/)

**目标读者**: 为 RodSki 框架贡献代码的开发者

**核心文档**:
- `ARCHITECTURE.md` — 整体架构设计
- `CONTRIBUTING.md` — 贡献流程规范
- `TESTING_GUIDE.md` — 测试编写规范
- `CODING_STANDARDS.md` — 代码风格规范

### 设计文档 (design/)

**目标读者**: 需要理解框架设计决策的开发者

保留现有 `docs/design/` 内容，重点补充架构决策记录（ADR - Architecture Decision Records）。

## MkDocs 配置设计

### 站点配置 (mkdocs.yml)

```yaml
site_name: RodSki 文档中心
site_url: https://Sirius1942.github.io/RodSki/
site_description: RodSki AI-Agent 自动化测试框架

theme:
  name: material
  language: zh
  features:
    - navigation.instant
    - navigation.tracking
    - toc.integrate
    - search.suggest
    - search.highlight
  palette:
    - media: "(prefers-color-scheme: light)"
      scheme: default
      primary: indigo
      accent: blue
    - media: "(prefers-color-scheme: dark)"
      scheme: slate
      primary: indigo
      accent: blue

nav:
  - Home: index.md
  - 用户指南:
    - user-guides/QUICKSTART.md
    - user-guides/CASE_WRITING.md
    - user-guides/BEST_PRACTICES.md
    - user-guides/EXCEPTION_HANDLING.md
    - user-guides/TROUBLESHOOTING.md
    - user-guides/API_TESTING.md
    - user-guides/VISION_TESTING.md
    - user-guides/MOBILE_TESTING.md
  - Agent 集成:
    - agent-guides/README.md
    - agent-guides/OPENCLAW_INTEGRATION.md
    - agent-guides/CLAUDE_CODE_INTEGRATION.md
    - agent-guides/DIRECT_API.md
    - agent-guides/SKILL_REFERENCE.md
    - agent-guides/EXAMPLES.md
    - agent-guides/PROTOCOL.md
  - 开发者:
    - developer-guides/ARCHITECTURE.md
    - developer-guides/CONTRIBUTING.md
  - 设计:
    - design/ARCHITECTURE.md
    - design/CORE_DESIGN_CONSTRAINTS.md
```

### GitHub Pages 部署

```yaml
# .github/workflows/docs.yml
name: Deploy documentation
on:
  push:
    branches: [main]
    paths: ['docs/**']

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install mkdocs-material
      - run: mkdocs gh-deploy --force
```

## Agent 通信协议设计

### 请求格式

```json
{
  "command": "run",
  "args": {
    "case_path": "case/login_case.xml",
    "--headless": true,
    "--output-format": "json"
  },
  "session_id": "agent-session-001"
}
```

### 响应格式（流式）

```json
// 进度事件
{"type": "progress", "step": 3, "total": 10, "status": "running"}

// 完成事件
{
  "type": "result",
  "status": "success",
  "summary": {"total": 5, "passed": 5, "failed": 0},
  "exit_code": 0
}
```

### 错误事件

```json
{
  "type": "error",
  "error": {
    "type": "ElementNotFoundError",
    "message": "无法定位元素: .login-btn",
    "step_index": 3,
    "screenshot": "screenshots/TC001_failure.png"
  }
}
```

## Skill 定义标准格式

```yaml
# SKILL.md 标准格式
name: rodski-test
description: 执行 RodSki XML 自动化测试用例
version: "1.0.0"

# 触发条件
trigger:
  type: command  # command | event | cron
  patterns:
    - "rodski run {case_path}"
    - "执行.*测试用例"

# 参数定义
parameters:
  case_path:
    type: string
    description: 测试用例 XML 文件路径
    required: true
    pattern: ".*\\.xml$"
  headless:
    type: boolean
    description: 无头模式执行
    default: false
  output_format:
    type: enum
    description: 输出格式
    default: json
    enum: [json, xml, text]

# 输出规范
output:
  format: json
  schema: |
    {
      "status": "success|failed|error",
      "summary": {...},
      "error": {...}
    }

# 执行环境
environment:
  python: ">=3.8"
  dependencies:
    - rodski>=3.0

# 示例
examples:
  - description: 执行登录测试用例
    input:
      case_path: case/login_case.xml
      headless: true
      output_format: json
    expected:
      status: success
```

## 文档迁移清单

| 原始路径 | 新路径 | 状态 |
|---------|--------|------|
| `docs/README.md` | 删除（内容合并到 index.md） | 待迁移 |
| `docs/user-guides/QUICKSTART.md` | `docs/user-guides/QUICKSTART.md` | 保留 |
| `docs/user-guides/EXCEPTION_HANDLING.md` | `docs/user-guides/EXCEPTION_HANDLING.md` | 增强 |
| `docs/agent-integration.md` | `docs/agent-guides/README.md` | 合并增强 |
| `docs/skill-integration.md` | `docs/agent-guides/SKILL_REFERENCE.md` | 合并增强 |
| `docs/design/ARCHITECTURE.md` | `docs/design/ARCHITECTURE.md` | 保留 |
| `docs/requirements/RODSKI_REQUIREMENTS.md` | `docs/requirements/RODSKI_REQUIREMENTS.md` | 保留 |
| 新增 | `docs/agent-guides/OPENCLAW_INTEGRATION.md` | 新建 |
| 新增 | `docs/agent-guides/CLAUDE_CODE_INTEGRATION.md` | 新建 |
| 新增 | `docs/agent-guides/DIRECT_API.md` | 新建 |
| 新增 | `docs/agent-guides/PROTOCOL.md` | 新建 |
| 新增 | `docs/developer-guides/CONTRIBUTING.md` | 新建 |
| 新增 | `docs/mkdocs.yml` | 新建 |
| 新增 | `.github/workflows/docs.yml` | 新建 |

## 质量检查工具

### 链接检查

```bash
pip install linkchecker
linkchecker docs/ --output=link_report.txt
```

### Markdown 格式检查

```bash
pip install markdownlint-cli
markdownlint docs/**/*.md
```

### 示例代码验证

```bash
# 提取所有代码块并验证语法
python scripts/validate_examples.py docs/
```
