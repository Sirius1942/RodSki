# Agent 开发规范

RodSki 作为 AI Agent 操作执行层的开发规范与集成指南。

## 文档列表

| 文档 | 说明 |
|------|------|
| [AGENT_INTEGRATION.md](AGENT_INTEGRATION.md) | Agent 集成指南 — 集成模式、核心职责、环境准备 |
| [AGENT_SKILL_GUIDE.md](AGENT_SKILL_GUIDE.md) | RodSki Agent 使用指南 — 协作模式、职责划分 |
| [SKILL_REFERENCE.md](SKILL_REFERENCE.md) | Skill 参考文档 — 核心 Skill 语法和示例 |
| [LIVING_DOCUMENTATION.md](LIVING_DOCUMENTATION.md) | 活文档规范 — XML 活文档 vs 传统文档 |
| [ERROR_HANDLING.md](ERROR_HANDLING.md) | 错误处理最佳实践 — 定位错误分类和 Agent 处理策略 |

## Agent 协作模式

```
1. Agent 探索 → 发现元素和操作路径
2. Agent 生成 XML → 记录为活文档
3. Agent 调用 RodSki → 执行 XML
4. RodSki 返回结果 → Agent 分析并决策下一步
```

**RodSki 的职责**：
- ✅ 执行 XML 定义的操作
- ✅ 支持视觉定位器类型（vision/vision_bbox）
- ✅ 返回结构化的执行结果
- ✅ 提供工具辅助 Agent 生成 XML

**Agent 的职责**：
- ✅ 探索页面/应用（使用自己的视觉能力）
- ✅ 生成模型 XML（使用 LLM 能力）
- ✅ 决策执行策略（选择用例、插入步骤）
- ✅ 处理执行结果并调整

---

**关联规范**: [../conventions/PROJECT_CONSTRAINTS.md](../conventions/PROJECT_CONSTRAINTS.md)
