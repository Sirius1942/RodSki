# RodSki 需求总览

**目的**：作为需求与验收的**单一入口**。

---

## 1. 原始需求与目的

RodSki 是一套**文档与工具系统**，核心定位是**辅助 AI Agent 工作**：

- **探索** — Vision/OmniParser 视觉感知界面元素
- **记录** — XML 活文档（Case + Model + Data）替代静态文档
- **执行** — 关键字驱动（type/send/verify/run）执行操作
- **观测** — 结构化结果（JSON）、日志、截图供 Agent 决策

统一覆盖 **Web / 移动端 / 桌面 / API / 数据库** 等场景。

---

## 2. 要解决的关键问题

| 问题域 | 说明 |
|--------|------|
| 用例与数据分离 | 用例步骤、元素/接口模型、测试数据分层管理，便于维护与复用 |
| 多端一致抽象 | 关键字与数据模型统一，驱动层可替换 |
| 可执行与可观测 | 解析、执行、结果、日志、截图、报告形成闭环 |
| 可扩展 | 新关键字、新驱动、新协议在约束下扩展 |
| 可演进 | 动态步骤、运行时控制、Agent 集成等能力在架构约束下迭代 |

---

## 3. 验收原则

验收分三层：

1. **需求与范围** — 与本文档一致。

2. **设计符合性** — 实现与 `../design/CORE_DESIGN_CONSTRAINTS.md` 一致；重大偏离需评审并更新文档。

3. **用户可交付性** — 最终用户能依据 RodSki 框架完成安装、编写用例、执行与报告。

---

## 4. 关键约束

- ⭐ 每个迭代的实现**绝对不能违反** `../design/CORE_DESIGN_CONSTRAINTS.md`
- ⭐ 每个迭代的实现**绝对不能违反** `../design/TEST_CASE_WRITING_GUIDE.md`

详见 `../conventions/PROJECT_CONSTRAINTS.md#8-核心文档不可违反约束`

---

## 5. 相关文档

- 设计约束: [../design/CORE_DESIGN_CONSTRAINTS.md](../design/CORE_DESIGN_CONSTRAINTS.md)
- 用例编写: [../design/TEST_CASE_WRITING_GUIDE.md](../design/TEST_CASE_WRITING_GUIDE.md)
- Agent 开发: [../agent/README.md](../agent/README.md)
- 项目规范: [../conventions/README.md](../conventions/README.md)
