# 6. GlobalValue XML — 全局变量

> **来源**: RodSki 测试用例编写指南 v3.4  
> 本文档为独立章节，完整指南请见 [TEST_CASE_WRITING_GUIDE.md](../TEST_CASE_WRITING_GUIDE.md)

---


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
  <group name="demodb">
    <var name="type" value="sqlite"/>
    <var name="database" value="product/DEMO/demo_site/demo.db"/>
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

### 6.4 WaitTime — 默认步骤等待时间

设置 `DefaultValue.WaitTime` 后，框架在**每个步骤执行完成后**自动等待指定秒数。

| 关键字 | 是否应用 WaitTime |
|--------|-----------------|
| navigate / type / click / verify 等 | 是 |
| wait | 否（wait 自身已包含等待） |
| close | 否（浏览器已关闭） |

### 6.5 数据库连接配置

DB 关键字通过 GlobalValue 中的组名获取连接参数：

| 组名 | Key | 说明 |
|------|-----|------|
| demodb | type | 数据库类型：sqlite / mysql / postgresql / sqlserver |
| demodb | host | 主机地址（sqlite 不需要） |
| demodb | port | 端口号（sqlite 不需要） |
| demodb | database | 数据库名或文件路径 |
| demodb | username | 用户名 |
| demodb | password | 密码 |

Case XML 中 DB 关键字的 `model` 属性填写组名（如 `demodb`），框架根据该组名查找连接配置。

---

