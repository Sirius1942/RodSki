# RodSki Agent 自动化测试设计（OpenClaw 等）

**版本**: v1.1  
**日期**: 2026-03-24  
**适用范围**: OpenClaw / 通用 AI Agent 与 RodSki 集成

---

## 1. 目标与范围

本文定义：如何让 OpenClaw 这类 Agent 在 RodSki 上实现“可观测、可决策、可干预”的自动化测试闭环，包含：

- Agent 如何学习并理解 RodSki 的测试模型（关键字、模型、数据、结果）
- Agent 如何在运行中动态控制（暂停 / 插入 / 终止）
- 安全与审计边界
- 文档目录与落地路线

非目标：

- 不定义具体大模型 Prompt 细节
- 不绑定单一传输协议（HTTP / WebSocket / MQ 可替换）

---

## 2. 核心能力地图

### 2.1 Agent 能力分层

| 层级 | 能力 | 说明 |
|------|------|------|
| L1 感知 | 读取用例结构、步骤状态、日志、结果 | 仅观测，不改执行流 |
| L2 建议 | 生成建议动作（重试、补充验证、截图） | 人工确认后执行 |
| L3 控制 | 直接下发 pause/resume/insert/terminate | 需要权限与审计 |
| L4 自主闭环 | 按策略自动执行、自动回写总结 | 需要灰度与风控 |

建议上线顺序：L1 -> L2 -> L3 -> L4。

### 2.2 RodSki 对接能力（现状）

- 已具备运行时控制队列：`RuntimeCommandQueue`
- 已具备混合步骤执行（固定 + 动态 insert）
- 已具备 case 级临时资源作用域（临时 model/data 不污染后续 case）

---

## 3. 系统架构

## 3.1 组件图（逻辑）

1. **RodSki 执行器**
   - 产出运行事件（步骤开始/结束、失败、截图路径）
   - 接收控制命令（pause/resume/insert/terminate）
2. **Control Bridge（桥接层）**
   - 协议适配（HTTP / WS / MQ）
   - 命令校验、鉴权、去重、限流
3. **Agent Orchestrator（OpenClaw）**
   - 事件订阅
   - 决策与命令生成
   - 执行策略和风险控制
4. **Policy / Audit**
   - 白名单、黑名单、角色权限
   - 命令审计与可回放

### 3.2 关键原则

- 执行器只消费**标准化控制命令**，不直接依赖 Agent 内部实现
- 动态插入步骤必须与 `test_step` 同构（`action/model/data`）
- 除 `force_terminate` 外，命令默认在**步骤边界**生效

---

## 4. 控制协议（建议）

### 4.1 命令模型

```json
{
  "run_id": "run_20260324_001",
  "case_id": "TC001",
  "command": "insert",
  "force": false,
  "steps": [
    {"action": "wait", "model": "", "data": "0.5"}
  ],
  "temp_models": {},
  "temp_tables": {},
  "reason": "agent_recovery_rule",
  "request_id": "uuid"
}
```

### 4.2 命令白名单

- `pause`
- `resume`
- `insert`
- `terminate`（`force=true/false`）

### 4.3 幂等与顺序

- `request_id` 做幂等去重
- 同一 `run_id + case_id` 内按接收顺序入队

---

## 5. Agent 学习与使用 RodSki 的方式

## 5.1 知识输入（静态）

Agent 首先学习：

- `核心设计约束.md`
- `../user-guides/TEST_CASE_WRITING_GUIDE.md`
- `../user-guides/CLI_DESIGN.md`
- `../user-guides/REPORT_GUIDE.md`

并抽取以下知识图谱：

- 关键字语义（type/send/verify/run/DB）
- 数据引用语义（GlobalValue、Return）
- 阶段语义（pre_process/test_case/post_process）
- 结果语义（PASS/FAIL/SKIP/ERROR）

### 5.2 运行输入（动态）

- 步骤事件流（start/end/error）
- 日志流
- 结果 XML / 汇总统计
- 运行时截图

### 5.3 决策策略（示例）

- 规则 1：`verify` 失败且错误可重试 -> `insert(wait 0.5s + verify)`  
- 规则 2：同 case 连续失败 >= N -> `pause` 并告警
- 规则 3：步骤超时风险高 -> `terminate(force=true)`

---

## 5.4 用户视角双阶段工作流（定稿）

