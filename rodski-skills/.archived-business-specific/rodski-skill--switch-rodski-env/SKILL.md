---
name: switch-rodski-env
description: RodSki 用例换环境助手。Use when the user asks to convert, migrate, audit, compare, sync missing, or verify RodSki test cases between environments such as beta/ci/stage/prod, especially requests mentioning “换环境”, “转换环境”, “补齐用例”, “缺少用例”, environment URL, database address, globalvalue.xml, model hardcoded URL, data.sqlite, beta_old/ci_new, or finding environment values that should change. This skill first supplements missing case/data/model/fun assets from old to new when applicable, then changes only URL and database-address values, keeps case writing and business data unchanged, and treats old/source cases as read-only.
---

# RodSki 换环境

## 硬规则

- 旧用例目录永远只读。不要对旧环境、源目录、历史目录执行写入命令。
- 新旧数据必须分开。实际转换只写目标/新用例目录，命令里用 `--target-root` 表达。
- 当用户只说“换环境”且没有指定目录时，默认旧目录是 `$HOME/beta_old/000 case_old`，新目录是 `$HOME/ci_new/000 case_new`。
- 默认先扫描旧/新目录差异，把新目录缺少的用例资产从旧目录补齐；只复制 `case/`、`data/`、`model/`、`fun/`，不复制 `plan/`、`result/`、报告、前端源码、依赖目录或其他杂项。
- 补齐缺失资产时不覆盖新目录已有文件。目标已有文件即使内容不同，也留给后续 URL/DB 切换流程处理。
- 换环境只允许改 URL 和数据库地址。数据库地址主要是 DB `host`，也包括明确属于连接地址的 URL。
- 用例写法、case 编排、定位器策略、业务数据、判定表、plan、result、报告目录都不因换环境改动。
- 如果 URL/DB 地址硬编码在 `model.xml`、`data.sqlite` 或 `fun/*.py`，也属于环境值；只改这个值本身，不改结构和逻辑。
- 先 dry-run 或 audit，再写入。没有用户明确要求，不使用 `--write`。
- 报告和中间产物默认是临时文件。优先把新的 dry-run、audit、compare、verify 输出写到 `/tmp` 或任务临时目录；只有用户明确要求留档，或需要让用户审阅文件时，才写进项目报告目录。
- 换环境最终校验无误后，清理本次生成的中间报告文件（例如 `convert_*`、`env_map_*`、`sync_missing_*`、`apply_*`、`verify_*`、`full_*` 的 `.json`/`.md`）。只删除报告目录或临时目录中的报告产物，不删除 `case/`、`data/`、`model/`、`fun/`、`plan/`、`result/`、备份目录或用户明确要求保留的文件。若校验失败，保留相关报告供排查。

## 工作流

标准换环境优先用一站式 `convert`，它在单进程里串完 extract-map → sync-missing → apply，默认 dry-run，只回紧凑摘要，省去多轮命令。只有需要单独审计、对比或排查时才拆步走下面的细分命令。

### 快速路径（推荐）

1. 先 dry-run，看摘要里的 `map`、`sync`、`apply.change_count` 和 `map_conflicts`：

```bash
python3 scripts/switch_rodski_env.py \
  convert \
  --old-root "$HOME/beta_old/000 case_old" \
  --new-root "$HOME/ci_new/000 case_new" \
  --map-out "/path/to/env_map.json" \
  --out "/path/to/convert_dry_run.json"
```

2. 摘要确认无误后，用户授权才加 `--write --backup-dir`：

```bash
python3 scripts/switch_rodski_env.py \
  convert --write \
  --old-root "$HOME/beta_old/000 case_old" \
  --new-root "$HOME/ci_new/000 case_new" \
  --backup-dir "/path/to/backups" \
  --out "/path/to/convert_result.json"
```

`convert` 说明：

