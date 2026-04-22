# RodSki XML + SQLite 测试数据共存设计

**版本**: v1.0  
**日期**: 2026-04-21  
**状态**: 草案 - 待讨论

---

## 1. 背景

RodSki 当前测试数据以 XML 组织，核心约束已经比较明确：

- `type` / `send` / `DB` 的 `model` 指向逻辑数据表
- `verify` 自动查找 `{模型名}_verify`
- Case 中 `data` 只写 DataID，不写表名前缀
- 现有运行时通过 `DataTableParser.get_data(table_name, data_id)` 读取数据

当前 XML 数据组织存在三个现实问题：

1. **同一个逻辑数据表中，不同行的字段集合可能不一致**
2. **缺少方便的 CLI 来快速查看数据表、schema 和行数据**
3. **缺少标准化的测试项目初始化命令**
   - 用户通常需要手工创建测试项目/模块目录结构，手工准备 `case/`、`model/`、`fun/`、`data/`、`result/` 目录，以及基础文件，难以快速部署测试用例、数据表数据和执行脚本

随着测试数据量增加，仅靠 XML 维护会带来以下问题：

- 大表 diff/review 不友好
- 数据查询、筛选、定位问题效率低
- 难以建立稳定的“表结构”概念
- 难以做结构化校验与快速排查

因此需要引入 SQLite 作为 **RodSki 测试数据的推荐主存储方案**，并支持 XML 与 SQLite 在同一测试模块中共存。

但需要明确：

- **混合模式受支持，但不推荐作为常态方案**
- 当模块采用 SQLite 后，XML 更适合作为补充性数据载体，而不是主存储
- 新建或持续演进的数据表，默认应优先进入 SQLite

> 注意：这里讨论的是 **RodSki 测试数据存储**，不是 `DB` 关键字访问的业务数据库。

---

## 2. 设计目标

1. **保持 RodSki 现有 DSL 语义不变**
   - `type Login L001`
   - `verify Login V001`
   - `DB QuerySQL Q001`

2. **允许 XML 与 SQLite 共存，但混合模式仅兼容、不推荐**
   - 同一模块下可以同时存在 `data.xml` / `data_verify.xml` 和 `testdata.sqlite`
   - 新建测试数据默认优先使用 SQLite

3. **明确逻辑表归属**
   - 同一逻辑表不能在 XML 与 SQLite 中同时生效
   - 默认采用“冲突即报错”，不做静默覆盖

4. **在 SQLite 方案中禁止“同表不同行列不一致”**
   - 同一逻辑表必须有固定字段集合
   - 这是 SQLite 方案的强约束

5. **提供 CLI 支持快速查询、校验与项目初始化**
   - 数据侧：list / schema / show / query / validate
   - 项目侧：init

6. **尽量减少运行时改动范围**
   - 保持 `KeywordEngine`、`DataResolver` 的数据访问语义不变
   - 变化尽量收敛在数据加载/校验层与 CLI 层

---

## 3. 非目标

本设计 **不包含** 以下内容：

1. **不修改 Case XML / Model XML 语法**
2. **不新增测试关键字**
3. **不改变 `verify` 自动拼接 `_verify` 的规则**
4. **不把 `DB` 关键字的业务数据库与测试数据 SQLite 混用**
5. **V1 不将 `globalvalue.xml` SQLite 化**
   - `globalvalue.xml` 继续保持 XML 解析方式
6. **不支持同名逻辑表跨源静默 merge**
   - 尤其不支持字段级 merge 或行级 merge

---

## 4. 核心约束

### 4.1 逻辑表命名规则（强约束）

RodSki 的“数据表”是 **逻辑表**，不是 SQLite 物理表。

- 普通数据表名必须等于模型名
- verify 数据表名必须等于 `模型名 + _verify`

示例：

- `type Login L001` → 逻辑表 `Login`
- `send LoginAPI D001` → 逻辑表 `LoginAPI`
- `DB QuerySQL Q001` → 逻辑表 `QuerySQL`
- `verify Login V001` → 逻辑表 `Login_verify`

### 4.2 Case 的 `data` 仍然只写 DataID

用户写法保持不变：

