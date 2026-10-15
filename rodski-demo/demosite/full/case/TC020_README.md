# TC020: 多窗口和iframe测试

## 概述

TC020 展示如何使用 RodSki 进行多窗口和 iframe 切换测试，包括：
- 浏览器窗口切换
- iframe 切换
- 在不同上下文中进行操作和验证

## 前置条件

1. **测试页面**: 需要包含多窗口或 iframe 的测试页面
2. **浏览器驱动**: 已配置 Selenium WebDriver

## 使用说明

### 1. 窗口切换 (switch_window.py)

```xml
<!-- 切换到第二个窗口 (索引从0开始) -->
<test_step action="run" model="" data="fun/switch_window.py 1"/>

<!-- 切换回第一个窗口 -->
<test_step action="run" model="" data="fun/switch_window.py 0"/>
```

**参数说明**:
- 参数: 窗口索引 (整数，从 0 开始)
- 索引 0: 第一个窗口 (通常是主窗口)
- 索引 1: 第二个窗口
- 以此类推

**使用场景**:
- 点击链接打开新窗口后需要切换
- 多窗口并行操作
- 弹出窗口处理

### 2. iframe 切换 (switch_frame.py)

```xml
<!-- 通过 name 或 id 切换到 iframe -->
<test_step action="run" model="" data="fun/switch_frame.py contentFrame"/>

<!-- 通过索引切换到第一个 iframe -->
<test_step action="run" model="" data="fun/switch_frame.py 0"/>

<!-- 返回主文档 -->
<test_step action="run" model="" data="fun/switch_frame.py default"/>
```

**参数说明**:
- `frame_name_or_id`: iframe 的 name 或 id 属性值
- `数字`: iframe 索引 (从 0 开始)
- `default`: 返回主文档 (退出 iframe)

**使用场景**:
- 页面包含嵌入的 iframe
- 需要在 iframe 内操作元素
- 多层嵌套 iframe

## 完整示例

### 多窗口测试

```xml
<case execute="是" id="TC020" title="多窗口测试" component_type="界面">
    <pre_process>
        <test_step action="navigate" model="" data="http://localhost:8000/multi-window"/>
    </pre_process>
    <test_case>
        <!-- 在主窗口点击按钮打开新窗口 -->
        <test_step action="type" model="WindowTest" data="W001"/>
        <test_step action="wait" model="" data="2"/>
        
        <!-- 切换到新窗口 -->
        <test_step action="run" model="" data="fun/switch_window.py 1"/>
        <test_step action="wait" model="" data="1"/>
        
        <!-- 在新窗口中验证内容 -->
        <test_step action="verify" model="NewWindow" data="V001"/>
        
        <!-- 切换回主窗口 -->
        <test_step action="run" model="" data="fun/switch_window.py 0"/>
        <test_step action="wait" model="" data="1"/>
        
        <!-- 在主窗口继续操作 -->
        <test_step action="verify" model="WindowTest" data="V001"/>
    </test_case>
    <post_process>
        <test_step action="close" model="" data=""/>
    </post_process>
</case>
```

### iframe 测试

```xml
<case execute="是" id="TC020" title="iframe测试" component_type="界面">
    <pre_process>
        <test_step action="navigate" model="" data="http://localhost:8000/iframe-test"/>
    </pre_process>
    <test_case>
        <!-- 验证主页面内容 -->
        <test_step action="verify" model="IframeTest" data="I001"/>
        
        <!-- 切换到 iframe (通过 name) -->
        <test_step action="run" model="" data="fun/switch_frame.py contentFrame"/>
        <test_step action="wait" model="" data="1"/>
        
        <!-- 在 iframe 内操作 -->
        <test_step action="verify" model="IframeContent" data="V001"/>
        <test_step action="type" model="IframeForm" data="F001"/>
        
        <!-- 返回主文档 -->
        <test_step action="run" model="" data="fun/switch_frame.py default"/>
        <test_step action="wait" model="" data="1"/>
        
        <!-- 在主页面继续操作 -->
        <test_step action="verify" model="IframeTest" data="I002"/>
    </test_case>
    <post_process>
        <test_step action="close" model="" data=""/>
    </post_process>
</case>
```

### 多层嵌套 iframe

