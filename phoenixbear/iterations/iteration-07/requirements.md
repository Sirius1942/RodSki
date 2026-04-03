# Iteration 07: 结果审查 Agent - 需求文档

## 一、背景

### 1.1 问题

当前测试结果仅基于关键字执行状态判断（PASS/FAIL），存在误判：
- 步骤执行成功，但页面显示错误
- 截图显示异常，但未被检测
- 日志有警告，但测试标记为 PASS

### 1.2 解决方案

使用 LangChain Agent 实现智能审查，通过多步推理判断测试真实性。

---

## 二、功能需求

### FR1: LangChain Agent 架构

**需求描述**
- 使用 LangChain ReAct Agent
- 支持多步推理和工具调用
- 自主决策审查流程

**验收标准**
- [ ] 实现 Agent 基类
- [ ] 集成 LangChain 框架
- [ ] 支持工具调用

### FR2: Agent 工具集

**需求描述**
- 日志读取工具
- 截图分析工具
- 预期对比工具

**验收标准**
- [ ] 实现至少 3 个工具
- [ ] 工具可独立测试

### FR3: CLI 工具

**需求描述**
```bash
rodski review result/run_20260403_084451
```

**验收标准**
- [ ] 提供 CLI 入口
- [ ] 输出审查报告

### FR4: 自动审查

**需求描述**
- 测试执行完成后自动触发
- 可配置开启/关闭

**验收标准**
- [ ] 集成到 ski_executor
- [ ] 配置文件控制

---

## 三、用例示例

### 用例 1：CLI 审查

```bash
rodski review result/run_20260403_084451

# 输出
正在审查: result/run_20260403_084451
Agent 推理过程:
  1. 读取日志，发现 timeout 警告
  2. 分析截图 05，发现错误提示
  3. 对比用例预期，不符合
结果: SUSPICIOUS (置信度 85%)
理由: 截图显示网络连接失败
```

### 用例 2：自动审查

```yaml
# config.yaml
review:
  enabled: true
  on_pass: false
  on_fail: true
```

```bash
# 执行测试
rodski run cases/login_test.xml

# 自动触发审查
[INFO] 测试完成: PASS
[INFO] 自动审查中...
[WARN] 审查结果: SUSPICIOUS - 发现异常
```

---

## 四、技术选型

| 组件 | 技术 | 理由 |
|------|------|------|
| Agent 框架 | LangChain | 成熟的 Agent 框架 |
| Agent 类型 | ReAct | 支持推理和工具调用 |
| 工具定义 | @tool 装饰器 | 简单易用 |

---

## 五、待讨论

1. Agent 推理过程是否展示给用户？
2. 审查报告格式（JSON/Markdown）？
3. 是否支持批量审查？


