<!-- 自动生成 from rodski/docs/TEST_CASE_WRITING_GUIDE.md  请勿手工编辑 -->

## 2. 目录结构

v3.0+ 版本使用固定目录结构组织测试模块：

- `data.sqlite` 是唯一测试数据文件

```
product/                           ← 产品根目录（最顶层）
└── {测试项目名}/                   ← 测试项目
    └── {测试模块名}/               ← 测试模块（业务）
        ├── case/                  ← 测试用例 XML，支持任意多级子目录（v11.5.0 起，递归发现）
        │   ├── smoke_root.xml
        │   └── order/             ← 可继续嵌套，层级不限；子目录名不得使用保留目录名
        │       ├── order_basic.xml
        │       └── refund/
        │           └── refund_apply.xml
        ├── model/                 ← 模型 XML
        │   └── model.xml
        ├── fun/                   ← 代码工程（run 关键字）
        │   └── data_gen/
        │       └── gen_phone.py
        ├── data/                  ← 测试数据 + 全局变量
        │   ├── globalvalue.xml    ← 全局变量（固定文件名）
        │   └── data.sqlite        ← 所有测试数据表（唯一数据文件）
        ├── plan/                  ← 测试计划 XML
        │   ├── project_full.xml
        │   └── *_smoke.xml
        ├── business/              ← 业务模型 XML（v11.4，可选；使用 business_call 时需要）
        │   └── business.xml
        ├── perf/                  ← 压测预编译产物（v8.0，kind=load 计划自动生成）
        │   └── api_load_basic.py
        ├── knowledge/             ← 漫游测试地图（v8.3，首次写入时自动生成）
        │   ├── test_map.json
        │   └── test_map.json.lock
        └── result/                ← 测试结果（框架自动生成）
            └── result_20260321_100000.xml
```

