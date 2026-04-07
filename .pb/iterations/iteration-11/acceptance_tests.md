# Iteration 11: 验收测试

## 设计合规性检查

| 检查项 | 结论 |
|--------|------|
| `set`/`get` 均在 ActionType 枚举中 | ✅ |
| `get_text` 废弃，不再新增 | ✅ |
| `set` data 格式 `key=${Return[-1]}` — 赋值表达式特殊例外 | ✅ |
| `get` 三模式：model+DataID → 模型模式；选择器 → UI 文本；标识符 → named | ✅ |
| UI 元素取值推荐 `get ModelName D001`（模型模式），选择器模式为低级补充 | ✅ |
| Return 引用在 verify 数据表 field 中 | ✅ |

---

## AC11-001: set 保存多个同类值

**测试用例名称**: set 保存两个命名变量，互不干扰

**case/ac11_set_get.xml**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<cases>
  <case execute="是" id="AC11-001" title="set保存多个同类值" component_type="界面">
    <pre_process>
      <test_step action="navigate" model="" data="http://localhost:8000"/>
      <test_step action="type" model="LoginForm" data="L001"/>
      <test_step action="type" model="NavMenu" data="N001"/>
    </pre_process>
    <test_case>
      <test_step action="type" model="TestForm" data="T001"/>
      <test_step action="set" model="" data="first_result=${Return[-1]}"/>
      <test_step action="type" model="TestForm" data="T002"/>
      <test_step action="set" model="" data="second_result=${Return[-1]}"/>
      <test_step action="get" model="" data="first_result"/>
      <test_step action="verify" model="SetGetVerify" data="V001"/>
    </test_case>
    <post_process>
      <test_step action="close" model="" data=""/>
    </post_process>
  </case>
</cases>
```

**model/model.xml**（新增）:
```xml
<model name="SetGetVerify" servicename="">
  <element name="value" type="web">
    <type>text</type>
    <location type="id">formResult</location>
  </element>
</model>
```

**data/SetGetVerify_verify.xml**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<datatable name="SetGetVerify_verify">
  <row id="V001" remark="验证get读取first_result等于T001提交值">
    <field name="value">${Return[-1]}</field>
  </row>
</datatable>
```

**验收条件**:
- `first_result` 和 `second_result` 值彼此独立
- `get first_result` 后 `${Return[-1]}` 指向第一次提交值，verify 通过

---

## AC11-002: get 读取不存在的 key 报错

**case/ac11_get_error.xml**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<cases>
  <case execute="是" id="AC11-002" title="get读取不存在key报错" component_type="界面">
    <test_case>
      <test_step action="get" model="" data="undefined_key"/>
    </test_case>
  </case>
</cases>
```

**验收条件**:
- 步骤失败，错误信息包含变量名 `undefined_key`，不 silent fail

---

## AC11-003: get UI 文本获取模式（低级补充手段）

**测试用例名称**: get 选择器模式读取元素文本写入 history

> ⚠️ 此用例验证低级补充能力。常规业务用例应优先使用 `verify` + model + 数据表获取页面值。

**case/ac11_get_selector.xml**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<cases>
  <case execute="是" id="AC11-003" title="get选择器模式读取元素文本" component_type="界面">
    <pre_process>
      <test_step action="navigate" model="" data="http://localhost:8000"/>
      <test_step action="type" model="LoginForm" data="L001"/>
      <test_step action="type" model="NavMenu" data="N001"/>
    </pre_process>
    <test_case>
      <test_step action="type" model="TestForm" data="T001"/>
      <test_step action="get" model="" data="#formResult"/>
      <test_step action="verify" model="GetVerify" data="V001"/>
    </test_case>
    <post_process>
      <test_step action="close" model="" data=""/>
    </post_process>
  </case>
</cases>
```

**model/model.xml**（新增）:
```xml
<model name="GetVerify" servicename="">
  <element name="result" type="web">
    <type>text</type>
    <location type="id">formResult</location>
  </element>
</model>
```

**data/GetVerify_verify.xml**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<datatable name="GetVerify_verify">
  <row id="V001" remark="验证get选择器模式结果写入history">
    <field name="result">${Return[-1]}</field>
  </row>
</datatable>
```

**验收条件**:
- `get #formResult` 读取元素文本并写入 history
- `${Return[-1]}` 指向读取到的文本值，verify 通过

---

## AC11-004: get 模型模式读取 UI 元素值（推荐方式）

**测试用例名称**: get 通过 model + DataID 读取元素文本，返回 dict

**model/model.xml**（新增）:
```xml
<model name="GetModel" servicename="">
  <element name="formResult" type="web">
    <type>text</type>
    <location type="id">formResult</location>
  </element>
</model>
```

**data/GetModel.xml**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<datatable name="GetModel">
  <row id="G001" remark="读取formResult">
    <field name="formResult"></field>
  </row>
</datatable>
```

**case/ac11_get_model.xml**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<cases>
  <case execute="是" id="AC11-004" title="get模型模式读取元素值" component_type="界面">
    <pre_process>
      <test_step action="navigate" model="" data="http://localhost:8000"/>
      <test_step action="type" model="LoginForm" data="L001"/>
      <test_step action="type" model="NavMenu" data="N001"/>
    </pre_process>
    <test_case>
      <test_step action="type" model="TestForm" data="T001"/>
      <test_step action="get" model="GetModel" data="G001"/>
      <test_step action="verify" model="GetModelVerify" data="V001"/>
    </test_case>
    <post_process>
      <test_step action="close" model="" data=""/>
    </post_process>
  </case>
</cases>
```

**data/GetModelVerify_verify.xml**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<datatable name="GetModelVerify_verify">
  <row id="V001" remark="验证get模型模式返回dict">
    <field name="formResult">${Return[-1].formResult}</field>
  </row>
</datatable>
```

**验收条件**:
- `get GetModel G001` 读取元素文本，history 中返回值为 dict（`{"formResult": "..."}`)
- `${Return[-1].formResult}` 可正常解析，verify 通过

---

## rodski 开发需求

**需要开发**: T11-001 ~ T11-004  
**demo 开发**: 新增 `SetGetVerify`、`GetVerify`、`GetModel`、`GetModelVerify` 模型及对应数据表
