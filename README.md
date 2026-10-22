# RodSki

**RodSki** 是面向 AI Agent 的跨平台确定性测试执行引擎，基于 XML 活文档协议，支持 Web（Playwright）、Android（Appium）、iOS（Appium）和桌面应用（PyWinAuto）的自动化测试执行。

> Agent 负责思考，RodSki 负责稳定执行。
>
> 测试数据：`data/data.sqlite` 是唯一测试数据文件（v6.0.0 起）。`data.xml` / `data_verify.xml` 已废弃，存在即运行报错，用 `rodski data import <module>` 迁移后删除。

## 特性

- **结构化 XML 协议** — model / case / data 活文档，Agent 可读可写
- **SQLite 测试数据** — `data/data.sqlite` 是唯一测试数据文件，`rodski data` 子命令查询与编辑
- **多平台确定性执行** — Web / Android / iOS / Desktop 统一关键字
- **视觉定位能力** — OmniParser + LLM 语义定位（可选 AI 能力层）
- **Agent 友好 CLI** — run / dry-run / data / init / plan / case lint / capabilities
- **活文档模式** — Agent 写 XML → RodSki 执行 → 结果反馈 → Agent 分析
- **自动等待** — 自动处理元素加载延迟，不配置默认最多等 10 秒（`AutoWait=0` 关闭）
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

# 基础安装（核心 + XML / SQLite 解析）
pip install -e .

# Web 测试（Playwright，需单独安装）
pip install playwright
playwright install chromium          # 安装浏览器

# 移动端测试（Appium，需单独安装）
pip install Appium-Python-Client

# 可选 extra（仅以下两个）
pip install -e ".[perception]"       # 本地视觉感知插件 rodski-perception
pip install -e ".[load]"             # 性能压测（Locust）

# 开发 / 全量依赖（含 Playwright、Appium、视觉、pytest）
pip install -r rodski/requirements.txt

# ---- rodski-agent（AI Agent 层）----

# 基础安装
pip install -e rodski-agent/

# 开发环境（含 pytest）
pip install -e "rodski-agent/[dev]"
```

### 离线安装包

仓库 `releases/rodski/` 下只保留历史离线包（v6.7.x、v8.0.2、v8.0.3、v8.1.0），**没有当前版本**的包。需要离线安装当前版本时，请在可联网环境用仓库根目录的 `pyproject.toml` 构建 wheel 后拷贝安装（`build` 读取工作区内容，应在没有未提交改动的干净检出中构建）：

```bash
pip install build
python -m build --wheel              # 在仓库根目录执行，产物在 dist/rodski-<版本>-py3-none-any.whl
pip install dist/rodski-*.whl
```

历史版本包附带 `SHA256SUMS`，可在对应目录执行 `shasum -a 256 -c SHA256SUMS` 校验。

### rodski 执行引擎

```bash
# 执行测试
rodski run case/ --output-format json

# 查看模块中的逻辑表
rodski data list rodski-demo/demosite/full/

# 查看逻辑表字段
rodski data schema rodski-demo/demosite/full/ RegisterAPI

# 查看指定数据行
rodski data show rodski-demo/demosite/full/ RegisterAPI L001

# 校验数据层；加 --orphans 额外检查未被引用的逻辑表与 DataID
rodski data validate rodski-demo/demosite/full/
rodski data validate rodski-demo/demosite/full/ --orphans

# 静态检查用例常见写法问题
rodski case lint rodski-demo/demosite/full/

# 初始化标准测试模块骨架（含 data.sqlite；--force 覆盖已有模板文件）
rodski init /path/to/MyTestModule

# 干跑模式（仅验证不执行）
rodski run case/ --dry-run
```

### SQLite 测试数据使用规则

- `data/data.sqlite` 是 `data/` 目录下唯一固定的 SQLite 测试数据文件
- 同一 `data/` 目录下的 DB 数据统一保存在 `data.sqlite`
- 逻辑表名必须与模型名强一致
- Case 中 `data` 只写 DataID（如 `L001` / `D001` / `V001`），不写 `表名.DataID`
- `type` / `send` / `DB` 默认按模型名查找同名逻辑表
- `verify` 默认按 `{model}_verify` 查找验证表
- 同一逻辑表所有行字段集合必须一致，缺字段显式填 `BLANK` / `NULL` / `NONE`
- `data.xml` / `data_verify.xml` 存在即报错；迁移用 `rodski data import <module>`（字段集合不一致时整体不写入），迁移后删除 XML

### rodski-agent (AI Agent 层)

```bash
# 从需求自动生成测试用例
rodski-agent design --requirement "测试登录功能" --output output/login/

