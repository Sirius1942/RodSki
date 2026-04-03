# 13. if/else 流程控制

> **来源**: RodSki 测试用例编写指南 v3.4  
> 本文档为独立章节，完整指南请见 [TEST_CASE_WRITING_GUIDE.md](../TEST_CASE_WRITING_GUIDE.md)

---


### 13.1 概述

if/else 是 RodSki XML DSL 的流程控制扩展，允许单个用例内处理条件分支，实现「一个用例看完整业务流程」的设计目标。

**基础语法：**

```xml
<if condition="条件表达式">
  <test_step action="动作" model="模型" data="数据"/>
  <!-- 更多 then 分支步骤 -->
  <else>
    <test_step action="动作" model="模型" data="数据"/>
    <!-- 更多 else 分支步骤 -->
  </else>
</if>
```

**规则：**
- `<if>` 可出现在 `pre_process`、`test_case`、`post_process` 任一阶段内
- `<else>` 可选，省略时条件为 False 则跳过
- `<if>` 内最多嵌套 2 层（ CORE_DESIGN_CONSTRAINTS.md §12 约束）
- `condition` 属性最长 200 字符

---

### 13.2 支持的条件类型

#### 类型 1：verify_fail — 上一步验证结果

根据前一个 `verify` 动作是否失败来决定分支，最常用。

```xml
<test_step action="verify" model="OrderForm" data="V001"/>

<if condition="verify_fail">
  <test_step action="type" model="AppendDialog" data="A001"/>
  <test_step action="click" model="AppendDialog" data="Confirm"/>
  <else>
    <test_step action="click" model="OrderForm" data="Next"/>
  </else>
</if>
```

#### 类型 2：${Return[N].field ==/contains value} — Return 字段判断

基于历史 API 返回值或 `get_text` 结果进行判断。

```xml
<!-- 接口状态码判断 -->
<test_step action="DB" model="API" data="query_order"/>

<if condition="${Return[-1].status == 200}">
  <test_step action="verify" model="OrderResult" data="V002"/>
  <else>
    <test_step action="screenshot" data="api_error.png"/>
  </else>
</if>

<!-- 包含判断（模糊匹配） -->
<if condition="${Return[-1].msg contains '追加'}">
  <test_step action="click" model="AppendConfirm" data="Yes"/>
</if>

<!-- 指定索引（-1=上一个，0=第一个） -->
<if condition="${Return[0].code != 0}">
  <test_step action="screenshot" data="first_call_failed.png"/>
</if>
```

支持比较操作符：`==`、`!=`、`>`、`<`、`>=`、`<=`、`contains`

#### 类型 3：element_exists(locator) — 元素可见

页面元素出现时执行分支。

```xml
<!-- 追加对话框弹出则处理 -->
<if condition="element_exists(#append_dialog)">
  <test_step action="type" model="AppendDialog" data="A001"/>
  <test_step action="click" model="AppendDialog" data="Submit"/>
</if>

<!-- 有错误提示时截图，无错误时继续 -->
<if condition="element_exists(.toast-error)">
  <test_step action="screenshot" data="error_toast.png"/>
  <else>
    <test_step action="click" model="MainPage" data="NextStep"/>
  </else>
</if>
```

#### 类型 4：element_not_exists(locator) — 元素不可见

元素不存在时执行分支。

```xml
<!-- 没有错误提示时才继续提交 -->
<if condition="element_not_exists(.error-msg)">
  <test_step action="click" model="Form" data="Submit"/>
</if>

<!-- 无弹窗走正常流程，有弹窗处理 -->
<if condition="element_not_exists(#modal-overlay)">
  <test_step action="click" model="Page" data="Continue"/>
  <else>
    <test_step action="click" model="Modal" data="Close"/>
  </else>
</if>
```

#### 类型 5：text_contains(text) — 页面含/不含文字

页面文本中包含指定文字时触发。

