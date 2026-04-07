# Iteration 13: 结构化执行日志 + 文档同步更新

**版本**: v4.1.4  
**日期**: 2026-04-07  
**分支**: V4.1.4  
**需求来源**: `.pb/specs/return_value_unified_design.md` §13.1 需求5、场景E/F/G  
**优先级覆盖**: P5（日志）+ 文档收尾  
**前置依赖**: iteration-09~12 全部完成

---

## 迭代目标

1. 实现 Info/Debug 两级结构化执行日志，满足人类快速阅读和 AI Agent 稳定消费的双重需求
2. 同步更新所有受影响的框架文档，将统一运行时上下文设计正式落入文档体系

---

## 核心约束（不可违反）

> - 不改变任何关键字的执行语义
> - 日志输出不影响测试结果判定逻辑
> - 结构化结果独立于日志文本，不依赖解析日志文本获取执行结果
> - 文档更新只补充新内容，不删除现有有效约束

---

## 设计决策

### D13-01: Info / Debug 双模式日志

**决策**:

- **Info 模式**（默认）：每步输出摘要行
  - 格式：`[STEP N] action=type model=InquiryCreate status=OK capture={inquiryNo: XJ001}`
  - 包含：步骤状态、关键返回值摘要、auto_capture 摘要、named 写入摘要
  - 不输出内部解析细节

- **Debug 模式**（`--log-level debug`）：每步输出完整链路
  - 参数解析链（模板替换前后）
  - auto_capture 触发过程、字段来源、字段值
  - history/named 增量变化
  - 失败类型区分：动作失败 / 自动提取失败 / 命名读取失败

**Why**: 规范需求5要求日志既适合人看也适合 AI Agent 判断，两种模式覆盖不同消费场景。

### D13-02: 结构化执行结果独立输出

**决策**: 每次 case 执行完成后，在结果目录写入 `execution_summary.json`：

```json
{
  "case": "...",
  "steps": [
    {
      "index": 1,
      "action": "type",
      "model": "InquiryCreate",
      "status": "ok",
      "return_source": "auto_capture",
      "return_value": {"inquiryNo": "XJ001"},
      "named_writes": {}
    }
  ],
  "context_snapshot": {
    "named": {"inquiryNo": "XJ001"}
  }
}
```

**Why**: AI Agent 不依赖解析自然语言日志，直接消费结构化 JSON，稳定可靠。

---

## 实施任务

### T13-001: 实现 Info 模式步骤日志
- 每步执行后输出摘要行（action、model、status、return 摘要）
- auto_capture 结果在摘要中体现
- named 写入在摘要中体现

### T13-002: 实现 Debug 模式步骤日志
- 参数解析链输出
- auto_capture 过程输出（字段名、locator、读取值）
- history/named 增量输出
- 失败类型区分输出

### T13-003: 生成 execution_summary.json
- case 执行完成后写入结果目录
- 包含每步的 return_source（keyword_result / auto_capture / get_named / evaluate）
- 包含 context 最终快照

### T13-004: 更新框架文档
- `CORE_DESIGN_CONSTRAINTS.md`：补充统一运行时上下文约束（§10 内容）
- `TEST_CASE_WRITING_GUIDE.md`：补充 set/get/auto_capture 用法示例
- `API_REFERENCE.md`：补充 get_text、更新 get/set/evaluate 说明
- `AGENT_INTEGRATION.md`：补充 execution_summary.json 消费说明

### T13-005: 验证用例
- 场景 E（Info 模式快速阅读）
- 场景 F（Debug 模式定位问题）
- 场景 G（AI Agent 基于结构化结果判断）
- 验收用例 7（evaluate 不替代主路径能力，文档层面体现）

---

## 验收标准

1. Info 模式每步输出摘要，包含 auto_capture 和 named 写入信息
2. Debug 模式可看到参数解析链、auto_capture 过程、history/named 增量
3. `execution_summary.json` 存在，包含 return_source 字段
4. 四份文档均已更新，内容与本设计规范一致
5. 现有回归用例全部通过

---

## 遗留与后续

- `context.objects` 路径访问能力（`${Order.first.orderNo}`）按需在后续迭代扩展
- 桌面端 auto_capture（OCR）按需扩展
