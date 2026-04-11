# Data 目录说明

## 文件组织

data 目录包含测试数据和全局配置，采用统一的 XML 格式：

```
data/
├── data.xml          # 所有测试数据表（必需）
├── globalvalue.xml   # 全局变量配置（必需）
├── DB_USAGE.md       # 数据库使用说明
└── README.md         # 本文件
```

## 文件说明

### data.xml

包含所有测试用例使用的数据表，每个 datatable 对应一个模型或验证场景。

**命名规范**:
- 数据表：模型名（如 `LoginForm`, `OrderAPI`）
- 验证表：模型名_verify（如 `LoginForm_verify`, `OrderAPI_verify`）

**数据表分类**:

#### 1. 登录相关 (6个)
- `Login` - 通用登录数据
- `LoginForm` - Web登录表单数据
- `Login_verify` - 登录验证
- `ErrorMessage_verify` - 错误消息验证
- `LoginAPI` - API登录数据
- `LoginAPI_verify` - API登录验证

#### 2. 界面操作 (12个)
- `Dashboard` / `Dashboard_verify` - 看板数据
- `NavMenu` - 导航菜单
- `TestForm` / `TestForm_verify` - 测试表单
- `Form` / `Form_verify` - 通用表单
- `UIActions` / `UIActions_verify` - UI动作测试
- `DemoForm` / `DemoFormVerify_verify` - Auto Capture演示
- `DemoFormBadCapture` - Auto Capture错误场景

#### 3. API接口 (4个)
- `OrderAPI` / `OrderAPI_verify` - 订单API
- `LoginAPICapture` / `LoginAPICapture_verify` - API Auto Capture

#### 4. 数据库查询 (8个)
- `QuerySQL` / `QuerySQL_verify` - SQL查询
- `QueryDB` / `QueryDB_verify` - 数据库查询
- `QueryOrder` / `QueryOrder_verify` - 订单查询
- `QueryUser` / `QueryUser_verify` - 用户查询

#### 5. 业务数据 (6个)
- `Order` / `Order_verify` - 订单数据
- `OrderTable_verify` - 订单表验证
- `Product` / `Product_verify` - 产品数据
- `User` / `User_verify` - 用户数据

#### 6. 高级特性 (8个)
- `ReturnTest` / `ReturnTest_verify` - Return引用测试
- `SetGetVerify_verify` - set/get命名访问
- `GetVerify_verify` - get选择器模式
- `GetModel` / `GetModelVerify_verify` - get模型模式
- `EvaluateResult_verify` - evaluate结构化返回

**总计**: 44个数据表

### globalvalue.xml

全局变量配置文件，包含：
- 数据库连接配置（demo_db）
- 环境变量
- 共享配置

详细使用说明参见 `DB_USAGE.md`。

## 使用方式

### 在测试用例中引用数据

```xml
<!-- 引用数据表中的某一行 -->
<test_step action="type" model="LoginForm" data="L001"/>

<!-- 引用验证数据 -->
<test_step action="verify" model="LoginForm" data="V001"/>

<!-- v5+ DB 新语法：model=数据库模型，data=数据行ID -->
<test_step action="DB" model="QuerySQL" data="Q001"/>
```

### 数据表结构

```xml
<datatable name="LoginForm">
    <row id="L001">
        <field name="username">admin</field>
        <field name="password">123456</field>
        <field name="loginBtn">click</field>
    </row>
</datatable>
```

## 维护规范

1. **统一管理**: 所有数据表必须在 data.xml 中定义，不要创建单独的 XML 文件
2. **命名规范**: 
   - 数据表名与模型名保持一致
   - 验证表统一使用 `_verify` 后缀
3. **ID规范**:
   - 数据行: L001, D001, F001, T001 等（按类型首字母）
   - 验证行: V001, V002 等
   - 查询行: Q001, Q002 等
4. **注释**: 使用 `remark` 属性说明数据用途

## 相关文档

- `DB_USAGE.md` - 数据库关键字使用说明
- `../model/model.xml` - 模型定义
- `../case/demo_case.xml` - 测试用例
