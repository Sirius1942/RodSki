# RodSki 迭代管理

## 迭代列表

| 迭代 | 周期 | 主题 | 状态 | 分支 |
|------|------|------|------|------|
| [Iteration 00](iteration-00/) | 2026-03-27 | 工程基础设施验证 | 📋 规划中 | iteration-00-infra |
| [Iteration 01](iteration-01/) | 2026-03-20 ~ 2026-03-27 | 视觉定位功能 | ✅ 已完成 | feature/vision-location |
| [Iteration 02](iteration-02/) | 2026-03-27 ~ 2026-04-10 | Agent 集成增强 | 🚧 进行中 | feature/agent-integration |
| [Iteration 03](iteration-03/) | TBD | CI/CD 能力重构 | 📋 规划中 | feature/cicd-refactor |

## 迭代类型说明

| 类型 | 说明 | 示例 |
|------|------|------|
| 基础设施 | 工程化准备、质量体系 | Iteration 00 |
| 功能开发 | 新功能实现 | Iteration 01, 02 |
| 重构优化 | 技术债务清理 | Iteration 03 |

## 迭代流程

### 1. 规划阶段
- 创建迭代目录 `iteration-XX/`
- 编写需求文档 `requirements.md`
- 设计技术方案 `design.md`
- 分解任务列表 `tasks.md`

### 2. 开发阶段
- 从 main 创建功能分支
- 按任务列表执行开发
- 编写测试用例
- 更新文档

### 3. 完成阶段
- 运行完整测试套件
- 代码审查
- 合并到 main 分支
- 更新迭代状态

## 规范引用

所有迭代必须遵循：
- [项目约束](../conventions/PROJECT_CONSTRAINTS.md)
- [Git 工作流](../conventions/GIT_WORKFLOW.md)

---

**最后更新**: 2026-03-27
