# RodSki Cursor 项目初始化管理记录

## 1. 记录元信息

- 项目名称：RodSki
- 初始化时间：2026-03-30
- 规则来源：`.pb/` 目录下规范与迭代文档
- 适用范围：Cursor 内 AI 协作开发、迭代管理、交付验收

## 2. 项目定位与目标

根据 `.pb/README.md`，RodSki 的定位是「辅助 AI Agent 工作」的文档与工具系统，核心能力为：

- 探索：视觉感知界面元素（Vision/OmniParser）
- 记录：以 XML 活文档沉淀 Case/Model/Data
- 执行：关键字驱动执行（如 type/send/verify/run）
- 观测：输出结构化结果、日志、截图供 Agent 决策

初始化目标：

- 建立统一的 Cursor 项目基线（规则、流程、验收口径）
- 明确不可违反的核心约束
- 将迭代执行标准化，降低协作偏差

## 3. 强制约束（必须遵守）

以下约束来自 `.pb/README.md` 与 `.pb/conventions/README.md`：

1. 不得违反核心设计约束文档  
   `rodski/docs/CORE_DESIGN_CONSTRAINTS.md`
2. 用例编写必须符合规范文档  
   `rodski/docs/TEST_CASE_WRITING_GUIDE.md`
3. 所有开发应从最新主干创建分支并遵循 Git 规范  
   `.pb/conventions/GIT_WORKFLOW.md`
4. 合并前必须完成基础自检（至少 `python selftest.py`）

## 4. 版本与分支管理基线

依据 `.pb/conventions/GIT_WORKFLOW.md`：

- 主干分支：`main`（保持可发布）
- 分支策略：Trunk-Based Development（分支开发、主干发布）
- 功能分支命名：
  - `feature/*`
  - `fix/*`
  - `refactor/*`
  - `docs/*`
  - `test/*`
  - `chore/*`
- 提交规范：Conventional Commits（`type(scope): subject`）

## 5. CI/CD 与质量基线

依据 `.pb/conventions/CI_CD_GUIDE.md`：

- 最小质量门槛：
  - 单元/自检可执行
  - 格式与质量检查可通过（Black、Flake8、Pylint、MyPy、Bandit）
- CI 输出物关注：
  - 测试结果
  - 失败截图与日志
- 建议在无头环境默认可执行（headless）

## 6. Agent 协作基线

依据 `.pb/agent/README.md` 与 `.pb/agent/LIVING_DOCUMENTATION.md`：

- 协作闭环：
  1. Agent 探索
  2. Agent 生成/更新 XML 活文档
  3. RodSki 执行
  4. Agent 解析结果并决策下一步
- 文档组织基线：
  - `model/`：页面模型
  - `case/`：测试用例
  - `data/`：测试数据
  - `result/`：执行结果
- 维护策略：
  - 优先增量更新
  - 文档变更纳入版本管理
  - 定期识别并更新过期文档

## 7. 迭代管理初始化状态

依据 `.pb/iterations/README.md` 当前内容（迭代 14-19 规划总结）：

- 规划状态：已完成
- 推荐执行原则：
  1. 按顺序执行迭代
  2. 每个迭代独立交付并记录
  3. 任务失败立即停止并记录问题
  4. 文档同步更新
  5. 回归测试必做

当前已定义后续迭代（14-19）的范围与工时，适合按发布节奏推进。

## 8. Cursor 初始化执行清单

- [ ] 阅读并确认核心约束文档（设计约束 + 用例规范）
- [ ] 以 `main` 为基线拉取最新并创建任务分支
- [ ] 建立本次迭代任务入口（目标、边界、验收标准）
- [ ] 明确本次改动的测试策略（单测/集成/回归）
- [ ] 开发完成后更新对应迭代记录（record/acceptance）
- [ ] 合并前完成自检并核对提交规范

## 9. 记录维护规则

- 本文档用于 Cursor 项目初始化和后续审计
- 当以下内容变化时必须更新：
  - 核心约束文档路径或条款
  - 分支/提交规范
  - CI 质量门槛
  - 迭代管理机制

---

最后更新：2026-03-30
