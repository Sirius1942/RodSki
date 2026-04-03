# RESTful API 测试指南

## 接口测试模式

RodSki 使用 **send + verify** 模式进行接口测试：

1. **send**: 发送 HTTP 请求，响应自动存储到 `${Return[-1]}`
2. **verify**: 使用 `_verify` 数据表验证响应内容

## 接口模型定义

接口模型使用特定元素命名约定：

- `_method`: HTTP 方法（GET/POST/PUT/DELETE）
- `_url`: 请求 URL
- `_header_*`: 请求头（如 `_header_Authorization`、`_header_Content-Type`）
- `_body`: 请求体（POST/PUT）
- 其他元素: 请求参数或响应字段

## 响应存储格式

send 执行后，响应自动存储为字典格式：

```python
{
    "status": 200,
    "headers": {...},
    "body": {...}  # JSON 响应会自动解析
}
```

## 验证机制

使用 `${Return[-1]}` 引用最近的响应，配合 `_verify` 数据表进行验证。

**Return 引用格式**：
- 格式：`${Return[x]}`（其中 x 为步骤索引）
- `${Return[0]}`：第一个步骤的返回值
- `${Return[-1]}`：上一个步骤的返回值
- `${Return[-2]}`：上上个步骤的返回值

**访问响应字段**：
- `${Return[-1]}.status`：状态码
- `${Return[-1]}.body.field`：响应体字段
- `${Return[-1]}.headers.Content-Type`：响应头

## 完整 XML 示例

### 示例 1: 简单 GET 请求

**Case_XML**
```xml
<TestCase id="api_get_user" name="获取用户信息">
    <Step action="send" model="GetUserAPI" data="user_001"/>
    <Step action="verify" target="${Return[-1]}" data="verify_user"/>
</TestCase>
```

**Data_XML**
```xml
<TestData>
    <DataTable name="user_001">
        <Row user_id="123"/>
    </DataTable>

    <DataTable name="verify_user">
        <Row _verify="status" _expect="200"/>
        <Row _verify="body.name" _expect="John"/>
        <Row _verify="body.age" _expect="25"/>
    </DataTable>
</TestData>
```

**Model_XML**
```xml
<TestModel>
    <Model name="GetUserAPI">
        <Element name="_method" value="GET"/>
        <Element name="_url" value="https://api.example.com/users/{user_id}"/>
        <Element name="_header_Authorization" value="Bearer token123"/>
    </Model>
</TestModel>
```

### 示例 2: POST 创建资源

**Case_XML**
```xml
<TestCase id="api_create_user" name="创建用户">
    <Step action="send" model="CreateUserAPI" data="new_user"/>
    <Step action="verify" target="Return[-1]" data="verify_created"/>
</TestCase>
```

**Data_XML**
```xml
<TestData>
    <DataTable name="new_user">
        <Row name="Alice" age="30" email="alice@example.com"/>
    </DataTable>

    <DataTable name="verify_created">
        <Row _verify="status" _expect="201"/>
        <Row _verify="body.id" _expect="456"/>
        <Row _verify="body.name" _expect="Alice"/>
    </DataTable>
</TestData>
```

**Model_XML**
```xml
<TestModel>
    <Model name="CreateUserAPI">
        <Element name="_method" value="POST"/>
        <Element name="_url" value="https://api.example.com/users"/>
        <Element name="_header_Content-Type" value="application/json"/>
        <Element name="_body" value='{"name":"{name}","age":{age},"email":"{email}"}'/>
    </Model>
</TestModel>
```

### 示例 3: PUT 更新资源

**Case_XML**
```xml
<TestCase id="api_update_user" name="更新用户">
    <Step action="send" model="UpdateUserAPI" data="update_data"/>
    <Step action="verify" target="Return[-1]" data="verify_updated"/>
</TestCase>
```

**Data_XML**
```xml
<TestData>
    <DataTable name="update_data">
        <Row user_id="123" age="26"/>
    </DataTable>

    <DataTable name="verify_updated">
        <Row _verify="status" _expect="200"/>
        <Row _verify="body.age" _expect="26"/>
    </DataTable>
</TestData>
```

**Model_XML**
```xml
<TestModel>
    <Model name="UpdateUserAPI">
        <Element name="_method" value="PUT"/>
        <Element name="_url" value="https://api.example.com/users/{user_id}"/>
        <Element name="_header_Content-Type" value="application/json"/>
        <Element name="_body" value='{"age":{age}}'/>
    </Model>
</TestModel>
```

### 示例 4: DELETE 删除资源

**Case_XML**
```xml
<TestCase id="api_delete_user" name="删除用户">
    <Step action="send" model="DeleteUserAPI" data="delete_target"/>
    <Step action="verify" target="Return[-1]" data="verify_deleted"/>
</TestCase>
```

**Data_XML**
```xml
<TestData>
    <DataTable name="delete_target">
        <Row user_id="123"/>
    </DataTable>

    <DataTable name="verify_deleted">
        <Row _verify="status" _expect="204"/>
    </DataTable>
</TestData>
```

**Model_XML**
```xml
<TestModel>
    <Model name="DeleteUserAPI">
        <Element name="_method" value="DELETE"/>
        <Element name="_url" value="https://api.example.com/users/{user_id}"/>
        <Element name="_header_Authorization" value="Bearer token123"/>
    </Model>
</TestModel>
```

### 示例 5: 多步骤接口测试

**Case_XML**
```xml
<TestCase id="api_login_flow" name="登录流程">
    <Step action="send" model="LoginAPI" data="login_creds"/>
    <Step action="verify" target="Return[-1]" data="verify_login"/>
    <Step action="send" model="GetProfileAPI" data="profile_req"/>
    <Step action="verify" target="Return[-1]" data="verify_profile"/>
</TestCase>
```

**Data_XML**
```xml
<TestData>
    <DataTable name="login_creds">
        <Row username="admin" password="123456"/>
    </DataTable>

    <DataTable name="verify_login">
        <Row _verify="status" _expect="200"/>
        <Row _verify="body.token" _expect="abc123xyz"/>
    </DataTable>

    <DataTable name="profile_req">
        <Row token="${Return[-1]}.body.token"/>
    </DataTable>

    <DataTable name="verify_profile">
        <Row _verify="status" _expect="200"/>
        <Row _verify="body.username" _expect="admin"/>
        <Row _verify="body.role" _expect="admin"/>
    </DataTable>
</TestData>
```

**Model_XML**
```xml
<TestModel>
    <Model name="LoginAPI">
        <Element name="_method" value="POST"/>
        <Element name="_url" value="https://api.example.com/login"/>
        <Element name="_header_Content-Type" value="application/json"/>
        <Element name="_body" value='{"username":"{username}","password":"{password}"}'/>
    </Model>

    <Model name="GetProfileAPI">
        <Element name="_method" value="GET"/>
        <Element name="_url" value="https://api.example.com/profile"/>
        <Element name="_header_Authorization" value="Bearer {token}"/>
    </Model>
</TestModel>
```

## 注意事项

1. **响应引用**: 使用 `${Return[-1]}` 引用最近一次 send 的响应
2. **字段访问**: 使用点号访问嵌套字段（如 `body.user.name`）
3. **参数替换**: 模型中使用 `{param}` 进行参数替换
4. **验证表**: `_verify` 列指定验证路径，`_expect` 列指定期望值
5. **状态码**: 通过 `${Return[-1]}.status` 访问 HTTP 状态码

## 完整示例

参考 `examples/api_test_demo.xml` 查看完整的 XML 格式接口测试用例。
