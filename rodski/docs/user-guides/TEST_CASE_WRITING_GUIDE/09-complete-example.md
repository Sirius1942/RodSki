# 9. 完整示例

> **来源**: RodSki 测试用例编写指南 v3.4  
> 本文档为独立章节，完整指南请见 [TEST_CASE_WRITING_GUIDE.md](../TEST_CASE_WRITING_GUIDE.md)

---


### 9.1 项目结构

```
product/DEMO/demo_site/
├── model/
│   └── model.xml
├── case/
│   └── demo_case.xml
├── data/
│   ├── globalvalue.xml
│   ├── Login.xml
│   ├── Login_verify.xml
│   └── QuerySQL.xml
├── fun/
└── result/
```

### 9.2 model.xml

```xml
<?xml version="1.0" encoding="UTF-8"?>
<models>
<model name="Login" servicename="">
    <element name="username" type="web">
        <type>input</type>
        <location type="id">username</location>
    </element>
    <element name="password" type="web">
        <type>input</type>
        <location type="id">password</location>
    </element>
    <element name="loginBtn" type="web">
        <type>button</type>
        <location type="id">login-btn</location>
    </element>
</model>
</models>
```

### 9.3 globalvalue.xml

```xml
<?xml version="1.0" encoding="UTF-8"?>
<globalvalue>
  <group name="DefaultValue">
    <var name="URL" value="http://127.0.0.1:5555"/>
    <var name="WaitTime" value="2"/>
  </group>
  <group name="demodb">
    <var name="type" value="sqlite"/>
    <var name="database" value="product/DEMO/demo_site/demo.db"/>
  </group>
</globalvalue>
```

### 9.4 Login.xml（数据表）

```xml
<?xml version="1.0" encoding="UTF-8"?>
<datatable name="Login">
  <row id="L001" remark="管理员">
    <field name="username">admin</field>
    <field name="password">admin123</field>
    <field name="loginBtn">click</field>
  </row>
</datatable>
```

### 9.5 Login_verify.xml（验证数据表）

```xml
<?xml version="1.0" encoding="UTF-8"?>
<datatable name="Login_verify">
  <row id="V001" remark="验证管理员登录">
    <field name="welcome_text">欢迎, admin</field>
  </row>
</datatable>
```

### 9.6 demo_case.xml（用例）

```xml
<?xml version="1.0" encoding="UTF-8"?>
<cases>
  <case execute="是" id="c001" title="登录" description="验证登录" component_type="界面">
    <pre_process>
      <test_step action="navigate" model="" data="GlobalValue.DefaultValue.URL/login"/>
    </pre_process>
    <test_case>
      <test_step action="type" model="Login" data="L001"/>
      <test_step action="verify" model="Login" data="V001"/>
    </test_case>
    <post_process>
      <test_step action="close" model="" data=""/>
    </post_process>
  </case>
</cases>
```

### 9.7 运行命令

```bash
cd rodski

# 方式1：指定 case XML 文件
python ski_run.py product/DEMO/demo_site/case/demo_case.xml

# 方式2：指定 case 目录（执行所有 XML）
python ski_run.py product/DEMO/demo_site/case/

# 方式3：指定测试模块目录
python ski_run.py product/DEMO/demo_site/
```

---

