# Iteration 09: 验收测试

## 设计合规性检查

| 检查项 | 结论 |
|--------|------|
| 所有 action 值在 ActionType 枚举中 | ✅ navigate/type/verify/close 均合法 |
| Return 引用写在数据表 field 中，不在 case XML data 属性 | ✅ |
| 不引入新关键字 | ✅ |
| 不改变 ${Return[-N]} 语义 | ✅ |

---

## AC09-001: history 连续性验证

**测试用例名称**: 所有关键字执行后 history 均有记录

**case/ac09_history.xml**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<cases>
  <case execute="是" id="AC09-001" title="history连续性验证" component_type="界面">
    <test_case>
      <test_step action="navigate" model="" data="http://localhost:8000"/>
      <test_step action="type" model="LoginForm" data="L001"/>
      <test_step action="verify" model="Dashboard" data="V001"/>
      <test_step action="close" model="" data=""/>
    </test_case>
  </case>
</cases>
```

**验收条件**:
- Debug 日志中 4 个步骤均有 history 记录
- navigate → `True`，type → 数据行，verify → 结果 list，close → `True`
- `${Return[-1]}` 在 close 后指向 `True`

---

## AC09-002: Return 语义回归

**测试用例名称**: ${Return[-N]} 语义与迭代前一致

**case/ac09_return.xml**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<cases>
  <case execute="是" id="AC09-002" title="Return语义回归" component_type="界面">
    <pre_process>
      <test_step action="navigate" model="" data="http://localhost:8000"/>
      <test_step action="type" model="LoginForm" data="L001"/>
      <test_step action="type" model="NavMenu" data="N001"/>
    </pre_process>
    <test_case>
      <test_step action="type" model="TestForm" data="T001"/>
      <test_step action="verify" model="TestForm" data="V001"/>
    </test_case>
    <post_process>
      <test_step action="close" model="" data=""/>
    </post_process>
  </case>
</cases>
```

**data/TestForm_verify.xml**（V001 使用 Return 引用，写在 field 中）:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<datatable name="TestForm_verify">
  <row id="V001" remark="验证表单结果">
    <field name="formResult">${Return[-1]}</field>
  </row>
</datatable>
```

**验收条件**:
- 用例执行通过，与 iteration-09 实施前行为完全一致

---

## rodski 开发需求

**需要开发**: T9-001 ~ T9-005  
**demo 开发**: 不需要，复用现有 `demo_full` 用例
