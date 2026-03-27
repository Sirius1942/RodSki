# RodSki 通用规范

本目录包含 RodSki 项目的通用开发规范和约束，适用于所有迭代开发。

## 规范文档

- [Git 工作流规范](GIT_WORKFLOW.md) - 分支管理、提交规范、发布流程
- [项目约束](PROJECT_CONSTRAINTS.md) - 项目结构、开发约束、测试规范
- [代码规范](CODING_STANDARDS.md) - 代码风格、命名规范、最佳实践（待补充）

## 使用方式

### 在 Specs 中引用

在功能开发的 spec 文档中引用这些规范：

```markdown
# 功能设计

遵循规范:
- #[[file:../../.kiro/conventions/PROJECT_CONSTRAINTS.md]]
- #[[file:../../.kiro/conventions/GIT_WORKFLOW.md]]
```

### 开发前检查

每次开始新功能开发前：

1. 阅读相关规范文档
2. 从 main 分支创建新的功能分支
3. 确保设计符合项目约束
4. 提交时遵循提交信息规范

---

**最后更新**: 2026-03-27