标准模块布局使用 `case/`、`model/`、`fun/`、`data/`、`plan/`、`result/` 这 6 个固定目录名，但当前目录合规硬检查只要求 `case/`、`model/`、`data/`。`fun/` 在使用 `run` 工程时需要，`plan/` 在按计划执行时需要，`result/` 由框架生成。`perf/`、`knowledge/` 与 `business/` 都按功能需要出现（`business/` 见[第 17 章](#17-业务模型business-modelv1140)）；`knowledge/` 不需要手工创建，也不参与 `REQUIRED_MODULE_DIRS` 检查。

`case/` 支持**任意多级子目录**（v11.5.0 起）：执行、解析、`plan`、`dry-run`、`rodski case lint` 都会**递归**查找 `case/**/*.xml`，不再假设扁平一层。子目录名不得使用保留名（`case/model/fun/data/plan/result/business/perf/knowledge`），命名建议见 [§2.3](#23-推荐命名规范v1150)。

### 2.1 XML 文件与目录映射

> 历史参考（已完成迁移）：早期版本使用单一文件格式，v3.0 起全面改用 XML 目录结构。

| 文件 | 位置 | 说明 |
|------|------|------|
| case/**/*.xml | `case/` 目录（支持任意多级子目录，v11.5.0 起） | 用例定义（三阶段容器 + test_step） |
| globalvalue.xml | `data/` 目录 | 全局变量 |
| data.sqlite | `data/` 目录 | 所有测试数据表（唯一数据文件） |
| plan/*.xml | `plan/` 目录 | 测试计划定义，每个文件一个计划 |
| result_*.xml | `result/` 目录 | 框架自动生成的测试结果 |
| model.xml | `model/` 目录 | 元素定位模型 |
| business/*.xml | `business/` 目录 | 业务模型：节点、条件边、业务流（v11.4，可选） |
| test_map.json | `knowledge/` 目录 | 漫游测试自动生成的知识地图；应用层校验 `schema_version=1`，无 XSD |

### 2.2 Schema 约束（与 `rodski/schemas` 对齐）

手工编写的 XML 建议用本仓库 XSD 做校验，约束以 XSD 为准；下面是与**用例编写**直接相关的摘要（完整定义见各文件内 `<xs:annotation>`）。

| XSD 文件 | 根元素 | 编写方 | 核心约束（摘要） |
|----------|--------|--------|------------------|
| `case.xsd` | `<cases>` | 人工 | 每个 `<case>` **必须且仅有 1 个** `<test_case>` 容器，其内 **至少 1 个**执行项；执行项可为裸 `<test_step>`，v6.3.0 起也可为 `<scenario>` 容器。`<pre_process>` / `<post_process>` 各 **0～1 个**容器，内为 **0～n 个** `<test_step>`。`execute` 与 `roam` 都只能是 `是` \| `否`，`roam` 默认 `否`。`component_type`（可选）只能是 `界面` \| `接口` \| `数据库`；`roam="是"` 仅允许 `component_type` 为空或为 `界面`。每个 `test_step` 的 `action` 为 `ActionType` 枚举（见 [3.6](#36-action-与-casexsd-枚举一致)）。 |
| `model.xsd` | `<models>` | 人工 | `<model>` 须 `name`；`<element>` 须 `name`。仅支持**完整格式**（子节点 `<type>` / `<location>` / `<desc>`），~~简化格式已移除（v5.4.0）~~。`DriverType` / `LocatorType` 取值见 [4.2](#42-元素属性说明)、[4.3](#43-定位类型)。接口保留元素名：`_method`、`_url`、`_header_*`（与数据字段一一对应）。 |
| `data.xsd` | `<datatable>` / `<datatables>` | 人工 | 已废弃（v6.0.0）。测试数据统一存储在 `data.sqlite`，验证数据表名为 `{模型名}_verify`，`table_kind='verify'`。 |
| `globalvalue.xsd` | `<globalvalue>` | 人工 | 每个 `<group>` 须 `name`；**所有 group 的 `name` 全局唯一**。每组内至少一个 `<var>`，每个 `var` 须同时具备 `name` 与 `value`；**同一 group 内** `var@name` **唯一**（XSD `xs:unique`）。引用格式：`GlobalValue.组名.变量名`。 |
| `business.xsd` | `<business_models>` | 人工 | v11.4 业务模型。`business_model` 须 `id`/`name`/`version`，内含 `nodes`/`edges`/`flows`；`flow@type` 只能是 `basic` \| `alternative` \| `exception` \| `boundary`。Case 中用 `<business_call ref flow input expect>` 引用（四个属性均必填）。详见 [第 17 章](#17-业务模型business-modelv1140)。 |
| `result.xsd` | `<testresult>` | **框架生成** | 手工一般无需编写；结构见 [附录：测试结果 XML](#附录测试结果-xmlresultxsd)。 |

本地校验示例（需安装 `xmllint`，Mac 可用 Xcode 命令行工具）：

```bash
xmllint --noout --schema rodski/schemas/case.xsd product/DEMO/demo_site/case/demo_case.xml
```

### 2.3 推荐命名规范（v11.5.0）

`case/` 支持多级嵌套后，目录与文件命名不再强制，但推荐遵循以下规范（不强制，`rodski case lint` 会对违反项给 WARNING）：

**原则**：目录表达"测什么"（业务结构）；`tag` / `priority` / `plan` 表达"怎么跑"。不要建 `smoke/`、`p0/` 这类目录，测试类型用 `tag` 表达。模块 ≠ 目录：共用同一套 `model.xml` / `data.sqlite` 的用例放同一模块内用子目录组织；页面或接口集合明显独立时应拆模块（`model.xml` 规模过大时，拆模块是唯一的扩容手段，见 §4）。

推荐目录结构：

```
case/
├── {业务域}/                     ← 如 order、payment、user
│   ├── {功能}/                   ← 如 refund、checkout
│   │   ├── {子功能}/             ← 按需继续嵌套，层级不限
│   │   └── {功能}_{关注点}.xml
│   └── README.md                ← 可选：该目录的中文说明
```

| 对象 | 规范 | 示例 |
|------|------|------|
| 目录名 | 小写 ASCII + 下划线，正则 `^[a-z][a-z0-9_]*$`；中文语义写在 `case@title` 和目录 README 中 | `order`、`refund` |
| 用例文件名 | `{功能}_{关注点}.xml`，`snake_case`，正则 `^[a-z][a-z0-9_]*\.xml$`；关注点常用词 `basic / boundary / negative / flow / api / db / ui`；文件名不带测试类型（不写 `_smoke`）；一个文件推荐 1–20 个用例 | `refund_apply.xml`、`refund_boundary.xml` |
| 用例 ID | ID 只需**文件内唯一**（见 [§3.2.1](#321-用例-id-唯一性v11500)），沿用"有规律编号" `TC001`、`TC002`… 文件内递增；需要跨文件检索时可选 `{功能缩写}_{序号}`，如 `REFUND_001`；已发布的 ID 不复用 | `TC001` |
| data_id | 同一逻辑表被多个目录的用例共用时，推荐 `{功能缩写}_{用例ID}[_{序号}]`；共用数据用 `COMMON_{含义}` | `REFUND_TC001`、`COMMON_ADMIN_LOGIN` |

**`rodski case lint <module>`**（v11.5.0 新增）：

| 检查项 | 级别 |
|--------|------|
| 同一文件内用例 ID 重复 | ERROR |
| 子目录使用保留名 | ERROR |
| plan 中的 stale 引用（文件 / ID / 目录不存在） | WARNING |
| 目录 / 文件名不符合 snake_case | WARNING |
| 单文件用例数 > 30 | WARNING |
| 跨文件同 ID | INFO（合法，只提示） |

---
