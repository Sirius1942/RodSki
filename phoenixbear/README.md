# PhoenixBear Studio

**飞熊项目工作室** — RodSki 自动化测试框架的项目管理体系。

## 概述

PhoenixBear 管理 RodSki 项目的所有迭代开发，涵盖需求、约束、设计、Agent 集成和测试规范。

## 核心约束（⭐ 必读）

> ⚠️ 每个迭代的实现**绝对不能违反**以下两份文档：
>
> - **[design/CORE_DESIGN_CONSTRAINTS.md](design/CORE_DESIGN_CONSTRAINTS.md)** — 框架核心设计决策（关键字、目录结构、XML Schema、自检约束等）
> - **[design/TEST_CASE_WRITING_GUIDE.md](design/TEST_CASE_WRITING_GUIDE.md)** — 用例编写规范（Case/Model/Data XML 格式）

详见 [conventions/PROJECT_CONSTRAINTS.md](conventions/PROJECT_CONSTRAINTS.md#8-核心文档不可违反约束)

## 目录索引

| 目录 | 说明 |
|------|------|
| **[design/](design/)** | 技术设计文档（含 ⭐ 核心约束） |
| **[conventions/](conventions/)** | 项目规范：Git 工作流、CI/CD、项目约束 |
| **[requirements/](requirements/)** | 需求文档总览 |
| **[agent/](agent/)** | Agent 开发规范与集成指南 |
| **[iterations/](iterations/)** | 迭代管理（iteration-03 ~ iteration-07） |

## 快速开始

### 1. 阅读核心约束

```bash
# 核心设计约束
cat phoenixbear/design/CORE_DESIGN_CONSTRAINTS.md

# 用例编写指南
cat phoenixbear/design/TEST_CASE_WRITING_GUIDE.md
```

### 2. 创建新迭代

```bash
git checkout main
git checkout -b feature/your-feature
```

### 3. 运行自检

```bash
cd rodski
python selftest.py
```

## 相关链接

- **框架源码**: `rodski/`
- **开发规范**: [conventions/](conventions/)

---

**最后更新**: 2026-04-02
