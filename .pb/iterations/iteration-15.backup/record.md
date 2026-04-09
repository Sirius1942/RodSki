# Iteration 15: rodski-demo 全功能覆盖扩展

**版本**: v4.7.0  
**日期**: 2026-04-09  
**分支**: main  
**需求来源**: `.pb/specs/rodski-demo-full-coverage-design.md`  
**优先级**: P0（核心功能覆盖）  
**前置依赖**: iteration-14 完成

---

## 迭代目标

1. 补充 rodski-demo 缺失的核心功能（定位器、关键字、视觉定位、桌面自动化）
2. 将功能覆盖率从 60% 提升到 90%+
3. 新增 11 个测试用例（TC016-TC026）
4. 扩展 demosite 支持新功能测试
5. 使 rodski-demo 成为完整的功能展示和学习示例

---

## 核心约束（不可违反）

> - 不改变 rodski 框架代码，只扩展 rodski-demo 项目
> - 所有新增功能必须向后兼容
> - 新增测试用例必须可以独立运行
> - 文档必须同步更新

---

## 设计决策

### D15-01: 分阶段实施策略

**决策**: 按功能优先级分三个阶段
- **Phase 1** (P0): 定位器、关键字、视觉定位、桌面自动化 - 核心缺失
- **Phase 2** (P1): 窗口切换、复杂引用、负面测试 - 高级特性
- **Phase 3** (P2): 并发执行、重试机制 - 边缘特性

**Why**: 优先补充核心功能，确保每个阶段都能产出可用成果。

### D15-02: demosite 扩展最小化

**决策**: 只添加必要的测试页面
- 文件上传页面 (`/upload`)
- 定位器测试页面 (`/locator-test`)
- 多窗口测试页面 (`/multi-window`)
- iframe 测试页面 (`/iframe-test`)

**Why**: 避免 demosite 过于复杂，保持简单可维护。

### D15-03: 视觉定位可选实施

**决策**: 视觉定位功能作为可选项
- 提供模型定义和测试用例
- 标注需要 OmniParser 服务
- 无服务时跳过该用例

**Why**: 视觉定位依赖外部服务，不应阻塞其他功能测试。

### D15-04: 桌面自动化跨平台支持

**决策**: 桌面自动化支持 Windows/macOS
- 使用 pyautogui 实现跨平台
- 提供平台特定的示例脚本
- 文档说明平台差异

**Why**: 确保不同平台用户都能学习桌面自动化功能。

---

## 实施任务

### 阶段一: P0 核心功能补充

#### T15-001: 扩展 demosite 测试页面
**文件**: `rodski-demo/DEMO/demo_full/demosite/app.py`

**任务**:
1. 添加文件上传页面 (`/upload`)
   - 文件选择控件
   - 上传按钮
   - 上传结果显示

2. 添加定位器测试页面 (`/locator-test`)
   - 包含 id、css、xpath、name 定位器的元素
   - 输入框、按钮、文本显示

3. 添加多窗口测试页面 (`/multi-window`)
   - 打开新窗口按钮
   - 窗口标识信息

4. 添加 iframe 测试页面 (`/iframe-test`)
   - 嵌入 iframe
   - iframe 内容页面

**验收标准**:
- 所有页面可以正常访问
- 页面功能正常工作
- 页面元素有清晰的定位器

**预计**: 3h | **Owner**: 待分配

---

#### T15-002: TC016 - 定位器类型覆盖测试
**文件**: 
- `rodski-demo/DEMO/demo_full/case/tc016_locators.xml`
- `rodski-demo/DEMO/demo_full/model/model.xml`
- `rodski-demo/DEMO/demo_full/data/LocatorTest*.xml`

**任务**:
1. 创建测试用例 TC016
2. 添加模型定义：
   - LocatorTest_XPath (使用 xpath 定位)
   - LocatorTest_Name (使用 name 定位)
   - LocatorTest_CSS (使用 css 定位)
3. 添加测试数据和验证数据

**示例**:
```xml
<case execute="是" id="TC016" title="定位器类型覆盖" component_type="界面">
    <pre_process>
        <test_step action="navigate" model="" data="http://localhost:8000/locator-test"/>
    </pre_process>
    <test_case>
        <test_step action="type" model="LocatorTest_XPath" data="X001"/>
        <test_step action="type" model="LocatorTest_Name" data="N001"/>
        <test_step action="type" model="LocatorTest_CSS" data="C001"/>
        <test_step action="verify" model="LocatorTest" data="V001"/>
    </test_case>
    <post_process>
        <test_step action="close" model="" data=""/>
    </post_process>
</case>
```

