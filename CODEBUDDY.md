# CODEBUDDY.md

This file provides guidance to CodeBuddy Code when working with code in this repository.

## 项目概述

RodSki 是面向 AI Agent 的跨平台确定性测试执行引擎。工作流：Agent 编写 XML 活文档（Case/Model/Data）→ RodSki 确定性执行 → JSON 结果反馈 → Agent 分析修复。支持 Web（Playwright）、Android/iOS（Appium）、桌面（PyWinAuto）。当前版本 v8.2.0。

## 文档优先级（Source of Truth）

处理任何任务前，按此顺序阅读相关文档；冲突时前者优先：

1. `rodski/docs/CORE_DESIGN_CONSTRAINTS.md` — **不可违反**的核心约束（17 关键字清单、目录结构、定位器格式、Return 引用规则）
2. `rodski/docs/TEST_CASE_WRITING_GUIDE.md` — 用例/模型/数据编写规范
3. `rodski/docs/AGENT_INTEGRATION.md` — Agent 集成与错误契约（SKI 错误码 → 处理策略）
4. `.pb/README.md` + `.pb/conventions/*`（Git 工作流、版本号、项目边界）
5. `.pb/requirements/*`、`.pb/specs/*`、`.pb/iterations/*` — 当前需求/设计/迭代任务
6. `CLAUDE.md`、`agent.md`

代码、文档、笔记冲突时：以活动文档为准，并在同一改动内更新过时材料。

## 常用命令

```bash
# ---- 测试（注意：必须在 rodski/ 目录内运行 pytest）----
cd rodski
python3 -m pytest tests/unit -q                     # 全部单测
python3 -m pytest tests/unit -k "hook or compliance" -q   # 迭代-60 hooks 相关
python3 -m pytest tests/unit/test_keyword_engine.py -q    # 单文件
python3 -m pytest tests/unit/test_keyword_engine.py::TestSendKeyword::test_send_post_success -q  # 单用例
python3 -m pytest tests/integration -q              # 集成测试
python3 selftest.py                                 # 框架自检

# ---- 执行用例 ----
rodski run rodski-demo/DEMO/demo_full/case/         # 官方验收基线
rodski run <case/路径> --trace                       # 导出 trace.json 三层 span
rodski run @plan_id --load-ui                        # 性能压测（v8.0+）
rodski run <case/路径> --dry-run                     # 干跑不执行
rodski run <case/路径> --output-format json          # 结构化输出

# ---- 数据层 ----
rodski data import <module>
rodski data list <module> / rodski data show <module> <table> <data_id>
rodski data validate <module> --strict

# ---- 校验 XML ----
xmllint --noout --schema rodski/schemas/case.xsd <case.xml>

# ---- 脚手架 ----
rodski init <target> --with-sqlite
```

**关键注意**：pytest 必须 `cd rodski` 后运行（`python3 -m pytest tests/unit`），因为部分历史测试文件用顶层 import（`from vision...` / `from drivers...`），在仓库根目录运行时 collection 会报 `ModuleNotFoundError`。

## 架构（大图）

### 分层

```
CLI 层       rodski/rodski_cli/run.py（run/data/init/explain/plan/profile 等子命令）
    ▼
核心引擎     core/ski_executor.py（主执行器：编排 run→case→keyword 三层）
             core/keyword_engine.py（17 关键字实现 + 自动重试 + before/after_keyword hooks）
             core/test_plan_selection.py（@plan_id / selector 选择）
             core/compliance_check.py（v8.2.0 on_run_start 内置合规检查）
             core/hooks_config.py + hooks_runner.py（v8.2.0 外部命令 hook，hooks.json）
             core/diagnosis_engine.py（失败诊断，未接入主流程，经 on_case_failure hook 接线）
    ▼
解析层       core/case_parser.py / model_parser.py / data_table_parser.py
             core/global_value_parser.py / data_schema_validator.py / sqlite_data_source.py
    ▼
驱动层       drivers/base_driver.py（抽象基类）
             playwright_driver.py / appium_driver.py / android_driver.py / ios_driver.py / pywinauto_driver.py
    ▼
输出层       core/result_writer.py / json_formatter.py / execution_stats.py / logger.py
```

### 执行流程

`rodski run` → `run.py` 解析 Case/Model/Data → 构造 `KeywordEngine(driver)` → `SKIExecutor` 逐个执行 case（pre_process → test_case → post_process，失败仍执行后处理）→ keyword 通过 `execute()` 走重试逻辑 → 结果写入 report（JSON/XML）+ 失败截图。

### 用例模型（三文件协议）

- `case/*.xml`：`<test_step action="type" model="Login" data="L001"/>`，action 只能是 17 关键字
- `model/model.xml`：元素定位，唯一格式 `<location type="id">value</location>`
- `data/data.sqlite`：唯一测试数据文件（v6.0.0+；`data.xml`/`data_verify.xml` 已废弃，存在即报错）

## 核心约束（不可违反）

