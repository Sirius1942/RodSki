# RodSki 桌面视觉定位演示

## 概述

本演示展示 RodSki 桌面端视觉定位能力，包括：
- `launch` 关键字启动桌面应用
- `vision` 定位器语义定位
- `vision_bbox` 定位器坐标定位
- `run` 关键字调用桌面操作脚本

## 前提条件

1. **OmniParser 服务**：`http://14.103.175.167:7862/parse/` 可访问
2. **LLM API**：配置 `ANTHROPIC_API_KEY` 环境变量
3. **依赖安装**：`pip install pyautogui pyperclip`
4. **平台**：Windows 或 macOS

## 运行命令

```bash
cd /Users/sirius05/Documents/project/RodSki
python rodski/ski_run.py rodski-demo/DEMO/vision_desktop/case/desktop_demo.xml
```

## 预期结果

1. 启动记事本应用
2. 通过视觉定位找到文本编辑区域
3. 输入 "Hello RodSki Vision!"
4. 执行 Ctrl+A 全选
5. 读取剪贴板内容
6. 关闭记事本

## 文件说明

- `model/model.xml` — 定义 vision 和 vision_bbox 定位器
- `case/desktop_demo.xml` — 测试用例（三阶段结构）
- `data/NotepadPage.xml` — 数据表
- `fun/desktop/*.py` — 桌面操作脚本（剪贴板、组合键、窗口切换）