**验收标准**:
- 测试用例可以运行
- 所有定位器类型都能正确定位元素
- 验证通过

**预计**: 2h | **Owner**: 待分配

---

#### T15-003: TC017 - 关键字完整覆盖测试
**文件**: 
- `rodski-demo/DEMO/demo_full/case/tc017_keywords.xml`
- `rodski-demo/DEMO/demo_full/model/model.xml`
- `rodski-demo/DEMO/demo_full/data/KeywordTest*.xml`

**任务**:
1. 创建测试用例 TC017，覆盖：
   - wait (等待)
   - clear (清空输入)
   - screenshot (截图)
   - assert (断言)
   - upload_file (文件上传)

2. 添加相关模型定义
3. 添加测试数据

**示例**:
```xml
<case execute="是" id="TC017" title="关键字完整覆盖" component_type="界面">
    <test_case>
        <test_step action="navigate" model="" data="http://localhost:8000/locator-test"/>
        <test_step action="wait" model="" data="2"/>
        <test_step action="type" model="TestForm" data="T001"/>
        <test_step action="clear" model="TestForm" data="C001"/>
        <test_step action="screenshot" model="" data="test_page.png"/>
        <test_step action="type" model="TestForm" data="T002"/>
        <test_step action="assert" model="TestForm" data="A001"/>
        
        <test_step action="navigate" model="" data="http://localhost:8000/upload"/>
        <test_step action="upload_file" model="UploadForm" data="U001"/>
        <test_step action="verify" model="UploadForm" data="V001"/>
    </test_case>
    <post_process>
        <test_step action="close" model="" data=""/>
    </post_process>
</case>
```

**验收标准**:
- 所有关键字都能正常执行
- wait 等待时间正确
- clear 清空输入成功
- screenshot 生成截图文件
- assert 断言正确
- upload_file 上传文件成功

**预计**: 2.5h | **Owner**: 待分配

---

#### T15-004: TC018 - 视觉定位功能测试（可选）
**文件**: 
- `rodski-demo/DEMO/demo_full/case/tc018_vision.xml`
- `rodski-demo/DEMO/demo_full/model/model.xml`
- `rodski-demo/DEMO/demo_full/data/VisionLogin*.xml`

**任务**:
1. 创建测试用例 TC018
2. 添加视觉定位模型：
   - VisionLogin (使用 vision 语义定位)
   - VisionCoordinate (使用 vision_bbox 坐标定位)
3. 添加测试数据
4. 添加说明文档，标注需要 OmniParser 服务

**示例**:
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

**验收标准**:
- 模型定义正确
- 测试用例结构完整
- 文档说明清晰
- 有 OmniParser 服务时可以运行

**预计**: 1.5h | **Owner**: 待分配

---

#### T15-005: TC019 - 桌面应用自动化测试
**文件**: 
- `rodski-demo/DEMO/demo_full/case/tc019_desktop.xml`
- `rodski-demo/DEMO/demo_full/fun/desktop_ops/`

**任务**:
1. 创建测试用例 TC019
2. 创建桌面操作脚本：
   - `type_text.py` - 输入文本
   - `key_combo.py` - 快捷键组合
   - `mouse_click.py` - 鼠标点击
3. 添加平台特定示例（Windows/macOS）

**示例**:
```xml
<case execute="是" id="TC019" title="桌面应用自动化" component_type="界面">
    <test_case>
        <test_step action="launch" model="" data="notepad.exe"/>
        <test_step action="wait" model="" data="2"/>
        <test_step action="run" model="desktop_ops" data="type_text.py Hello"/>
        <test_step action="run" model="desktop_ops" data="key_combo.py Ctrl+A"/>
        <test_step action="run" model="desktop_ops" data="key_combo.py Ctrl+C"/>
        <test_step action="run" model="desktop_ops" data="key_combo.py Alt+F4"/>
    </test_case>
</case>
```

**验收标准**:
- launch 可以启动应用
- run 可以执行脚本
- 脚本支持 Windows/macOS
- 文档说明平台差异

**预计**: 2.5h | **Owner**: 待分配