```xml
<test_step action="type" model="Login" data="L001"/>
<test_step action="verify" model="Login" data="V001"/>
<test_step action="DB" model="QuerySQL" data="Q001"/>
```

### 4.3 同一逻辑表默认只能由一个数据源拥有

在同一测试模块中：

- XML 可以拥有 `Login`
- SQLite 可以拥有 `QuerySQL`
- XML 可以拥有 `Login_verify`
- SQLite 可以拥有 `OrderAPI_verify`

但如果同一个逻辑表（如 `Login`）同时出现在 XML 和 SQLite 中，则 **默认报错**。

### 4.4 XML 文件组织约束（补充）

即使引入 SQLite，XML 侧仍保持固定文件组织：

- `data.xml` 仍然是唯一的输入数据 XML 文件
- `data_verify.xml` 仍然是唯一的验证数据 XML 文件（可选）
- 不支持把 XML 数据再拆成多个业务表文件

设计意图是：

- XML 继续作为兼容路径与补充路径存在
- SQLite 成为推荐主路径
- 避免重新回到“多 XML 文件分散维护”的旧问题

### 4.5 SQLite 中同一逻辑表必须固定字段集合

这是本设计新增的核心约束：

> **同一逻辑表中的所有数据行，字段集合必须完全一致。**

也就是说：

- 不允许某些行少一列
- 不允许某些行多一列
- 不允许“这一行临时多一个参数字段”

### 4.6 固定字段集合不等于“必须覆盖模型全部字段”

固定字段集合是 **表级 schema**，它必须稳定，但不一定等于模型的全部元素集合。

示例：

- `Login` 模型可能有 `username/password/loginBtn/rememberMe`
- 某张逻辑表 `Login` 的 schema 可以定义为 `{username, password, loginBtn}`
- 只要这张表中的所有行都严格遵守这个字段集合即可

### 4.7 DB 逻辑表也受“固定字段集合”约束

数据库模型是特殊情况。

例如 `QuerySQL` 表可能使用：

- 模板模式：`query + 参数列`
- 原始 SQL 模式：`sql + operation`

SQLite 方案中，`QuerySQL` 也必须固定字段集合，因此：

- 不允许某些行是 `query + limit`
- 另一些行是 `query + order_no`
- 再另一些行是 `sql + operation`

如果同一逻辑表需要支持多种查询模板且参数不同，则应采用 **固定列集合 + 显式占位值** 的方式，例如使用 `NONE` / `NULL` / `BLANK` / 空字符串，而不是省略字段。

### 4.8 特殊控制值语义保持不变

SQLite 只负责存储字符串值，不改变以下值的执行语义：

- `BLANK`
- `NULL`
- `NONE`
- `click`
- `select【...】`
- `${Return[-1]}`
- `GlobalValue.xxx.yyy`

---

## 5. 总体方案

### 5.1 数据源共存模型

同一测试模块的数据目录扩展为：

```text
{module}/
├── case/
├── model/
├── fun/
├── data/
│   ├── data.xml
│   ├── data_verify.xml
│   ├── globalvalue.xml
│   └── testdata.sqlite      # 新增，可选
└── result/
```

其中：

- `data.xml` 仍然是唯一输入数据 XML 文件
- `data_verify.xml` 仍然是唯一验证数据 XML 文件（可选）
- `testdata.sqlite` 是推荐的主数据存储文件（可选）
- 当模块采用 SQLite 后，XML 文件主要用于兼容旧表或补充性少量数据

### 5.2 数据所有权模型

V1 采用 **逻辑表归属制**：

- 每个逻辑表只能属于一个数据源
- 跨源同名视为配置冲突
- 不做覆盖优先级、不做 merge

这种设计比“XML 优先”或“SQLite 优先”更符合 RodSki 的确定性原则，也更利于排查。

### 5.3 运行时统一访问抽象

执行引擎对上层仍然只看到：

```python
get_data(table_name, data_id)
```

即：

- `KeywordEngine` 不关心数据来自 XML 还是 SQLite
- `DataResolver` 不关心底层数据源
- 底层由统一数据管理器负责加载、索引、冲突检查与校验

### 5.4 项目初始化能力

除数据查询与校验外，CLI 还应提供测试项目初始化能力，用于在指定目录快速创建 RodSki 测试项目/测试模块骨架。

