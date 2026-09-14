<!-- 自动生成 from rodski/docs/TEST_CASE_WRITING_GUIDE.md  请勿手工编辑 -->

## 16. 性能压测（v8.0）

### 16.1 核心概念

v8.0 新增压测能力（`kind="load"` 计划），与功能测试完全独立：

| 维度 | 功能测试（kind=suite） | 性能测试（kind=load） |
|------|---------------------|-------------------|
| 执行路径 | SKIExecutor | LoadExecutor |
| 用例语义 | 每条 case 执行一次，记录 PASS/FAIL | 多 VU 反复执行，记录 RPS/延迟 |
| verify 失败 | case FAIL | 记为错误请求，继续执行 |
| 截图 | 失败时自动截图 | 不截图 |

### 16.2 两种压测模式

| 模式 | `mode` | 适用场景 | 后端 |
|------|--------|---------|------|
| 接口压测 | `api`（默认） | REST API | Locust FastHttpUser |
| 浏览器压测 | `browser` | Web 页面 | Playwright 多进程池 |

### 16.3 压测计划 XML（plan/xxx_load.xml）

**接口压测示例**（kind=load + mode=api）：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<test_plan id="api_load_basic" kind="load">

  <load_profile mode="api">
    <concurrency>50</concurrency>           <!-- 并发 VU 数 -->
    <duration_seconds>120</duration_seconds>
    <ramp_up_seconds>30</ramp_up_seconds>
    <think_time_ms min="200" max="800"/>    <!-- 迭代间思考时间 -->
    <max_rps>0</max_rps>                    <!-- 0 = 不限制 -->
    <host>http://api.example.com</host>     <!-- 覆盖 GlobalValue URL -->
  </load_profile>

  <cases>
    <!-- weight 控制 VU 任务调度权重 -->
    <case id="login_api"    execute="是" weight="3"/>
    <case id="order_query"  execute="是" weight="1"/>
  </cases>

</test_plan>
```

**浏览器压测示例**（kind=load + mode=browser）：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<test_plan id="web_load_basic" kind="load">

  <load_profile mode="browser">
    <concurrency>10</concurrency>           <!-- 并发浏览器进程数（受内存限制） -->
    <duration_seconds>60</duration_seconds>
    <ramp_up_seconds>10</ramp_up_seconds>
    <think_time_ms min="500" max="2000"/>
  </load_profile>

  <cases>
    <case id="login_ui" execute="是" weight="1"/>
  </cases>

</test_plan>
```

**load_profile 属性说明**：

| 元素 | 必填 | 说明 |
|------|------|------|
| `concurrency` | 是 | 并发 VU 数（api）或并发进程数（browser） |
| `duration_seconds` | 是 | 持续时长（秒） |
| `ramp_up_seconds` | 否 | 爬坡时间（默认 0） |
| `think_time_ms` | 否 | 迭代间思考时间范围（毫秒） |
| `max_rps` | 否 | 最大 RPS 上限，0 = 不限（api 模式专用） |
| `host` | 否 | 覆盖 GlobalValue 中的目标地址 |

`mode` 属性：`api`（默认）/ `browser`

### 16.4 约束

- **必须通过 plan 文件声明**，不支持 `--load --concurrency N` 临时压测
- `mode="api"` 计划只能引用 `component_type="接口"` 的 case
- `mode="browser"` 计划只能引用 `component_type="界面"` 的 case
- load 计划不支持 scenario 级别选择（只能整个 case 粒度）
- `@plan_id` 与 selector 互斥约束照常成立

### 16.5 perf/ 目录

`kind="load"` 计划首次执行时，LoadCompiler 自动在 `perf/` 目录生成预编译产物：

```
{测试模块}/
├── plan/
│   └── api_load_basic.xml     ← kind="load"
└── perf/                      ← 自动生成（可纳入版本管理）
    ├── api_load_basic.py       ← 预编译 Locust 脚本
    └── api_load_basic.py.meta ← 哈希元数据（用于检测变更）
```

`perf/` 产物可脱离 RodSki 独立运行（直接 `locust -f perf/api_load_basic.py`）。

### 16.6 CLI 命令

```bash
# 执行压测计划
rodski run @api_load_basic

# 启动 Locust Web UI 实时监控（默认端口 8089）
rodski run @api_load_basic --load-ui
rodski run @api_load_basic --load-ui-port 9090

# 跳过预编译（直接使用已有 perf/*.py）
rodski run @api_load_basic --no-compile

# 预览执行范围（不发真实请求）
rodski run @api_load_basic --dry-run
```

### 16.7 结果输出

压测结果写入 `result/result_*.xml`，扩展 `<load_summary>` 节点，包含：

- RPS（每秒请求数）
- P50 / P95 / P99 延迟
- 错误率
- 总请求数 / 失败数

`--report html` 报告含"性能概览"区块。

### 16.8 安装依赖

```bash
# 压测依赖（Locust）为可选 extras
pip install rodski[load]
```

---

### Q1: 用例没有执行？

1. 检查 Case XML 的 `execute` 属性是否为 `是`（不是 `Y`、`true`；XSD 仅允许 `是` / `否`）
2. 检查 XML 文件编码是否为 UTF-8
3. 检查 XML 格式是否合法（可用浏览器打开验证）
4. 可选：用 `xmllint` 对照 `rodski/schemas/case.xsd` 校验（见上文 **§2.2 Schema 约束**）

### Q2: type 批量输入失败？

1. 检查 model.xml 元素 `name` 是否与数据表 field `name` **完全一致**（区分大小写）
2. 检查定位方式是否正确（用浏览器 F12 验证）
3. 数据表中未定义的字段会被跳过

### Q3: verify 报错"缺少验证目标"？

verify 必须同时填写 **model 和 data** 属性，走批量验证模式。不支持只传 locator 的简单模式。

### Q4: DB 连接失败？

1. 检查 globalvalue.xml 中是否有对应组名的连接配置
2. SQLite：确认 `database` 路径正确且文件存在
3. MySQL/PostgreSQL：确认已安装对应驱动（pymysql / psycopg2）

### Q5: Return 引用没有生效？

Return 引用只应写在**数据表 XML 的 field 值中**，不要直接写在 Case XML。如果 Return 引用的索引不存在，原文保持不变。

### Q6: 数据引用不生效？

1. 检查 `datatable@name` 是否与模型名一致
2. 检查 DataID（row id）是否存在
3. 引用格式：`表名.DataID`（整行）或 `表名.DataID.字段名`（单字段）

### Q7: XSD 校验报错「元素 test_step 缺失」？

`case.xsd` 要求每个 `<case>` **必须**包含恰好一个 `<test_step>`。仅写 `<pre_process>` 等而不写 `<test_step>` 不会通过校验。

---
