# RodSki 项目开发 Agent 指南

本文件是 AI Agent（Codex、Claude Code 等）在 RodSki 主仓库中开发、修复、测试和发布时必须遵守的工作契约。

## 1. 项目定位与仓库边界

RodSki 是面向 AI Agent 的跨平台、确定性测试执行引擎。Agent 负责理解需求、生成或修改测试资产并分析结果；RodSki 负责稳定执行并输出结构化结果。

主要目录：

- `rodski/`：核心执行引擎、CLI、解析器、关键字、驱动、Schema、单元测试。
- `rodski-demo/`：官方示例与**唯一验收基线**。所有功能变更最终都必须在这里落地为可执行验收用例，或由现有验收用例覆盖。
- `rodski-agent/`：AI Agent 层，独立代码库；依赖 RodSki，不反向修改核心契约。
- `rodski-browser-plugin/`：浏览器插件独立子项目。
- `rodski-vscode/`：VS Code 数据编辑器子项目。
- `web/`：测试用例管理系统。
- `.pb/`：需求、规格、迭代记录、项目约定和归档资料。
- `rodski/docs/`：框架设计、用例、数据、API 和 Agent 集成文档。
- `.claude/`：Claude 项目配置和历史协作资料，仅作为补充参考。

不要把 `result/`、日志、截图、构建产物或临时文件当作源码；不要手工编辑自动生成的 Demo 结果。

## 2. 权威资料与阅读顺序

开始开发前，先阅读与任务相关的最小资料集。发生冲突时按以下优先级处理：

1. `rodski/docs/CORE_DESIGN_CONSTRAINTS.md`
2. `rodski/docs/TEST_CASE_WRITING_GUIDE.md`
3. `rodski/docs/AGENT_INTEGRATION.md`
4. `rodski/docs/ARCHITECTURE.md`、`SKILL_REFERENCE.md`、`DATA_FILE_ORGANIZATION.md` 等专项文档
5. `.pb/README.md`、`.pb/conventions/`、当前有效的 `.pb/requirements/`、`.pb/specs/`、`.pb/iterations/`
6. `CLAUDE.md`
7. 本文件
8. `.claude/memory/`、`.pb/archive/` 等历史资料

代码、文档和历史记录不一致时，以当前有效设计约束和专项文档为准，并在同一变更中修正文档漂移；不能只依据历史资料实现新行为。

## 3. 不可违反的核心约束

### 3.1 关键字契约

当前受支持的核心关键字必须保持一致：

```text
close, type, verify, wait, navigate, launch, assert, evaluate,
screenshot, upload_file, clear, get_text, get, send, set, DB, run
```

兼容别名：`check` 等同于 `verify`。

以下不是独立关键字，只能作为数据表 field 值，由 `type` 的批量模式识别：

```text
click, double_click, right_click, hover, select, key_press, drag, scroll
```

不要自行增加 `http_get`、`http_post`、`assert_json`、`assert_status` 等独立关键字。确需新增关键字时，必须同步修改实现、`rodski/schemas/case.xsd`、核心设计约束、关键字参考文档以及 `rodski-demo` 验收用例。

### 3.2 测试资产和数据契约

标准模块结构为：

```text
product/
└── <项目名>/
    └── <模块名>/
        ├── case/
        ├── model/          # model.xml
        ├── fun/
        ├── data/           # data.sqlite + globalvalue.xml
        ├── plan/
        └── result/         # 自动生成
```

必须遵守：

- `data/data.sqlite` 是测试数据主文件；不要重新引入 `data.xml` 或 `data_verify.xml` 作为运行时数据入口。
- `globalvalue.xml` 独立维护，不写入 SQLite。
- 同一逻辑表的所有数据行字段集合必须一致；缺失值显式写 `BLANK`、`NULL` 或 `NONE`。
- 模型定位器使用 `<location type="...">值</location>`，不要使用已废弃的 `value` 属性格式。
- Case 的 `data` 属性只写 DataID，不写 `表名.DataID`。
- `${Return[-N]}` 只能出现在数据表 field 值中，不能出现在 Case XML 的 `data` 属性。
- 接口/DB 模型的 `_verify` 表禁止使用 `${Return[-1]}`；UI 模型按现行文档处理。
- 测试计划放在 `plan/*.xml`，不能写入 `data.sqlite`；`@plan_id` 与 `--tag`、`--group`、`--priority` 等 selector 不能混用。

## 4. 开发流程

### 4.1 开始任务

1. 查看工作区：
   ```bash
   git status --short --branch
   ```
2. 判断任务影响范围，读取对应源码、测试和权威文档。
3. 如果工作区已有修改，视为用户内容；不要重置、覆盖或清理无关变更。
4. 优先使用 `rg`/`rg --files`（不可用时使用 `grep`/`find`）定位代码；遵循现有模块边界。

### 4.2 修改代码

- 先理解调用链、解析流程和数据契约，再进行最小修改。
- 保持现有命名、错误码、日志和异常风格。
- 不为了局部问题进行无关重构。
- 修改公共行为时，同时更新对应文档、Schema、Demo 用例和必要的 `.pb/iterations/` 记录。
- 不直接修改生成结果来“修复”测试；应修复源码、测试资产或测试环境。
- 不把 `rodski-agent`、插件或网站的独立仓库 Git 操作混入主仓库任务。

### 4.3 测试分层

- 单元测试：`rodski/tests/`。
- 集成/回归测试：根据受影响模块选择已有测试。
- 验收测试：必须位于 `rodski-demo/` 并可执行。
- **仅单元测试通过不能视为验收完成。**

