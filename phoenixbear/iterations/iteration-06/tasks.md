# Iteration 06: LLM 能力统一架构 - 任务列表

## 阶段 1：基础设施层（Week 1）

### 1.1 配置管理
- [ ] 创建 `rodski/llm/config.py`
- [ ] 实现配置加载逻辑（YAML + 环境变量）
- [ ] 编写配置单元测试

### 1.2 Provider 抽象
- [ ] 创建 `rodski/llm/providers/base.py`
- [ ] 实现 `OpenAIProvider`
- [ ] 实现 `ClaudeProvider`
- [ ] 编写 Provider 单元测试

### 1.3 统一客户端
- [ ] 创建 `rodski/llm/client.py`
- [ ] 实现 `LLMClient.chat()`
- [ ] 实现 `LLMClient.chat_with_vision()`
- [ ] 实现错误处理和重试机制
- [ ] 编写客户端单元测试

---

## 阶段 2：能力迁移（Week 2）

### 2.1 能力抽象
- [ ] 创建 `rodski/llm/capabilities/base.py`
- [ ] 实现 `BaseCapability` 抽象类

### 2.2 视觉定位迁移
- [ ] 创建 `rodski/llm/capabilities/vision_locator.py`
- [ ] 迁移 `llm_analyzer.py` 逻辑
- [ ] 更新 `rodski/vision/locator.py` 调用新架构
- [ ] 编写集成测试

### 2.3 缓存机制
- [ ] 创建 `rodski/llm/cache.py`
- [ ] 实现内存缓存
- [ ] 集成到 `LLMClient`

### 2.4 日志与监控
- [ ] 创建 `rodski/llm/telemetry.py`
- [ ] 记录调用耗时和 token 数

### 2.5 文档和测试
- [ ] 编写用户文档
- [ ] 端到端测试
- [ ] 兼容性测试

### 2.6 独立验证
- [ ] 创建独立测试脚本 `tests/llm/test_standalone.py`
- [ ] 验证配置加载（无需真实 API key）
- [ ] 验证 Provider 切换（OpenAI/Claude）
- [ ] 验证缓存机制
- [ ] 验证视觉定位能力（Mock LLM 响应）
- [ ] 生成验证报告

---

## 预计工时

| 阶段 | 任务数 | 工时 |
|------|--------|------|
| 阶段 1 | 9 | 40h |
| 阶段 2 | 15 | 48h |
| **总计** | **24** | **88h** |

---

## 不包含（移至 iteration-07）

- 结果审查 Agent（LangChain Agent）
- Agent 工具集
- 自动审查集成