```xml
<!-- 页面出现"追加"文字则处理追加逻辑 -->
<if condition="text_contains('追加询价单')">
  <test_step action="type" model="AppendInput" data="A001"/>
  <test_step action="click" model="AppendInput" data="OK"/>
</if>

<!-- 没有"失败"字样才继续 -->
<if condition="text_not_contains('失败')">
  <test_step action="screenshot" data="operation_success.png"/>
</if>
```

#### 类型 6：变量比较 — var ==/!=/>/< value

```xml
<!-- 配合 set 关键字设置的变量 -->
<if condition="retry_count > 0">
  <test_step action="click" model="RetryButton" data="Retry"/>
</if>

<if condition="error_type == 'timeout'">
  <test_step action="navigate" model="LoginPage" data="refresh"/>
</if>
```

---

### 13.3 逻辑组合

```xml
<!-- AND：多个条件同时满足 -->
<if condition="element_exists(#dialog) AND text_contains('追加')">
  <test_step action="click" model="Dialog" data="Confirm"/>
</if>

<!-- OR：任一条件满足 -->
<if condition="verify_fail OR element_exists(.error-banner)">
  <test_step action="screenshot" data="error_state.png"/>
</if>

<!-- NOT：取反 -->
<if condition="NOT element_exists(#loading-spinner)">
  <test_step action="click" model="Page" data="Submit"/>
</if>

<!-- 混合组合 -->
<if condition="element_exists(#append_dialog) AND text_contains('追加') AND NOT verify_fail">
  <test_step action="type" model="AppendForm" data="A001"/>
</if>
```

---

### 13.4 完整用例示例

```xml
<?xml version="1.0" encoding="UTF-8"?>
<cases>
  <case id="ORDER_001" title="询价单追加对话框处理" execute="是">
    <metadata>
      <metadata updated_at="2026-04-02"/>
    </metadata>

    <pre_process>
      <test_step action="navigate" model="LoginPage" data="url"/>
      <test_step action="type" model="LoginForm" data="credentials"/>
      <test_step action="click" model="LoginForm" data="LoginBtn"/>
    </pre_process>

    <test_case>
      <!-- 填写询价单 -->
      <test_step action="type" model="OrderForm" data="VIN001"/>
      <test_step action="type" model="OrderForm" data="PartData"/>

      <!-- 提交并验证 -->
      <test_step action="click" model="OrderForm" data="Submit"/>
      <test_step action="verify" model="OrderResult" data="V001"/>

      <!-- 根据 verify 结果处理追加对话框 -->
      <if condition="verify_fail">
        <test_step action="type" model="AppendDialog" data="ExtraItems"/>
        <test_step action="click" model="AppendDialog" data="ConfirmAppend"/>
        <else>
          <test_step action="click" model="OrderForm" data="NextStep"/>
        </else>
      </if>

      <!-- 根据页面状态再次分支 -->
      <if condition="element_exists(#confirm_modal)">
        <test_step action="click" model="ConfirmModal" data="Yes"/>
        <else>
          <test_step action="navigate" model="OrderList" data="back"/>
        </else>
      </if>

      <!-- 最终验证 -->
      <test_step action="verify" model="FinalResult" data="V002"/>
    </test_case>

    <post_process>
      <test_step action="screenshot" data="final_state.png"/>
      <test_step action="close" model="" data=""/>
    </post_process>
  </case>
</cases>
```

---

### 13.5 错误处理

条件表达式无法评估时，框架会：

1. 自动截图保存到 `results/<run>/screenshots/`
2. 记录详细错误日志（含条件内容、错误原因）
3. 跳过该 if/else 块，继续执行后续步骤

日志示例：

```
[IF] 条件无法评估: condition=element_exists(#append_dialog)
   错误: 'NoneType' object has no attribute 'locate_element'
   截图: screenshots/if_cond_failed_3a7f2c1d.png
   建议: Agent 检查条件语法或页面状态
   可用操作: 调整条件 / 跳过此分支 / 插入 cleanup 步骤
```

---

### 13.6 约束速查

| 约束 | 值 |
|------|-----|
| 最大嵌套层数 | 2 |
| condition 最大长度 | 200 字符 |
| else 分支 | 可选 |
| 支持的阶段 | pre_process / test_case / post_process |

---

