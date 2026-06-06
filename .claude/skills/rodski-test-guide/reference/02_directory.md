<!-- 自动生成 from rodski/docs/TEST_CASE_WRITING_GUIDE.md  请勿手工编辑 -->

## 2. 目录结构

v3.0+ 版本使用固定目录结构组织测试模块：

- `data.sqlite` 是唯一测试数据文件

```
product/                           ← 产品根目录（最顶层）
└── {测试项目名}/                   ← 测试项目
    └── {测试模块名}/               ← 测试模块（业务）
        ├── case/                  ← 测试用例 XML
        │   └── demo_case.xml
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
        └── result/                ← 测试结果（框架自动生成）
            └── result_20260321_100000.xml
```

### 2.1 XML 文件与目录映射

> 历史参考（已完成迁移）：早期版本使用单一文件格式，v3.0 起全面改用 XML 目录结构。

| 文件 | 位置 | 说明 |
|------|------|------|
| case/*.xml | `case/` 目录 | 用例定义（三阶段容器 + test_step） |
| globalvalue.xml | `data/` 目录 | 全局变量 |
| data.sqlite | `data/` 目录 | 所有测试数据表（唯一数据文件） |
| plan/*.xml | `plan/` 目录 | 测试计划定义，每个文件一个计划 |
| result_*.xml | `result/` 目录 | 框架自动生成的测试结果 |
| model.xml | `model/` 目录 | 元素定位模型 |

### 2.2 Schema 约束（与 `rodski/schemas` 对齐）

手工编写的 XML 建议用本仓库 XSD 做校验，约束以 XSD 为准；下面是与**用例编写**直接相关的摘要（完整定义见各文件内 `<xs:annotation>`）。

| XSD 文件 | 根元素 | 编写方 | 核心约束（摘要） |
|----------|--------|--------|------------------|
| `case.xsd` | `<cases>` | 人工 | 每个 `<case>` **必须且仅有 1 个** `<test_case>` 容器，其内 **至少 1 个**执行项；执行项可为裸 `<test_step>`，v6.3.0 起也可为 `<scenario>` 容器。`<pre_process>` / `<post_process>` 各 **0～1 个**容器，内为 **0～n 个** `<test_step>`。`execute` 只能是 `是` \| `否`。`component_type`（可选）只能是 `界面` \| `接口` \| `数据库`。每个 `test_step` 的 `action` 为 `ActionType` 枚举（见 [3.6](#36-action-与-casexsd-枚举一致)）。 |
| `model.xsd` | `<models>` | 人工 | `<model>` 须 `name`；`<element>` 须 `name`。仅支持**完整格式**（子节点 `<type>` / `<location>` / `<desc>`），~~简化格式已移除（v5.4.0）~~。`DriverType` / `LocatorType` 取值见 [4.2](#42-元素属性说明)、[4.3](#43-定位类型)。接口保留元素名：`_method`、`_url`、`_header_*`（与数据字段一一对应）。 |
| `data.xsd` | `<datatable>` / `<datatables>` | 人工 | 已废弃（v6.0.0）。测试数据统一存储在 `data.sqlite`，验证数据表名为 `{模型名}_verify`，`table_kind='verify'`。 |
| `globalvalue.xsd` | `<globalvalue>` | 人工 | 每个 `<group>` 须 `name`；**所有 group 的 `name` 全局唯一**。每组内至少一个 `<var>`，每个 `var` 须同时具备 `name` 与 `value`；**同一 group 内** `var@name` **唯一**（XSD `xs:unique`）。引用格式：`GlobalValue.组名.变量名`。 |
| `result.xsd` | `<testresult>` | **框架生成** | 手工一般无需编写；结构见 [附录：测试结果 XML](#附录测试结果-xmlresultxsd)。 |

本地校验示例（需安装 `xmllint`，Mac 可用 Xcode 命令行工具）：

```bash
xmllint --noout --schema rodski/schemas/case.xsd product/DEMO/demo_site/case/demo_case.xml
```

---
