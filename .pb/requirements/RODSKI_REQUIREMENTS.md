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

2. **设计符合性** — 实现与 `../../rodski/docs/CORE_DESIGN_CONSTRAINTS.md` 一致；重大偏离需评审并更新文档。

3. **用户可交付性** — 最终用户能依据 RodSki 框架完成安装、编写用例、执行与报告。

---

## 4. 关键约束

- ⭐ 每个迭代的实现**绝对不能违反** `../../rodski/docs/CORE_DESIGN_CONSTRAINTS.md`
- ⭐ 每个迭代的实现**绝对不能违反** `../../rodski/docs/TEST_CASE_WRITING_GUIDE.md`

### 4.1 单元测试与报告门禁

1. 任何代码修改（源码、测试、配置、脚本）完成后，必须运行与改动范围对应的单元测试；涉及核心公共逻辑或无法明确影响面时，默认执行 `python3 -m pytest tests/unit -q` 全量单元测试。
2. 单元测试未通过时，该次修改不得视为完成；若存在已知问题，必须通过失败说明、`xfail` 或后续修复记录明确标注。
3. 每次执行 pytest 单元测试后，必须将执行结果整理为 Markdown 报告并纳入 `.pb` 项目管理文档。
4. 报告统一存放到对应迭代目录，文件名使用 `test_report_YYYY-MM-DD_HHMM.md`，例如 `.pb/iterations/iteration-25/test_report_2026-04-13_0804.md`。
5. 报告至少包含：执行时间、分支/commit、执行命令、通过/失败/xfailed/skipped 汇总、关键 warnings、是否可交付的结论。

详见 `../../rodski/docs/CORE_DESIGN_CONSTRAINTS.md` 附录 A

---

## 5. 相关文档

- 设计约束: [../../rodski/docs/CORE_DESIGN_CONSTRAINTS.md](../../rodski/docs/CORE_DESIGN_CONSTRAINTS.md)
- 用例编写: [../../rodski/docs/TEST_CASE_WRITING_GUIDE.md](../../rodski/docs/TEST_CASE_WRITING_GUIDE.md)
- Agent 开发: [../agent/README.md](../agent/README.md)
- 项目规范: [../conventions/README.md](../conventions/README.md)
