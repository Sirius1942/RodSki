# RodSki 数据文件组织规则

## 数据目录结构

```
project/
├── case/           # 测试用例 XML
├── model/          # 页面模型 XML
├── data/           # 测试数据
│   ├── data.sqlite        # 唯一测试数据文件（必须）
│   └── globalvalue.xml    # 全局变量（独立）
├── plan/           # 测试计划 XML（执行配置，不是测试数据）
├── fun/            # 自定义函数
└── result/         # 测试结果
```

## 加载规则

框架固定识别以下数据文件：

1. 测试数据 → `data.sqlite`（唯一数据源）
2. 全局变量 → `globalvalue.xml`
3. `data/` 目录下的其他文件不会被框架读取

`plan/` 是与 `data/` 同级的执行配置目录。测试计划 XML 只描述 case/scenario/step 的执行选择，不属于测试数据，不会写入或读取 `data.sqlite`。

**v6.0.0 破坏性变更**：`data.xml` 和 `data_verify.xml` 已废弃。若这两个文件存在，运行时将报错并提示执行迁移命令。

## 数据迁移

如果项目中存在 `data.xml` / `data_verify.xml`，执行以下命令一次性迁移：

```bash
rodski data import <module>          # 默认跳过已存在的表
rodski data import <module> --overwrite  # 覆盖已存在的表
```

迁移完成后删除 `data.xml` 和 `data_verify.xml`。

## SQLite 测试数据文件：data.sqlite

**规则：**
- `data.sqlite` 是 `data/` 目录下唯一固定的测试数据文件
- 同一 `data/` 目录下的所有测试数据统一保存在这个文件中
- 其他 SQLite 文件（如 `other.sqlite`）不会被框架读取

**约束：**
- SQLite 中的同一逻辑表必须有显式 schema，且所有数据行字段集合完全一致
- `globalvalue.xml` 不进入 SQLite，仍独立维护

**初始化：**

```bash
rodski init <target>          # 默认创建 data.sqlite
rodski init <target> --no-sqlite  # 不创建 data.sqlite（不推荐）
```

## 全局变量文件：globalvalue.xml（独立）

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
