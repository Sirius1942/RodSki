# Iteration 06: LLM 能力统一架构

## 概述

统一 RodSki 中所有 LLM 相关能力的基础设施，建立统一的配置、客户端和能力管理体系。

## 目标

1. 统一配置管理：单一配置文件 `llm_config.yaml`
2. 统一客户端：抽象 Provider（OpenAI/Claude/Azure）
3. 能力模块化：可插拔的 Capability 架构
4. 向后兼容：现有代码无需修改

## 范围

**包含**
- LLM 基础设施层（配置、客户端、Provider）
- 简单能力：视觉定位（迁移现有功能）
- 缓存、日志、测试

**不包含**
- 复杂 Agent（结果审查 Agent → iteration-07）
- 智能断言（未来）

## 文档

- [需求文档](requirements.md)
- [设计文档](design.md)
- [任务列表](tasks.md)
- [Agent 架构分析](review-agent-analysis.md)（为 iteration-07 准备）

## 状态

- 状态：设计中
- 开始时间：2026-04-03
- 预计完成：2 周

