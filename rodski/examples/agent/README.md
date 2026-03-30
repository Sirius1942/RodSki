# RodSki Agent 集成示例

本目录包含 RodSki 与各类 AI Agent 框架集成的完整示例代码：

- `claude_code_integration.py` — Claude Code 集成完整示例
- `opencode_integration.py` — OpenCode / Gemini CLI 集成完整示例
- `multi_agent_example.py` — 多 Agent 协作示例

## 快速开始

```bash
# Claude Code 集成
python examples/agent/claude_code_integration.py test_cases/login.xml

# OpenCode 集成
python examples/agent/opencode_integration.py test_cases/search.xml

# 多 Agent 协作
python examples/agent/multi_agent_example.py test_suite/
```

## 前置条件

- RodSki 已安装 (`pip install -e .`)
- RodSki CLI 在 PATH 中
- Python 3.9+

## 示例说明

每个示例文件都包含详细注释，说明如何：
1. 调用 RodSki 执行测试
2. 处理执行结果
3. 错误处理和重试
4. 与 Agent 工作流集成
