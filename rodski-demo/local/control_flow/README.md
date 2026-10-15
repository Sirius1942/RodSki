# local/control_flow - v7.0 特性演示

## 概述

演示 v7.0.0 引入的移动端测试能力、录像架构、多设备并发等核心特性。

## 环境要求

- 根据用例选择：
  - Web 用例：demosite :8000
  - 移动端用例：Appium + Android 模拟器或真机

## 用例说明

| 用例类型 | 说明 |
|---------|------|
| `case/*.xml` | v7 特性覆盖（具体数量以实际文件为准） |

## 两种运行方式

### 1. 使用编排脚本（推荐）

```bash
cd /path/to/rodski-demo/local/control_flow
python3 run_v7_demo.py
```

编排脚本会处理前置准备（如启动目标页服务、设置环境变量等）。

### 2. 直接运行用例

```bash
rodski run case/
```

需手动满足环境依赖，可能因缺少前置而部分失败。

## 验收标准

- 使用 `run_v7_demo.py` 时：exit 0，演示完成
- 直接 `rodski run case/` 且环境齐全时：用例通过

## 相关文档

- CHANGELOG.md v7.0.0 / v7.1.1
- CORE §11：移动端约束

---

## 控制流与执行语义验收（case/flow/，`run_acceptance.py`）

只用 `set/get/run/DB/verify` 与内嵌 `data:` 页面（`GlobalValue.CfPage.READY`），不依赖 :8000；
DB 连接 `cf_db` 指向 `result/cf_flow.sqlite`（只执行常量 SELECT，result/ 已 gitignore）。数据由 `data/init_data.py` 生成（编排脚本每次开头自动重建）。

```bash
python3 rodski-demo/local/control_flow/run_acceptance.py          # 全部 25 项
python3 rodski-demo/local/control_flow/run_acceptance.py C05 C21  # 指定项
python3 rodski-demo/local/control_flow/run_acceptance.py --strict # KNOWN 也计为失败
```

输出逐项 `PASS / FAIL / KNOWN`；退出码 0 = 无意外失败，1 = 存在 FAIL。

| 文件 | 用例 | 功能 | 文档条款 |
|------|------|------|---------|
| `flow/phase_negative.xml` | F062_01~03 | 预处理失败跳过用例阶段仍执行后处理；用例阶段失败仍执行后处理；后处理失败整条失败 | GUIDE §3.3、CORE §7.2 |
| `flow/scenario_depends.xml` | F066_01~02 | depends 依赖 FAIL / SKIP → 依赖方 SKIP；多依赖；正向对照 | GUIDE §3.4 |
| `flow/branch_else.xml` | F067_01~05 | if/else 条件为假走 else（文本 / 变量 / Return 两种写法 / element_exists） | GUIDE §3.8、CORE §12.2~12.4 |
| `flow/branch_elif_nested.xml` | F068_01~07 | elif 链、2 层嵌套、loop 内 if、循环变量分流、变量 elif、CORE 嵌套原文、`>=`/`<=` | GUIDE §3.8、CORE §12.2/§12.6、case.xsd |
| `flow/loop_basic.xml` | F069_01~03 | `range="1,2,3"` / `"1-3"` / `"1,5"`，`${var}` 在 run/DB/verify 的 data 中解析 | GUIDE §3.8 |
| `flow/wait_basic.xml`、`flow/wait_override.xml` | F070_01~02 | WaitTime 毫秒、≤30 按秒兼容 + 弃用告警、31 边界、step_wait 覆盖 WaitTime | GUIDE §3.2、§6.4.1 |

用例自检写法：按文档不应执行的分支放 `run fail.py`（走错即失败）；应执行的分支 `run mark.py` 留执行轨迹
（编排脚本经环境变量 `RODSKI_CF_MARKER` 收集）并 `set hits=${hits}x` 计数，末尾 `run assert_eq.py` 校验命中次数——
条件块被整体跳过时用例也会失败。按文档应失败的 F062/F066_01 标 `expect_fail="是"`，编排脚本再断言 `[预期失败]` 前缀。

F070 由编排脚本把模块复制到临时目录、改写 `WaitTime` / `step_wait` 后计时（阈值留足余量）。
直接 `rodski run case/flow/ --headless` 时按本模块 `WaitTime=500` 执行（flow 下除 wait_* 外都写了 `step_wait="0"`）。

### KNOWN 缺陷（按文档写用例，框架行为不符）

| 检查项 | 用例 | 现象 | 怀疑位置 |
|------|------|------|---------|
| C06/C14 | F067_02、F068_05 | `set` 的变量在 `<if condition>` 中不可见，`${flag} == off` 为假 | `rodski/core/ski_executor.py:2393`（以 model 空串为键同步变量）、`rodski/core/dynamic_executor.py:236-239`（`${x}` 只剥 `$`） |
| C07/C08 | F067_03、F067_04 | `${Return[-1].status} == 200` / `${Return[-1].status == 200}` 恒为假 | `rodski/core/dynamic_executor.py:23`（`return_values or []` 使空 history 脱钩）、`:168` 正则不识别 GUIDE 写法 |
| C09 | F067_05 | `element_exists` 恒假、`element_not_exists` 恒真 | `rodski/core/dynamic_executor.py:209` 以 1 参调用 `playwright_driver.py:516 locate_element(type, value)` |
| C12/C13 | F068_03、F068_04 | `<loop>` 内的 `<if>/<elif>/<else>` 被静默丢弃 | `rodski/core/case_parser.py:_parse_branch_steps` |
| C15/C16 | F068_06、F068_07 | `>=` / `<=` 条件被当作"评估失败"整块跳过 | `rodski/core/dynamic_executor.py:90` 运算符拆分顺序 |
