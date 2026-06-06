<!-- 自动生成 from rodski/docs/TEST_CASE_WRITING_GUIDE.md  请勿手工编辑 -->

## 7. 数据引用与变量解析

### 7.1 解析顺序

框架在执行步骤前，对 Case XML `data` 属性的值按以下顺序解析：

1. **GlobalValue 引用**：`GlobalValue.组名.变量名` → 替换为对应值
2. **数据表字段引用**：`表名.DataID.字段名` → 替换为数据表中的值
3. **Return 引用**：`Return[-1]` / `Return[0]` → 替换为步骤返回值

### 7.2 支持的引用格式

| 格式 | 说明 | 示例 |
|------|------|------|
| `GlobalValue.组名.Key` | 全局变量 | `GlobalValue.DefaultValue.URL` |
| `表名.DataID` | 整行数据（用于 type/verify） | `Login.L001` |
| `表名.DataID.字段名` | 单个字段值 | `Login.L001.username` |
| `${Return[-1]}` | 上一步返回值 | 写在**数据表 field**中 |
| `${Return[-2]}` | 上上步返回值 | 写在**数据表 field**中 |
| `${Return[0]}` | 第一步返回值 | 写在**数据表 field**中 |

### 7.3 Return 引用的正确用法

Return 引用**只应出现在数据表 XML 的 field 值中**，不要写在 Case XML 的 `data` 属性。

原因：Case XML `data` 属性中如果写 `${Return[-1]}`，会在进入关键字前被替换成字符串，导致 verify 无法走批量验证模式。

正确做法：

```xml
<!-- data.sqlite 中的 UI 验证表 -->
<datatable name="OrderDetail_verify">
  <row id="V001" remark="验证订单号">
    <field name="orderNo">ORD-20260411-001</field>
  </row>
</datatable>
```

```xml
<!-- Case XML：verify 作为 test_case 内一步 -->
<test_case>
  <test_step action="verify" model="OrderDetail" data="V001"/>
</test_case>
```