# 执行测试用例（含智能重试）；--format 是顶层选项，写在子命令之前
rodski-agent --format json run --case output/login/

# 设计 + 执行一步到位
rodski-agent --format json pipeline --requirement "测试登录" --output output/login/

# 诊断失败用例
rodski-agent diagnose --result output/login/result/
```

## 架构概览

```text
Agent (探索/决策) → XML / SQLite 测试数据 → RodSki (执行) → JSON (结果) → Agent (分析)
```

RodSki 作为 Agent 工具链中的执行层，提供确定性、可重复的测试执行能力。Agent 通过 XML 协议描述测试意图，RodSki 负责跨平台执行并以 JSON 格式返回结构化结果，供 Agent 进一步分析和决策。

在数据层，RodSki 保持现有 DSL 语义不变：Case 的 `data` 仍只写 DataID；逻辑表名仍与模型名一致；`verify` 仍自动查找 `{model}_verify`。`data.sqlite` 只是 Data 层的承载方式，不改变关键字写法。

## 项目结构

```
RodSki/
├── rodski/              # Layer 1: 执行引擎
│   ├── core/            # 执行引擎（关键字、解析器、诊断）
│   ├── drivers/         # 平台驱动（Playwright/Appium/PyWinAuto）
│   ├── llm/             # LLM 能力层（可选）
│   ├── vision/          # 视觉定位（可选）
│   ├── rodski_cli/      # CLI 子命令（run/data/init/plan/case ...）
│   ├── config/          # 配置文件
│   └── docs/            # 框架文档
├── rodski-agent/        # Layer 2: AI Agent 层
│   ├── src/rodski_agent/
│   │   ├── design/      # Design Agent（需求→用例）
│   │   ├── execution/   # Execution Agent（执行→诊断→修复）
│   │   ├── pipeline/    # Pipeline 编排
│   │   ├── common/      # 共享工具（LLM、XML、配置）
│   │   └── cli.py       # CLI 入口
│   └── tests/           # 单元测试
├── rodski-demo/         # 官方示例
└── .pb/                 # 项目管理文档
```

## 文档

| 文档 | 说明 |
|------|------|
| [Agent 集成指南](rodski/docs/AGENT_INTEGRATION.md) | Agent 接入主入口 |
| [用例编写指南](rodski/docs/TEST_CASE_WRITING_GUIDE.md) | 用例 / 模型 / 数据编写规范 |
| [核心设计约束](rodski/docs/CORE_DESIGN_CONSTRAINTS.md) | 框架不可违反的设计约束 |
| [数据文件组织](rodski/docs/DATA_FILE_ORGANIZATION.md) | `data.sqlite` / `globalvalue.xml` 组织规则与 XML 数据迁移 |
| [关键字参考](rodski/docs/SKILL_REFERENCE.md) | 全部关键字语法说明 |
| [架构说明](rodski/docs/ARCHITECTURE.md) | 框架内部架构 |
| [视觉定位](rodski/docs/VISION_LOCATION.md) | OmniParser 视觉定位能力 |
| [移动端 App 模式设计](rodski/docs/MOBILE_APP_MODE_DESIGN.md) | v7.x Android / iOS App 自动化目标设计 |

## 自动等待（AutoWait）

RodSki 对**所有驱动（Web / Android / iOS / 桌面视觉）的所有查找测试对象的步骤**自动等待——
包括 `type` 批量里的每一个字段（输入、click、select、hover……）、`verify`、`get`、`clear`、`upload_file`，无需手写 `wait`。

- **本质**：try 查找并执行 → 捕获"未找到 / 不可操作" → 等待 1 秒 → 再执行；成功即继续，超过自动等待时间即失败
- **命中即走**：元素已就绪时不产生任何额外等待
- **按元素计时**：每个字段独立一份预算；同一元素的多个定位器共享这一份预算
- **不掩盖失败**：等不到就失败，错误信息含元素名、尝试过的定位器、`AutoWait=Nms` 和探测次数

在模块的 `data/globalvalue.xml` 中配置（单位毫秒）。**不设置默认最多等待 10000ms**（v11.10.0），每 1 秒探测一次；写 `0` 关闭自动等待；`rodski init` 生成的模板显式写 10000：

```xml
<group name="DefaultValue">
    <var name="AutoWait" value="10000"/>
</group>
```

## License

MIT License - 详见 [LICENSE](rodski/LICENSE)