- 旧目录只读，只写 `--new-root`（目标）。`--old-root == --new-root` 会直接报错。
- 映射默认从旧/新结构化资产（globalvalue/model/sqlite）推导，不从 text 推导；要复用固定映射加 `--map env_map.json`，跳过推导。
- 默认输出紧凑摘要：去重后的 old→new 变化、按文件/来源计数、缺失资产、映射冲突。要逐条明细加 `--full`，要文本 diff 加 `--diff`。
- `sync` 与 `apply` 的写入行为同细分命令；`--write` 同时落补齐和 URL/DB 切换。

### 细分命令（审计 / 排查时）

1. 明确任务是审计、对比、补齐缺失资产、提取映射，还是转换目标目录。
2. 如果会修改 RodSki 用例资产，先按 RodSki 用例规则确认当前 CLI 版本。
3. 如果用户说“换环境”且存在旧/新目录，先运行 `extract-map` 从当前旧/新样本只读生成映射。
4. 然后运行 `sync-missing` dry-run，检查新目录缺失的 `case/data/model/fun` 文件；确认后用 `sync-missing --write` 补齐。
5. 运行 `apply` dry-run，把映射应用到整个新目录，包含刚复制过来的缺失资产；检查 `change_count`、明细和 diff。
6. 用户确认后才运行 `apply --write --backup-dir ...` 写目标目录。
7. 写入后重新 `audit` 或 `compare` 验证，并把报告输出到用户指定目录。
8. 确认无误后做报告清理：如果报告只是本次流程生成的中间产物，删除项目报告目录中的临时 JSON/MD；最终答复里直接列出关键校验命令和摘要，不要求用户再看一堆报告文件。

## 推荐脚本

使用 `scripts/switch_rodski_env.py`。

```bash
# 审计一个目录中所有 URL/DB 地址，默认扫 globalvalue/model/data.sqlite/text
python3 scripts/switch_rodski_env.py \
  audit --root "/path/to/cases" --out "/path/to/audit.json"

# 只读对比旧/新两套环境。旧目录不会写入
python3 scripts/switch_rodski_env.py \
  compare --old-root "/path/to/old cases" --new-root "/path/to/new cases" \
  --out "/path/to/env_compare.json" --markdown "/path/to/env_compare.md"

# 补齐新目录缺少的用例资产。默认 dry-run；只看 case/data/model/fun，不覆盖已有文件
python3 scripts/switch_rodski_env.py \
  sync-missing \
  --old-root "$HOME/beta_old/000 case_old" \
  --new-root "$HOME/ci_new/000 case_new" \
  --out "/path/to/sync_missing_dry_run.json"

# 确认 dry-run 后才复制缺失文件
python3 scripts/switch_rodski_env.py \
  sync-missing --write \
  --old-root "$HOME/beta_old/000 case_old" \
  --new-root "$HOME/ci_new/000 case_new" \
  --out "/path/to/sync_missing_result.json"

# 从旧/新样本只读提取映射。遇到同一旧值映射到多个新值时，会生成 scoped key_replacements
python3 scripts/switch_rodski_env.py \
  extract-map --old-root "/path/to/old cases" --new-root "/path/to/new cases" \
  --out "/path/to/env_map.json"

# 根据映射转换目标目录。默认 dry-run，不写文件
python3 scripts/switch_rodski_env.py \
  apply --target-root "/path/to/new-or-copied cases" --map "/path/to/env_map.json" \
  --diff --out "/path/to/dry_run.json"

# 确认 dry-run 后才真实写入目标目录；同时备份被改文件
python3 scripts/switch_rodski_env.py \
  apply --target-root "/path/to/new-or-copied cases" --map "/path/to/env_map.json" \
  --write --backup-dir "/path/to/backups" --out "/path/to/apply_result.json"
```

## 扫描范围

### 缺失用例补齐

`sync-missing` 默认比较：

- 旧环境：`$HOME/beta_old/000 case_old`
- 新环境：`$HOME/ci_new/000 case_new`
- 资产目录：`case,data,model,fun`

它按相对路径判断目标是否缺失。例如旧目录存在 `某模块/case/A.xml` 而新目录没有同一路径，就复制该文件；如果新目录已有同名路径，不覆盖、不合并、不改名。

