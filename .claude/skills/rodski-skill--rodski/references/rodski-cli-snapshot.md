# RodSki 本机 CLI 快照

这是最近一次本机快照，不是事实来源。使用前必须重新运行当前 CLI 的 `--version`、`--help` 和相关子命令 `--help`；当前 CLI 顶层 `--help` 列出 `capabilities` 子命令时即可调用它，关键字/定位器/特殊值等清单直接以它的实时输出为准。当快照与当前 CLI、XSD、guide 冲突时，以当前验证结果为准，并在结论中说明冲突。

快照采集入口：

```bash
/opt/homebrew/bin/rodski
```

快照版本（采集时；当前以 `--version` 为准，本机最近一次确认为 7.1.5）：

```text
RodSki 7.1.5  ← 历史采集值，使用前用 `/opt/homebrew/bin/rodski --version` 重新确认
```

## 入口

TestCase 用例任务优先使用：

```bash
/opt/homebrew/bin/rodski --version
```

默认使用主 skill 声明的全局入口：

```bash
RODSKI="/opt/homebrew/bin/rodski"
"$RODSKI" --version
```

仅当 `/opt/homebrew/bin/rodski` 不可用，或直接调用 CLI 出现 `ModuleNotFoundError: No module named 'core'` 这类安装形态/PYTHONPATH 问题时，才临时使用历史 wrapper：

```bash
RODSKI="scripts/rodski.sh"
"$RODSKI" --version
```

wrapper 会从 RodSki 入口脚本的 Python shebang 动态探测 `rodski.__path__[0]`，再按需注入 `PYTHONPATH`。不要写死 Python 版本或 site-packages 路径。

## 顶层命令

```text
rodski [--version] {run,model,config,log,report,docs,data,init,plan,capabilities}
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
```

`case` 参数可以是 XML 文件、`case/` 目录、测试模块目录或计划引用 `@plan_id`。`--output-format` 支持 `text`、`json`。`--browser` 支持 `chromium`、`firefox`、`webkit`。`--debug` 只对 `scenario_debug` / `step_debug` 类型 plan 生效。

## data

```bash
"$RODSKI" data list <module>
"$RODSKI" data schema <module> <table>
"$RODSKI" data show <module> <table> <DataID>
"$RODSKI" data query <module> <table>
"$RODSKI" data query <module> <table> --limit 20
"$RODSKI" data validate <module>
"$RODSKI" data import <module>
"$RODSKI" data import <module> --overwrite
```

`module` 是测试模块目录，通常包含 `case/`、`model/`、`data/`。不要给 `validate` 加未确认的 `--strict`。

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
"$RODSKI" plan add-case <plan_id> <case_id>
"$RODSKI" plan add-scenario <plan_id> <case_id> <scenario_id>
"$RODSKI" plan enable-case <plan_id> <case_id>
"$RODSKI" plan disable-case <plan_id> <case_id>
"$RODSKI" plan enable-scenario <plan_id> <case_id> <scenario_id>
"$RODSKI" plan disable-scenario <plan_id> <case_id> <scenario_id>
"$RODSKI" plan debug-scenario ...
"$RODSKI" plan debug-step ...
```

`plan` 子命令较多，实际使用前先跑对应 `"$RODSKI" plan <subcommand> --help`。

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
/opt/homebrew/bin/rodski capabilities
# 只看关键字 / 定位器 / 特殊值：
/opt/homebrew/bin/rodski capabilities | python3 -c "import sys,json; d=json.load(sys.stdin); print('version', d['version']); print('keywords', d['supported_keywords']); print('locators', d['locator_types']); print('special', d['special_values'])"
```

`rodski_case_guard.py` 已经直接读取 `capabilities` 的 `supported_keywords` 校验 action、
读取 `locator_types` 校验 `<location type>`；散文档里出现的关键字/定位器名单只是示例，不是完整白名单。

## 当前注意点

- `capabilities` 可能列出当前安装包 `case.xsd` 的 `ActionType` 枚举里没有的 action（或反之）。
  guard 会把这类差异作为 WARN 报出；遇到不一致时不要只信单一来源。
- 遇到这类元数据不一致时，用目标用例的 `rodski run ... --dry-run --output-format json` 做最终可执行性确认。

当前 XSD 路径可动态确认（用当前 RodSki 安装环境的 python，不要写死路径）：

```bash
RODSKI_PY="$(/opt/homebrew/bin/rodski --help >/dev/null 2>&1; echo $HOME/.local/share/rodski/venv/bin/python)"
"$RODSKI_PY" -c "import pathlib, rodski; print(pathlib.Path(rodski.__path__[0]) / 'schemas' / 'case.xsd')"
```
