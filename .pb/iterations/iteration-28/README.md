# Iteration 28: LLM 统一服务层

**版本**: v5.6.0  
**分支**: release/v5.6.0  
**预计工时**: 5h  
**优先级**: P1  
**状态**: 📋 待开始  
**依赖**: iteration-27 完成

---

## 目标

1. BaseProvider 增加 `call_text()` 方法
2. 新增 `screenshot_verifier` 能力，迁移 ai_verifier.py
3. 新增 `test_reviewer` 能力，迁移 llm_reviewer.py
4. 移除 llm_analyzer.py 遗留回退代码
5. 合并 3 个配置文件为 1 个 `llm_config.yaml`

## 包含工作项

| WI | 名称 | 大小 | 来源 |
|----|------|------|------|
| WI-08 | BaseProvider 增加 call_text | S | Phase 2 |
| WI-09 | screenshot_verifier 能力 | M | Phase 2 |
| WI-10 | test_reviewer 能力 | M | Phase 2 |
| WI-11 | llm_analyzer 移除遗留 | S | Phase 2 |
| WI-12 | 合并配置 + diagnosis_engine | M | Phase 2 |

## 设计约束

- 所有 LLM 直接 SDK 调用集中到 `rodski/llm/providers/` 目录
- 外部模块通过 `LLMClient.get_capability()` 获取能力
- 配置统一从 `llm_config.yaml` 加载
- AI 能力作为可选层，核心执行不依赖 LLM
