# RodSki 数据文件组织规则

## 数据目录结构

```
project/
├── case/           # 测试用例 XML
├── model/          # 页面模型 XML
├── data/           # 测试数据
│   ├── data.xml           # 所有数据表（必须）
│   └── globalvalue.xml    # 全局变量（独立）
├── fun/            # 自定义函数
└── result/         # 测试结果
```

## 数据文件规则

### 1. 数据表文件：data.xml（必须）

**规则：** 所有数据表必须合并到一个 `data.xml` 文件中

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

### 2. 全局变量文件：globalvalue.xml（独立）

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

