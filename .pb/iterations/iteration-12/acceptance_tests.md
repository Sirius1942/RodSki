# Iteration 12: 验收测试

## 设计合规性检查

| 检查项 | 结论 |
|--------|------|
| `type`/`send`/`verify` 均在 ActionType 枚举中 | ✅ |
| `auto_capture` 是模型新增节点，不改变 case XML 语法 | ✅ |
| Return 引用写在数据表 field 中 | ✅ |
| `${Return[-1].field}` 路径访问语法已有设计支持 | ✅ |
| send 响应 dict 结构不破坏现有 verify 步骤 | ✅（_capture 作为新增字段，不覆盖原有字段） |

---

## AC12-001: type Auto Capture 成功提取关键值

**测试用例名称**: type 执行后自动提取 resultId，无需额外 get

**model/model.xml**（新增 DemoForm，含 auto_capture）:
```xml
<model name="DemoForm" servicename="">
  <element name="username" type="web">
    <type>input</type>
    <location type="id">username</location>
  </element>
  <element name="submitBtn" type="web">
    <type>button</type>
    <location type="id">submitBtn</location>
  </element>
  <auto_capture trigger="type">
    <field name="resultId">
      <location type="id">resultId</location>
    </field>
  </auto_capture>
</model>

<model name="DemoFormVerify" servicename="">
  <element name="resultId" type="web">
    <type>text</type>
    <location type="id">resultId</location>
  </element>
</model>
```

**data/DemoForm.xml**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<datatable name="DemoForm">
  <row id="F001" remark="提交表单">
    <field name="username">testuser</field>
    <field name="submitBtn">click</field>
  </row>
</datatable>
```

**data/DemoFormVerify_verify.xml**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<datatable name="DemoFormVerify_verify">
  <row id="V001" remark="验证auto_capture提取resultId">
    <field name="resultId">${Return[-1].resultId}</field>
  </row>
</datatable>
```

**case/ac12_auto_capture.xml**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<cases>
  <case execute="是" id="AC12-001" title="type Auto Capture成功" component_type="界面">
    <pre_process>
      <test_step action="navigate" model="" data="http://localhost:8000/form"/>
    </pre_process>
    <test_case>
      <test_step action="type" model="DemoForm" data="F001"/>
      <test_step action="verify" model="DemoFormVerify" data="V001"/>
    </test_case>
    <post_process>
      <test_step action="close" model="" data=""/>
    </post_process>
  </case>
</cases>
```

**验收条件**:
- type 执行后 history 中该步骤返回值为 dict，包含 `resultId`
- verify 直接读取 `${Return[-1].resultId}` 通过，无额外 get 步骤

---

## AC12-002: type Auto Capture 失败时可见报错

**model/model.xml**（新增，auto_capture 指向不存在元素）:
```xml
<model name="DemoFormBadCapture" servicename="">
  <element name="username" type="web">
    <type>input</type>
    <location type="id">username</location>
  </element>
  <element name="submitBtn" type="web">
    <type>button</type>
    <location type="id">submitBtn</location>
  </element>
  <auto_capture trigger="type">
    <field name="nonExistentField">
      <location type="id">nonExistentField</location>
    </field>
  </auto_capture>
</model>
```

**case/ac12_capture_fail.xml**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<cases>
  <case execute="是" id="AC12-002" title="Auto Capture失败报错" component_type="界面">
    <pre_process>
      <test_step action="navigate" model="" data="http://localhost:8000/form"/>
    </pre_process>
    <test_case>
      <test_step action="type" model="DemoFormBadCapture" data="F001"/>
    </test_case>
    <post_process>
      <test_step action="close" model="" data=""/>
    </post_process>
  </case>
</cases>
```

**验收条件**:
- 步骤失败，抛出 `AutoCaptureError`，错误信息包含字段名和 locator，不 silent fail

---

## AC12-003: send Auto Capture 从响应 body 提取字段

**model/model.xml**（新增 LoginAPICapture，含 auto_capture）:
```xml
<model name="LoginAPICapture" servicename="">
  <element name="_method" type="interface">
    <location type="static">POST</location>
  </element>
  <element name="_url" type="interface">
    <location type="static">http://localhost:8000/api/login</location>
  </element>
  <element name="username" type="interface">
    <location type="field">username</location>
  </element>
  <element name="password" type="interface">
    <location type="field">password</location>
  </element>
  <auto_capture trigger="send">
    <field name="token" path="data.token"/>
  </auto_capture>
</model>
```

**data/LoginAPICapture.xml**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<datatable name="LoginAPICapture">
  <row id="D001" remark="登录">
    <field name="username">admin</field>
    <field name="password">admin123</field>
  </row>
</datatable>
```

**data/LoginAPICapture_verify.xml**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<datatable name="LoginAPICapture_verify">
  <row id="V001" remark="验证send auto_capture提取token">
    <field name="status">200</field>
    <field name="_capture.token">${Return[-1]._capture.token}</field>
  </row>
</datatable>
```

**case/ac12_send_capture.xml**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<cases>
  <case execute="是" id="AC12-003" title="send Auto Capture成功" component_type="接口">
    <test_case>
      <test_step action="send" model="LoginAPICapture" data="D001"/>
      <test_step action="verify" model="LoginAPICapture" data="V001"/>
    </test_case>
  </case>
</cases>
```

**验收条件**:
- send 执行后响应 dict 包含 `_capture.token`
- `${Return[-1]._capture.token}` 可正常解析，verify 通过
- 原始响应 body 完整保留

---

## rodski 开发需求

**需要开发**: T12-001 ~ T12-004  
**demo 开发**: 新增表单页面（含 `resultId` 展示）、上述模型定义及数据表