> **注意**：如果 verify 的模型是 UI 模型，期望值可以引用 `${Return[-N]}`（跨源比对）；但接口/DB 模型的 `_verify` 表**禁止**使用 `${Return[-1]}`，详见 [7.4 节](#74-verify-数据表中禁止自引用)。

**与动态步骤（规划）**：若未来支持「CLI/运行时插入步骤」，`${Return[-1]}` 仍表示**固定步骤**管线中的「上一步」；**不要**在数据表中用 `${Return}` 引用仅由动态步骤产生的数据。详见 **[§10](#10-固定与动态测试步骤规划)** 与《核心设计约束》第 8 节。

### 7.4 verify 数据表中禁止自引用

接口和数据库模型的 `_verify` 数据表中**禁止**使用 `${Return[-1]}`。

原因：verify 对接口/DB 模型自动从 `Return[-1]` 读取实际值。如果期望值也引用 `Return[-1]`，
等于自己跟自己比较，断言永远通过，无法发现问题。

| 场景 | 期望值 | 结论 |
|------|--------|------|
| 接口/DB verify + `${Return[-1]}` | 自引用 | **禁止** |
| 接口/DB verify + 字面值 `"demo_token"` | 真正断言 | **正确** |
| UI verify + `${Return[-2].token}` | 跨源比对 | **允许** |

### 7.5 哪些关键字会产生 Return 值

| 关键字 | 返回值内容 |
|--------|-----------|
| get / get_text | 元素文本（get_text 已废弃，请使用 get） |
| verify | 批量验证时的实际值字典 |
| assert | 断言结果 |
| type（批量模式） | 本次输入使用的完整数据行 |
| send | HTTP 响应（含 `status` 状态码 + 响应体字段） |
| DB | query → 结果集列表；execute → 受影响行数 |
| run | 脚本 stdout 输出（自动尝试 JSON 解析） |

### 7.6 推荐：使用 set/get 命名变量

推荐使用 `set`/`get` 命名变量作为步骤间数据传递的首选方式：

**推荐写法（set/get 命名变量）：**

```xml
<!-- 保存接口返回的 token -->
<test_step action="send" model="LoginAPI" data="L001"/>
<test_step action="set" model="" data="auth_token=${Return[-1].token}"/>

<!-- 在后续步骤中使用命名变量 -->
<test_step action="send" model="OrderAPI" data="O001"/>
<!-- data.sqlite 中: <field name="_headers">Authorization: Bearer ${auth_token}</field> -->
```

**进阶写法（Return 索引）：**

Return 索引适合步骤紧邻且无歧义的场景：

```xml
<test_step action="send" model="LoginAPI" data="L001"/>
<test_step action="verify" model="LoginAPI" data="V001"/>
<!-- data.sqlite 中: <field name="status">${Return[-1].status}</field> -->
```

**为什么推荐 set/get？**

- **可读性更好**：`${auth_token}` 比 `${Return[-3].token}` 更清晰
- **更稳定**：插入新步骤不会导致 Return 索引偏移
- **适合 AI Agent 生成**：减少索引计算错误

> **注意**：Return 索引仍然完全支持，不会被废弃。set/get 是推荐的首选方式，Return 索引是合法的进阶用法。

### 7.7 内置函数：random() 和 date()（v6.7.0）

数据表字段值中可使用内置函数生成动态数据，语法为 `${函数名(type, 参数...)}`。

**仅支持两个函数**：

#### `${random(type, ...)}` — 随机数据

| 写法 | 结果示例 | 说明 |
|------|----------|------|
| `${random(int, 1000, 9999)}` | `3847` | 指定范围的随机整数 |
| `${random(int, 4)}` | `3847` | 4 位随机整数 |
| `${random(float, 10.00, 999.99)}` | `156.73` | 随机浮点数 |
| `${random(str, 6)}` | `aB3kP9` | 6 位随机字母数字 |
| `${random(digits, 8)}` | `03847291` | 8 位纯数字 |
| `${random(phone)}` | `13812345678` | 随机中国手机号 |
| `${random(email)}` | `a3k9pm@test.com` | 随机邮箱 |
| `${random(choice, A, B, C)}` | `B` | 从候选值中随机选一个 |
| `${random(uuid)}` | `550e8400-e29b-...` | UUID v4 |

#### `${date(type, ...)}` — 时间数据

| 写法 | 结果示例 | 说明 |
|------|----------|------|
| `${date(now)}` | `2026-05-12 14:30:00` | 当前日期时间 |
| `${date(now, %Y%m%d_%H%M%S)}` | `20260512_143000` | 自定义格式 |
| `${date(today)}` | `2026-05-12` | 当前日期 |
| `${date(today, %Y%m%d)}` | `20260512` | 紧凑日期 |
| `${date(time)}` | `14:30:00` | 当前时间 |
| `${date(timestamp)}` | `1778745000` | Unix 时间戳（秒） |
| `${date(timestamp_ms)}` | `1778745000123` | Unix 时间戳（毫秒） |
| `${date(offset, 30)}` | `2026-06-11` | 30 天后 |
| `${date(offset, -7)}` | `2026-05-05` | 7 天前 |
| `${date(offset, -2h)}` | `2026-05-12 12:30:00` | 2 小时前 |
| `${date(offset, -2h, %H:%M)}` | `12:30` | 2 小时前，自定义格式 |

#### 字符串拼接

函数可出现在字段值任意位置，前后拼接静态文本：

```sql
-- 唯一用户名
INSERT INTO rs_field VALUES ('RegisterAPI', 'D001', 'username', 'user_${random(int, 4)}');

-- 测试邮箱
INSERT INTO rs_field VALUES ('RegisterAPI', 'D001', 'email', 'test_${random(str, 6)}@example.com');

-- 订单号 = 前缀 + 日期 + 随机数
INSERT INTO rs_field VALUES ('OrderAPI', 'D001', 'order_no', 'ORD_${date(today, %Y%m%d)}_${random(digits, 4)}');

-- 有效期
INSERT INTO rs_field VALUES ('OrderAPI', 'D001', 'expire_date', '${date(offset, 30)}');

-- 交易流水号
INSERT INTO rs_field VALUES ('PayAPI', 'D001', 'txn_no', 'TXN${date(today, %Y%m%d)}${random(digits, 8)}');
```

#### 注意事项

- 内置函数**只在数据表字段值中生效**，不要写在 Case XML 的 `data` 属性中
- 每次执行时重新计算，不缓存结果
- 不支持嵌套调用（如 `${random(int, ${date(...)})}`）
- 需要字面量 `${` 时使用 `$${` 转义

---
