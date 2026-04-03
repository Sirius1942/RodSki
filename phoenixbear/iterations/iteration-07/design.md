# Iteration 07: 结果审查 Agent - 设计文档

## 一、架构设计

### 1.1 目录结构

```
rodski/
├── agents/                     # Agent 层（新增）
│   ├── __init__.py
│   ├── base.py                 # Agent 基类
│   ├── review_agent.py         # 结果审查 Agent
│   └── tools/                  # Agent 工具集
│       ├── __init__.py
│       ├── log_reader.py       # 日志读取工具
│       ├── screenshot_analyzer.py  # 截图分析工具
│       └── expectation_checker.py  # 预期对比工具
│
├── cli/
│   └── review.py               # CLI 入口
│
└── llm/                        # 依赖 iteration-06
    └── client.py
```

### 1.2 Agent 工作流程

```
用户触发
   ↓
ReviewAgent.invoke(result_dir)
   ↓
LangChain ReAct Agent
   ↓
推理循环:
  1. Thought: 我需要先读取日志
  2. Action: log_reader(result_dir)
  3. Observation: 发现 timeout 警告
  4. Thought: 需要查看截图
  5. Action: screenshot_analyzer(screenshot_05)
  6. Observation: 显示错误提示
  7. Thought: 对比预期
  8. Action: expectation_checker(case_xml)
  9. Final Answer: SUSPICIOUS
```

## 二、核心实现

### 2.1 Agent 基类

```python
# rodski/agents/base.py
from abc import ABC, abstractmethod
from langchain.agents import AgentExecutor

class BaseAgent(ABC):
    def __init__(self, llm_client):
        self.llm_client = llm_client
        self.agent = self._create_agent()

    @abstractmethod
    def _create_agent(self) -> AgentExecutor:
        """创建 LangChain Agent"""

    @abstractmethod
    def invoke(self, **kwargs):
        """执行 Agent"""
```

### 2.2 工具定义

```python
# rodski/agents/tools/log_reader.py
from langchain.tools import tool

@tool
def read_execution_log(result_dir: str) -> str:
    """读取测试执行日志，查找错误和警告"""
    log_path = f"{result_dir}/execution.log"
    with open(log_path) as f:
        return f.read()
```

