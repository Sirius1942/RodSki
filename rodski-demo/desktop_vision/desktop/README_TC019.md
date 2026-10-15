# TC019: 桌面应用自动化测试

## 概述

TC019 展示如何使用 RodSki 进行桌面应用自动化测试，包括：
- 启动桌面应用
- 模拟键盘输入
- 执行快捷键组合
- 鼠标点击操作

## 前置条件

1. **安装 pyautogui**:
   ```bash
   pip install pyautogui
   ```

2. **平台特定要求**:
   - **macOS**: 需要在"系统偏好设置 > 安全性与隐私 > 辅助功能"中授权终端或 Python
   - **Linux**: 需要安装 `python3-tk` 和 `python3-dev`

## 使用说明

### 1. 启动应用 (launch)

```xml
<!-- Windows -->
<test_step action="launch" model="" data="notepad.exe"/>
<test_step action="launch" model="" data="calc.exe"/>

<!-- macOS -->
<test_step action="launch" model="" data="open -a TextEdit"/>
<test_step action="launch" model="" data="open -a Calculator"/>

<!-- Linux -->
<test_step action="launch" model="" data="gedit"/>
```

### 2. 输入文本 (run + type_text.py)

```xml
<test_step action="run" model="desktop_ops" data="type_text.py Hello_World"/>
<test_step action="run" model="desktop_ops" data="type_text.py 测试文本"/>
```

**注意**: 
- 文本中的空格需要用下划线 `_` 替代
- 或者使用引号包裹: `type_text.py "Hello World"`

### 3. 快捷键组合 (run + key_combo.py)

```xml
<!-- 全选 -->
<test_step action="run" model="desktop_ops" data="key_combo.py ctrl+a"/>

<!-- 复制 -->
<test_step action="run" model="desktop_ops" data="key_combo.py ctrl+c"/>

<!-- 粘贴 -->
<test_step action="run" model="desktop_ops" data="key_combo.py ctrl+v"/>

<!-- 保存 -->
<test_step action="run" model="desktop_ops" data="key_combo.py ctrl+s"/>

<!-- 关闭窗口 (Windows) -->
<test_step action="run" model="desktop_ops" data="key_combo.py alt+f4"/>

<!-- 退出应用 (macOS) -->
<test_step action="run" model="desktop_ops" data="key_combo.py command+q"/>
```

**平台差异**:
- Windows/Linux: `ctrl`, `alt`, `shift`
- macOS: `command`, `option`, `shift`, `ctrl`

### 4. 鼠标点击 (run + mouse_click.py)

```xml
<!-- 左键点击 -->
<test_step action="run" model="desktop_ops" data="mouse_click.py 100 200 left"/>

<!-- 右键点击 -->
<test_step action="run" model="desktop_ops" data="mouse_click.py 100 200 right"/>

<!-- 中键点击 -->
<test_step action="run" model="desktop_ops" data="mouse_click.py 100 200 middle"/>
```

**注意**: 坐标是屏幕绝对坐标，需要根据实际屏幕分辨率调整。

## 完整示例

### Windows 记事本测试

```xml
<case execute="否" id="TC019" title="桌面应用自动化测试" component_type="界面">
    <test_case>
        <!-- 启动记事本 -->
        <test_step action="launch" model="" data="notepad.exe"/>
        <test_step action="wait" model="" data="2"/>
        
        <!-- 输入文本 -->
        <test_step action="run" model="desktop_ops" data="type_text.py Hello_RodSki"/>
        <test_step action="wait" model="" data="1"/>
        
        <!-- 全选并复制 -->
        <test_step action="run" model="desktop_ops" data="key_combo.py ctrl+a"/>
        <test_step action="run" model="desktop_ops" data="key_combo.py ctrl+c"/>
        
        <!-- 关闭应用 -->
        <test_step action="run" model="desktop_ops" data="key_combo.py alt+f4"/>
    </test_case>
</case>
```

### macOS 文本编辑器测试

```xml
<case execute="否" id="TC019" title="桌面应用自动化测试" component_type="界面">
    <test_case>
        <!-- 启动文本编辑器 -->
        <test_step action="launch" model="" data="open -a TextEdit"/>
        <test_step action="wait" model="" data="2"/>
        
        <!-- 输入文本 -->
        <test_step action="run" model="desktop_ops" data="type_text.py Hello_RodSki"/>
        <test_step action="wait" model="" data="1"/>
        
        <!-- 全选并复制 -->
        <test_step action="run" model="desktop_ops" data="key_combo.py command+a"/>
        <test_step action="run" model="desktop_ops" data="key_combo.py command+c"/>
        
        <!-- 退出应用 -->
        <test_step action="run" model="desktop_ops" data="key_combo.py command+q"/>
    </test_case>
</case>
```

## 脚本说明

### type_text.py
- **功能**: 在当前焦点窗口输入文本
- **参数**: 要输入的文本内容
- **特点**: 每个字符间隔 0.1 秒，模拟真实输入

### key_combo.py
- **功能**: 执行键盘快捷键组合
- **参数**: 快捷键组合 (如 `ctrl+a`, `alt+f4`)
- **支持**: 所有 pyautogui 支持的按键

### mouse_click.py
- **功能**: 在指定坐标点击鼠标
- **参数**: x坐标 y坐标 [按钮类型]
- **按钮**: left(默认), right, middle

## 注意事项

1. **默认不执行**: TC019 默认 `execute="否"`，需要手动启用
2. **环境依赖**: 需要图形界面环境，无法在 CI/CD 无头环境运行
3. **权限要求**: macOS 需要辅助功能权限
4. **坐标适配**: 鼠标点击坐标需要根据屏幕分辨率调整
5. **时序控制**: 使用 `wait` 确保应用启动和操作完成
6. **平台差异**: 注意不同操作系统的快捷键差异

## 扩展建议

可以创建更多桌面操作脚本：
- `screenshot.py` - 截图
- `find_image.py` - 图像识别定位
- `drag_drop.py` - 拖拽操作
- `scroll.py` - 滚动操作
- `get_window_info.py` - 获取窗口信息
