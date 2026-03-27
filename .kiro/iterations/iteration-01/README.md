# 迭代 01 - 视觉定位功能

**迭代周期**: 2026-03-20 ~ 2026-03-27
**状态**: ✅ 已完成
**分支**: `feature/vision-location`

## 目标

实现基于 OmniParser + 多模态 LLM 的视觉定位功能，支持 Web 和 Desktop 平台。

## 需求文档

- [需求说明](requirements.md)
- [技术设计](design.md)
- [任务列表](tasks.md)

## 交付物

- 视觉定位核心模块 (`rodski/vision/`)
- Web 和 Desktop 演示项目
- 完整的单元测试和集成测试
- 用户文档和 Agent 指南

## 关键决策

1. 不新增关键字，通过 `locator` 属性实现
2. 桌面操作使用 `run` 关键字调用脚本
3. 新增 `launch` 关键字用于启动应用

## 成果

- 16个任务全部完成
- 191+ 测试通过
- 文档完整更新

---

参考规范:
- #[[file:../../conventions/PROJECT_CONSTRAINTS.md]]
- #[[file:../../conventions/GIT_WORKFLOW.md]]
