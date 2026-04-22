# Data 目录说明

## 文件组织

`data/` 目录包含测试数据、全局配置，以及可选的 SQLite 测试数据文件：

```
data/
├── data.xml          # 输入/执行数据（必需）
├── data_verify.xml   # 验证数据（可选）
├── globalvalue.xml   # 全局变量配置（必需）
├── data.sqlite       # SQLite 测试数据（可选，固定文件名）
├── DB_USAGE.md       # 数据库/SQLite 使用说明
└── README.md         # 本文件
```

## 文件说明

### data.xml / data_verify.xml

- `data.xml`：普通输入数据，逻辑表名必须与模型名强一致
- `data_verify.xml`：验证数据，逻辑表名必须为 `{模型名}_verify`
- Case 中 `data` 只写 DataID，例如 `L001` / `V001`

### globalvalue.xml

全局变量配置文件，包含：
- 数据库连接配置（如 `demo_db`）
- 环境变量
- 共享配置

### data.sqlite

`data/data.sqlite` 是 demo 中唯一允许自动加载的 SQLite 测试数据文件。当前用于承载 `RegisterAPI` 逻辑表，演示 XML + SQLite 共存：

- XML 继续承载 `LoginAPI`、`QuerySQL` 等历史表
- SQLite 承载 `RegisterAPI`
- 同名逻辑表不能同时出现在 XML 与 SQLite 中，否则运行时和 `rodski data validate --strict` 都会报错

## 使用方式

### 在测试用例中引用数据

```xml
<!-- 引用 XML 数据 -->
<test_step action="type" model="LoginForm" data="L001"/>

<!-- 引用验证数据 -->
<test_step action="verify" model="LoginForm" data="V001"/>

<!-- 引用 SQLite 数据：表名仍然等于模型名 -->
<test_step action="send" model="RegisterAPI" data="L001"/>
```

### 查看 SQLite 数据

```bash
rodski data list rodski-demo/DEMO/demo_full/
rodski data schema rodski-demo/DEMO/demo_full/ RegisterAPI
rodski data show rodski-demo/DEMO/demo_full/ RegisterAPI L001
rodski data validate rodski-demo/DEMO/demo_full/ --strict
```

## 维护规范

1. `data.xml` 仍然是唯一输入 XML 文件，`data_verify.xml` 仍然是唯一验证 XML 文件
2. SQLite 测试数据固定保存在 `data/data.sqlite`，不要再创建 `testdata.sqlite` 等别名
3. 数据表名必须与模型名强一致；验证表必须使用 `_verify` 后缀
4. Case 的 `data` 只写 DataID，不写 `表名.DataID`
5. SQLite 与 XML 不能同时拥有同名逻辑表

## 相关文档

- `DB_USAGE.md` - 数据库关键字与 SQLite 使用说明
- `../model/model.xml` - 模型定义
- `../case/tc030_sqlite_data.xml` - SQLite 数据源示例
