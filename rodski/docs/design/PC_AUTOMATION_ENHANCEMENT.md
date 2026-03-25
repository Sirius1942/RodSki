# RodSki PC 桌面自动化增强方案

**版本**: v1.0
**日期**: 2026-03-25

## 1. 目标

为 RodSki 补充完整的 PC 桌面自动化能力，支持 Windows 和 macOS 两大平台。

---

## 2. 技术选型

### 2.1 Windows 平台

| 技术方案 | 优势 | 劣势 | 推荐度 |
|---------|------|------|--------|
| **PyWinAuto** (当前) | 原生 Windows UI Automation | 仅 Windows | ⭐⭐⭐⭐ |
| pyautogui | 跨平台 | 基于坐标，不稳定 | ⭐⭐ |
| win32com | COM 自动化 | 仅限支持 COM 的应用 | ⭐⭐⭐ |

**决策**: 继续使用 **PyWinAuto**，但大幅增强功能。

### 2.2 macOS 平台

| 技术方案 | 优势 | 劣势 | 推荐度 |
|---------|------|------|--------|
| **pyobjc + Accessibility** | 原生 macOS API | 学习曲线陡 | ⭐⭐⭐⭐⭐ |
| AppleScript (osascript) | 系统原生支持 | 语法特殊 | ⭐⭐⭐⭐ |
| pyautogui | 跨平台 | 基于坐标 | ⭐⭐ |
| atomacos | Python 封装 | 维护不活跃 | ⭐⭐⭐ |

**决策**: 采用 **pyobjc + Accessibility API** 为主，**AppleScript** 为辅。

---

## 3. 功能增强清单

### 3.1 Windows 增强 (PyWinAutoDriver)

#### 当前实现问题
```python
# 当前代码仅 73 行，功能极简
def click(self, locator: str, **kwargs) -> bool:
    self.app.window(title=locator).click()  # 仅支持 title 定位
```

#### 增强功能列表

**A. 多种定位方式**
```python
# 支持的定位器格式
- title:窗口标题
- class:ClassName
- control_type:Button
- automation_id:btnSubmit
- name:控件名称
- xpath://Window/Button[@Name='确定']
```

**B. 键盘操作**
```python
- key_press(key)           # 单键: Enter, Esc, Tab, F1-F12
- key_combination(keys)    # 组合键: Ctrl+C, Alt+F4, Shift+Tab
- type_keys(text, interval) # 模拟打字，支持延迟
```

**C. 剪贴板操作**
```python
- clipboard_set(text)      # 设置剪贴板
- clipboard_get()          # 获取剪贴板
- clipboard_paste()        # 粘贴 (Ctrl+V)
- clipboard_copy()         # 复制 (Ctrl+C)
```

**D. 窗口管理**
```python
- window_maximize()        # 最大化
- window_minimize()        # 最小化
- window_restore()         # 还原
- window_close()           # 关闭
- window_focus()           # 激活窗口
- window_exists(title)     # 检查窗口是否存在
```

**E. 高级操作**
```python
- get_window_list()        # 获取所有窗口
- switch_window(title)     # 切换窗口
- wait_window(title, timeout) # 等待窗口出现
- capture_window(path)     # 截图指定窗口
```

### 3.2 macOS 新增 (MacOSDriver)

#### 核心功能

**A. 应用控制**
```python
- launch_app(app_name)     # 启动应用: "Safari", "Notes"
- quit_app(app_name)       # 退出应用
- activate_app(app_name)   # 激活应用到前台
- is_app_running(app_name) # 检查应用是否运行
```

**B. UI 元素操作 (Accessibility API)**
```python
- click(locator)           # 点击元素
- type(locator, text)      # 输入文本
- get_text(locator)        # 获取文本
- check(locator)           # 检查元素存在
```

**定位器格式**:
```python
- role:AXButton            # 角色定位
- title:确定               # 标题定位
- description:提交按钮     # 描述定位
- identifier:btn_submit    # 标识符定位
```

**C. 键盘操作**
```python
- key_press(key)           # Command, Option, Control, Shift
- key_combination(keys)    # Command+C, Command+V, Command+Q
- type_keys(text)          # 模拟打字
```

**D. 剪贴板操作**
```python
- clipboard_set(text)      # 使用 AppKit.NSPasteboard
- clipboard_get()
- clipboard_paste()        # Command+V
- clipboard_copy()         # Command+C
```

**E. 窗口管理**
```python
- window_list()            # 获取所有窗口
- window_focus(title)      # 激活窗口
- window_close(title)      # 关闭窗口
- window_minimize(title)   # 最小化
```

**F. AppleScript 集成**
```python
- run_applescript(script)  # 执行 AppleScript
- menu_click(app, menu_path) # 点击菜单: ["File", "Save"]
```

---

## 4. 实现架构

### 4.1 驱动层结构

```
drivers/
├── base_driver.py              # 基类 (已有)
├── playwright_driver.py        # Web (已有)
├── appium_driver.py            # Mobile (已有)
├── pywinauto_driver.py         # Windows (增强)
├── macos_driver.py             # macOS (新增)
└── desktop_driver_factory.py  # 桌面驱动工厂 (新增)
```

### 4.2 统一接口设计

```python
# base_driver.py 新增桌面操作抽象方法
class BaseDriver(ABC):
    # ... 现有方法 ...

    # 桌面自动化扩展
    def launch_app(self, app_name: str) -> bool:
        """启动应用 (桌面驱动实现)"""
        return False

    def key_combination(self, keys: str) -> bool:
        """组合键 (如 Ctrl+C, Command+V)"""
        return False

    def clipboard_set(self, text: str) -> bool:
        """设置剪贴板"""
        return False

    def clipboard_get(self) -> Optional[str]:
        """获取剪贴板"""
        return None

    def window_focus(self, title: str) -> bool:
        """激活窗口"""
        return False
```

