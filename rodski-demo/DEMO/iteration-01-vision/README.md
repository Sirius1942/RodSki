# 迭代 01 - 视觉定位功能测试 Demo

## 概述

本 demo 演示 RodSki v2.1.0 的视觉定位功能，包括：
- Web 平台视觉定位（vision/ocr/vision_bbox）
- Desktop 平台视觉定位
- 混合定位器降级策略

## 目录结构

```
iteration-01-vision/
├── case/
│   └── vision_test.xml       # 测试用例
├── data/
│   ├── web_login.xml         # Web 登录数据
│   └── desktop_edit.xml      # Desktop 编辑数据
├── model/
│   ├── web_model.xml         # Web 模型定义
│   └── desktop_model.xml     # Desktop 模型定义
├── fun/
│   └── test_page.html        # 测试页面
└── run_test.py               # 运行脚本
```

## 运行方式

```bash
# Web 测试
python run_test.py --case web

# Desktop 测试（仅 macOS）
python run_test.py --case desktop

# 全部测试
python run_test.py --case all
```

## 依赖

- OmniParser 服务运行在 http://localhost:7861
- LLM API 配置在环境变量中
