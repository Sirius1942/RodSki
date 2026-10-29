<!-- 自动生成 from rodski/docs/TEST_CASE_WRITING_GUIDE.md  请勿手工编辑 -->

## 9. 完整示例

### 9.1 项目结构

```text
rodski-demo/demosite/full/
├── model/
│   └── model.xml
├── case/
│   └── demo_case.xml
├── data/
│   ├── globalvalue.xml
│   └── data.sqlite
├── fun/
└── result/
```

### 9.2 model.xml

```xml
<?xml version="1.0" encoding="UTF-8"?>
<models>
<model name="Login" servicename="">
    <element name="username" type="web">
        <type>input</type>
        <location type="id">username</location>
    </element>
    <element name="password" type="web">
        <type>input</type>
        <location type="id">password</location>
    </element>
    <element name="loginBtn" type="web">
        <type>button</type>
        <location type="id">login-btn</location>
    </element>
</model>
</models>
```

### 9.3 globalvalue.xml

```xml
<?xml version="1.0" encoding="UTF-8"?>
<globalvalue>
  <group name="DefaultValue">
    <var name="URL" value="http://127.0.0.1:5555"/>
    <var name="WaitTime" value="0"/>
  </group>
  <group name="sqlite_db">
    <var name="type" value="sqlite"/>
    <var name="database" value="demo.db"/>
  </group>
</globalvalue>
```

### 9.4 data.sqlite（数据表）

所有测试数据（输入表和验证表）均存储在 `data/data.sqlite` 中。输入表 `table_kind='data'`，验证表 `table_kind='verify'`。

迁移命令：`rodski data import <module>`

### 9.6 demo_case.xml（用例）

```xml
<?xml version="1.0" encoding="UTF-8"?>
<cases>
  <case execute="是" id="c001" title="登录" description="验证登录" component_type="界面">
    <pre_process>
      <test_step action="navigate" model="" data="GlobalValue.DefaultValue.URL/login"/>
    </pre_process>
    <test_case>
      <test_step action="type" model="Login" data="L001"/>
      <test_step action="verify" model="Login" data="V001"/>
    </test_case>
    <post_process>
      <test_step action="close" model="" data=""/>
    </post_process>
  </case>

  <case execute="是" id="c002" title="数据库查询" description="验证 DB 新语法" component_type="数据库">
    <test_case>
      <test_step action="DB" model="QuerySQL" data="Q001"/>
    </test_case>
  </case>
</cases>
```

### 9.7 运行命令

```bash
# 方式1：指定 case XML 文件
rodski run rodski-demo/demosite/full/case/demo_case.xml

# 方式2：指定 case 目录（递归执行该目录下所有 XML，任意层级，v11.5.0 起）
rodski run rodski-demo/demosite/full/case/

# 方式2b：指定 case 下的任意子目录（同样递归，v11.5.0 起；示意路径）
rodski run product/shop/order/case/refund/

# 方式3：指定测试模块目录
rodski run rodski-demo/demosite/full/

# 方式4：文件 + --case-id，只执行该文件中的指定用例（v11.5.0 起，可逗号分隔多个）
rodski run rodski-demo/demosite/full/case/demo_case.xml --case-id TC002

# 按标签过滤（OR 匹配，命中任一即可；--tags 为兼容写法）
rodski run case/ --tag smoke
rodski run case/ --tag "smoke,regression"

# 按优先级过滤
rodski run case/ --priority P0
rodski run case/ --priority "P0,P1"

# 排除标签（--exclude-tags 为兼容写法）
rodski run case/ --exclude-tag slow

# 组合过滤（标签 AND 优先级）
rodski run case/ --tag smoke --priority P0

# 执行后自动生成 HTML 报告
rodski run case/ --report html

# 生成 JUnit XML（CI 用，v11.6.0）；可与 html 逗号并列
rodski run case/ --report junit
rodski run case/ --report html,junit

# 浏览器会话复用（v11.6.0，覆盖 DefaultValue.SessionMode）
rodski run case/ --session-mode shared_browser

# 按用例文件并行，4 个 worker（v11.6.0）
rodski run case/ --workers 4

# 简洁记录模式：只保留失败截图，录像不受影响（v11.6.0，覆盖 DefaultValue.EvidenceMode）
rodski run case/ --evidence concise

# 以上执行方式参数可与 @plan_id 同用（它们不是执行范围 selector）
rodski run @project_full --workers 4 --session-mode shared_browser --report junit

# 静态检查常见写法问题（固定 wait、evaluate 断言、弹窗垫片、sql/query 均无效等）
rodski case lint <module>

# 无头模式
rodski run case/ --headless

# 指定浏览器（默认 chromium；DefaultValue.BrowserType 不生效）
rodski run case/ --browser firefox

# 只校验、不执行（解析用例 / 计划并预览执行范围）
rodski run case/ --dry-run

# 机器可读输出（Agent / CI 解析用）；--verbose 输出详细日志
rodski run case/ --output-format json
rodski run case/ --verbose

# 导出 trace.json（run / case / keyword 三层 span + 耗时 / 重试指标）；--report html 也会采集
rodski run case/ --trace

# 录像（--record-mode auto|screen|playwright|off 等细项默认读取配置）
rodski run case/ --record

# 移动端：临时切换平台、指定设备（覆盖 Mobile.Platform / Mobile.UDID）
rodski run case/ --platform ios --udid <设备UDID>

# 附加到已启动的远程调试浏览器，复用其页面与登录态（仅 Web；此时 --headless / --browser 不生效）
rodski run case/ --cdp :9222
```

