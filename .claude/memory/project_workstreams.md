---
name: project_workstreams
description: 当前迭代状态和待处理 Bug
type: project
---

**当前分支**：`main`（最新）

**最近的 git commit**：
- `608dccc` docs: 更新项目定位 - RodSki 是辅助 AI Agent 的文档与工具系统
- `7c5a8f0` docs: 整合 phoenixbear 文档 + 创建 .claude 项目空间
- `0662070` docs: 建立 PhoenixBear 项目管理体系
- `a542045` fix(keyword_engine): 修复批量输入时 click 等动作传入坐标缺失的问题
- `b84980f` release: Iteration 03 完成 - Bug 修复

**迭代状态**：
| 迭代 | 主题 | 状态 |
|------|------|------|
| iteration-03 | Bug 修复与依赖完善 | 已完成 |
| iteration-04 | Agent 集成基础设施 | 已完成 |
| iteration-05 | 活文档增强 | 待开始 |
| iteration-06 | 动态执行能力 | 待开始 |
| iteration-07 | 文档体系重构 | 待开始 |

**待处理事项（按优先级）**：
1. P0: 修复 `driver.type` 方法不存在
2. P1: 移除 pytest 依赖，改用 selftest.py
3. P1: 更新 config.yaml 中的数据路径
4. P2: 补充 `screenshot` 到 SUPPORTED
