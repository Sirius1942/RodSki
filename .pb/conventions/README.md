# RodSki 通用规范

本目录包含 RodSki 项目的通用开发规范和约束，适用于所有迭代开发。

## 规范文档

- [Git 工作流规范](GIT_WORKFLOW.md) - 分支管理、提交规范、发布流程
- [核心设计约束](../../rodski/docs/CORE_DESIGN_CONSTRAINTS.md) - 项目结构、关键字设计、开发约束、测试规范
- [CI/CD 集成指南](CI_CD_GUIDE.md) - GitHub Actions、Jenkins、GitLab CI 集成

## 核心约束

> ⚠️ 本项目有 **绝对不可违反的核心约束**，详见 [CORE_DESIGN_CONSTRAINTS.md](../../rodski/docs/CORE_DESIGN_CONSTRAINTS.md) 附录 A。

## 示例目录约定

- `rodski-demo/` 是项目正式示例，必须纳入仓库管理
- `rodski-demo/` 的内容以 `rodski/docs/TEST_CASE_WRITING_GUIDE.md` 为准，承担示例、示范和验收基线作用
- `rodski/examples/` 已废弃，后续不再新增或维护

## 使用方式

### 在迭代文档中引用

```markdown
# 功能设计

遵循规范:
- #[[file:../../rodski/docs/CORE_DESIGN_CONSTRAINTS.md]]
- #[[file:../conventions/GIT_WORKFLOW.md]]
```

### 开发前检查

每次开始新功能开发前：

1. 阅读 [CORE_DESIGN_CONSTRAINTS.md](../../rodski/docs/CORE_DESIGN_CONSTRAINTS.md) 中的核心约束条款
2. 从 main 分支创建新的功能分支
3. 确保设计符合项目约束
4. 提交时遵循提交信息规范

---

**最后更新**: 2026-04-05
