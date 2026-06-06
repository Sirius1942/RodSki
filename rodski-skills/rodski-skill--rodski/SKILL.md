---
name: rodski
description: 用于 RodSki 框架源码、XML 活文档协议、关键字实现、XSD schema、CLI、视觉/Desktop/API/DB 能力和 demo 验收链路。处理 RodSki 用例、model.xml、data.sqlite/globalvalue.xml、plan/*.xml 或 TEST_CASE_WRITING_GUIDE.md 合规任务时，优先使用 rodski-case-writer。
---

# RodSki

使用本 skill 时，必须让 RodSki 相关工作遵循项目契约。

RodSki 是面向 AI Agent 的确定性执行引擎与 XML 协议层。Agent 负责探索、决策和生成 XML；RodSki 负责解析 XML、执行确定性动作并返回结果。

## 任务边界

如果目标是编写、修改、审查或校验 RodSki 用例、`case/*.xml`、`model/model.xml`、`data/data.sqlite`、`data/globalvalue.xml` 或 `plan/*.xml`，优先使用 `rodski-case-writer`，不限于 `$HOME/TestCase`。本 skill 主要服务 RodSki 框架源码、协议、schema、关键字实现、CLI 能力和 demo 验收链路。

## 规范来源

在 RodSki 仓库内工作时，以下文件是规范来源；修改行为前先读取相关章节。

- `rodski/docs/CORE_DESIGN_CONSTRAINTS.md`：强制设计约束。
- `rodski/docs/TEST_CASE_WRITING_GUIDE.md`：用例、模型、数据编写契约。
- `rodski/docs/DATA_FILE_ORGANIZATION.md`：测试数据与全局变量组织规则。
- `rodski/docs/VISION_LOCATION.md`：视觉定位契约。
- `rodski/docs/AGENT_INTEGRATION.md`：Agent 与 RodSki 职责边界。
- `rodski/schemas/*.xsd`：可执行 XML 约束。

如果代码与 `CORE_DESIGN_CONSTRAINTS.md` 或 `TEST_CASE_WRITING_GUIDE.md` 冲突，以文档为准并让代码服从，除非用户明确要求修改契约。

需要精简契约摘要时，读取 `references/rodski-contract.md`。

需要本机 CLI 命令、参数或能力清单时，先运行当前 CLI 的 `--version`、顶层 `--help` 和相关子命令 `--help`。只有当前 `--help` 明确列出 `capabilities` 子命令时，才运行 `capabilities`；否则用 `help`、XSD 和最小 dry-run 判断。`references/rodski-cli-snapshot.md` 只是最近一次本机快照，不是事实来源。

## 本机工具入口

优先使用稳定全局入口 `/opt/homebrew/bin/rodski`。该入口会转发到长期 RodSki 安装环境，并在需要时通过 skill wrapper 补齐执行 `run`、`data` 等命令所需的 `PYTHONPATH`：

```bash
RODSKI="/opt/homebrew/bin/rodski"
"$RODSKI" --version
```

不要把 skill 文档、历史快照或旧会话中的版本当作当前事实。每次执行或修改 RodSki 相关行为前，先运行 `--version`。需要确认参数或能力时，先看帮助；只有当前 CLI 暴露 `capabilities` 时才运行它：

```bash
"$RODSKI" --help
"$RODSKI" run --help
"$RODSKI" data --help
"$RODSKI" plan --help
"$RODSKI" --help | rg -q '\bcapabilities\b' && "$RODSKI" capabilities
```

当前 `$HOME/TestCase` 环境里优先使用全局入口 `/opt/homebrew/bin/rodski` 或 `rodski-case-writer` 的流程。该全局入口应转发到长期 RodSki 安装环境 `$HOME/.local/share/rodski/venv/bin/rodski`，不依赖仓库本地 `myenv`。若直接调用 CLI 并看到 `ModuleNotFoundError: No module named 'core'`，改用 wrapper 或设置匹配的 `PYTHONPATH`。

本机可能有多个 RodSki 入口。若用户明确指定某个入口，先运行 `--version` 重新确认。

可用性选择顺序：

1. 用户明确指定的 RodSki CLI
2. `/opt/homebrew/bin/rodski`（稳定全局入口）
3. `$HOME/.local/share/rodski/venv/bin/rodski`（长期 RodSki 安装环境）
4. `command -v rodski` 找到的全局入口

只有在这些入口都不存在，或用户要求安装/升级 RodSki 时，才进入安装流程。

## 安装方法

在 RodSki 仓库根目录安装 RodSki。优先使用仓库 `README.md` 的当前命令；若与核心约束文档冲突，行为契约仍以 `CORE_DESIGN_CONSTRAINTS.md` 和 `TEST_CASE_WRITING_GUIDE.md` 为准。

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
pip install -e ".[web]"
playwright install chromium
```

兼容旧入口时，可能会看到 `pip install -r rodski/requirements.txt`、`python3 rodski/cli_main.py ...` 或 `python rodski/ski_run.py ...`。新任务优先使用已安装后的 CLI；只有在仓库未安装或用户明确要求旧入口时，才使用旧命令。

## 使用方法

常用执行命令：

```bash
RODSKI="/opt/homebrew/bin/rodski"

# 执行一个 case 文件、case 目录或测试模块
"$RODSKI" run rodski-demo/DEMO/demo_full/case/demo_case.xml
"$RODSKI" run rodski-demo/DEMO/demo_full/case/
"$RODSKI" run rodski-demo/DEMO/demo_full/

# 输出 JSON，便于 Agent 解析
"$RODSKI" run case/ --output-format json

# 干跑模式：只校验，不真正执行
"$RODSKI" run case/ --dry-run

# 无头模式执行 Web 用例
"$RODSKI" run case/ --headless

# 生成 HTML 报告
"$RODSKI" run case/ --report html

# 如果当前 CLI 支持，可使用本次执行录制
"$RODSKI" run case/ --record
"$RODSKI" run case/ --record-mode auto
"$RODSKI" run case/ --record-scope target
```

筛选执行：

```bash
"$RODSKI" run case/ --tags smoke
"$RODSKI" run case/ --tags "smoke,regression"
"$RODSKI" run case/ --priority P0
"$RODSKI" run case/ --priority "P0,P1"
"$RODSKI" run case/ --exclude-tags slow
"$RODSKI" run case/ --tags smoke --priority P0
```

数据与模块管理：

```bash
# 初始化标准测试模块骨架
"$RODSKI" init /path/to/MyTestModule

# 查看模块中的逻辑表
"$RODSKI" data list rodski-demo/DEMO/demo_full/

# 查看逻辑表字段
"$RODSKI" data schema rodski-demo/DEMO/demo_full/ RegisterAPI

# 查看指定数据行
"$RODSKI" data show rodski-demo/DEMO/demo_full/ RegisterAPI L001

# 查看逻辑表前 50 行，或通过 --limit 限制数量
"$RODSKI" data query rodski-demo/DEMO/demo_full/ RegisterAPI --limit 20

# 校验数据层
"$RODSKI" data validate rodski-demo/DEMO/demo_full/

# 从废弃 XML 数据迁移到 data.sqlite
"$RODSKI" data import <module>
"$RODSKI" data import <module> --overwrite
```

不要在未重新确认工具存在前生成 `rodski explain ...`、`rodski-agent ...`、`rodski init --with-verify --with-sqlite`、`rodski data validate --strict` 或 `rodski capabilities`。先以当前 CLI 的顶层 `--help`、子命令帮助、XSD 和最小 dry-run 为准；仅在 `--help` 列出 `capabilities` 时才调用它。

查看帮助/能力：

```bash
"$RODSKI" --help
"$RODSKI" run --help
"$RODSKI" --help | rg -q '\bcapabilities\b' && "$RODSKI" capabilities
```

## 工作流程

1. 识别任务面：用例编写、模型编写、数据迁移、关键字行为、Schema 变更、驱动行为、视觉/Desktop 支持、API/DB 支持、demo 验收或文档。
2. 读取相关规范章节；任务涉及 XML、数据或关键字语义时，同时读取 `references/rodski-contract.md`。
3. 保持三元模型：关键字 + 模型 + 数据。不要引入第二套语法或临时捷径。
4. 修改 XML 或 Schema 时执行校验；行为变化优先用现有测试和真实模块验收链路验证。
5. 框架改动如果涉及关键字、XML Schema 或数据契约，必须同步更新文档与 XSD。

## 核心约束

- RodSki 只做确定性执行引擎；不要把 Agent 规划、对话管理或策略编排放进 RodSki。
- 用例编写细则以目标仓库的 `TEST_CASE_WRITING_GUIDE.md`、`rodski-case-writer`、当前 CLI/XSD 为准；本 skill 不复制完整规则，避免多处漂移。
- 保持三元模型：Case 编排动作，Model 定义元素/API/DB 字段，数据进入 `data/data.sqlite`，全局变量只放 `data/globalvalue.xml`。
- 受支持关键字、定位器类型、特殊值的权威清单以 `rodski capabilities` 为准；本文档与 `references/` 出现的关键字名单只是示例和常见幻觉提示，不是完整白名单。API 测试使用 `send` + `verify`；UI 批量输入和原子动作使用 `type` + 数据行；不要新增 `http_get`、`assert_json`、`vision_click`、`clipboard` 等第二套关键字。
- Web/Mobile 导航用 `navigate`；Desktop 启动或切换用 `launch` 前必须确认当前 guide、CLI help、XSD、可选 capabilities 输出和 dry-run 一致。若它们冲突，报告冲突并以 dry-run 结果为准。

## 校验

使用仓库现有校验方式。常见检查包括：

```bash
RODSKI="/opt/homebrew/bin/rodski"
"$RODSKI" --version
"$RODSKI" --help
"$RODSKI" run --help
"$RODSKI" data validate /path/to/module/
"$RODSKI" run /path/to/module/case/ --dry-run --output-format json
python3 -m pytest rodski/tests
```

修改 XML 时，如果工具可用，应使用当前 RodSki 安装包中的匹配 XSD 校验；先通过当前 CLI、Python 环境或仓库源码确认 schema 位置。验收行为变化时，新增或更新真实的 case/model/data 链路，不只依赖单元测试。