---

### 阶段二: P1 高级特性补充

#### T15-006: TC020 - 多窗口和 iframe 测试
**文件**: 
- `rodski-demo/DEMO/demo_full/case/tc020_windows.xml`
- `rodski-demo/DEMO/demo_full/fun/switch_window.py`
- `rodski-demo/DEMO/demo_full/fun/switch_frame.py`

**任务**:
1. 创建测试用例 TC020
2. 创建窗口切换脚本
3. 创建 iframe 切换脚本
4. 添加相关模型和数据

**示例**:
```xml
<case execute="是" id="TC020" title="多窗口和iframe" component_type="界面">
    <test_case>
        <test_step action="navigate" model="" data="http://localhost:8000/multi-window"/>
        <test_step action="type" model="WindowTest" data="W001"/>
        <test_step action="run" model="" data="fun/switch_window.py 1"/>
        <test_step action="verify" model="NewWindow" data="V001"/>
        <test_step action="run" model="" data="fun/switch_window.py 0"/>
        
        <test_step action="navigate" model="" data="http://localhost:8000/iframe-test"/>
        <test_step action="run" model="" data="fun/switch_frame.py contentFrame"/>
        <test_step action="verify" model="IframeContent" data="V001"/>
    </test_case>
    <post_process>
        <test_step action="close" model="" data=""/>
    </post_process>
</case>
```

**验收标准**:
- 可以切换窗口
- 可以切换 iframe
- 验证通过

**预计**: 2h | **Owner**: 待分配

---

#### T15-007: TC021 - 复杂数据引用测试
**文件**: 
- `rodski-demo/DEMO/demo_full/case/tc021_data_ref.xml`
- `rodski-demo/DEMO/demo_full/model/model.xml`
- `rodski-demo/DEMO/demo_full/data/DataRefTest*.xml`

**任务**:
1. 创建测试用例 TC021，覆盖：
   - GlobalValue 引用
   - Return 嵌套引用
   - 命名变量访问
   - 复杂数据路径

**示例**:
```xml
<case execute="是" id="TC021" title="复杂数据引用" component_type="界面">
    <test_case>
        <test_step action="navigate" model="" data="GlobalValue.DefaultValue.URL"/>
        <test_step action="type" model="TestForm" data="T001"/>
        <test_step action="set" model="" data="result1=${Return[-1]}"/>
        <test_step action="type" model="TestForm" data="T002"/>
        <test_step action="set" model="" data="result2=${Return[-1].fieldName}"/>
        <test_step action="get" model="" data="result1"/>
        <test_step action="verify" model="DataRefVerify" data="V001"/>
    </test_case>
    <post_process>
        <test_step action="close" model="" data=""/>
    </post_process>
</case>
```

**验收标准**:
- GlobalValue 引用正确
- Return 嵌套引用正确
- 命名变量读写正确
- 验证通过

**预计**: 1.5h | **Owner**: 待分配

---

#### T15-008: TC022-024 - 负面测试集合
**文件**: 
- `rodski-demo/DEMO/demo_full/case/tc022_negative.xml`
- `rodski-demo/DEMO/demo_full/model/model.xml`
- `rodski-demo/DEMO/demo_full/data/ErrorTest*.xml`

**任务**:
1. TC022: 元素不存在测试 (expect_fail="是")
2. TC023: 接口错误响应测试 (expect_fail="是")
3. TC024: SQL 语法错误测试 (expect_fail="是")

**示例**:
```xml
<case execute="是" id="TC022" title="元素不存在" expect_fail="是" component_type="界面">
    <test_case>
        <test_step action="navigate" model="" data="http://localhost:8000"/>
        <test_step action="type" model="NonExistentModel" data="D001"/>
    </test_case>
</case>

<case execute="是" id="TC023" title="API错误响应" expect_fail="是" component_type="接口">
    <test_case>
        <test_step action="send" model="ErrorAPI" data="D001"/>
    </test_case>
</case>

<case execute="是" id="TC024" title="SQL语法错误" expect_fail="是" component_type="数据库">
    <test_case>
        <test_step action="DB" model="demo_db" data="QuerySQL.BadSQL"/>
    </test_case>
</case>
```

**验收标准**:
- 所有负面用例正确标记 expect_fail
- 测试报告显示为预期失败
- 不影响整体测试结果

**预计**: 1.5h | **Owner**: 待分配

