# Iteration 07: 文档体系重构

**周期**: 2026-05-18 ~ 2026-05-24 (1 周)
**分支**: `iteration-07-docs-restructuring`

## 目标

对 RodSki 文档体系进行全面重构，建立清晰的文档分类、完整的 Agent 集成指南、标准的 Skill 参考文档和结构化的错误处理最佳实践文档。

## 背景

当前 RodSki 文档存在以下问题：
1. **分类不清**: docs/ 目录下混有设计文档、用户指南、需求文档，缺乏统一分类
2. **Agent 集成指南不完整**: 现有 `docs/agent-integration.md` 和 `docs/skill-integration.md` 内容单薄
3. **Skill 参考文档缺失**: 没有标准的 Skill 定义格式说明
4. **错误处理文档分散**: 异常处理相关内容分散在多处
5. **示例不足**: 缺乏从入门到精通的完整示例体系

## 成功标准

1. docs/ 目录按 `user-guides/` / `agent-guides/` / `developer-guides/` / `design/` 分类
2. Agent 集成指南覆盖完整集成路径（OpenClaw / Claude Code / 直接 API）
3. Skill 参考文档提供标准 Skill 定义模板和示例
4. 错误处理最佳实践文档覆盖所有异常类型和处理策略
5. 文档可通过 `mkdocs` 或类似工具构建为静态站点

---

## 需求详述

### R7-001: 文档目录结构重构

将 `docs/` 重构为以下结构：

```
docs/
├── index.md                      # 文档首页
├── user-guides/                  # 用户指南（面向测试工程师）
│   ├── QUICKSTART.md
│   ├── INSTALLATION.md
│   ├── CASE_WRITING.md
│   ├── BEST_PRACTICES.md
│   ├── TROUBLESHOOTING.md
│   ├── API_TESTING.md
│   ├── VISION_TESTING.md
│   ├── MOBILE_TESTING.md
│   ├── PARALLEL_EXECUTION.md
│   ├── EXCEPTION_HANDLING.md
│   └── DYNAMIC_EXECUTION.md      # Iteration-06 完成后新增
├── agent-guides/                 # Agent 集成指南（面向 AI Agent 开发者）
│   ├── README.md                 # Agent 集成总览
│   ├── OPENCLAW_INTEGRATION.md   # OpenClaw skill 集成
│   ├── CLAUDE_CODE_INTEGRATION.md # Claude Code 集成
│   ├── DIRECT_API.md             # 直接 Python API 集成
│   ├── SKILL_REFERENCE.md        # Skill 定义参考
│   ├── EXAMPLES.md               # Agent 集成示例
│   └── PROTOCOL.md               # Agent-RodSki 通信协议
├── developer-guides/             # 开发者指南（面向框架贡献者）
│   ├── ARCHITECTURE.md
│   ├── CONTRIBUTING.md
│   ├── TESTING_GUIDE.md
│   └── CODING_STANDARDS.md
├── design/                       # 设计文档（架构决策记录）
│   ├── ARCHITECTURE.md
│   ├── RPA_ROADMAP_SUMMARY.md
│   └── CORE_DESIGN_CONSTRAINTS.md
├── requirements/                  # 需求文档（追溯用）
│   └── RODSKI_REQUIREMENTS.md
└── mkdocs.yml                    # MkDocs 配置文件
```

### R7-002: Agent 集成指南完善

#### `agent-guides/OPENCLAW_INTEGRATION.md`

完整的 OpenClaw Skill 集成指南：

```yaml
# .openclaw/skills/rodski/SKILL.md 示例
name: rodski
description: 执行 RodSki XML 自动化测试用例
...

commands:
  run:
    description: 执行测试用例
    args:
      - name: case_path
        type: string
        required: true
      - name: --headless
        type: flag
    example: rodski run case/login_case.xml --headless
```

包含：
- OpenClaw Skill 定义格式
- 目录结构要求
- 输出格式说明
- 错误处理集成

#### `agent-guides/CLAUDE_CODE_INTEGRATION.md`