初始化后的项目应满足 RodSki 目录约束，至少包含：

```text
{module}/
├── case/
├── model/
├── fun/
├── data/
└── result/
```

并创建最基础的文件骨架：

- `model/model.xml`
- `data/data.xml`
- `data/globalvalue.xml`
- （可选）`data/data_verify.xml`
- （可选）`data/testdata.sqlite`

初始化的目标是：

- 用户可以直接把测试用例 XML 部署到 `case/`
- 把测试数据 XML 或 SQLite 数据部署到 `data/`
- 把 `run` 关键字依赖的脚本部署到 `fun/`
- 把执行结果输出到 `result/`

该能力与数据查询 CLI 一样，属于**工程初始化与辅助工具能力**，不是新增测试关键字。

---

## 6. SQLite 存储设计

### 6.1 设计原则

不采用“每个逻辑表一张 SQLite 物理表”的方案，原因如下：

1. 逻辑表数量动态增长，DDL 管理成本高
2. 与 XML 共存时不利于统一查询接口
3. 不利于实现统一 CLI
4. 不利于做跨表 schema 元数据与通用校验

因此采用 **固定元表 + 逻辑表索引** 的设计。

### 6.2 SQLite 文件命名

建议固定文件名：

```text
data/testdata.sqlite
```

使用 `.sqlite` 后缀是为了与业务数据库（如 `demo.db`）区分，减少误用风险。

### 6.3 元表设计

#### 6.3.1 逻辑表定义

