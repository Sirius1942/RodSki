# RodSki 本机 CLI 快照

这是最近一次本机快照，不是事实来源。使用前必须重新运行当前 CLI 的 `--version`、`--help` 和相关子命令 `--help`；当前 CLI 顶层 `--help` 列出 `capabilities` 子命令时即可调用它，关键字/定位器/特殊值等清单直接以它的实时输出为准。当快照与当前 CLI、XSD、guide 冲突时，以当前验证结果为准，并在结论中说明冲突。

快照采集入口：`PATH` 上的 `rodski`（`command -v rodski`）。

快照版本（采集时；当前以 `--version` 为准，本机最近一次确认为 11.4.1）：

```text
RodSki 11.4.1  ← 历史采集值，使用前用 `rodski --version` 重新确认
```

## 入口

默认使用主 skill 声明的入口选择顺序：

```bash
RODSKI="${RODSKI_BIN:-$(command -v rodski)}"
"$RODSKI" --version
```

仅当 `PATH` 上的 `rodski` 不可用，或直接调用 CLI 出现 `ModuleNotFoundError: No module named 'core'` 这类安装形态/PYTHONPATH 问题时，才临时使用历史 wrapper：

```bash
RODSKI="scripts/rodski.sh"
"$RODSKI" --version
```

wrapper 会从 RodSki 入口脚本的 Python shebang 动态探测 `rodski.__path__[0]`，再按需注入 `PYTHONPATH`。不要写死 Python 版本或 site-packages 路径。

## 顶层命令

```text
rodski [--version] {run,roam,model,config,log,report,docs,data,init,plan,capabilities,explore,queue,business,case}
```

未重新确认前不要生成：

- `rodski explain ...`
- `rodski-agent ...`
- `rodski init --with-verify --with-sqlite`
- `rodski data validate --strict`

## run

```bash
"$RODSKI" run <case-file-or-case-dir-or-module-dir-or-@plan_id>
"$RODSKI" run case/ --dry-run
"$RODSKI" run case/ --output-format json
"$RODSKI" run case/ --headless
"$RODSKI" run case/ --report html
"$RODSKI" run case/ --output result/
"$RODSKI" run case/ --model model/model.xml
"$RODSKI" run case/ --browser chromium
"$RODSKI" run case/ --tag smoke
"$RODSKI" run case/ --tags smoke,regression
"$RODSKI" run case/ --group smoke
"$RODSKI" run case/ --priority P0,P1
"$RODSKI" run case/ --exclude-tag slow
"$RODSKI" run case/ --exclude-tags slow,manual
"$RODSKI" run case/ --insert-step action,model,data
"$RODSKI" run @plan_id --debug
"$RODSKI" run case/ --record
"$RODSKI" run case/ --record-mode auto
"$RODSKI" run case/ --record-mode screen
"$RODSKI" run case/ --record-mode playwright
"$RODSKI" run case/ --record-mode off
"$RODSKI" run case/ --record-scope target
"$RODSKI" run case/ --record-scope full_screen
"$RODSKI" run case/ --record-scope all_screens
"$RODSKI" run case/ --record-monitor 1
"$RODSKI" run case/ --record-resolution 1920x1080
"$RODSKI" run case/order/refund/refund_apply.xml --case-id tc001,tc002
```

`case` 参数可以是 XML 文件、`case/` 目录（v11.5.0 起支持任意多级嵌套子目录）、测试模块目录或计划引用 `@plan_id`。`--case-id`（v11.5.0 新增）按用例 ID 过滤，逗号分隔多个，必须与单个用例文件路径一起使用（不能配合目录或 `@plan_id`），与 `@plan_id` 固定互斥。`--output-format` 支持 `text`、`json`。`--browser` 支持 `chromium`、`firefox`、`webkit`。`--debug` 只对 `scenario_debug` / `step_debug` 类型 plan 生效。

## roam（v11.5.0 起支持嵌套定位）

```bash
"$RODSKI" roam <module_dir> --case-file order/refund/refund_apply.xml --case-id tc001
"$RODSKI" roam <module_dir> --case tc001   # 旧模式：仅当模块只有一个用例文件或 ID 全模块唯一时可用
```

`--case-file` + `--case-id` 是 v11.5.0 起推荐的定位方式（`--case-file` 是相对 `case/` 的 POSIX 路径）；旧的单独 `--case` 参数保留作向后兼容。两者都缺失时以 argparse 用法错误退出（exit code 2）。其余参数（`--model`/`--browser`/`--headless`/`--trace`/`--platform` 等）与 `run` 一致，实际使用前用 `--help` 再确认。

## case（v11.5.0 新增）

```bash
"$RODSKI" case lint <module>
```

检查 `case/` 目录结构与内容：ERROR（同文件内 ID 重复、子目录使用保留名）会让命令以非 0 退出；WARNING（目录/文件名不是 snake_case、单文件用例数超过 30）和 INFO（合法的跨文件同 ID）只提示不影响退出码。

## data

