# 测试规范索引

## 目录结构

```
rodski-test-specs/
└── iteration-01/
    ├── test-requirements.md    # 测试需求
    └── test-tasks.md           # 测试任务清单
```

## 对应 Demo

测试 demo 位于: `rodski-demo/DEMO/iteration-01-vision/`

## 迭代概述

**迭代 01** 实现了视觉定位功能，包括：
- vision 定位器（语义描述）
- ocr 定位器（文字识别）
- vision_bbox 定位器（坐标）
- Web 和 Desktop 平台支持
- launch 关键字

## 测试覆盖

- TC01: Web 视觉定位登录场景
- TC02: 混合定位器降级（待实现）
- TC03: Desktop 文本编辑
- TC04: 坐标定位（待实现）
