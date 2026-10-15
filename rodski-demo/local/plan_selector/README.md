# local/plan_selector — 执行范围选择验收（F081 / F091 / F092 / F093 / F094）

验收"这次执行跑哪些用例 / scenario / step"：用例级过滤（`--tags/--priority/--exclude-tags`）、
scenario 级临时 selector（`--tag/--group/--exclude-tag`）、测试计划执行优先级、`rodski plan` 子命令与默认计划、
调试计划（`debug-scenario / debug-step + --debug`）以及 `@plan_id` 与 selector 互斥。

所有步骤都是 `run fun/mark.py <标签>`：不需要浏览器、不依赖任何外部服务。
编排脚本经环境变量 `RODSKI_PS_MARKER` 收集执行轨迹（精确到 scenario 内第几步），
再与 `result.xml` 中 PASS/FAIL 的用例集合交叉核对——断言的是**真实执行集合**，不是 dry-run 预览。

## 目录

```
case/
├── catalog/catalog_basic.xml   <cases tags="catalog,regression">，无 scenario
│     CAT_001 P0 tags="smoke"（用例级 tags）· CAT_002 P1 · CAT_003 P2 tags="slow"
├── checkout/checkout_flow.xml  <cases tags="checkout">，含 scenario
│     CHK_001 P0  pre + 裸步骤 + S01(positive; smoke,p0; 3 步) + S02(negative; slow) + S03(positive; api) + post
│     CHK_002 P1  S01(negative; smoke) + S02(positive; api)
│     CHK_003 P0  execute="否"（case XML 硬关闭）
└── report/report_basic.xml     RPT_001 P3（add-dir / case_dir 目标）
plan/
├── project_full.xml            默认全量计划（rodski run 无参数）
├── priority_regression.xml     F092 优先级矩阵（default_execute=否）
├── disabled_regression.xml     F092 test_plan execute=否
├── defaulton_regression.xml    F092 default_execute=是 + 显式关闭
├── checkout_step_debug.xml     F094 step_debug（S01 第 2 步，auto + only）
└── checkout_scenario_debug.xml F094 scenario_debug（S03，prepare=case，cleanup=是）
fun/mark.py                     执行轨迹标记
data/init_data.py               重建 data.sqlite（仅公共元表；编排脚本每次开头调用）
```

## 运行

```bash
python3 rodski-demo/local/plan_selector/run_acceptance.py            # 全部 32 项
python3 rodski-demo/local/plan_selector/run_acceptance.py P13 P25    # 指定项
python3 rodski-demo/local/plan_selector/run_acceptance.py --strict   # KNOWN 也计为失败

# 手工
cd rodski-demo/local/plan_selector
rodski run case/ --group negative
rodski run @priority_regression
rodski run @checkout_step_debug --debug
rodski run                                   # 默认计划 project_full
```

输出逐项 `PASS / FAIL / KNOWN`；退出码 0 = 无意外失败，1 = 存在 FAIL。
改写 `plan/` 的检查（plan 子命令、默认计划解析、调试计划矩阵）先把模块复制到临时目录再执行，仓库内 `plan/` 不变。

## 检查项

| 编号 | 功能 | 文档条款 |
|------|------|---------|
| P01~P06 | `--tags` 套件/用例级、`--priority` 单值/多值、`--exclude-tags`、标签 AND 优先级 | GUIDE §9.7、§3.2，case.xsd `CaseType@tags` |
| P08~P12 | `--tag`（scenario tag）、`--group`、`--tag + --exclude-tag`、无路径 `rodski run --group`、`--dry-run` | GUIDE §10.5、CORE §7.7 |
| P13~P15 | case execute=否 > test_plan.execute=否 > plan case > scenario > step > default_execute | GUIDE §10.9、CORE §7.7 |
| P17~P26 | 无参数 `rodski run`、默认计划解析、`plan init/create/add-case/add-dir/add-scenario/--from-tag/migrate/list/validate/disable-*/enable-*/preview` | GUIDE §10.3、§10.4、§10.8，CORE §7.7 |
| P28~P34 | `plan debug-scenario/debug-step`、`--debug`、prepare(auto/case/none) × step_mode(only/from/all)、cleanup | GUIDE §10.7 |
| P35 | `@plan_id` 与 `--tag/--group/--exclude-tag/--priority/--case-id` 固定互斥 | GUIDE §10.6、CORE §7.7 |

prepare=auto 文档写作"执行 pre_process + 目标 step 之前的步骤"，未说明 test_case 中 scenario 之前的裸步骤是否计入，
调试类检查不对 `CHK_001/bare` 做断言。

## KNOWN 缺陷（按文档写期望，框架行为不符）

| 检查项 | 现象 | 怀疑位置 |
|------|------|---------|
| P01/P04/P06 | 任一 selector 生效时，不含 scenario 的用例一律 SKIP(plan_not_selected)，`--tags catalog` 0 条执行 | `rodski/core/ski_executor.py:1047-1049`、`rodski/core/test_plan_selection.py:compile_from_selector` **已修复 v11.8.7（BUG-A06）** |
| P02/P05 | 用例级 `tags` 属性被忽略；`--tags smoke` 0 条执行 | `rodski/core/case_parser.py:118` **已修复 v11.8.9（BUG-A07）** |
| P03 | `--priority P0,P1` 只按 P0 生成 scenario 选择 | `rodski/core/ski_executor.py:648`、`rodski/rodski_cli/run.py:903` |
| P08 | `--tag p0`（只在 scenario@tag 上）0 条执行：`--tag` 先按文件级 tags 做用例级过滤 | `rodski/core/ski_executor.py:1317` **已修复 v11.8.8（BUG-A09）** |
| P11 | 无路径 `rodski run --group negative`：有 project_full 时报 SKI703 互斥，无时报"未找到默认测试计划" | `rodski/rodski_cli/run.py:593-603` |
| P21/P22/P28/P29 | `add-scenario`、`create --from-tag`、`debug-scenario`、`debug-step` 生成的 `<case>` 不带 `file`，多文件模块中 SKI207 | `rodski/rodski_cli/plan.py:185/542/746/764` |
| P33 | prepare=none 调试用例 FAIL：`'SKIExecutor' object has no attribute '_phase_runtime_seq'` | `rodski/core/ski_executor.py:2000`（`_execute_debug_case` 未初始化计数器） |
