# demo_hooks

这是一个自包含、无浏览器依赖的 v8.2.0 Hooks 演示模块。它覆盖两种不同的
hook 接口：CLI 的外部 `on_run_start` 命令 hook，以及 Python API 的进程内
`before_keyword` 回调。

## 目录

```text
demo_hooks/
├── case/demo_case.xml
├── model/model.xml
├── data/globalvalue.xml
├── data/README.md
├── fun/hooks/on_run_start.py
├── plan/demo_plan.xml
├── result/
├── hooks.json
└── run_demo.py
```

`data/data.sqlite` 是模块内持久、自包含的演示数据库，同时保存 RodSki 的
`DemoDB` 逻辑数据表和演示用 `audit_log` 业务表。`Q_WRITE` 尝试插入审计行，
`Q_READ` 查询审计行数；`run_demo.py` 只在执行前清空 `audit_log`，不会删除或
重建数据文件，因此可以直接执行 CLI dry-run 和 Python API 验收。

## 一键验收

从仓库根目录执行：

```bash
python3 rodski-demo/DEMO/demo_hooks/run_demo.py
```

脚本会断言以下结果，并在全部通过后输出 JSON：

1. `@demo_plan` 与 `--tag smoke` 同时使用时，内置合规检查返回 `SKI703`。
2. 外部 hook 设为 allow 后，`--force-compliance` 可显式跳过该内置检查并留痕。
3. 外部 `on_run_start` 返回 exit code 2 时，CLI 被拒绝。
4. `--force-compliance` 不能绕过外部 hook 的 deny。
5. Python API 的 `before_keyword` 将 `Q_WRITE` 拦截为 `SKI701`，`Q_READ`
   正常通过，且 `audit_log` 最终仍为 0 行。

## 分步执行

外部命令 hook 使用相对脚本路径，因此分步命令从模块目录执行：

```bash
cd rodski-demo/DEMO/demo_hooks
```

内置合规检查默认拒绝 plan 与 selector 冲突：

```bash
RODSKI_DEMO_HOOK_MODE=allow \
  python3 ../../../rodski/cli_main.py run @demo_plan --tag smoke --dry-run
```

显式 force 只跳过内置检查；`--verbose` 会显示跳过留痕：

```bash
RODSKI_DEMO_HOOK_MODE=allow \
  python3 ../../../rodski/cli_main.py run @demo_plan --tag smoke \
  --dry-run --force-compliance --verbose
```

默认或显式 deny 模式下，外部 hook 返回 exit code 2。即使附加
`--force-compliance`，外部策略仍然拒绝：

```bash
RODSKI_DEMO_HOOK_MODE=deny \
  python3 ../../../rodski/cli_main.py run case --dry-run

RODSKI_DEMO_HOOK_MODE=deny \
  python3 ../../../rodski/cli_main.py run case --dry-run --force-compliance
```

这是设计约束：`--force-compliance` 只作用于 RodSki 内置合规检查，不会覆盖
项目自定义的外部 `on_run_start` 决策。

## Python API

`run_demo.py` 通过以下公共接口注册关键字级策略：

```python
executor = SKIExecutor(
    case_path="case",
    driver=None,
    module_dir=".",
    hooks={"before_keyword": [block_db_writes]},
)
```

回调收到 `keyword="DB"` 和 `params={"model": "DemoDB", "data": "Q_WRITE"}`；
返回 `HookDecision(allow=False, reason=...)` 后，写步骤在连接 SQLite 之前即被
阻断。只读行 `Q_READ` 返回 allow，并真实执行查询。