```sql
CREATE TABLE rs_datatable (
    table_name TEXT PRIMARY KEY,
    model_name TEXT NOT NULL,
    table_kind TEXT NOT NULL CHECK (table_kind IN ('data', 'verify')),
    row_mode TEXT NOT NULL CHECK (row_mode IN ('standard', 'db_query', 'db_sql')),
    remark TEXT DEFAULT '',
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

字段说明：

- `table_name`: RodSki 逻辑表名，如 `Login`、`Login_verify`、`QuerySQL`
- `model_name`: 对应模型名，不含 `_verify`
- `table_kind`: `data` / `verify`
- `row_mode`:
  - `standard`: UI / interface 等普通表
  - `db_query`: DB 模板查询表（含 `query`）
  - `db_sql`: DB 原始 SQL 表（含 `sql`）

#### 6.3.2 逻辑表字段定义

```sql
CREATE TABLE rs_datatable_field (
    table_name TEXT NOT NULL,
    field_name TEXT NOT NULL,
    field_order INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (table_name, field_name),
    FOREIGN KEY (table_name) REFERENCES rs_datatable(table_name)
);
```

这张表用于显式声明逻辑表 schema，是“固定字段集合”的正式定义。

#### 6.3.3 数据行定义

```sql
CREATE TABLE rs_row (
    table_name TEXT NOT NULL,
    data_id TEXT NOT NULL,
    remark TEXT DEFAULT '',
    PRIMARY KEY (table_name, data_id),
    FOREIGN KEY (table_name) REFERENCES rs_datatable(table_name)
);
```

#### 6.3.4 字段值定义

```sql
CREATE TABLE rs_field (
    table_name TEXT NOT NULL,
    data_id TEXT NOT NULL,
    field_name TEXT NOT NULL,
    field_value TEXT NOT NULL,
    PRIMARY KEY (table_name, data_id, field_name),
    FOREIGN KEY (table_name, data_id) REFERENCES rs_row(table_name, data_id),
    FOREIGN KEY (table_name, field_name) REFERENCES rs_datatable_field(table_name, field_name)
);
```

### 6.4 为什么必须显式 schema

SQLite 虽然可以通过查询数据本身“推断字段集合”，但 RodSki 需要的是 **稳定契约**，不是运行时猜测。

因此 V1 明确要求：

> **SQLite 逻辑表必须显式声明 schema，运行时和 CLI 都以 schema 为准。**

好处：

1. 能明确判断“缺列 / 多列”
2. CLI 能稳定输出 `schema`
3. 能在导入 XML → SQLite 时做硬校验
4. 有利于后续导出、比对、迁移

---

## 7. 逻辑表字段规则

### 7.1 standard 模式

适用于 UI / interface 等普通逻辑表。

规则：

- 逻辑表 schema 是固定字段集合
- 所有行必须完整拥有这组字段
- 字段名必须满足对应模型的可用字段约束

注意：这里的固定字段集合可以是模型字段的 **子集**，不要求必须覆盖模型全部元素。

### 7.2 db_query 模式

适用于数据库模型的“查询模板 + 参数”模式。

规则：

- schema 中必须包含 `query`
- 其余字段为该逻辑表允许的参数列
- 同一逻辑表内所有行必须共享同一组参数列
- 不允许有的行缺少某个参数列

示例：

```text
QuerySQL schema = {query, limit, order_no}
```

其中：

- `Q001`: `query=list, limit=5, order_no=NONE`
- `Q002`: `query=get_by_id, limit=NONE, order_no=ORD001`

允许，因为列集合一致；
不允许某行直接缺 `limit` 列或缺 `order_no` 列。

### 7.3 db_sql 模式

适用于数据库模型的“原始 SQL”模式。

规则：

- schema 中必须包含 `sql`
- 可选包含 `operation`
- 同一逻辑表内所有行必须共享相同字段集合
- 不允许部分行使用 `query` 模式、部分行使用 `sql` 模式

---

## 8. XML + SQLite 共存规则

### 8.1 合法共存

以下情况是允许的：

- XML 中有 `Login`
- SQLite 中有 `QuerySQL`
- XML 中有 `Login_verify`
- SQLite 中有 `OrderAPI_verify`

即：**不同逻辑表可以分散在不同数据源中。**

但需要强调：

- XML + SQLite 混合模式是**兼容能力**，不是推荐主模式
- 新建数据表、长期维护的数据表默认优先进入 SQLite
- XML 更适合作为历史遗留表或补充性表的承载路径

### 8.2 非法共存（默认报错）

如果同一个逻辑表同时出现在 XML 与 SQLite 中，则视为配置冲突。

示例：

- XML: `Login`
- SQLite: `Login`

运行时与 CLI `validate` 都应报错。

### 8.3 V1 不支持的策略

V1 明确 **不支持**：

1. XML 优先覆盖 SQLite
2. SQLite 优先覆盖 XML
3. 跨源行级 merge
4. 跨源字段级 merge

原因：

- 与“确定性测试执行引擎”定位相冲突
- 会让数据来源变得难以解释
- CLI 与运行时行为会更难对齐

---

## 9. 列一致性校验规则

### 9.1 SQLite 硬校验

对 SQLite 逻辑表，必须执行以下硬校验：

1. `rs_datatable` 中存在对应逻辑表定义
2. `rs_datatable_field` 中定义了 schema
3. 每个 `data_id` 的字段集合必须等于 schema
4. 不允许缺字段
5. 不允许多字段
6. 不允许未声明字段进入 `rs_field`

### 9.2 XML 兼容策略

当前 XML 历史数据可能存在“同表不同行列不一致”的情况。

因此 V1 采用以下兼容策略：

- **XML-only 运行模式**：保持当前兼容行为，不强制因旧 XML 脏数据而中断执行
- **SQLite 导入 / 共存 / validate 严格校验模式**：必须对目标逻辑表执行固定字段集合校验
- **混合模式**：允许 XML 与 SQLite 共存，但 XML 在此时仅建议承担补充性数据，不建议继续作为主存储扩张

这意味着：

- 旧 XML 项目不会因为 V1 立即全部跑不起来
- 但只要某逻辑表要进入 SQLite，或用户执行严格校验，就必须先修正不一致列问题
- 当模块已经采用 SQLite 后，新逻辑表应优先进入 SQLite，而不是继续堆积到 XML

### 9.3 显式占位值规则

为满足固定字段集合约束，不能通过“省略字段”表达“本行不用这个列”，必须使用显式值，例如：

- `NONE`
- `NULL`
- `BLANK`
- 空字符串

具体使用哪一种，仍然遵循各关键字现有语义。

---

## 10. 运行时架构设计

### 10.1 设计原则

尽量不改动执行链路，只扩展数据层。

### 10.2 建议改动文件

#### 保持主语义不变

- `rodski/core/keyword_engine.py`
  - 继续通过 `data_manager.get_data(table_name, data_id)` 取数
  - `verify` 继续自动拼接 `_verify`

- `rodski/data/data_resolver.py`
  - 继续通过 `data_manager.get_data(table_name, data_id).get(field)` 解析数据引用

#### 重点改动

- `rodski/core/data_table_parser.py`
  - 从“纯 XML parser”升级为统一数据管理器 facade
  - 内部负责加载 XML / SQLite、建立逻辑表索引、做冲突检测

- 新增建议模块：`rodski/core/data_schema_validator.py`
  - 负责 SQLite schema 校验
  - 负责列一致性校验
  - 负责逻辑表命名规则校验

- 新增建议模块：`rodski/core/sqlite_data_source.py`
  - 负责读取 `testdata.sqlite`

- `rodski/core/ski_executor.py`
  - 初始化数据管理器时注入 `model_parser`
  - 其余执行语义不变

### 10.3 加载流程

建议流程如下：

1. 解析 `model.xml`
2. 加载 XML 数据表（`data.xml` + `data_verify.xml`）
3. 如果存在 `data/testdata.sqlite`，加载 SQLite 逻辑表与 schema
4. 检查跨源同名逻辑表冲突
5. 校验 SQLite schema 与行数据一致性
6. 构造统一逻辑表索引
7. 对外暴露 `get_data(table_name, data_id)`

### 10.4 GlobalValue 边界

V1 不将 `globalvalue.xml` SQLite 化：

- `rodski/core/global_value_parser.py` 保持现状
- `DB` 关键字的业务连接配置仍然从 `globalvalue.xml` 读取
- 避免把测试数据 SQLite 与业务库连接配置混在一起

---

## 11. CLI 设计

### 11.1 目标

需要提供一组面向测试设计、调试、迁移和工程初始化的 CLI，帮助用户：

- 快速查看模块有哪些逻辑数据表
- 查看某张逻辑表的 schema
- 查看某条数据行
- 查询一张表的内容
- 校验跨源冲突与列一致性问题
- 快速初始化一个符合 RodSki 目录约束的测试项目/测试模块

### 11.2 新增子命令

建议新增：

```text
rodski data ...
rodski init ...
```

实现位置建议：

- 新文件：`rodski/rodski_cli/data.py`
- 新文件：`rodski/rodski_cli/init.py`
- 在 `rodski/cli_main.py` 中注册 `data` 与 `init` 子命令

### 11.3 数据命令清单

#### 11.3.1 list

列出模块中的逻辑数据表及来源：

```bash
rodski data list rodski-demo/
```

建议输出：

```text
数据目录: rodski-demo/data

