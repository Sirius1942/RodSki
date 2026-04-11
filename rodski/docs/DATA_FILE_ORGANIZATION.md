# RodSki 数据文件组织规则

## 数据目录结构

```
project/
├── case/           # 测试用例 XML
├── model/          # 页面模型 XML
├── data/           # 测试数据
│   ├── data.xml           # 所有输入数据表（必须）
│   ├── data_verify.xml    # 所有验证数据表（verify 关键字使用，可选）
│   └── globalvalue.xml    # 全局变量（独立）
├── fun/            # 自定义函数
└── result/         # 测试结果
```

## 加载规则

框架只加载以上三个固定文件名，不扫描目录下其他 XML 文件。

1. 输入数据（type/send/DB 关键字使用）→ 全部放入 `data.xml`
2. 验证数据（verify 关键字使用）→ 全部放入 `data_verify.xml`
3. 全局变量 → `globalvalue.xml`
4. `data/` 目录下的其他 XML 文件不会被框架读取

## 数据文件规则

### 1. 数据表文件：data.xml（必须）

**规则：** 所有输入数据表必须合并到一个 `data.xml` 文件中

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

### 3. 全局变量文件：globalvalue.xml（独立）

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

