# demo_v7_features - v7.0 特性演示

## 概述

演示 v7.0.0 引入的移动端测试能力、录像架构、多设备并发等核心特性。

## 环境要求

- 根据用例选择：
  - Web 用例：demosite :8000
  - 移动端用例：Appium + Android 模拟器或真机

## 用例说明

| 用例类型 | 说明 |
|---------|------|
| `case/*.xml` | v7 特性覆盖（具体数量以实际文件为准） |

## 两种运行方式

### 1. 使用编排脚本（推荐）

```bash
cd /path/to/rodski-demo/DEMO/demo_v7_features
python3 run_v7_demo.py
```

编排脚本会处理前置准备（如启动目标页服务、设置环境变量等）。

### 2. 直接运行用例

```bash
rodski run case/
```

需手动满足环境依赖，可能因缺少前置而部分失败。

## 验收标准

- 使用 `run_v7_demo.py` 时：exit 0，演示完成
- 直接 `rodski run case/` 且环境齐全时：用例通过

## 相关文档

- CHANGELOG.md v7.0.0 / v7.1.1
- CORE §11：移动端约束