> `--case-id` 必须与**单个用例文件**路径一起使用；传目录会报 `SKI208 CaseIdRequiresFile`。`--case-id` 与 `@plan_id` 固定互斥（见 §10.6），与 `--tag` / `--priority` 同用时只在指定用例内过滤。
>
> `--data-id` / `--exclude-data-id` **只能**与测试计划一起使用（`@plan_id`，或不带路径时的默认计划），用于过滤数据驱动实例；直接对用例文件 / 目录使用会报错并以退出码 1 结束（见 [§10.10](#1010-计划级数据驱动v1190)）。
>
> `--workers N` 以**用例文件**为单位分给 N 个进程，同一文件内的用例在同一进程中按顺序执行；结果合并到同一个运行目录（`result.xml`、`junit.xml`、截图镜像目录都在一起）。有先后依赖的用例（如先保存登录态、再使用）请放在同一个文件里。

### 9.8 结果目录说明（v11.5.0）

一次运行目录（`result/rodski_{ts}/`；同一秒内先后启动的多次运行，后者目录名追加 `_2`、`_3`，互不覆盖，v11.6.0）下，**用例级产物**（步骤截图、失败截图、场景截图子目录、录像）按用例文件路径镜像存放在运行目录的 `case/` 子目录中，与 `case/` 的目录结构完全一致；用例文件对应的目录名为文件名去掉 `.xml`。**此规则适用于所有用例文件，包括位于 `case/` 根目录的文件**，没有特例：

```
case/                              result/rodski_20260928_100000/
├── smoke_root.xml                 ├── result.xml               ← 汇总产物，位置不变
├── order/                         ├── execution_summary.json   ← 汇总产物，位置不变
│   ├── order_basic.xml            ├── execution.log            ← 汇总产物，位置不变
│   └── refund/                    └── case/                    ← 镜像 case/ 目录结构
│       └── refund_apply.xml           ├── smoke_root/
                                        │   └── screenshots/
                                        └── order/
                                            ├── order_basic/
                                            │   └── screenshots/
                                            └── refund/
                                                └── refund_apply/
                                                    ├── screenshots/
                                                    └── recordings/
```

截图**文件名格式不变**（`{caseid}_{stepindex}_{phase}_{timestamp}.png`、场景截图子目录 `{caseid}_{scenarioid}_{scenariotitle}/`、失败截图 `{caseid}_{timestamp}_failure.png`）。跨文件同 `case_id` 的用例分别写入各自文件的镜像目录，互不覆盖——这是引入镜像目录的主要动机之一。

`result.xml`、`execution_summary.json`、`execution.log`、`trace.json`、HTML 报告等**汇总产物保持在运行目录根**，不随用例文件镜像；其中记录的截图/录像路径同步改为相对运行目录的新路径。消费方（HTML 报告、web、rodski-agent、browser-plugin、VSCode 插件）应优先读取结果中记录的路径，不要自行按旧的扁平规则拼接 `result/screenshots/...`。

`--report junit` 生成的 `junit.xml` 同样在运行目录根（v11.6.0）。`--evidence concise` 时 `screenshots/` 下只有失败截图（文件名含 `failure`）。

### 9.9 CI 接入（JUnit，v11.6.0）

`--report junit` 在运行目录根生成 `junit.xml`：每个用例文件是一个 `<testsuite>`，每个用例是一个 `<testcase>`（`classname` = 用例文件相对 `case/` 的路径，`name` = 用例 ID），失败用例带 `<failure>`（错误信息 + 失败截图相对路径）。运行目录名带时间戳，CI 中用通配符收集。

**GitLab CI**：

```yaml
rodski-test:
  image: mcr.microsoft.com/playwright/python:v1.47.0-jammy
  script:
    - pip install rodski
    - cd product/shop/order
    - rodski run case/ --headless --session-mode shared_browser --workers 4 --report html,junit
  artifacts:
    when: always
    paths:
      - product/shop/order/result/
    reports:
      junit: product/shop/order/result/*/junit.xml
```

**GitHub Actions**：

```yaml
jobs:
  rodski:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install rodski && python -m playwright install --with-deps chromium
      - run: rodski run case/ --headless --session-mode shared_browser --workers 4 --report html,junit
        working-directory: product/shop/order
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: rodski-result
          path: product/shop/order/result/
      - uses: mikepenz/action-junit-report@v4
        if: always()
        with:
          report_paths: product/shop/order/result/*/junit.xml
```

- 退出码：有失败用例时非 0，CI 据此判定失败；`expect_fail="是"` 且确实失败的用例按通过计。
- CI 里建议 `WaitTime=0`，并用 `--evidence concise` 缩短耗时；需要排查偶发失败时加 `--record` 保留录像。

### 9.10 断点与部分执行参数（REQ-012，能力有限）

`rodski run` 提供以下调试参数（v11.8.0 引入）。**这组能力目前只完成了一小部分**：REQ-012 的 37 条真实验收中只有 1 条通过，交互式断点 / 单步并不可用。下表按当前实际行为列出，行为可能调整；排查失败请优先用 `--trace`、截图 / 录像和 [§10.7](#107-调试计划) 的调试计划。

| 参数 | 设计用途 | 当前实际行为 |
|------|---------|-------------|
| `--start-from N` | 从第 N 个步骤开始执行 | **可用**：每个用例内序号小于 N 的步骤不执行，在步骤记录中标为 `skipped`。序号在每个用例内从 1 开始，`pre_process` / `test_case` / `post_process` 连续计数 |
| `--break-at <断点>` | 在断点处暂停，逗号分隔多个；格式 `step:N`、`scenario:ID`、`node:NAME`、`flow:ID`、`driver:ACTION`、`batch:row:N` | 不生效：断点会被解析，但执行时任何类型都不会命中，也不会暂停 |
| `--stop-at N` | 执行到第 N 步后停止 | 不生效 |
| `--step-mode` | 单步执行（**开关**，不带取值） | 不生效 |
| `--driver-level` | 驱动动作级单步（配合 `--step-mode`） | 不生效 |

```bash
# 跳过每个用例的前 4 步，从第 5 步开始执行（如 pre_process 已手工准备好）
rodski run rodski-demo/demosite/full/case/demo_case.xml --case-id TC001 --start-from 5
```

- 上述任一参数（`--driver-level` 除外）出现时，本次运行开启调试会话。
- `rodski debug {status|queue|objects|context|get-object <id>}` 用于查看调试会话，但调试会话只存在于 `rodski run` 自身进程中：在另一个终端执行 `rodski debug ...` 看不到它，总是提示 "Debug session is not active"。
- 同名参数不要混淆：`rodski run --step-mode` 是上表的开关参数；`rodski plan debug-step --step-mode all|from|only` 是生成单步调试计划时的取值参数（见 [§10.7](#107-调试计划)），后者可用。
- 这组参数与 `@plan_id` 能否同用、是否算执行范围 selector 尚未定义，建议只对单个用例文件使用。

---
