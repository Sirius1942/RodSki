# Iteration 10: 验收测试

## 设计合规性检查

| 检查项 | 结论 |
|--------|------|
| `evaluate` 在 ActionType 枚举中 | ✅ |
| Return 引用写在数据表 field 中 | ✅ |
| 不改变 evaluate 的 DSL 语法 | ✅ |
| 修复范围仅限 store_return 调用 | ✅ |

---

## AC10-001: evaluate 结构化返回验证

**测试用例名称**: evaluate 返回 dict 时 history 保留结构

**case/ac10_evaluate.xml**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<cases>
  <case execute="是" id="AC10-001" title="evaluate结构化返回" component_type="界面">
    <pre_process>
      <test_step action="navigate" model="" data="http://localhost:8000"/>
    </pre_process>
    <test_case>
      <test_step action="evaluate" model="" data="() => ({title: document.title})"/>
      <test_step action="verify" model="EvaluateResult" data="V001"/>
    </test_case>
    <post_process>
      <test_step action="close" model="" data=""/>
    </post_process>
  </case>
</cases>
```

**model/model.xml**（新增）:
```xml
<model name="EvaluateResult" servicename="">
  <element name="title" type="web">
    <type>text</type>
    <location type="id">pageTitle</location>
  </element>
</model>
```

**data/EvaluateResult_verify.xml**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<datatable name="EvaluateResult_verify">
  <row id="V001" remark="验证evaluate返回title字段">
    <field name="title">${Return[-1].title}</field>
  </row>
</datatable>
```

**验收条件**:
- history 中 evaluate 步骤返回值为 dict，未被 `str()` 降级
- `${Return[-1].title}` 可正常解析，verify 通过

---

## AC10-002: 非 Web driver 调用 evaluate 报错

**测试用例名称**: evaluate 在非 Web 场景下抛出明确错误

**验收方式**: 单元测试，在 macos driver 上下文中调用 evaluate

**验收条件**:
- 抛出明确异常，信息包含"evaluate 仅支持 Web 浏览器驱动"
- 不 silent fail

---

## rodski 开发需求

**需要开发**: T10-001 ~ T10-003  
**demo 开发**: 新增 `EvaluateResult` 模型 + `EvaluateResult_verify.xml`
