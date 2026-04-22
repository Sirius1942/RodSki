# RodSki 数据文件组织规则

## 数据目录结构

```
project/
├── case/           # 测试用例 XML
├── model/          # 页面模型 XML
├── data/           # 测试数据
│   ├── data.xml           # 所有输入数据表（必须，唯一 XML 输入文件）
│   ├── data_verify.xml    # 所有验证数据表（verify 关键字使用，可选）
│   ├── globalvalue.xml    # 全局变量（独立）
│   └── testdata.sqlite    # SQLite 测试数据主存储（可选，推荐）
├── fun/            # 自定义函数
└── result/         # 测试结果
```

## 加载规则

框架固定识别以下数据文件：

1. 输入数据（type/send/DB 关键字使用）→ `data.xml`
2. 验证数据（verify 关键字使用）→ `data_verify.xml`
3. 全局变量 → `globalvalue.xml`
4. SQLite 测试数据 → `testdata.sqlite`
5. `data/` 目录下的其他 XML 文件不会被框架读取

## 共存与优先策略

- XML 与 SQLite 可以在同一测试模块中共存
- **混合模式受支持，但不推荐作为常态方案**
- 新建或持续演进的测试数据，默认应优先进入 `testdata.sqlite`
- `data.xml` 仍然是唯一 XML 输入数据文件，不支持拆分为多个 XML 数据表文件
- 采用 SQLite 后，`data.xml` / `data_verify.xml` 主要承担兼容旧表或补充性小表的职责
- 同一逻辑表不能同时存在于 XML 与 SQLite；若跨源同名，运行时与 `rodski data validate` 都必须报错

## 数据文件规则

### 1. 数据表文件：data.xml（必须）

**规则：** 所有输入数据表必须合并到一个 `data.xml` 文件中；即使模块引入 SQLite，`data.xml` 仍然保持这一单文件约束。

**格式：**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<datatables>
    <datatable name="Login">
        <row id="L001">
            <field name="username">admin</field>
            <field name="password">123456</field>
        </row>
    </datatable>

    <datatable name="Product">
        <row id="P001">
            <field name="productName">iPhone 15</field>
            <field name="price">5999</field>
        </row>
    </datatable>
</datatables>
```

### 2. 验证数据表文件：data_verify.xml（可选）

**规则：** 所有验证数据表放入 `data_verify.xml`，供 `verify` 关键字使用

**格式：**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<datatables>
    <datatable name="Login_verify">
        <row id="V001">
            <field name="welcomeMsg">欢迎, admin</field>
        </row>
    </datatable>

    <datatable name="LoginAPI_verify">
        <row id="V001">
            <field name="status">200</field>
            <field name="username">admin</field>
        </row>
    </datatable>
</datatables>
```

**说明：** 验证数据也可以放在 `data.xml` 中；若两个文件中存在同名表，`data_verify.xml` 中的表会覆盖 `data.xml` 中的同名表。

> 上述覆盖规则只适用于 **XML 内部**（`data.xml` 与 `data_verify.xml`）。如果同名逻辑表同时出现在 XML 和 `testdata.sqlite` 中，则视为**跨源冲突**，必须报错，不能覆盖。

### 3. SQLite 测试数据文件：testdata.sqlite（可选，推荐）

**规则：** `testdata.sqlite` 是测试数据的推荐主存储文件名，固定放在 `data/` 目录下。

**约束：**
- 同一逻辑表只能由 XML 或 SQLite 其中一种来源拥有
- SQLite 中的同一逻辑表必须有显式 schema，且所有数据行字段集合完全一致
- 采用 SQLite 后，建议新逻辑表优先进入 SQLite，而不是继续扩张 XML
- `globalvalue.xml` 不进入 SQLite，仍独立维护

### 4. 全局变量文件：globalvalue.xml（独立）

**规则：** 全局变量保持独立的 XML 文件

**格式：**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<globalvalue>
    <group name="DefaultValue">
        <var name="WaitTime" value="500"/>
    </group>
    <group name="demo_db">
        <var name="type" value="sqlite"/>
        <var name="database" value="demo.db"/>
    </group>
</globalvalue>
```

