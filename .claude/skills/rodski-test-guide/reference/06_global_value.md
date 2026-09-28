<!-- 自动生成 from rodski/docs/TEST_CASE_WRITING_GUIDE.md  请勿手工编辑 -->

## 6. GlobalValue XML — 全局变量

### 6.1 文件格式

全局变量文件固定命名为 `globalvalue.xml`，存放在 `data/` 目录下。

**与 `globalvalue.xsd` 一致**：全文件内 **`<group name="...">` 不得重名**；同一 `<group>` 内 **`<var name="...">` 不得重名**；每个 `<var>` 必须同时有 `name` 与 `value` 属性。

```xml
<?xml version="1.0" encoding="UTF-8"?>
<globalvalue>
  <group name="DefaultValue">
    <var name="URL" value="http://127.0.0.1:5555"/>
    <var name="BrowserType" value="chromium"/>
    <var name="WaitTime" value="2"/>
  </group>
  <group name="sqlite_db">
    <var name="type" value="sqlite"/>
    <var name="database" value="product/DEMO/demo_site/demo.db"/>
  </group>
  <group name="Roam">
    <var name="Enabled" value="否"/>
    <var name="MaxVariantsPerCase" value="5"/>
    <var name="MaxDurationSeconds" value="120"/>
    <var name="MinConfidenceToAct" value="0.6"/>
    <var name="MaxTokenBudget" value="20000"/>
    <var name="MaxCostUsd" value="0.5"/>
  </group>
</globalvalue>
```

### 6.2 引用语法

```
GlobalValue.组名.变量名
```

示例：

```
GlobalValue.DefaultValue.URL          → "http://127.0.0.1:5555"
GlobalValue.DefaultValue.WaitTime     → "2"
```

### 6.3 框架内置全局变量

| 组名 | Key | 说明 | 示例值 |
|------|-----|------|--------|
| DefaultValue | URL | 测试环境地址 | http://127.0.0.1:5555 |
| DefaultValue | BrowserType | 浏览器类型 | chromium / firefox / webkit |
| DefaultValue | WaitTime | 每步执行后自动等待秒数 | 2 |
| DefaultValue | Headless | 无头模式 | True / False |
| Roam | Enabled | 漫游全局开关；只有 `是` 才允许显式漫游 | 是 / 否 |
| Roam | MaxVariantsPerCase | 单个基础用例最多执行的漫游变体数 | 5 |
| Roam | MaxDurationSeconds | 单个漫游会话时长上限（秒） | 120 |
| Roam | MinConfidenceToAct | 自动执行动作的最低置信度 | 0.6 |
| Roam | MaxTokenBudget | 自定义/后续 LLM 引擎 token 上限；核心默认引擎不使用 LLM | 20000 |
| Roam | MaxCostUsd | 自定义/后续 LLM 引擎成本上限（美元） | 0.5 |

### 6.4 WaitTime — 默认步骤等待时间

设置 `DefaultValue.WaitTime` 后，框架在**每个步骤执行完成后**自动等待指定秒数。

| 关键字 | 是否应用 WaitTime |
|--------|-----------------|
| navigate / type / click / verify 等 | 是 |
| wait | 否（wait 自身已包含等待） |
| close | 否（浏览器已关闭） |

### 6.5 数据库连接配置

DB 关键字最终仍通过 `globalvalue.xml` 中的组读取数据库连接参数，但引用路径已调整为：

1. Case 中 `model` 填数据库模型名（如 `QuerySQL`）
2. 数据库模型通过 `connection="sqlite_db"` 指向连接组
3. 框架再到 `globalvalue.xml` 中读取 `sqlite_db` 组参数

| 组名 | Key | 说明 |
|------|-----|------|
| sqlite_db | type | 数据库类型：sqlite / mysql / postgresql / sqlserver |
| sqlite_db | host | 主机地址（sqlite 不需要） |
| sqlite_db | port | 端口号（sqlite 不需要） |
| sqlite_db | database | 数据库名或文件路径 |
| sqlite_db | username | 用户名 |
| sqlite_db | password | 密码 |

因此，Case XML 中 DB 关键字的 `model` 属性**不再**填写连接组名，而是填写数据库模型名。

---
