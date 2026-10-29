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

启动桌面应用要用 **Desktop 模型**（`driver_type="windows"` 或 `"macos"`）：`launch <Desktop模型> <DataID>`，应用路径写在该模型同名数据表的数据行里。

```xml
<!-- model.xml：只用于启动的 Desktop 模型，不需要元素 -->
<model name="NotepadApp" driver_type="windows"/>
<model name="TextEditApp" driver_type="macos"/>
```

| 数据表 | DataID | 字段 | 说明 |
|--------|--------|------|------|
| `NotepadApp` | `A001` | `app_path` = `C:\Windows\System32\notepad.exe` | Windows 只读 `app_path`，且该路径必须存在 |
| `TextEditApp` | `A001` | `app_name` = `TextEdit`（或 `app_path` = `/System/Applications/TextEdit.app`） | macOS 优先 `app_path`（须存在，用 `open` 打开），否则用 `open -a <app_name>` |

```xml
<!-- Windows -->
<test_step action="launch" model="NotepadApp" data="A001"/>

<!-- macOS -->
<test_step action="launch" model="TextEditApp" data="A001"/>
```

- 数据行既没有 `app_path` 也没有 `app_name` 时报参数错误。启动后框架固定等待约 1 秒。
- **Web 模型或 `model` 为空时，`launch` 只接受完整的 `http://` / `https://` URL，等同于 `navigate`**；应用名（如 `notepad.exe`）、漏写协议、`ftp://` 等其他值都报参数错误（v11.8.26）。旧写法 `<test_step action="launch" model="" data="notepad.exe"/>` 已不可用。
- 接口模型不支持 `launch`（报参数错误，请用 `send`）。

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
    <test_step action="launch" model="NotepadApp" data="A001"/>
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

`NotepadApp` 模型与数据行见 [§13.2](#132-launch-关键字)。启动后不需要写 `wait`：后续 `type` 查找窗口元素时按 `AutoWait` 自动等待。

### 13.6 约束

- ❌ 桌面端不支持接口测试（无 `send` 关键字）
- ❌ 不新增 `clipboard`、`key_combination`、`window` 等独立关键字
- ✅ 桌面操作通过 `run` 调用脚本实现
- ✅ 视觉定位为主，辅以命令行工具
