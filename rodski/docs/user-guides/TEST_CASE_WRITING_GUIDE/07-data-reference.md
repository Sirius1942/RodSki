# 7. 数据引用与变量解析

> **来源**: RodSki 测试用例编写指南 v3.4  
> 本文档为独立章节，完整指南请见 [TEST_CASE_WRITING_GUIDE.md](../TEST_CASE_WRITING_GUIDE.md)

---


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
<!-- data/VerifyData.xml -->
<datatable name="VerifyData">
  <row id="V001" remark="验证订单">
    <field name="orderNo">${Return[-1]}</field>
  </row>
</datatable>
```

```xml
<!-- Case XML：verify 作为 test_case 内一步 -->
<test_case>
  <test_step action="verify" model="OrderDetail" data="VerifyData.V001"/>
</test_case>
```

**与动态步骤（规划）**：若未来支持「CLI/运行时插入步骤」，`${Return[-1]}` 仍表示**固定步骤**管线中的「上一步」；**不要**在数据表中用 `${Return}` 引用仅由动态步骤产生的数据。详见 **[§10](#10-固定与动态测试步骤规划)** 与《核心设计约束》第 8 节。

### 7.4 哪些关键字会产生 Return 值

| 关键字 | 返回值内容 |
|--------|-----------|
| get / get_text | 元素文本 |
| verify | 批量验证时的实际值字典 |
| assert | 断言结果 |
| type（批量模式） | 本次输入使用的完整数据行 |
| send | HTTP 响应（含 `status` 状态码 + 响应体字段） |
| DB | query → 结果集列表；execute → 受影响行数 |
| run | 脚本 stdout 输出（自动尝试 JSON 解析） |

---

