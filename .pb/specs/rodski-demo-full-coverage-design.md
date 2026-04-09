# RodSki 全功能覆盖设计方案

**创建日期**: 2026-04-09  
**目标**: 在 rodski-demo 项目中实验和展示 RodSki 的所有功能  
**版本**: v1.0

---

## 📋 目录

1. [功能清单](#功能清单)
2. [当前覆盖情况](#当前覆盖情况)
3. [缺失功能补充方案](#缺失功能补充方案)
4. [测试用例设计](#测试用例设计)
5. [实施计划](#实施计划)

---

## 功能清单

### 1. 核心关键字 (18个)

| 关键字 | 用途 | 优先级 |
|--------|------|--------|
| `navigate` | 页面导航 | P0 |
| `type` | UI批量输入 | P0 |
| `verify` | 批量验证 | P0 |
| `send` | HTTP请求 | P0 |
| `DB` | 数据库操作 | P0 |
| `close` | 关闭浏览器 | P0 |
| `wait` | 等待 | P1 |
| `get` | 三模式取值 | P1 |
| `set` | 命名变量 | P1 |
| `run` | 执行脚本 | P1 |
| `launch` | 启动应用 | P1 |
| `evaluate` | JS表达式 | P2 |
| `assert` | 断言 | P2 |
| `screenshot` | 截图 | P2 |
| `upload_file` | 文件上传 | P2 |
| `clear` | 清空输入 | P2 |
| `get_text` | 获取文本(已废弃) | P3 |
| `check` | verify别名 | P3 |

### 2. 定位器类型 (6种)

| 定位器 | 说明 | 平台 | 优先级 |
|--------|------|------|--------|
| `id` | ID定位 | Web/Mobile | P0 |
| `css` | CSS选择器 | Web | P0 |
| `xpath` | XPath | Web/Mobile | P1 |
| `name` | Name属性 | Web/Mobile | P1 |
| `vision` | 视觉语义定位 | Web/Desktop | P1 |
| `vision_bbox` | 视觉坐标定位 | Web/Desktop | P1 |

### 3. 高级特性 (10项)

| 特性 | 说明 | 优先级 |
|------|------|--------|
| Auto Capture | type/send自动提取返回值 | P0 |
| Return引用 | Return[-1]引用上一步 | P0 |
| set/get命名访问 | 命名变量存取 | P0 |
| expect_fail | 负面测试标记 | P0 |
| GlobalValue | 全局变量 | P0 |
| evaluate结构化返回 | JS返回对象 | P1 |
| pre/post_process | 前后置处理 | P1 |
| 数据驱动 | 模型+数据分离 | P0 |
| 并发执行 | 多用例并行 | P2 |
| 重试机制 | 失败重试 | P2 |

### 4. UI 动作关键字 (扩展)

| 动作 | 说明 | 优先级 |
|------|------|--------|
| hover | 鼠标悬停 | P1 |
| double_click | 双击 | P1 |
| right_click | 右键 | P1 |
| scroll | 滚动 | P1 |
| drag | 拖拽 | P1 |
| switch_window | 切换窗口 | P2 |
| switch_frame | 切换iframe | P2 |

---

## 当前覆盖情况

### ✅ 已覆盖功能 (15个测试用例)

| 用例ID | 功能点 | 覆盖内容 |
|--------|--------|---------|
| TC001 | Web登录 | navigate, type |
| TC002 | 看板验证 | verify, pre_process |
| TC003 | 表单操作 | type多控件 |
| TC004 | API登录 | send, verify (接口) |
| TC005 | API查询 | send GET |
| TC006 | 数据库 | DB关键字 |
| TC007 | 代码执行 | run关键字 |
| TC008 | UI动作 | hover, double_click, right_click, scroll, drag |
| TC009 | Return引用 | Return[-1] |
| TC009A | history连续性 | 跨步骤引用 |
| TC010 | set/get | 命名变量 |
| TC011 | get选择器 | get #selector |
| TC012 | evaluate | 结构化返回 |
| TC012A | get报错 | expect_fail (缺标记) |
| TC012B | get模型 | get ModelName D001 |
| TC013 | type Auto Capture | 自动提取 |
| TC014 | send Auto Capture | 接口自动提取 |
| TC014A | Capture失败 | expect_fail (缺标记) |
| TC015 | 结构化日志 | execution_summary |

**覆盖率**: 约 60%

---

## 缺失功能补充方案

### 🔴 P0 - 核心缺失 (必须补充)

#### 1. 定位器类型覆盖不足

**缺失**:
- xpath 定位器
- name 定位器
- vision 视觉定位
- vision_bbox 坐标定位

**补充方案**:
```xml
<!-- TC016: 多种定位器测试 -->
<case execute="是" id="TC016" title="定位器类型覆盖" component_type="界面">
    <pre_process>
        <test_step action="navigate" model="" data="http://localhost:8000"/>
        <test_step action="type" model="LoginForm" data="L001"/>
    </pre_process>
    <test_case>
        <!-- XPath 定位 -->
        <test_step action="type" model="LocatorTest_XPath" data="X001"/>
        <!-- Name 定位 -->
        <test_step action="type" model="LocatorTest_Name" data="N001"/>
        <!-- CSS 定位 -->
        <test_step action="type" model="LocatorTest_CSS" data="C001"/>
        <test_step action="verify" model="LocatorTest" data="V001"/>
    </test_case>
    <post_process>
        <test_step action="close" model="" data=""/>
    </post_process>
</case>
```

#### 2. 关键字缺失

**缺失**:
- `assert` 断言
- `screenshot` 截图
- `upload_file` 文件上传
- `clear` 清空输入
- `wait` 等待（虽然在用，但没有独立测试）

**补充方案**:
```xml
<!-- TC017: 关键字覆盖测试 -->
<case execute="是" id="TC017" title="关键字完整覆盖" component_type="界面">
    <pre_process>
        <test_step action="navigate" model="" data="http://localhost:8000"/>
        <test_step action="type" model="LoginForm" data="L001"/>
        <test_step action="type" model="NavMenu" data="N001"/>
    </pre_process>
    <test_case>
        <!-- wait 等待 -->
        <test_step action="wait" model="" data="2"/>
        
        <!-- clear 清空 -->
        <test_step action="type" model="TestForm" data="T001"/>
        <test_step action="clear" model="TestForm" data="C001"/>
        
        <!-- screenshot 截图 -->
        <test_step action="screenshot" model="" data="test_page.png"/>
        
        <!-- assert 断言 -->
        <test_step action="type" model="TestForm" data="T002"/>
        <test_step action="assert" model="TestForm" data="A001"/>
        
        <!-- upload_file 文件上传 -->
        <test_step action="upload_file" model="UploadForm" data="U001"/>
        <test_step action="verify" model="UploadForm" data="V001"/>
    </test_case>
    <post_process>
        <test_step action="close" model="" data=""/>
    </post_process>
</case>
```

#### 3. 视觉定位功能

**缺失**: 完全没有视觉定位示例

**补充方案**:
```xml
<!-- TC018: 视觉定位测试 -->
<case execute="是" id="TC018" title="视觉定位功能" component_type="界面">
    <pre_process>
        <test_step action="navigate" model="" data="http://localhost:8000"/>
    </pre_process>
    <test_case>
        <!-- 语义定位 -->
        <test_step action="type" model="VisionLogin" data="L001"/>
        
        <!-- 坐标定位 -->
        <test_step action="type" model="VisionCoordinate" data="C001"/>
        
        <test_step action="verify" model="Dashboard" data="V001"/>
    </test_case>
    <post_process>
        <test_step action="close" model="" data=""/>
    </post_process>
</case>
```

**模型定义**:
```xml
<model name="VisionLogin" type="ui" servicename="">
    <element name="username" locator="vision:用户名输入框"/>
    <element name="password" locator="vision:密码输入框"/>
    <element name="loginBtn" locator="vision:登录按钮"/>
</model>

<model name="VisionCoordinate" type="ui" servicename="">
    <element name="submitBtn" locator="vision_bbox:100,200,150,250"/>
</model>
```

#### 4. 桌面自动化

**缺失**: 没有 `launch` 关键字示例

**补充方案**:
```xml
<!-- TC019: 桌面应用测试 -->
<case execute="是" id="TC019" title="桌面应用自动化" component_type="界面">
    <test_case>
        <!-- 启动应用 -->
        <test_step action="launch" model="" data="notepad.exe"/>
        <test_step action="wait" model="" data="2"/>
        
        <!-- 执行桌面操作脚本 -->
        <test_step action="run" model="desktop_ops" data="type_text.py Hello"/>
        <test_step action="run" model="desktop_ops" data="key_combo.py Ctrl+S"/>
        
        <!-- 关闭应用 -->
        <test_step action="run" model="desktop_ops" data="key_combo.py Alt+F4"/>
    </test_case>
</case>
```

---

### 🟡 P1 - 重要补充

#### 5. 窗口和iframe切换

**补充方案**:
```xml
<!-- TC020: 窗口切换测试 -->
<case execute="是" id="TC020" title="多窗口和iframe" component_type="界面">
    <test_case>
        <test_step action="navigate" model="" data="http://localhost:8000/multi-window"/>
        
        <!-- 打开新窗口 -->
        <test_step action="type" model="WindowTest" data="W001"/>
        
        <!-- 切换窗口 -->
        <test_step action="run" model="" data="fun/switch_window.py 1"/>
        <test_step action="verify" model="NewWindow" data="V001"/>
        
        <!-- 切换回主窗口 -->
        <test_step action="run" model="" data="fun/switch_window.py 0"/>
        
        <!-- iframe 切换 -->
        <test_step action="navigate" model="" data="http://localhost:8000/iframe-test"/>
        <test_step action="run" model="" data="fun/switch_frame.py contentFrame"/>
        <test_step action="verify" model="IframeContent" data="V001"/>
    </test_case>
    <post_process>
        <test_step action="close" model="" data=""/>
    </post_process>
</case>
```

#### 6. 复杂数据引用

**补充方案**:
```xml
<!-- TC021: 复杂数据引用 -->
<case execute="是" id="TC021" title="数据引用完整测试" component_type="界面">
    <test_case>
        <!-- GlobalValue 引用 -->
        <test_step action="navigate" model="" data="GlobalValue.DefaultValue.URL"/>
        
        <!-- Return 引用 -->
        <test_step action="type" model="TestForm" data="T001"/>
        <test_step action="set" model="" data="result1=${Return[-1]}"/>
        
        <!-- 嵌套引用 -->
        <test_step action="type" model="TestForm" data="T002"/>
        <test_step action="set" model="" data="result2=${Return[-1].fieldName}"/>
        
        <!-- 命名访问 -->
        <test_step action="get" model="" data="result1"/>
        <test_step action="verify" model="DataRefVerify" data="V001"/>
    </test_case>
    <post_process>
        <test_step action="close" model="" data=""/>
    </post_process>
</case>
```

#### 7. 负面测试完善

**补充方案**:
```xml
<!-- TC022: 负面测试集合 -->
<case execute="是" id="TC022" title="元素不存在" expect_fail="是" component_type="界面">
    <test_case>
        <test_step action="navigate" model="" data="http://localhost:8000"/>
        <test_step action="type" model="NonExistentModel" data="D001"/>
    </test_case>
</case>

<!-- TC023: 接口错误 -->
<case execute="是" id="TC023" title="API错误响应" expect_fail="是" component_type="接口">
    <test_case>
        <test_step action="send" model="ErrorAPI" data="D001"/>
    </test_case>
</case>

<!-- TC024: 数据库错误 -->
<case execute="是" id="TC024" title="SQL语法错误" expect_fail="是" component_type="数据库">
    <test_case>
        <test_step action="DB" model="demo_db" data="QuerySQL.BadSQL"/>
    </test_case>
</case>
```

---

## 测试用例设计

### 新增测试用例规划

| 用例ID | 标题 | 覆盖功能 | 优先级 |
|--------|------|---------|--------|
| TC016 | 定位器类型覆盖 | xpath, name, css | P0 |
| TC017 | 关键字完整覆盖 | wait, clear, screenshot, assert, upload_file | P0 |
| TC018 | 视觉定位功能 | vision, vision_bbox | P0 |
| TC019 | 桌面应用自动化 | launch, desktop run | P0 |
| TC020 | 多窗口和iframe | switch_window, switch_frame | P1 |
| TC021 | 复杂数据引用 | GlobalValue, Return嵌套, 命名访问 | P1 |
| TC022-024 | 负面测试集合 | expect_fail 完整覆盖 | P1 |
| TC025 | 并发执行测试 | 多用例并行 | P2 |
| TC026 | 重试机制测试 | 失败重试配置 | P2 |

### 需要扩展的 demosite 功能

为了支持新测试用例，需要在 demosite 中添加：

1. **文件上传页面** (`/upload`)
   - 文件选择控件
   - 上传按钮
   - 上传结果显示

2. **多窗口测试页面** (`/multi-window`)
   - 打开新窗口按钮
   - 窗口标识信息

3. **iframe测试页面** (`/iframe-test`)
   - 嵌入iframe
   - iframe内容页面

4. **定位器测试页面** (`/locator-test`)
   - 包含各种定位器类型的元素
   - name属性元素
   - 复杂xpath路径元素

---

## 实施计划

### Phase 1: P0 核心补充 (1-2天)

**目标**: 补充核心缺失功能，达到 80% 覆盖率

1. **Day 1 上午**: 扩展 demosite
   - 添加文件上传页面
   - 添加定位器测试页面
   - 添加多窗口/iframe测试页面

2. **Day 1 下午**: 编写测试用例
   - TC016: 定位器类型覆盖
   - TC017: 关键字完整覆盖
   - TC018: 视觉定位功能

3. **Day 2 上午**: 桌面自动化
   - TC019: 桌面应用测试
   - 编写桌面操作脚本

4. **Day 2 下午**: 测试验证
   - 运行所有新增用例
   - 修复发现的问题
   - 更新文档

### Phase 2: P1 重要补充 (1天)

**目标**: 完善高级特性，达到 90% 覆盖率

1. **上午**: 高级特性
   - TC020: 多窗口和iframe
   - TC021: 复杂数据引用

2. **下午**: 负面测试
   - TC022-024: 负面测试集合
   - 修复 TC012A, TC014A 的 expect_fail 标记

### Phase 3: P2 可选补充 (0.5天)

**目标**: 补充边缘特性，达到 95%+ 覆盖率

1. TC025: 并发执行测试
2. TC026: 重试机制测试
3. 性能测试用例

---

## 功能覆盖矩阵

### 关键字覆盖

| 关键字 | 当前 | Phase 1 | Phase 2 | Phase 3 |
|--------|------|---------|---------|---------|
| navigate | ✅ | ✅ | ✅ | ✅ |
| type | ✅ | ✅ | ✅ | ✅ |
| verify | ✅ | ✅ | ✅ | ✅ |
| send | ✅ | ✅ | ✅ | ✅ |
| DB | ✅ | ✅ | ✅ | ✅ |
| close | ✅ | ✅ | ✅ | ✅ |
| get | ✅ | ✅ | ✅ | ✅ |
| set | ✅ | ✅ | ✅ | ✅ |
| run | ✅ | ✅ | ✅ | ✅ |
| evaluate | ✅ | ✅ | ✅ | ✅ |
| wait | ⚠️ | ✅ | ✅ | ✅ |
| clear | ❌ | ✅ | ✅ | ✅ |
| screenshot | ❌ | ✅ | ✅ | ✅ |
| assert | ❌ | ✅ | ✅ | ✅ |
| upload_file | ❌ | ✅ | ✅ | ✅ |
| launch | ❌ | ✅ | ✅ | ✅ |

### 定位器覆盖

| 定位器 | 当前 | Phase 1 | Phase 2 |
|--------|------|---------|---------|
| id | ✅ | ✅ | ✅ |
| css | ⚠️ | ✅ | ✅ |
| xpath | ❌ | ✅ | ✅ |
| name | ❌ | ✅ | ✅ |
| vision | ❌ | ✅ | ✅ |
| vision_bbox | ❌ | ✅ | ✅ |

### 高级特性覆盖

| 特性 | 当前 | Phase 1 | Phase 2 |
|------|------|---------|---------|
| Auto Capture | ✅ | ✅ | ✅ |
| Return引用 | ✅ | ✅ | ✅ |
| set/get | ✅ | ✅ | ✅ |
| expect_fail | ⚠️ | ✅ | ✅ |
| GlobalValue | ✅ | ✅ | ✅ |
| evaluate结构化 | ✅ | ✅ | ✅ |
| pre/post_process | ✅ | ✅ | ✅ |
| 视觉定位 | ❌ | ✅ | ✅ |
| 桌面自动化 | ❌ | ✅ | ✅ |
| 窗口切换 | ❌ | ❌ | ✅ |

**图例**: ✅ 已覆盖 | ⚠️ 部分覆盖 | ❌ 未覆盖

---

## 📊 预期成果

完成后，rodski-demo 将包含：

- **测试用例**: 26+ 个（当前15个 + 新增11个）
- **功能覆盖**: 95%+
- **关键字覆盖**: 16/18 (89%)
- **定位器覆盖**: 6/6 (100%)
- **高级特性**: 10/10 (100%)

成为 RodSki 框架的**完整功能展示和学习示例**。

---

## 📝 备注

1. 视觉定位功能需要 OmniParser 服务支持
2. 桌面自动化需要安装 pyautogui
3. 部分功能可能需要特定平台（Windows/macOS）
4. 建议按优先级逐步实施，确保每个阶段都能运行
