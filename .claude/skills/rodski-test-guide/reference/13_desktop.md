<!-- 自动生成 from rodski/docs/TEST_CASE_WRITING_GUIDE.md  请勿手工编辑 -->

## 13. 桌面端自动化（Desktop）

### 13.1 平台标识

桌面平台使用操作系统类型作为 `driver_type`：

```xml
<model name="NotepadPage" driver_type="windows">
  <element name="textArea">
      <location type="vision">文本编辑区域</location>
  </element>
</model>

<model name="TextEditPage" driver_type="macos">
  <element name="textArea">
      <location type="vision">文本编辑区域</location>
  </element>
</model>
```

### 13.2 launch 关键字

启动桌面应用（与 `navigate` 功能相同，场景不同）：

```xml
<!-- Windows -->
<test_step action="launch" model="" data="notepad.exe"/>

<!-- macOS -->
<test_step action="launch" model="" data="TextEdit.app"/>
```

### 13.3 vision_bbox 坐标约定

桌面场景下 `vision_bbox` 使用**屏幕绝对坐标**：

```xml
<element name="closeBtn">
    <location type="vision_bbox">1850,50,1900,100</location>
</element>
```

**约束**：
- 坐标为屏幕绝对像素坐标（左上角为 0,0）
- 桌面应用执行时**默认全屏**，避免窗口位置变化导致坐标偏移

### 13.4 桌面操作脚本（run 关键字）

桌面特有操作（剪贴板、组合键、窗口管理）通过 `run` 调用脚本：

```xml
<!-- 组合键 -->
<test_step action="run" model="" data="fun/desktop/key_combo.py Ctrl+V"/>

<!-- 剪贴板 -->
<test_step action="run" model="" data="fun/desktop/clipboard_copy.py"/>

<!-- 窗口切换 -->
<test_step action="run" model="" data="fun/desktop/switch_window.py 记事本"/>
```

脚本返回 JSON 格式：
```json
{"status": "success", "result": "..."}
```

### 13.5 完整示例

**case/desktop_demo.xml**：
```xml
<case execute="是" id="d001" title="桌面演示">
  <pre_process>
    <test_step action="launch" model="" data="notepad.exe"/>
    <test_step action="wait" model="" data="2"/>
  </pre_process>
  <test_case>
    <test_step action="type" model="NotepadPage" data="D001"/>
    <test_step action="run" model="" data="fun/desktop/key_combo.py Ctrl+A"/>
  </test_case>
  <post_process>
    <test_step action="run" model="" data="fun/desktop/key_combo.py Alt+F4"/>
  </post_process>
</case>
```

### 13.6 约束

- ❌ 桌面端不支持接口测试（无 `send` 关键字）
- ❌ 不新增 `clipboard`、`key_combination`、`window` 等独立关键字
- ✅ 桌面操作通过 `run` 调用脚本实现
- ✅ 视觉定位为主，辅以命令行工具
