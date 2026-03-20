# RESTful API JSON 数据支持示例

## 方案 1：Excel 中直接嵌入 JSON

在 Excel 数据表中直接写 JSON：

| DataID | request_body | expected_response |
|--------|--------------|-------------------|
| API001 | {"username":"test","password":"123"} | {"status":"success"} |

## 方案 2：引用外部 JSON 文件

| DataID | request_body | expected_response |
|--------|--------------|-------------------|
| API002 | @file:data/login_request.json | @file:data/login_response.json |

## 方案 3：混合使用（推荐）

简单 JSON 直接写，复杂 JSON 用文件：

| DataID | request_body | expected_response |
|--------|--------------|-------------------|
| API003 | {"action":"logout"} | @file:data/logout_response.json |

## 变量替换

支持在 JSON 中使用变量：

```json
{
  "username": "${user}",
  "token": "${auth_token}"
}
```

## 代码示例

```python
from data.data_resolver import DataResolver

resolver = DataResolver(
    data_source={"user": "admin"},
    base_path=Path("examples/api_test")
)

# 解析 JSON 字符串
data = resolver.resolve_json('{"name": "${user}"}')
# 结果: {"name": "admin"}

# 加载 JSON 文件
data = resolver.resolve_json("@file:data/login_request.json")
```
