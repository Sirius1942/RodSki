# 模型编写指南

## 概述

model.xml 用于定义页面元素的定位信息，支持通过 `ModelName.ElementName` 格式在测试用例中引用。

## 文件格式

```xml
<?xml version="1.0" encoding="UTF-8"?>
<model>
    <element name="ElementName" locator="定位表达式" type="定位类型"/>
</model>
```

## 定位类型

- `id` - 通过元素ID定位
- `name` - 通过元素name属性定位
- `xpath` - 通过XPath表达式定位
- `css` - 通过CSS选择器定位
- `class` - 通过class名称定位
- `tag` - 通过标签名定位
- `link` - 通过链接文本定位

## 示例

### LoginPage.xml

```xml
<?xml version="1.0" encoding="UTF-8"?>
<model>
    <element name="username" locator="user-input" type="id"/>
    <element name="password" locator="pass-input" type="id"/>
    <element name="loginBtn" locator="//button[@type='submit']" type="xpath"/>
</model>
```

### 在用例中引用

```xml
<step keyword="type">
    <param name="locator">${LoginPage.username}</param>
    <param name="text">admin</param>
</step>
<step keyword="click">
    <param name="locator">${LoginPage.loginBtn}</param>
</step>
```

## 命名规范

- 模型文件名使用 PascalCase，如 `LoginPage.xml`
- 元素名使用 camelCase，如 `username`, `loginBtn`
- 定位表达式应简洁明确

## 最佳实践

1. 按页面或功能模块组织模型文件
2. 使用语义化的元素名称
3. 优先使用稳定的定位方式（id > name > css > xpath）
4. 避免使用过于复杂的XPath表达式