为避免 Agent 直接“边跑边猜”导致不可控，RodSki 面向通用 AI Agent 采用两阶段闭环：

### A. 测试任务设计阶段（Design Time）

目标：根据测试任务设计要求，利用 Agent 自身探索能力生成并调试可执行用例。

1. 读取任务目标与约束（业务流程、关键断言、优先级）
2. 探索目标测试网站（页面结构、关键路径、异常分支）
3. 依据 RodSki 规则生成 `case/model/data/globalvalue`
4. 进行 dry-run 与小样本执行调试
5. 产出可执行用例包与设计说明（覆盖点/边界/已知风险）

### B. 测试执行与监控阶段（Run Time）

目标：根据执行需求选择合适用例运行，并在失败时通过动态机制进行分诊与处置。

1. 按执行目标选择用例集（冒烟/回归/模块）
2. 执行并实时监控（步骤状态、日志、截图、结果）
3. 失败触发动态机制（pause/insert/terminate）
4. 判断失败属于“用例问题”还是“环境问题”（见 §5.5）
5. 形成执行结论与后续动作（修用例/修环境/提产品缺陷）

---

## 5.5 动态机制中的问题分诊（规划）

在动态用例机制中，Agent 不应只做“是否重试”的浅判断，而应输出标准化问题类型：

- `CASE_DEFECT`：用例设计或数据定义问题
- `ENV_DEFECT`：环境/依赖服务异常
- `PRODUCT_DEFECT`：疑似产品缺陷
- `UNKNOWN`：证据不足，待人工确认

该分诊结果用于后续动作路由：

- `CASE_DEFECT` -> 建议修复/重生用例
- `ENV_DEFECT` -> 暂停/重试/切换环境
- `PRODUCT_DEFECT` -> 保全证据并提缺陷

> 说明：分诊能力可先规则化实现，后续接入多模态 LLM 增强（与《核心设计约束》后续条款保持一致）。

---

## 6. 安全、风控与审计

### 6.1 权限模型

| 角色 | 权限 |
|------|------|
| Observer | 只读观测 |
| Operator | pause/resume/普通 terminate |
| Controller | insert |
| Admin | force_terminate |

### 6.2 风控规则

- `insert` 的 `action` 白名单（首版建议限制为 wait/verify/screenshot/set）
- 单 case 最大插入步数上限（如 10）
- 单 run 命令频率限制（如 5/s）
- `force_terminate` 需高权限 + 审计理由

### 6.3 审计字段

- `timestamp`, `operator`, `agent_id`, `run_id`, `case_id`
- `command`, `payload_hash`, `reason`, `result`

---

## 7. 文档目录建议（信息架构）

建议在 `rodski/docs/design/agent/`（或同级专题目录）下新增：

```text
design/agent/
├── AGENT_AUTOMATION_OVERVIEW.md      # 总览与术语
├── AGENT_CONTROL_PROTOCOL.md         # 命令协议与字段定义
├── AGENT_POLICY_AND_GUARDRAILS.md    # 安全策略、权限、风控
├── AGENT_RUNTIME_EVENTS.md           # 事件模型与回调字段
├── AGENT_PLAYBOOK.md                 # 典型场景 SOP（失败恢复、超时处理）
└── AGENT_ROLLOUT_PLAN.md             # 灰度、验收、回滚策略
```

当前文档（本文件）可作为总入口，后续按专题拆分。

---

## 8. 落地计划（建议）

### Phase 1（最小可用）

- 增加 Control Bridge（本地 HTTP）
- 支持四个命令：pause/resume/insert/terminate
- 事件日志输出到 JSONL

### Phase 2（可运营）

- 增加鉴权、审计、限流、命令白名单
- 增加策略引擎（规则优先，LLM 辅助）

### Phase 3（自主闭环）

- Agent 自动恢复策略（带置信度阈值）
- 回归报表自动生成与问题聚类

---

## 9. 验收标准

- 95% 命令在预期步骤边界生效
- pause/resume 无死锁
- insert 不污染后续 case 资源
- 审计日志可完整回放
- 关键失败场景（超时/元素缺失/断言失败）可自动处置

---

## 10. 与当前代码映射

- 运行时控制：`core/runtime_control.py`
- 执行器消费命令：`core/ski_executor.py`
- demo：`rodski-demo/DEMO/demo_runtime_control/`
- 现有约束：`核心设计约束.md` 第 8 节

