# 数据引用语法

## 概述

测试用例支持三种数据引用方式：数据表引用、返回值引用和变量引用。

## 1. 数据表引用

### 格式

```
${DataTable.DataID.Field}
```

### 说明

- `DataTable` - Excel数据文件名（不含.xlsx扩展名）
- `DataID` - 数据行的ID值
- `Field` - 字段名（Excel列名）

### 示例

数据文件 `data/users.xlsx`:

| id | username | password |
|----|----------|----------|
| 001 | admin | admin123 |
| 002 | user1 | pass456 |

用例中引用:

```xml
<step keyword="type">
    <param name="locator">${LoginPage.username}</param>
    <param name="text">${users.001.username}</param>
</step>
```

## 2. 返回值引用

### 格式

```
${Return[index]}
```

### 说明

- `index` - 返回值索引，支持正负数
- `Return[0]` - 第一个返回值
- `Return[-1]` - 最后一个返回值

### 示例

```xml
<step keyword="get_text">
    <param name="locator">${HomePage.title}</param>
    <param name="var_name">page_title</param>
</step>
<step keyword="assert">
    <param name="locator">${HomePage.header}</param>
    <param name="expected">${Return[0]}</param>
</step>
```

### 存储返回值的关键字

- `get_text` - 存储获取的文本
- `http_get` - 存储响应内容
- `http_post` - 存储响应内容
- `assert` - 存储断言结果

## 3. 变量引用

### 使用 set 关键字

```xml
<step keyword="set">
    <param name="var_name">base_url</param>
    <param name="value">https://example.com</param>
</step>
```

变量存储在 `keyword_engine._variables` 字典中，可在后续步骤中使用。

## 组合使用

```xml
<step keyword="http_get">
    <param name="url">${api.001.endpoint}</param>
</step>
<step keyword="assert_json">
    <param name="path">$.data.name</param>
    <param name="expected">${Return[0]}</param>
</step>
```

## 注意事项

1. 数据引用必须使用 `${}` 包裹
2. 索引越界时返回原始引用字符串
3. 数据表文件必须位于 `data/` 目录
4. Excel数据表必须包含 `id` 或 `ID` 列
