# Iteration 03: Bug 修复与依赖完善

**周期**: 2026-03-29 ~ 2026-04-05 (1 周)
**分支**: `iteration-03-bugfix`

## 目标

修复 GitHub Issues 中的 Critical 和 High 优先级问题，确保核心功能可用。

## 背景

当前存在多个阻塞性 Bug：
- VisionLocator 导入错误导致视觉定位完全不可用
- BaseDriver 接口设计冲突
- 缺少核心依赖导致功能崩溃
- 核心设计约束违规

## 成功标准

1. 所有 Critical Issues 修复完成
2. 所有 High Priority Issues 修复完成
3. 核心功能可正常使用（Web/Vision/API）
4. 依赖声明完整
5. 通过对抗测试验证