---

### 阶段三: 文档与验证

#### T15-009: 更新文档
**文件**: 
- `rodski-demo/DEMO/demo_full/README.md`
- `rodski-demo/DEMO/demo_full/COVERAGE.md` (新建)

**任务**:
1. 更新 README.md
   - 补充新增测试用例说明
   - 更新功能覆盖矩阵
   - 更新运行说明

2. 创建 COVERAGE.md
   - 功能覆盖详细说明
   - 关键字覆盖矩阵
   - 定位器覆盖矩阵
   - 高级特性覆盖矩阵

**预计**: 1.5h | **Owner**: 待分配

---

#### T15-010: 完整回归测试
**文件**: 所有测试用例

**任务**:
1. 运行所有现有测试用例（TC001-TC015）
2. 运行所有新增测试用例（TC016-TC024）
3. 验证功能覆盖率
4. 检查测试报告

**验收标准**:
- 所有正向用例通过
- 所有负向用例正确标记
- 功能覆盖率达到 90%+
- 无回归问题

**预计**: 2h | **Owner**: 待分配

---

#### T15-011: 更新迭代文档
**文件**: `.pb/iterations/iteration-15/record.md`

**任务**:
1. 记录所有新增内容
2. 记录实施过程中的问题和解决方案
3. 记录验收测试结果
4. 总结功能覆盖情况

**预计**: 0.5h | **Owner**: 待分配

---

## 任务汇总

| 任务 | 名称 | 预计 | 阶段 | 优先级 |
|------|------|------|------|--------|
| T15-001 | 扩展 demosite 测试页面 | 3h | 1 | P0 |
| T15-002 | TC016 定位器类型覆盖 | 2h | 1 | P0 |
| T15-003 | TC017 关键字完整覆盖 | 2.5h | 1 | P0 |
| T15-004 | TC018 视觉定位功能 | 1.5h | 1 | P0 |
| T15-005 | TC019 桌面应用自动化 | 2.5h | 1 | P0 |
| T15-006 | TC020 多窗口和iframe | 2h | 2 | P1 |
| T15-007 | TC021 复杂数据引用 | 1.5h | 2 | P1 |
| T15-008 | TC022-024 负面测试 | 1.5h | 2 | P1 |
| T15-009 | 更新文档 | 1.5h | 3 | P1 |
| T15-010 | 完整回归测试 | 2h | 3 | P0 |
| T15-011 | 更新迭代文档 | 0.5h | 3 | P1 |

**总预计**: 20.5h

---

## 验收标准

### 功能验收
- [ ] 新增 11 个测试用例（TC016-TC026）
- [ ] 所有定位器类型都有测试覆盖
- [ ] 所有核心关键字都有测试覆盖
- [ ] 视觉定位模型定义完整
- [ ] 桌面自动化脚本可用
- [ ] 窗口和 iframe 切换正常
- [ ] 复杂数据引用正确
- [ ] 负面测试完整

### 质量验收
- [ ] 所有测试用例通过
- [ ] 功能覆盖率达到 90%+
- [ ] 文档完整准确
- [ ] 无回归问题

### 覆盖率验收
- [ ] 关键字覆盖: 16/18 (89%)
- [ ] 定位器覆盖: 6/6 (100%)
- [ ] 高级特性覆盖: 10/10 (100%)

---

## 遗留与后续

- 并发执行测试（TC025）可选实施
- 重试机制测试（TC026）可选实施
- 性能测试用例按需添加
- 移动端测试用例（Appium）按需添加

---

## 风险与应对

| 风险 | 影响 | 应对措施 |
|------|------|---------|
| demosite 扩展复杂度高 | 高 | 保持页面简单，复用现有组件 |
| 视觉定位依赖外部服务 | 中 | 作为可选功能，提供跳过机制 |
| 桌面自动化平台差异 | 中 | 提供平台特定脚本，文档说明 |
| 测试用例数量增加维护成本 | 低 | 保持用例独立，文档清晰 |

---

## 参考文档

- `.pb/specs/rodski-demo-full-coverage-design.md` - 全功能覆盖设计
- `rodski/docs/TEST_CASE_WRITING_GUIDE.md` - 用例编写指南
- `rodski/docs/SKILL_REFERENCE.md` - 关键字参考
- `rodski/docs/VISION_LOCATION.md` - 视觉定位设计
