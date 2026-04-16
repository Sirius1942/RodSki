# Iteration 30: v7.0 Agent 优化 — Wave 1

> 版本: v7.0
> 分支: feature/rodski-agent-arch-refactor
> 日期: 2026-04-16
> 优先级: P0
> 状态: 🚧 进行中

---

## 目标

v7 核心目标：让 RodSki 的 AI Agent 壳（test agent + design agent）更好用、更准确、可度量。

本迭代（Iteration 30）覆盖 v7 全部 14 个工作项，分 3 波执行：

## 开发波次

### Wave 1 — 基础模块（并行开发）

无依赖的独立 WI，4 个 agent 并行：

| Agent | WI | 内容 | 文件范围 |
|-------|----|------|---------|
| Agent A | WI-63 + WI-64 | Case Tag + elif | schemas/, core/, CLI |
| Agent B | WI-40 | 报告数据模型 | NEW: report/ |
| Agent C | WI-50 + WI-62 | Trace + Network | NEW: observability/ + builtins/ |
| Agent D | WI-60 + WI-61 | Agent 记忆 + 文档 | rodski-agent/ + docs/ |

### Wave 2 — 依赖项（Wave 1 完成后）

| Agent | WI | 内容 | 依赖 |
|-------|----|------|------|
| Agent E | WI-41 | HTML 报告生成器 | WI-40 |
| Agent F | WI-42 + WI-44 | 历史趋势 + Agent 可视化 | WI-40 |
| Agent G | WI-43 + WI-51 | CLI 集成 + Token 计量 | WI-41 |

### Wave 3 — 顶层（Wave 2 完成后）

| Agent | WI | 内容 | 依赖 |
|-------|----|------|------|
| Agent H | WI-52 + WI-53 | KPI 评估 + 对比实验 | WI-50, WI-51 |

### 验收 — rodski-demo 端到端测试

使用 test agent 运行 rodski-demo 验收测试套件。

## 验收标准

1. 所有单元测试通过：`cd rodski && python3 -m pytest tests/unit -q`
2. rodski-demo 核心验收通过
3. 报告系统可生成 HTML 报告
4. Trace 数据可导出 JSON
5. Case Tag 过滤功能可用
6. elif 嵌套条件可用

## 参考文档

- `.pb/requirements/roadmap_v7_agent_optimization.md` — v7 需求文档
- `rodski/docs/CORE_DESIGN_CONSTRAINTS.md` — 核心约束