不要用 `rsync` 直接同步整模块目录，避免把 `plan/`、报告、录制产物、前端源码或其他非用例资产带过去。

默认范围：

- `globalvalue`：`**/data/globalvalue.xml`
- `model`：`**/model/model.xml` 中的 URL/DB 地址，例如接口 `_url`
- `sqlite`：`**/data/data.sqlite` 的 `rs_field.field_value` 中的 URL/DB 地址
- `text`：默认只扫 `fun/` 下文本和 `.env`。前端源码、`package-lock.json`、依赖目录等不会默认扫描，避免把非用例资产混入换环境。

可以用 `--scope globalvalue,model,sqlite,text` 指定范围。实际转换仍只替换 URL/DB 地址字符串本身。

只有在明确需要全量文本扫描时才加 `--broad-text`。

## 映射文件格式

优先使用明确映射，不猜未知环境。

```json
{
  "value_replacements": {
    "https://ec-hwbeta.casstime.com/agentBuy/": "https://ec-hwci.casstime.com/agentBuy/",
    "<old_db_host>": "<new_db_host>"
  },
  "key_replacements": {
    "globalvalue:登录/ec-agent-buy-login::DefaultValue.ECAgentBuyURL": "https://ec-hwci.casstime.com/agentBuy/",
    "登录/ec-agent-buy-login::DefaultValue.ECAgentBuyURL": "https://ec-hwci.casstime.com/agentBuy/"
  },
  "regex_replacements": [
    {
      "pattern": "https://ec-hwbeta\\.casstime\\.com",
      "replacement": "https://ec-hwci.casstime.com"
    }
  ]
}
```

优先级：`key_replacements` > `value_replacements` > `regex_replacements`。

`key_replacements` 推荐使用脚本输出的 `selector`，格式类似：

```text
globalvalue:<module>::<group>.<var>
model:<module>::<Model>.<Element>.location[1]
sqlite:<module>::<table>/<data_id>/<field>
```

## 当前 beta → ci 经验

需要参考本次已有转换时，读取：

- `references/current-beta-to-ci.md`

其中记录了本次实际观察到的 URL 域名、DB host 映射，以及仍未切走的 `f2b-beta` 项。

## 校验要求

转换完成后至少执行：

```bash
python3 scripts/switch_rodski_env.py \
  audit --root "/path/to/converted" --out "/path/to/verify_audit.json"
```

如果有转换前目录，再执行：

```bash
python3 scripts/switch_rodski_env.py \
  compare --old-root "/path/to/source-readonly" --new-root "/path/to/converted" \
  --out "/path/to/verify_compare.json" --markdown "/path/to/verify_compare.md"
```

如果用户要求跑 RodSki，再按目标模块运行最小 `data validate` / dry-run；否则最终答复明确说明只做了静态 URL/DB 地址转换与审计。

### 报告清理

最终复查优先输出到 `/tmp`，避免污染用例仓库：

```bash
python3 scripts/switch_rodski_env.py \
  apply --target-root "/path/to/converted" --map "/path/to/env_map.json" \
  --out "/tmp/rodski_apply_old_values_check.json"

python3 scripts/switch_rodski_env.py \
  sync-missing --old-root "/path/to/source-readonly" --new-root "/path/to/converted" \
  --out "/tmp/rodski_sync_missing_check.json"
```

清理前确认：

- `apply` dry-run 的 `change_count` 为 `0`。
- `sync-missing` dry-run 的 `missing` 和 `blocked` 为 `0`。
- `compare`/`audit` 没有未切换的旧 URL 或旧 DB host；命中的连接名、用户名或业务库名要先人工辨别，不把它们误判成环境地址。

清理时只删除本次生成的报告文件，不使用递归删除，不用通配符覆盖整个目录；删除后用 `test ! -e` 或 `find` 复核。最终答复写明删除了哪些报告、保留了哪些目录、执行过的校验摘要。
