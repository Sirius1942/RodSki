# TC041: macOS 桌面录制验收

## 目的

验证 `--record --record-mode screen` 在真实桌面场景下能够录制：

- 启动桌面应用（TextEdit）
- 输入文本
- 执行快捷键（Command+A / Command+C）
- 鼠标点击
- 关闭应用

## 运行方式

```bash
python3 run_demo.py --case case/tc041_desktop_recording.xml --record --record-mode screen
```

## 前置条件

1. macOS 图形界面环境
2. 已安装依赖：`pyautogui`、`pyperclip`、`mss`、`opencv-python`、`numpy`
3. 终端/Python 已授予辅助功能权限与屏幕录制权限
4. TextEdit 可通过 `/System/Applications/TextEdit.app` 启动

## 验收点

1. `result/rodski_*/recordings/` 下生成 `.mp4`
2. `result.xml` 中 `recording_path` 已回填
3. 录制中可见 TextEdit 启动、输入、快捷键和点击动作
4. 录制范围为目标/主屏，而不是默认拼接所有显示器

## 说明

- 该用例是桌面录制验收集合，不纳入默认稳定回归
- 若需更复杂的桌面场景，可继续参考 `tc040_vscode_plugin.xml`