```xml
<!-- 切换到外层 iframe -->
<test_step action="run" model="" data="fun/switch_frame.py outerFrame"/>

<!-- 切换到内层 iframe (相对于当前 iframe) -->
<test_step action="run" model="" data="fun/switch_frame.py innerFrame"/>

<!-- 返回主文档 (一次性退出所有 iframe) -->
<test_step action="run" model="" data="fun/switch_frame.py default"/>
```

## 脚本说明

### switch_window.py
- **功能**: 切换到指定索引的浏览器窗口
- **参数**: 窗口索引 (整数，从 0 开始)
- **返回**: 打印当前窗口总数和切换结果
- **错误处理**: 索引超出范围时报错

### switch_frame.py
- **功能**: 切换到指定的 iframe 或返回主文档
- **参数**: 
  - frame name/id (字符串)
  - 索引 (数字字符串)
  - "default" (返回主文档)
- **返回**: 打印切换结果
- **错误处理**: iframe 不存在时报错

## 模型定义示例

```xml
<!-- 多窗口测试模型 -->
<model name="WindowTest" type="ui" servicename="">
    <element name="openWindowBtn" type="button">
        <location type="id">openWindowBtn</location>
    </element>
    <element name="mainWindowTitle" type="text">
        <location type="id">mainTitle</location>
    </element>
</model>

<model name="NewWindow" type="ui" servicename="">
    <element name="newWindowTitle" type="text">
        <location type="id">newWindowTitle</location>
    </element>
    <element name="newWindowContent" type="text">
        <location type="id">newWindowContent</location>
    </element>
</model>

<!-- iframe测试模型 -->
<model name="IframeTest" type="ui" servicename="">
    <element name="mainContent" type="text">
        <location type="id">mainContent</location>
    </element>
</model>

<model name="IframeContent" type="ui" servicename="">
    <element name="iframeTitle" type="text">
        <location type="id">iframeTitle</location>
    </element>
    <element name="iframeText" type="text">
        <location type="id">iframeText</location>
    </element>
</model>
```

## 数据定义示例

```xml
<!-- 多窗口测试数据 -->
<datatable name="WindowTest">
    <row id="W001" remark="打开新窗口">
        <field name="openWindowBtn">click</field>
    </row>
</datatable>

<datatable name="NewWindow_verify">
    <row id="V001" remark="验证新窗口内容">
        <field name="newWindowTitle">新窗口标题</field>
        <field name="newWindowContent">这是新窗口的内容</field>
    </row>
</datatable>

<!-- iframe测试数据 -->
<datatable name="IframeContent_verify">
    <row id="V001" remark="验证iframe内容">
        <field name="iframeTitle">iframe标题</field>
        <field name="iframeText">这是iframe中的内容</field>
    </row>
</datatable>
```

## 注意事项

1. **窗口索引**: 窗口索引从 0 开始，需要确保索引不超出范围
2. **等待时间**: 切换窗口或 iframe 后建议添加 wait 确保页面加载完成
3. **iframe 定位**: iframe 可以通过 name、id 或索引定位
4. **返回主文档**: 使用 `default` 参数可以一次性退出所有嵌套 iframe
5. **错误处理**: 如果窗口或 iframe 不存在，脚本会报错并退出
6. **上下文切换**: 切换窗口或 iframe 后，所有后续操作都在新上下文中执行

## 常见问题

### Q1: 如何知道当前有多少个窗口？
A: `switch_window.py` 会打印当前窗口总数，也可以在脚本中添加日志。

### Q2: 如何处理动态打开的窗口？
A: 在打开新窗口后添加 `wait` 步骤，确保窗口完全加载后再切换。

### Q3: iframe 切换失败怎么办？
A: 检查 iframe 的 name/id 是否正确，或尝试使用索引方式切换。

### Q4: 如何在多个 iframe 之间切换？
A: 每次切换前先返回主文档 (`default`)，再切换到目标 iframe。

## 扩展建议

可以创建更多窗口管理脚本：
- `close_window.py` - 关闭指定窗口
- `get_window_title.py` - 获取窗口标题
- `switch_to_window_by_title.py` - 根据标题切换窗口
- `get_frame_count.py` - 获取 iframe 数量
- `switch_to_parent_frame.py` - 切换到父级 iframe
