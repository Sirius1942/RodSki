# RodSki测试用例编写实战经验

**版本**: v1.0
**日期**: 2026-03-24
**基于**: demo_full项目实战总结

---

## 1. 核心经验

### 1.1 先验证XSD再运行
```bash
# 避免运行时才发现格式错误
xmllint --noout --schema rodski/schemas/case.xsd case/demo_case.xml
xmllint --noout --schema rodski/schemas/model.xsd model/model.xml
```

### 1.2 模型元素name必须与数据字段name完全一致
```xml
<!-- model.xml -->
<element name="username" type="web">...</element>

<!-- data/LoginForm.xml -->
<field name="username">admin</field>  <!-- 必须完全一致，区分大小写 -->
```

### 1.3 case属性常见错误
- ❌ `name="测试"` → ✅ `title="测试"`
- ❌ `component_type="其他"` → ✅ `component_type="界面"`
- ❌ `<test_step desc="描述">` → ✅ 不要用desc属性

---

## 2. 关键字使用技巧

### 2.1 type关键字 - UI批量输入
**原理**：遍历模型所有元素，从数据表取值，自动识别操作类型

**技巧**：
- 按钮元素的值用 `click`
- 下拉框元素的值用选项的value
- 输入框元素的值用文本内容

```xml
<!-- 数据表 -->
<field name="username">admin</field>
<field name="role">admin</field>        <!-- 选择value=admin的选项 -->
<field name="submitBtn">click</field>   <!-- 点击按钮 -->
```

### 2.2 verify关键字 - 自动查找验证表
**技巧**：verify会自动查找 `{模型名}_verify.xml`

```xml
<!-- 用例中 -->
<test_step action="verify" model="Dashboard" data="V001"/>

<!-- 框架自动查找 data/Dashboard_verify.xml -->
```

### 2.3 send关键字 - API接口测试
**接口模型保留字段**：
- `_method` - HTTP方法
- `_url` - 请求地址
- `_header_*` - 请求头

```xml
<model name="LoginAPI">
    <element name="_method" type="interface">
        <location type="static">POST</location>
    </element>
    <element name="_url" type="interface">
        <location type="static">http://localhost:8000/api/login</location>
    </element>
</model>
```

---

## 3. 常见问题快速定位

### 3.1 "模型不存在"
**检查顺序**：
1. model.xml中是否定义了该模型
2. 模型name拼写是否正确
3. 文件是否保存

### 3.2 "数据不存在"
**检查顺序**：
1. 数据文件名是否与模型名一致
2. row的id是否匹配
3. field的name是否与模型元素name一致

### 3.3 "no such column"
**原因**：SQL中的列名与实际表结构不一致

**快速验证**：
```bash
sqlite3 demo.db ".schema orders"  # 查看表结构
```

---

## 4. 调试技巧

### 4.1 逐步验证法
1. 先验证XSD格式
2. 再验证模型定义
3. 最后验证数据匹配

### 4.2 简化用例调试
遇到问题时，先创建最小用例验证：
```xml
<case execute="是" id="TEST" title="最小测试" component_type="界面">
    <test_case>
        <test_step action="navigate" model="" data="http://localhost:8000"/>
    </test_case>
</case>
```

### 4.3 查看测试结果
```bash
# 结果保存在 result/ 目录
ls -lt result/  # 查看最新结果
```

---

## 5. 性能优化经验

### 5.1 避免冗余等待
- ❌ 每步都加wait
- ✅ 框架有统一等待机制，只在必要时显式wait

### 5.2 复用前置处理
```xml
<pre_process>
    <test_step action="navigate" model="" data="http://localhost:8000"/>
    <test_step action="type" model="LoginForm" data="L001"/>
</pre_process>
```

---

## 6. 数据管理技巧

### 6.1 数据复用
一个数据表可以有多个row，用不同id区分：
```xml
<datatable name="LoginForm">
    <row id="L001" remark="管理员">
        <field name="username">admin</field>
    </row>
    <row id="L002" remark="普通用户">
        <field name="username">user</field>
    </row>
</datatable>
```

### 6.2 GlobalValue使用
```xml
<group name="env">
    <var name="base_url" value="http://localhost:8000"/>
</group>
```

引用：`GlobalValue.env.base_url`

---

## 7. CLI功能测试

### 7.1 基本运行
```bash
# 运行测试
python3 ski_run.py case/demo_case.xml

# 无头模式
python3 ski_run.py case/demo_case.xml --headless

# 指定浏览器
python3 ski_run.py case/demo_case.xml --browser firefox
```

### 7.2 结果查看
```bash
# 查看最新结果
ls -lt result/

# 查看结果内容
cat result/result_*.xml
```

---

## 8. 检查清单

**编写前**：
- [ ] 确认测试目标
- [ ] 设计模型结构

**编写中**：
- [ ] case用title不用name
- [ ] test_step只用action/model/data
- [ ] 模型name与数据name一致

**编写后**：
- [ ] XSD校验通过
- [ ] 本地运行通过

---

**编写者**：基于demo_full实战经验
**适用版本**：RodSki v3.0+