```bash
"$RODSKI" data list <module>
"$RODSKI" data schema <module> <table>
"$RODSKI" data show <module> <table> <DataID>
"$RODSKI" data query <module> <table>
"$RODSKI" data query <module> <table> --limit 20
"$RODSKI" data validate <module>
"$RODSKI" data validate <module> --orphans
"$RODSKI" data import <module>
"$RODSKI" data import <module> --overwrite
"$RODSKI" data dump <module>
"$RODSKI" data dump <module> --format json
"$RODSKI" data add-field <module> <table> <field> --default BLANK
```

`module` 是测试模块目录，通常包含 `case/`、`model/`、`data/`。不要给 `validate` 加未确认的 `--strict`；孤儿数据检查用 `--orphans`（v11.5.0 新增）。`dump` 只读、输出到 stdout、字段/行稳定排序，便于 diff。`add-field`（v11.5.0 新增）为逻辑表新增字段并回填所有已存在行的默认值。

## init

```bash
"$RODSKI" init <target>
"$RODSKI" init <target> --no-sqlite
"$RODSKI" init <target> --force
```

默认创建 `data.sqlite`。`--no-sqlite` 不推荐，除非用户明确要求兼容非 SQLite 数据形态。

## plan

```bash
"$RODSKI" plan init
"$RODSKI" plan list
"$RODSKI" plan show <plan_id>
"$RODSKI" plan validate <plan_id>
"$RODSKI" plan preview <plan_id>
"$RODSKI" plan create <plan_id> --kind suite --title "标题"
"$RODSKI" plan create <plan_id> --from-tag smoke
"$RODSKI" plan create <plan_id> --from-group smoke
"$RODSKI" plan add-case <plan_id> <case_file> <case_id>
"$RODSKI" plan add-dir <plan_id> <path>
"$RODSKI" plan migrate <module>
"$RODSKI" plan add-scenario <plan_id> <case_id> <scenario_id>
"$RODSKI" plan enable-case <plan_id> <case_id>
"$RODSKI" plan disable-case <plan_id> <case_id>
"$RODSKI" plan enable-scenario <plan_id> <case_id> <scenario_id>
"$RODSKI" plan disable-scenario <plan_id> <case_id> <scenario_id>
"$RODSKI" plan debug-scenario ...
"$RODSKI" plan debug-step ...
```

`add-case`（v11.5.0 起签名变更：新增 `case_file` 位置参数，相对 `case/` 的路径）写入 `<case file="..." id="...">`；`add-dir`（v11.5.0 新增）写入 `<case_dir path="...">` 批量选择一个 `case/` 子目录，`path` 为空字符串表示整个 `case/`；`migrate`（v11.5.0 新增）为旧 plan 中缺少 `file` 属性的 `<case>` 按模块自动补齐。`plan` 子命令较多，实际使用前先跑对应 `"$RODSKI" plan <subcommand> --help`。

## report/log/config/docs/model

```bash
"$RODSKI" report generate <result_dir>
"$RODSKI" report generate <result_dir> --single-file --output report.html
"$RODSKI" report trend <result_dir> --last 10
"$RODSKI" log list
"$RODSKI" log view
"$RODSKI" log clear
"$RODSKI" config list
"$RODSKI" config get <key>
"$RODSKI" config set <key> <value>
"$RODSKI" config reset
"$RODSKI" docs dev
"$RODSKI" docs build
"$RODSKI" docs preview
"$RODSKI" model create <name> <type>
"$RODSKI" model list
"$RODSKI" model validate <name>
"$RODSKI" model delete <name>
```

这些子命令示例应在使用前用 `"$RODSKI" <command> --help` 再确认参数，尤其是报告、配置、模型和文档站点相关命令。

## capabilities（不再冻结快照，按需实时获取）

受支持关键字、定位器类型、驱动、case_phases、schema_types、special_values、required/optional_dirs、
component_types、execute_values 等是会随版本漂移的清单。**不要在本文冻结这份 JSON**——以当前 CLI 实时输出为权威来源：

```bash
rodski capabilities
# 只看关键字 / 定位器 / 特殊值：
rodski capabilities | python3 -c "import sys,json; d=json.load(sys.stdin); print('version', d['version']); print('keywords', d['supported_keywords']); print('locators', d['locator_types']); print('special', d['special_values'])"
```

`rodski_case_guard.py` 已经直接读取 `capabilities` 的 `supported_keywords` 校验 action、
读取 `locator_types` 校验 `<location type>`；散文档里出现的关键字/定位器名单只是示例，不是完整白名单。

## 当前注意点

- `capabilities` 可能列出当前安装包 `case.xsd` 的 `ActionType` 枚举里没有的 action（或反之）。
  guard 会把这类差异作为 WARN 报出；遇到不一致时不要只信单一来源。
- 遇到这类元数据不一致时，用目标用例的 `rodski run ... --dry-run --output-format json` 做最终可执行性确认。

当前 XSD 路径可动态确认（用当前 RodSki 安装环境的 python，不要写死路径）：

```bash
RODSKI_PY="$(head -1 "$(command -v rodski)" | sed 's/^#!//')"   # rodski 入口脚本的 shebang 解释器
"$RODSKI_PY" -c "import pathlib, rodski; print(pathlib.Path(rodski.__path__[0]) / 'schemas' / 'case.xsd')"
```
