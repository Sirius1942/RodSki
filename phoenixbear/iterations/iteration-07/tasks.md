# Iteration 07: 结果审查 Agent - 任务列表

## 阶段 1：Agent 基础（Week 1）

### 1.1 Agent 架构
- [ ] 创建 `rodski/agents/base.py`
- [ ] 实现 `BaseAgent` 抽象类
- [ ] 集成 LangChain 框架

### 1.2 工具集
- [ ] 创建 `rodski/agents/tools/log_reader.py`
- [ ] 创建 `rodski/agents/tools/screenshot_analyzer.py`
- [ ] 创建 `rodski/agents/tools/expectation_checker.py`
- [ ] 编写工具单元测试

### 1.3 ReviewAgent
- [ ] 创建 `rodski/agents/review_agent.py`
- [ ] 实现 ReAct Agent
- [ ] 编写 Agent 测试

---

## 阶段 2：集成（Week 2）

### 2.1 CLI 工具
- [ ] 创建 `rodski/cli/review.py`
- [ ] 实现命令行参数解析
- [ ] 输出格式化报告

### 2.2 自动审查
- [ ] 更新 `ski_executor.py`
- [ ] 添加配置支持
- [ ] 集成测试

### 2.3 文档
- [ ] 用户文档
- [ ] 示例和教程

---

## 预计工时

| 阶段 | 任务数 | 工时 |
|------|--------|------|
| 阶段 1 | 9 | 40h |
| 阶段 2 | 6 | 24h |
| **总计** | **15** | **64h** |