## 5. Demo 验收是硬性发布门禁

`rodski-demo/` 是项目官方示例和验收基线。任何影响执行引擎、CLI、关键字、解析器、Schema、数据层、驱动、报告、计划或公共 API 的变更，在合并或发布前都必须执行相关 Demo 验收并确认通过。

### 5.1 默认稳定回归

默认浏览器/API/SQLite 回归位于 `rodski-demo/DEMO/demo_full/`。从仓库根目录执行：

```bash
cd rodski-demo/DEMO/demo_full
python3 init_db.py
python3 demosite/app.py                 # 单独终端启动服务，默认 http://localhost:8000

# 回到仓库根目录后执行默认稳定回归
cd <仓库根目录>
rodski run rodski-demo/DEMO/demo_full/case/demo_case.xml
```

也可以使用 Demo 自带入口（会初始化数据库）：

```bash
cd rodski-demo/DEMO/demo_full
./run_demo.sh
# 或
python3 run_demo.py
```

默认稳定回归覆盖浏览器/API/SQLite 关键路径。修改其他能力时，不能只运行默认集合，应按影响范围执行 `rodski-demo/DEMO/` 下对应 Demo 的 README、`run_demo.py`、脚本或专用测试入口。

### 5.2 变更到专项能力时

至少补跑对应专项验收：

- 数据、模型、Case、计划、关键字：`rodski-demo/DEMO/demo_full/`。
- Hook：`rodski-demo/DEMO/demo_hooks/`。
- 暂停、接管、运行时控制：`demo_pause_takeover/`、`demo_runtime_control/`。
- 视觉感知：`demo_perception/`；需要额外模型或服务时，明确记录环境前置条件。
- 漫游执行：`demo_roaming_test/`。
- 性能压测：`demo_load/`，遵守 `LOAD_TESTING_GUIDE.md`。
- Android/iOS、异构设备队列：`mobile_app/`，遵守其 README 和设备前置条件。
- 浏览器插件、网站、桌面应用：执行对应 Demo，不得用普通 Web 回归替代。

专项 Demo 如果因真实设备、浏览器、外部服务或 GUI 环境不可用而无法执行，不能默认为通过；应在最终报告中明确列出未执行项、原因和风险。

### 5.3 发布前门禁

发布流程至少包括：

1. 运行受影响的单元/集成测试。
2. 运行默认 `demo_full` 稳定回归。
3. 运行本次变更涉及的专项 Demo。
4. 检查结果状态、退出码和 `result/` 中的错误，而不是只看命令是否启动。
5. 通过后再执行构建和发布检查：
   ```bash
   scripts/release_check.sh <version> --build
   ```
6. 只有 Demo 验收和发布检查都通过，才允许发布；`scripts/release_check.sh` 的构建检查不能替代 Demo 验收。

## 6. 常用验证命令

使用项目已经准备好的 Python 环境，不要在没有必要时重新创建环境或升级依赖。

```bash
# 查看 CLI
rodski --help
rodski --version

# 核心自检
python3 rodski/selftest.py

# 单元测试
python3 -m pytest rodski/tests/unit -q

# 运行 Demo 验收
rodski run rodski-demo/DEMO/demo_full/case/demo_case.xml
rodski run rodski-demo/DEMO/demo_full/case/

# 数据校验
rodski data validate <模块路径> --strict

# XML Schema 校验
xmllint --noout --schema rodski/schemas/case.xsd <case.xml>

# 仅解析/校验，不执行
rodski run <case-or-module> --dry-run

# 诊断执行过程
rodski run <case-or-module> --trace
```

如果 `rodski` 命令不在 PATH，使用当前解释器的等价调用，或先激活仓库已有环境；不要通过修改源码绕过环境问题。

## 7. 版本与发布规则

版本遵循 `.pb/conventions/VERSIONING.md`：

- PATCH：修复 Bug。
- MINOR：新增功能。
- MAJOR：架构级里程碑，只能由 Owner 决定。

版本更新必须同步检查项目约定要求的版本文件，包括：

- `pyproject.toml`
- `rodski/pyproject.toml`
- `rodski/__init__.py`
- `rodski-skills/VERSION`
- `CLAUDE.md`
- 按约定需要同步的独立子项目版本文件

不擅自升级 MAJOR，不跳过 Demo 验收，不在未确认版本策略时修改版本号。

## 8. 完成任务前检查清单

- [ ] 已阅读与任务相关的权威文档。
- [ ] 未破坏关键字清单、数据文件、模型定位器、计划和 Return 引用契约。
- [ ] 代码、测试、Schema、文档和 Demo 资产已同步（若适用）。
- [ ] 相关单元/集成测试通过。
- [ ] `rodski-demo/DEMO/demo_full` 默认稳定回归通过。
- [ ] 变更涉及的专项 Demo 已通过，或已明确记录无法执行的前置条件和风险。
- [ ] 发布前已运行构建/发布检查，且没有用它替代 Demo 验收。
- [ ] `git status` 中没有误生成或无关文件。

## 9. 最终汇报格式

任务结束时只报告事实，至少包含：

1. 修改的文件和核心变更。
2. 执行过的验证命令及结果。
3. 未执行的验证、失败原因和遗留风险。
4. 如果是发布相关任务，明确写出 Demo 验收是否通过。

不要把“代码已修改”写成“功能已验收”；没有通过 `rodski-demo` 的变更不能宣称发布就绪。