表名             类型      来源      行数   字段数   模型
Login            data      xml       3      3       Login
Login_verify     verify    xml       2      1       Login
QuerySQL         data      sqlite    5      3       QuerySQL
```

#### 11.3.2 schema

查看某张逻辑表的 schema：

```bash
rodski data schema rodski-demo/ Login
```

建议输出：

```text
表: Login
模型: Login
类型: data
来源: xml
字段:
1. username
2. password
3. loginBtn
```

#### 11.3.3 show

查看某张逻辑表中的某一行：

```bash
rodski data show rodski-demo/ Login L001
```

建议输出：

```text
表: Login
DataID: L001
username = admin
password = admin123
loginBtn = click
```

#### 11.3.4 query

浏览一张逻辑表的数据：

```bash
rodski data query rodski-demo/ Login --limit 20
```

该命令用于快速“看表”，比手工打开 XML 或写 SQL 更方便。

#### 11.3.5 validate

执行结构校验：

```bash
rodski data validate rodski-demo/
```

校验内容：

1. 跨源同名逻辑表冲突
2. SQLite schema 是否完整
3. SQLite 行字段集合是否与 schema 完全一致
4. 逻辑表命名是否符合 RodSki 规则
5. 字段名是否符合逻辑表类型约束
6. XML 表是否存在“列漂移”（建议通过 `--strict` 显式启用严格检查）

建议输出：

```text
[OK] Login: schema 一致
[OK] QuerySQL: schema 一致
[FAIL] Login_verify: 与 SQLite 中同名逻辑表冲突
[FAIL] OrderQuery: 行 Q002 缺少字段 order_no
```

### 11.4 项目初始化命令

#### 11.4.1 init

初始化一个符合 RodSki 目录约束的测试项目/测试模块：

```bash
rodski init /path/to/project/MyTestModule
```

建议支持参数：

- `--with-verify`：同时创建 `data/data_verify.xml`
- `--with-sqlite`：同时创建 `data/testdata.sqlite`
- `--force`：目标目录为空或部分存在时允许覆盖模板文件（默认禁止覆盖已有内容）

初始化结果建议至少包含：

```text
MyTestModule/
├── case/
├── model/
│   └── model.xml
├── fun/
├── data/
│   ├── data.xml
│   ├── globalvalue.xml
│   ├── data_verify.xml      # --with-verify 时创建
│   └── testdata.sqlite      # --with-sqlite 时创建
└── result/
```

其中模板文件建议提供最小可运行骨架：

- `model/model.xml`：空 `<models>` 根节点或最小示例模型
- `data/data.xml`：空 `<datatables>` 根节点
- `data/globalvalue.xml`：至少包含 `DefaultValue` 组
- `data/data_verify.xml`：空 `<datatables>` 根节点（若启用）
- `data/testdata.sqlite`：初始化 SQLite 元表结构（若启用）

#### 11.4.2 init 的约束

1. `init` 只负责创建项目骨架与模板文件，不生成业务测试内容
2. `init` 不应破坏已有目录中的用户文件，除非显式传入 `--force`
3. `init` 创建的目录结构必须符合 RodSki 当前固定约束：`case/`、`model/`、`fun/`、`data/`、`result/`
4. 如果启用 `--with-sqlite`，则必须创建符合本设计的 SQLite 元表
5. `init` 生成的项目必须能够作为后续 `run` / `data` CLI 的合法输入目录

### 11.5 CLI 与运行时的关系

- CLI 是**辅助查询/校验/初始化工具**，不是新增关键字
- CLI 不改变 Case / Model / Data 三层关系
- CLI 不影响 `type/send/verify/DB` 的执行语义

---

## 12. 错误语义

建议定义以下错误语义（名称可后续再定）：

### 12.1 逻辑表冲突错误

触发条件：

- 同一逻辑表同时存在于 XML 与 SQLite

示例：

```text
逻辑表冲突: 'Login' 同时存在于 XML 和 SQLite，请保留单一来源。
```

### 12.2 SQLite schema 缺失错误

触发条件：

- `rs_datatable` 有表定义，但 `rs_datatable_field` 缺失 schema

### 12.3 列集合不一致错误

触发条件：

- 某行字段集合不等于逻辑表 schema

示例：

```text
数据表 'Login' 结构不一致: 行 'L002' 缺少字段 'loginBtn'
```

### 12.4 表命名错误

触发条件：

- `table_name` 不等于 `model_name`
- 或 verify 表名不等于 `model_name + _verify`

### 12.5 表类型错误

触发条件：

- `row_mode=standard` 的表使用了不允许的控制字段
- `row_mode=db_query` 未包含 `query`
- `row_mode=db_sql` 未包含 `sql`

---

## 13. 兼容性与迁移

### 13.1 纯 XML 项目

V1 保持当前可执行性：

- 现有 XML-only 项目无需立即迁移
- `KeywordEngine` / `DataResolver` 语义保持不变

### 13.2 SQLite 项目

如果模块启用了 `testdata.sqlite`，则 SQLite 逻辑表必须通过完整校验。

同时约定：

- SQLite 是推荐主存储
- `data.xml` / `data_verify.xml` 在此模式下主要承担兼容旧表或补充性小表的职责
- 不推荐在已经采用 SQLite 的模块中继续把新增主表长期写回 XML

### 13.3 XML → SQLite 迁移规则

迁移时必须先做 schema 归一化。

迁移步骤建议：

1. 用 `rodski data validate --strict` 检查 XML 表结构
2. 若同表不同行列不一致，先修复 XML
3. 为目标逻辑表定义显式 schema
4. 导入到 `testdata.sqlite`
5. 确保该逻辑表不再同时保留 XML 版本

---

## 14. XSD / 文档影响分析

### 14.1 XSD 影响

V1 **不修改** 以下 XSD：

- `case.xsd`
- `model.xsd`
- `data.xsd`
- `globalvalue.xsd`

原因：

- Case / Model / Data 的 XML 语法没有变化
- SQLite 是新增运行时数据源，不是 XML 语法扩展

### 14.2 文档影响

需要更新的不是 XSD，而是“数据组织规则”文档、CLI 文档和工程初始化说明，说明：

- `data/testdata.sqlite` 成为可选固定文件名
- XML 与 SQLite 可共存
- 混合模式受支持，但不推荐作为常态
- `data.xml` 仍然是唯一 XML 输入数据文件，采用 SQLite 后应视为补充路径
- 同名逻辑表默认冲突报错
- SQLite 逻辑表必须固定字段集合
- 新建测试数据优先进入 SQLite
- 新增 `rodski data` CLI
- 新增 `rodski init` CLI，用于创建符合 RodSki 约束的测试项目骨架
- `rodski/docs/CORE_DESIGN_CONSTRAINTS.md` 需要同步成为上述约束的规范落点

---

## 15. 与现有约束对齐检查

### 15.1 不新增测试关键字

符合。V1 只新增 CLI，不新增执行关键字。

### 15.2 `verify` 自动推导 `_verify`

符合。运行时语义保持不变。

### 15.3 Case / Model / Data 三层分离

符合。SQLite 只是 Data 层的另一种承载方式。

### 15.4 `DB` 关键字职责

符合。业务数据库连接与测试数据 SQLite 严格分离。

### 15.5 目录结构约束

符合。仍然在 `data/` 目录下工作，只是新增一个可选文件 `testdata.sqlite`。

### 15.6 XML Schema 约束

符合。若 XML 文件存在，仍然按原有 XSD 校验；SQLite 走独立运行时校验。

### 15.7 模型与数据关系

符合。逻辑表名仍然受模型名约束，verify 表仍然受 `_verify` 规则约束。

---

## 16. 验收建议

### 16.1 正向场景

1. **XML-only**
   - 无 SQLite 文件
   - 用例正常运行

2. **SQLite-only**
   - XML 中无目标逻辑表
   - `testdata.sqlite` 提供目标逻辑表
   - 用例正常运行

3. **XML + SQLite 共存但无冲突**
   - `Login` 来自 XML
   - `QuerySQL` 来自 SQLite
   - 用例正常运行

4. **CLI schema/show/query 可用**
   - `rodski data schema`
   - `rodski data show`
   - `rodski data query`

5. **CLI init 可创建标准项目骨架**
   - `rodski init /path/to/MyTestModule`
   - 自动创建 `case/`、`model/`、`fun/`、`data/`、`result/`
   - 后续可直接部署测试用例、数据表数据和执行脚本

6. **CLI init --with-sqlite 可创建 SQLite 元表**
   - `rodski init /path/to/MyTestModule --with-sqlite`
   - 自动创建 `data/testdata.sqlite`
   - 后续可直接写入逻辑表 schema 和数据

### 16.2 反向场景

1. **同名逻辑表跨源冲突**
   - XML 与 SQLite 同时定义 `Login`
   - 应报错

2. **SQLite 同表不同行列不一致**
   - `Login.L001` 有 3 列
   - `Login.L002` 只有 2 列
   - 应报错

3. **DB 表混用不同 row_mode**
   - 同一 `QuerySQL` 表中混用 `query` 模式和 `sql` 模式
   - 应报错

4. **逻辑表命名不符合规则**
   - verify 表未使用 `_verify`
   - 应报错

---

## 17. 结论

V1 设计的核心原则是：

1. **保留 RodSki 现有 DSL 语义**
2. **允许 XML 与 SQLite 共存，但按逻辑表归属，不做静默覆盖**
3. **混合模式只作为兼容能力保留，推荐 SQLite 成为新数据的主存储**
4. **保留单一 `data.xml` / `data_verify.xml` 组织，XML 在 SQLite 模块中作为补充来源存在**
5. **将“同表固定字段集合”作为 SQLite 方案的强约束**
6. **通过 CLI 提供可观测性、初始化能力与快速排查能力**

这套方案可以在不破坏现有执行模型的前提下，为 RodSki 增加更稳定、可查询、可校验的测试数据存储能力。