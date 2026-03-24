# RESTful API JSON 数据支持设计文档

## 设计目标

为 SKI 框架增加对 RESTful API 测试的 JSON 数据支持，使其能够方便地处理 API 请求和响应数据。

## 核心功能

### 1. JSON 字符串解析
直接在 Excel 数据表中写入 JSON：
```
| DataID | request_body | expected_response |
|--------|--------------|-------------------|
| API001 | {"name":"test","age":25} | {"status":"success"} |
```

### 2. 外部文件引用
使用 `@file:` 引用外部 JSON 文件：
```
| DataID | request_body | expected_response |
|--------|--------------|-------------------|
| API002 | @file:data/login_request.json | @file:data/login_response.json |
```

### 3. 变量替换
JSON 中支持 `${var}` 和 `@{model.field}` 变量：
```json
{
  "username": "${user}",
  "token": "${auth_token}"
}
```

## 实现方案

### DataResolver 增强

新增方法：
- `resolve_json(text)`: 解析 JSON 字符串或文件引用，返回 Python 对象
- `_resolve_file_refs(text)`: 处理 @file: 引用
- `_load_json_file(path)`: 加载 JSON 文件
- `_resolve_json_vars(data)`: 递归解析 JSON 中的变量

### RestHelper 工具类

提供 API 测试辅助功能：
- JSON Schema 验证
- JSONPath 数据提取

## 使用示例

### 代码调用
```python
from data.data_resolver import DataResolver
from pathlib import Path

resolver = DataResolver(
    data_source={"user": "admin", "token": "abc123"},
    base_path=Path("testdata")
)

# 解析 JSON 字符串
data = resolver.resolve_json('{"name": "${user}"}')
# 结果: {"name": "admin"}

# 加载 JSON 文件
data = resolver.resolve_json("@file:api/login_request.json")
```

### Excel 用例编写

**方案 1：简单 JSON 内嵌**
```
| 用例ID | 接口 | 请求体 | 预期响应 |
|--------|------|--------|----------|
| TC001 | /api/login | {"username":"admin","password":"123"} | {"status":"success"} |
```

**方案 2：复杂 JSON 文件引用**
```
| 用例ID | 接口 | 请求体 | 预期响应 |
|--------|------|--------|----------|
| TC002 | /api/user | @file:data/create_user.json | @file:data/user_response.json |
```

**方案 3：混合使用（推荐）**
```
| 用例ID | 接口 | 请求体 | 预期响应 |
|--------|------|--------|----------|
| TC003 | /api/logout | {"token":"${auth_token}"} | @file:data/logout_response.json |
```

## 测试验证

所有测试通过：
- ✅ JSON 字符串解析
- ✅ 嵌套 JSON 处理
- ✅ 文件引用加载
- ✅ 变量替换
- ✅ 向后兼容（原有测试全部通过）

## 优势

1. **灵活性**：支持内嵌和文件引用两种方式
2. **易用性**：保持 Excel 编写习惯
3. **可维护性**：复杂 JSON 独立文件管理
4. **扩展性**：支持变量和模型引用
5. **兼容性**：不影响现有功能

## 文件清单

- `data/data_resolver.py` - 核心解析器（已增强）
- `api/rest_helper.py` - API 测试辅助工具
- `tests/unit/test_json_support.py` - 单元测试
- `examples/api_test/` - 使用示例
- `doc/design/json_support_design.md` - 本设计文档

---
**设计者**: 阿尔茜 (Arcee) 🏍️  
**日期**: 2026-03-15  
**版本**: 1.0