Claude Code 集成指南：
- Claude Code `--mcp` 标志使用 RodSki MCP server
- 从 Claude Code 调用 RodSki 的 Python API
- 处理执行结果并解析 JSON 输出
- 完整的对话示例

#### `agent-guides/PROTOCOL.md`

Agent-RodSki 通信协议规范：
- 命令请求格式（JSON）
- 响应格式（结构化 JSON）
- 错误码体系
- 事件流（start/progress/complete/error）

### R7-003: Skill 参考文档

`agent-guides/SKILL_REFERENCE.md`:

完整的 Skill 定义参考：

```yaml
# Skill 定义模板
name: <skill-name>
description: <简洁描述，一句话>
version: "1.0.0"
entrypoint: <主入口脚本>

# 输入参数定义
parameters:
  <param_name>:
    type: string | number | boolean | file | enum
    required: true | false
    default: <默认值>
    description: <参数说明>
    enum: [<选项列表>]  # 仅 enum 类型

# 输出格式
output:
  format: json | xml | text
  schema: <JSON Schema>

# 环境要求
requirements:
  - python >= 3.8
  - rodski >= 3.0

# 示例
examples:
  - description: <示例描述>
    input:
      case_path: case/demo.xml
    output:
      status: success
```

包含：
- YAML Skill 定义格式说明
- 参数类型详解
- 输出格式规范
- 多示例说明

### R7-004: 错误处理最佳实践文档增强

增强现有 `docs/user-guides/EXCEPTION_HANDLING.md`：

**新增章节**:
1. **错误恢复策略模式**
   - Retry Pattern（重试模式）
   - Circuit Breaker Pattern（断路器模式）
   - Fallback Pattern（降级模式）
2. **AI 辅助诊断集成**
   - 如何配置 Claude / OpenAI 诊断
   - 自定义诊断规则
   - 诊断结果解读
3. **自定义异常类型扩展**
   - 如何注册自定义异常类型
   - 如何定义错误恢复动作
4. **生产环境最佳实践**
   - 日志记录规范
   - 告警阈值设置
   - 故障复盘流程

### R7-005: MkDocs 文档站点

配置 `docs/mkdocs.yml`：

```yaml
site_name: RodSki 文档
site_description: RodSki 自动化测试框架文档
site_author: RodSki Team

nav:
  - 首页: index.md
  - 用户指南:
    - 快速入门: user-guides/QUICKSTART.md
    - 用例编写: user-guides/CASE_WRITING.md
    - 异常处理: user-guides/EXCEPTION_HANDLING.md
  - Agent 集成:
    - 概述: agent-guides/README.md
    - OpenClaw 集成: agent-guides/OPENCLAW_INTEGRATION.md
    - Claude Code 集成: agent-guides/CLAUDE_CODE_INTEGRATION.md
    - Skill 参考: agent-guides/SKILL_REFERENCE.md
  - 开发者指南:
    - 架构设计: developer-guides/ARCHITECTURE.md
    - 贡献指南: developer-guides/CONTRIBUTING.md

theme:
  name: material
  palette: ...
```

**GitHub Pages 部署配置**:
- `.github/workflows/docs.yml` — 自动构建和部署
- 每次 push 到 main 分支自动更新文档站点

### R7-006: 文档质量审核

- 文档链接完整性检查（无死链）
- 示例代码可运行验证
- 文档一致性检查（术语统一）
- 中英文混排规范

---

## 非功能需求

- **可搜索**: 所有文档通过 MkDocs 全文搜索
- **可离线**: 文档可本地构建，不依赖在线服务
- **版本化**: 支持多版本文档（当前版本 + 历史版本）
- **可参与**: 贡献流程清晰，有 CONTRIBUTING.md

## 依赖

- `docs/mkdocs.yml` — MkDocs 配置
- `.github/workflows/docs.yml` — CI/CD 部署
- 各指南文档 — 需要补充完善的内容

## 测试策略

- 文档构建测试: `mkdocs build` 成功无错误
- 链接检查: 无死链（使用 linkchecker）
- 示例验证: 示例代码可执行
