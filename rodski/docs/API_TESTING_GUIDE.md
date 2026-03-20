# RESTful API 测试指南

## 支持的 API 关键字

### HTTP 请求关键字

| 关键字 | 说明 | 参数 |
|--------|------|------|
| `http_get` | GET 请求 | url, headers, expected_status |
| `http_post` | POST 请求 | url, body, headers, expected_status |
| `http_put` | PUT 请求 | url, body, headers, expected_status |
| `http_delete` | DELETE 请求 | url, headers, expected_status |

### 断言关键字

| 关键字 | 说明 | 参数 |
|--------|------|------|
| `assert_status` | 断言 HTTP 状态码 | expected |
| `assert_json` | 断言 JSON 响应内容 | path, expected |

## Excel 用例格式示例

### 示例 1: 简单 GET 请求

| 步骤 | 关键字 | 参数1 | 参数2 | 参数3 |
|------|--------|-------|-------|-------|
| 1 | http_get | url=https://api.example.com/users | expected_status=200 | |
| 2 | assert_json | path=$.data[0].name | expected=John | |

### 示例 2: POST 创建资源

| 步骤 | 关键字 | 参数1 | 参数2 | 参数3 |
|------|--------|-------|-------|-------|
| 1 | http_post | url=https://api.example.com/users | body={"name":"Alice","age":25} | expected_status=201 |
| 2 | assert_json | path=$.data.id | expected=123 | |

### 示例 3: 带 Headers 的请求

| 步骤 | 关键字 | 参数1 | 参数2 | 参数3 |
|------|--------|-------|-------|-------|
| 1 | http_get | url=https://api.example.com/profile | headers={"Authorization":"Bearer token123"} | expected_status=200 |
| 2 | assert_json | path=$.username | expected=admin | |

## JSONPath 语法说明

JSONPath 用于从 JSON 响应中提取数据：

```
$.data.name          # 获取 data.name
$.users[0].id        # 获取 users 数组第一个元素的 id
$.items[*].price     # 获取所有 items 的 price
$..email             # 递归查找所有 email 字段
```

## 常见场景示例

### 场景 1: 用户登录

| 步骤 | 关键字 | 参数1 | 参数2 | 参数3 |
|------|--------|-------|-------|-------|
| 1 | http_post | url=https://api.example.com/login | body={"username":"admin","password":"123456"} | expected_status=200 |
| 2 | assert_json | path=$.token | expected=abc123xyz | |
| 3 | assert_json | path=$.user.role | expected=admin | |

### 场景 2: CRUD 操作

**创建**
| 步骤 | 关键字 | 参数1 | 参数2 |
|------|--------|-------|-------|
| 1 | http_post | url=https://api.example.com/products | body={"name":"iPhone","price":999} |
| 2 | assert_status | expected=201 | |

**读取**
| 步骤 | 关键字 | 参数1 | 参数2 |
|------|--------|-------|-------|
| 1 | http_get | url=https://api.example.com/products/1 | expected_status=200 |
| 2 | assert_json | path=$.name | expected=iPhone |

**更新**
| 步骤 | 关键字 | 参数1 | 参数2 |
|------|--------|-------|-------|
| 1 | http_put | url=https://api.example.com/products/1 | body={"price":899} |
| 2 | assert_status | expected=200 | |

**删除**
| 步骤 | 关键字 | 参数1 | 参数2 |
|------|--------|-------|-------|
| 1 | http_delete | url=https://api.example.com/products/1 | expected_status=204 |

### 场景 3: 错误处理

| 步骤 | 关键字 | 参数1 | 参数2 |
|------|--------|-------|-------|
| 1 | http_get | url=https://api.example.com/notfound | expected_status=404 |
| 2 | assert_json | path=$.error | expected=Not Found |

## UI + API 混合测试

可以在同一个用例中混合使用 UI 和 API 测试：

| 步骤 | 关键字 | 参数1 | 参数2 | 参数3 |
|------|--------|-------|-------|-------|
| 1 | http_post | url=https://api.example.com/login | body={"username":"admin","password":"123456"} | expected_status=200 |
| 2 | assert_json | path=$.token | expected=abc123 | |
| 3 | navigate | url=https://example.com/dashboard | | |
| 4 | type | locator=#search | text=test | |
| 5 | click | locator=#submit | | |
| 6 | http_get | url=https://api.example.com/results | expected_status=200 | |

## 注意事项

1. **状态码默认值**: 如果不指定 `expected_status`，默认期望 200
2. **响应保存**: HTTP 请求的响应会自动保存，供后续 `assert_json` 使用
3. **Headers 格式**: headers 参数需要是 JSON 字符串格式
4. **Body 格式**: POST/PUT 的 body 参数需要是 JSON 字符串格式
5. **断言顺序**: `assert_json` 和 `assert_status` 必须在 HTTP 请求之后使用

## 完整示例

参考 `examples/api_test_demo.xlsx` 查看完整的 API 测试用例示例。