### 4.3 驱动工厂

```python
# desktop_driver_factory.py
import sys
from typing import Optional
from .base_driver import BaseDriver

class DesktopDriverFactory:
    @staticmethod
    def create(platform: Optional[str] = None) -> BaseDriver:
        """根据平台创建桌面驱动

        Args:
            platform: 'windows' | 'macos' | None (自动检测)
        """
        if platform is None:
            platform = sys.platform

        if platform == 'win32':
            from .pywinauto_driver import PyWinAutoDriver
            return PyWinAutoDriver()
        elif platform == 'darwin':
            from .macos_driver import MacOSDriver
            return MacOSDriver()
        else:
            raise NotImplementedError(f"不支持的平台: {platform}")
```

---

## 5. 关键字引擎集成

### 5.1 新增关键字

在 `keyword_engine.py` 中新增桌面自动化关键字：

```python
SUPPORTED = [
    # ... 现有关键字 ...
    "launch",      # 启动应用
    "clipboard",   # 剪贴板操作
    "window",      # 窗口管理
]
```

### 5.2 关键字实现示例

```python
def _kw_launch(self, params: Dict) -> bool:
    """启动桌面应用

    用法:
    <action keyword="launch" model="Calculator" />
    """
    app_name = params.get("app_name") or params.get("model")
    return self.driver.launch_app(app_name)

def _kw_clipboard(self, params: Dict) -> bool:
    """剪贴板操作

    用法:
    <action keyword="clipboard" operation="set" value="Hello" />
    <action keyword="clipboard" operation="get" var="text" />
    """
    operation = params.get("operation", "get")
    if operation == "set":
        return self.driver.clipboard_set(params["value"])
    elif operation == "get":
        text = self.driver.clipboard_get()
        if "var" in params:
            self._variables[params["var"]] = text
        return True
    return False
```

---

## 6. 依赖管理

### 6.1 requirements.txt 更新

```txt
# 现有依赖
playwright>=1.40.0
pywinauto>=0.6.8; sys_platform == 'win32'

# 新增依赖
pyobjc-framework-Cocoa>=10.0; sys_platform == 'darwin'
pyobjc-framework-Quartz>=10.0; sys_platform == 'darwin'
pyperclip>=1.8.2  # 跨平台剪贴板
```

### 6.2 可选依赖

```txt
# 图像识别 (下一阶段)
opencv-python>=4.8.0
pillow>=10.0.0
```

---

## 7. 测试用例示例

### 7.1 Windows 记事本自动化

```xml
<!-- case/notepad_test.xml -->
<case name="记事本测试">
  <action keyword="launch" model="Notepad" />
  <action keyword="type" model="Notepad" data="T001" />
  <action keyword="clipboard" operation="set" value="Hello RodSki" />
  <action keyword="key_combination" keys="Ctrl+V" />
  <action keyword="window" operation="close" title="无标题 - 记事本" />
</case>
```

### 7.2 macOS Safari 自动化

```xml
<!-- case/safari_test.xml -->
<case name="Safari 测试">
  <action keyword="launch" model="Safari" />
  <action keyword="wait" seconds="2" />
  <action keyword="key_combination" keys="Command+L" />
  <action keyword="type" text="https://www.baidu.com" />
  <action keyword="key_press" key="Return" />
</case>
```

---

## 8. 实施计划

### Phase 1: Windows 增强 (1 周)
- [ ] 扩展 PyWinAutoDriver 定位方式
- [ ] 实现键盘组合键
- [ ] 实现剪贴板操作
- [ ] 实现窗口管理
- [ ] 编写单元测试

### Phase 2: macOS 基础 (1.5 周)
- [ ] 创建 MacOSDriver 骨架
- [ ] 实现应用启动/退出
- [ ] 实现 Accessibility API 元素定位
- [ ] 实现键盘操作
- [ ] 实现剪贴板操作

### Phase 3: macOS 高级 (1 周)
- [ ] 实现窗口管理
- [ ] 集成 AppleScript
- [ ] 实现菜单点击
- [ ] 编写单元测试

### Phase 4: 集成测试 (0.5 周)
- [ ] 跨平台集成测试
- [ ] 文档更新
- [ ] 示例用例

**总计**: 约 4 周

---

## 9. 风险与限制

### 9.1 技术限制
- **macOS 权限**: 需要用户授予辅助功能权限
- **应用兼容性**: 部分应用可能不支持 Accessibility API
- **跨版本差异**: macOS/Windows 不同版本 API 可能有差异

### 9.2 缓解措施
- 提供清晰的权限配置文档
- 对不支持 Accessibility 的应用，提供图像识别降级方案
- 在主流版本上充分测试

---

## 10. 后续扩展方向

1. **Linux 支持**: 基于 python-xlib 或 pyatspi
2. **图像识别**: 作为定位方式的补充
3. **录制回放**: GUI 录制操作生成用例
4. **性能优化**: 元素缓存、智能等待

---

## 附录: 参考资料

- [PyWinAuto 文档](https://pywinauto.readthedocs.io/)
- [macOS Accessibility API](https://developer.apple.com/documentation/accessibility)
- [PyObjC 文档](https://pyobjc.readthedocs.io/)
- [AppleScript 语言指南](https://developer.apple.com/library/archive/documentation/AppleScript/)