- **17 个关键字**（`SUPPORTED` 列表）：`close type verify wait navigate launch assert evaluate screenshot upload_file clear get_text get send set DB run`；`check` 为 `verify` 兼容别名。`click/double_click/right_click/hover/select/key_press/drag/scroll` **不是独立关键字**，只能写在数据表 field 值中由 `type` 批量识别。新增关键字必须同时更新 `rodski/schemas/case.xsd` 和 CORE_DESIGN_CONSTRAINTS.md
- **目录结构**强制：`product/{项目}/{模块}/{case,model,fun,data,plan,result}`，`product/` 必须最顶层，6 个固定目录名不可改，`model.xml` 唯一
- **Return 引用**：`${Return[-1]}` 只能写在数据表 field 值中；接口/DB 模型 `_verify` 表禁止使用；UI 模型 `_verify` 允许 `${Return[-N]}`
- **测试计划**：`@plan_id` 与 `--tag/--group/--priority` 固定互斥；计划只存 `plan/*.xml`，不写入 `data.sqlite`
- **测试分层**：单元测试在 `rodski/tests/`；验收测试必须在 `rodski-demo/` 落地为可执行用例——只有单测通过而无 demo 验收用例，**不能判定验收完成**
- 每次实现后对照 CORE_DESIGN_CONSTRAINTS.md 附录 A 合规清单

## 版本号规则

格式 `MAJOR.MINOR.PATCH`：PATCH 修 Bug、MINOR 加功能（AI Agent 可自主递增）、MAJOR 架构里程碑（**必须 Owner 手动决定**）。版本号必须在 5 处同步：

`pyproject.toml`、`rodski/pyproject.toml`、`rodski/__init__.py`、`rodski-skills/VERSION`、`CLAUDE.md`

（当前 v8.2.0，iteration-60 Hooks MVP 进行中，工作区有未提交改动）

## .pb 项目管理体系

- `.pb/requirements/` 需求、`.pb/iterations/iteration-XX/tasks.md` 迭代任务、`.pb/specs/` 设计定稿、`.pb/conventions/` 规范、`.pb/archive/` 仅追踪不作参考
- 新迭代：从 main 建 `feature/xxx` 分支 → 按 iteration tasks.md 实现 → 每完成一个 WI 跑对应单测 → demo 验收 → 提交
- 提交规范：Conventional Commits（`feat/fix/refactor/docs/test/chore/perf` + scope），禁止在 main 直接开发

## Hooks 机制（v8.2.0，iteration-60）

- 设计定稿：`.pb/specs/rodski-hooks-design.md`；接口契约见 §11；参考文档 `rodski/docs/HOOKS_REFERENCE.md`
- **进程内回调**：`SKIExecutor(hooks={"before_keyword": [fn], "after_keyword": [fn], "on_case_failure": [fn]})`，`before_keyword` 返回 `HookDecision(allow=False, reason=...)` 拒绝，抛 `HookDeniedError(SKI701)`
- **外部命令 hook**：项目内 `hooks.json` 覆盖全局 `~/.rodski/hooks.json`；`command` 必须为数组（防注入）；stdin 传 JSON；exit code 0=放行 / 2=拒绝 / 其他=警告；超时抛 `HookTimeoutError(SKI702)`
- `on_run_start` 内置 4 类合规检查（目录结构/plan_id 互斥/data.sqlite schema/Return 引用），失败默认阻断，`--force-compliance` 显式跳过（目录结构缺失除外），跳过留痕
- `on_case_failure` 同时接入 `DiagnosisEngine`（`SKIExecutor(diagnosis_engine=...)`），输出 `recovery_action`
- 不配置 hooks 时行为与以前完全一致（`hooks=None`、无 `hooks.json`、`diagnosis_engine=None` 三个回归场景）

## 独立子项目

`rodski-web/`（Next.js 官网）、`rodski-agent/`（LangGraph Agent 层）、`rodski-perception/`、`rodski-vscode/` 是独立 Git 仓库，物理上位于主仓库下但被根 `.gitignore` 忽略。**在主仓库会话中不得修改它们的版本文件和 git 操作**；如需操作需单独开启对应目录会话。`rodski-agent` 依赖已安装的 `rodski` 包，方向不可倒置。

## 已知基线问题（非本次改动引入）

- `rodski/tests/unit` 有 10 个失败在 HEAD（v8.1.1）即存在，与迭代-60 工作无关：
  - `test_evaluate_console_and_slow_step.py::TestEvaluateConsoleCapture`（7 个）：mock driver 不是 PlaywrightDriver，`evaluate` 关键字要求 Web 驱动
  - `test_keyword_engine.py::TestSendKeyword`（3 个）：测试发真实 HTTP 请求，因 DNS 解析失败（mock 未拦截 requests）
- 处理这两类问题前先确认是否属于你任务范围，不要顺手修改无关测试

## 工作规范

- 改动前先读最相关的最小文档集；改动尽量小而局部；不改动任务范围外的东西
- 改动影响公共契约（关键字、schema、CLI、XML 结构）时，须在同一改动内更新对应文档与 `.pb/iterations/` 记录
- 产物（`result/`、demo 输出、构建产物）不作为源码处理，不手动编辑
- 遇到下列情况先停下来问用户：改核心契约但不同步文档、删除/重写任务范围外的工作、无法从活动文档调和的矛盾、超出请求范围的大重构
