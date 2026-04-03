# 2. 目录结构

> **来源**: RodSki 测试用例编写指南 v3.4  
> 本文档为独立章节，完整指南请见 [TEST_CASE_WRITING_GUIDE.md](../TEST_CASE_WRITING_GUIDE.md)

---


v3.0 版本使用 XML 文件替代 Excel，每个测试模块按如下固定结构组织：

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
        ├── data/                  ← 数据 XML + 全局变量
        │   ├── globalvalue.xml    ← 全局变量（固定文件名）
        │   ├── Login.xml          ← 数据表（与模型同名）
        │   ├── Login_verify.xml   ← 验证数据表
        │   └── QuerySQL.xml       ← SQL 数据表
        └── result/                ← 测试结果（框架自动生成）
            └── result_20260321_100000.xml
```

### 2.1 原 Excel 到 XML 的映射

| 原 Excel | 新 XML | 位置 |
|---------|--------|------|
| Case Sheet | case/*.xml | `case/` 目录 |
| GlobalValue Sheet | globalvalue.xml | `data/` 目录 |
| 数据表 Sheet（如 Login） | {模型名}.xml | `data/` 目录 |
| 验证数据表 Sheet（如 Login_verify） | {模型名}_verify.xml | `data/` 目录 |
| TestResult Sheet | result_*.xml | `result/` 目录 |
| model.xml | model.xml（不变） | `model/` 目录 |

### 2.2 Schema 约束（与 `rodski/schemas` 对齐）

手工编写的 XML 建议用本仓库 XSD 做校验，约束以 XSD 为准；下面是与**用例编写**直接相关的摘要（完整定义见各文件内 `<xs:annotation>`）。

| XSD 文件 | 根元素 | 编写方 | 核心约束（摘要） |
|----------|--------|--------|------------------|
| `case.xsd` | `<cases>` | 人工 | 每个 `<case>` **必须且仅有 1 个** `<test_case>` 容器，其内 **至少 1 个** `<test_step>`；`<pre_process>` / `<post_process>` 各 **0～1 个**容器，内为 **0～n 个** `<test_step>`。`execute` 只能是 `是` \| `否`。`component_type`（可选）只能是 `界面` \| `接口` \| `数据库`。每个 `test_step` 的 `action` 为 `ActionType` 枚举（见 [3.5](#35-action-与-casexsd-枚举一致)）。 |
| `model.xsd` | `<models>` | 人工 | `<model>` 须 `name`；`<element>` 须 `name`。支持**完整格式**（子节点 `<type>` / `<location>` / `<desc>`）与**简化格式**（`element` 上 `type`+`value`，此时 `type` 为定位类型）。`DriverType` / `LocatorType` 取值见 [4.2](#42-元素属性说明)、[4.3](#43-定位类型)。接口保留元素名：`_method`、`_url`、`_header_*`（与数据字段一一对应）。 |
| `data.xsd` | `<datatable>` | 人工 | `datatable@name` **必须与文件名一致**（不含 `.xml`）。每个 `<row>` 须 `id`（DataID）；**同一数据表内** `row@id` **全局唯一**（XSD `xs:unique`）。每行至少一个 `<field>`，`field@name` 须与对应模型元素 `name` 一致。验证表文件名为 `{模型名}_verify.xml`。 |
| `globalvalue.xsd` | `<globalvalue>` | 人工 | 每个 `<group>` 须 `name`；**所有 group 的 `name` 全局唯一**。每组内至少一个 `<var>`，每个 `var` 须同时具备 `name` 与 `value`；**同一 group 内** `var@name` **唯一**（XSD `xs:unique`）。引用格式：`GlobalValue.组名.变量名`。 |
| `result.xsd` | `<testresult>` | **框架生成** | 手工一般无需编写；结构见 [附录：测试结果 XML](#附录测试结果-xmlresultxsd)。 |

本地校验示例（需安装 `xmllint`，Mac 可用 Xcode 命令行工具）：

```bash
xmllint --noout --schema rodski/schemas/case.xsd product/DEMO/demo_site/case/demo_case.xml
```

---

