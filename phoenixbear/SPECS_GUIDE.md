# PhoenixBear Studio 使用指南

## 什么是 PhoenixBear

PhoenixBear（飞熊项目工作室）是 RodSki 框架的**项目管理体系**，位于项目根目录 `phoenixbear/` 下。

### 定位

- 管理 RodSki 项目的需求、约束和迭代
- 作为所有迭代开发的**不可违反基准**
- 统一文档入口，解决历史文档散落各处的问题

## 目录结构

```
phoenixbear/
├── design/              # 技术设计文档（含核心约束 ⭐）
├── conventions/        # 项目规范（Git、CI/CD、项目约束）
├── requirements/       # 需求文档
├── agent/             # Agent 开发规范
├── iterations/        # 迭代管理（iteration-03 ~ iteration-07）
└── test-specs/        # 测试规范
```

## 核心约束

> ⚠️ 以下两份文档是**绝对不能违反**的硬约束：
>
> - [design/CORE_DESIGN_CONSTRAINTS.md](design/CORE_DESIGN_CONSTRAINTS.md) — 框架核心设计决策
> - [design/TEST_CASE_WRITING_GUIDE.md](design/TEST_CASE_WRITING_GUIDE.md) — 用例编写规范
>
> 详见 [conventions/PROJECT_CONSTRAINTS.md](conventions/PROJECT_CONSTRAINTS.md#8-核心文档不可违反约束)

## 在 Specs 中引用

在迭代的 design/requirements 文档中引用规范：

```markdown
# 功能设计

遵循规范:
- #[[file:../conventions/PROJECT_CONSTRAINTS.md]]
- #[[file:../conventions/GIT_WORKFLOW.md]]
```

## 开发前检查清单

每次开始新迭代前：

1. [ ] 阅读 [design/CORE_DESIGN_CONSTRAINTS.md](design/CORE_DESIGN_CONSTRAINTS.md)
2. [ ] 阅读 [design/TEST_CASE_WRITING_GUIDE.md](design/TEST_CASE_WRITING_GUIDE.md)
3. [ ] 阅读 [conventions/PROJECT_CONSTRAINTS.md](conventions/PROJECT_CONSTRAINTS.md)
4. [ ] 从 main 分支创建新迭代分支
5. [ ] 确保设计符合核心约束
6. [ ] 提交时遵循 [conventions/GIT_WORKFLOW.md](conventions/GIT_WORKFLOW.md)

## 相关链接

- **框架源码**: `rodski/`
- **历史文档归档**: `rodski/docs/archive/`
- **原始规范参考**: `.kiro/conventions/` (git history)

---

**最后更新**: 2026-04-02
