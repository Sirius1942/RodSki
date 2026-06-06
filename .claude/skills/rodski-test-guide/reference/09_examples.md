<!-- 自动生成 from rodski/docs/TEST_CASE_WRITING_GUIDE.md  请勿手工编辑 -->

## 9. 完整示例

### 9.1 项目结构

```text
product/DEMO/demo_site/
├── model/
│   └── model.xml
├── case/
│   └── demo_case.xml
├── data/
│   ├── globalvalue.xml
│   └── data.sqlite
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
  <group name="sqlite_db">
    <var name="type" value="sqlite"/>
    <var name="database" value="product/DEMO/demo_site/demo.db"/>
  </group>
</globalvalue>
```

### 9.4 data.sqlite（数据表）

所有测试数据（输入表和验证表）均存储在 `data/data.sqlite` 中。输入表 `table_kind='input'`，验证表 `table_kind='verify'`。

迁移命令：`rodski data import <module>`

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

  <case execute="是" id="c002" title="数据库查询" description="验证 DB 新语法" component_type="数据库">
    <test_case>
      <test_step action="DB" model="QuerySQL" data="Q001"/>
    </test_case>
  </case>
</cases>
```

### 9.7 运行命令

```bash
# 方式1：指定 case XML 文件
rodski run rodski-demo/DEMO/demo_full/case/demo_case.xml

# 方式2：指定 case 目录（执行所有 XML）
rodski run rodski-demo/DEMO/demo_full/case/

# 方式3：指定测试模块目录
rodski run rodski-demo/DEMO/demo_full/

# 按标签过滤（OR 匹配，命中任一即可）
rodski run case/ --tags smoke
rodski run case/ --tags "smoke,regression"

# 按优先级过滤
rodski run case/ --priority P0
rodski run case/ --priority "P0,P1"

# 排除标签
rodski run case/ --exclude-tags slow

# 组合过滤（标签 AND 优先级）
rodski run case/ --tags smoke --priority P0

# 执行后自动生成 HTML 报告
rodski run case/ --report html

# 无头模式
rodski run case/ --headless
```

---
