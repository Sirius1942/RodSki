# Iteration 29 任务清单

**版本**: v5.7.0  
**分支**: release/v5.7.0  
**依赖**: iteration-27 + iteration-28 完成

---

## T29-001: 重写 README.md [1h]

### 改动

1. **标题/定位**
   - 从：`RodSki 是一个关键字驱动的自动化测试框架`
   - 到：`RodSki — 面向 AI Agent 的跨平台确定性执行引擎`

2. **副标题**
   - 新增：`Agent 负责思考，RodSki 负责稳定执行。`

3. **特性列表重写**
   - 结构化 XML 协议（model/case/data 活文档）
   - 多平台确定性执行（Web/Android/iOS/Desktop）
   - 视觉定位能力（OmniParser + LLM，可选）
   - Agent 友好 CLI（run/validate/explain/dry-run，JSON 输出）
   - 活文档模式（Agent 写 XML → RodSki 执行 → 结果反馈 → Agent 分析）
   - 智能诊断与恢复（AI 可选能力层）

4. **快速开始重写**
   - 展示 Agent 集成流：
     ```bash
     rodski run case/ --output-format json
     rodski explain case/login.xml
     rodski run case/ --dry-run
     ```
   - 保留人类手动使用方式作为次要说明

5. **项目结构更新**
   - 反映 XML-only、无 Excel、无 examples/agent/

### 验证

- README 中不再出现"自动化测试框架"作为主定位
- 首屏传达的是 Agent 执行引擎定位

---

## T29-002: 重写 AGENT_INTEGRATION.md 为主入口文档 [1.5h]

### 改动

1. **开头**：明确 RodSki 是工具和协议，不是 Agent 框架
2. **新增 "Agent 接口契约"节**：
   - CLI 命令清单（run/validate/explain/dry-run）
   - 输入格式规范（XML-only，`<location>` 唯一格式）
   - 输出格式规范（execution_summary.json 结构定义）
   - 错误契约（错误类型 → Agent 处理策略映射）
3. **XML 生成策略**（§3）：所有示例代码改为生成 `<location>` 格式
4. **视觉定位集成**（§5）：所有示例改为 `<location>` 格式
5. **return_source 说明**：统一描述 Return 引用机制和 execution_summary.json
6. **最佳实践**：强调 Agent 作为调用方，RodSki 作为执行器
7. **删除/简化**：移除已归档 Agent 示例的引用

### 验证

- 文档作为 Agent 开发者唯一入口，信息自洽
- 无 `locator=` 旧格式、无 Excel 引用

---

## T29-003: ARCHITECTURE.md 叙事更新 [0.5h]

### 改动

1. 标题从"项目架构文档"调整为体现执行引擎定位
2. 核心架构图中的文字描述从"测试框架"改为"执行引擎"
3. 确认已在 iteration-27 中清理完 Excel 引用
4. 增加 LLM 能力层在架构图中的位置（可选层）

---

## T29-004: CORE_DESIGN_CONSTRAINTS.md 新增 Agent 契约节 [0.5h]

### 改动

新增一节 "Agent 契约摘要"：
- 唯一输入格式：XML（case/model/data）
- 唯一定位器格式：`<location type="...">value</location>`
- 唯一结果格式：execution_summary.json
- 关键字清单（type/send/verify/run/navigate/launch/...）
- 版本号标注，便于 Agent 判断兼容性

---

## T29-005: CLAUDE.md + SKILL_REFERENCE.md 更新 [0.3h]

### 改动

1. `CLAUDE.md` 项目描述更新：
   - 从"关键字驱动测试框架"改为"面向 AI Agent 的执行引擎"
   - 更新项目结构（无 examples/agent/、无 Excel）

2. `rodski/docs/SKILL_REFERENCE.md`：
   - 确认叙事与 Agent 执行引擎定位一致

---

## T29-006: 最终全面审计 [0.2h]

### 验证

```bash
# 定位叙事审计：主要文档中不应出现"自动化测试框架"作为主定位
grep -r '自动化测试框架' rodski/docs/ README.md CLAUDE.md

# 旧格式残留审计
grep -r 'locator="' rodski/ --include="*.xml" --include="*.md"
grep -ri 'excel\|\.xlsx' rodski/ --include="*.py" --include="*.md"
grep -r 'from openai\|import openai\|import anthropic' rodski/ --include="*.py"

# Agent 示例审计
ls rodski/examples/agent/ 2>/dev/null && echo "FAIL: 目录仍存在" || echo "OK"
```

---

## 执行顺序

```
T29-001 (README)
    ↓
T29-002 (AGENT_INTEGRATION)
    ↓
T29-003 ~ T29-005 (其他文档，可并行)
    ↓
T29-006 (最终审计)
```

## 工时估算

| 任务 | 预估 |
|------|------|
| T29-001 | 1.0h |
| T29-002 | 1.5h |
| T29-003 | 0.5h |
| T29-004 | 0.5h |
| T29-005 | 0.3h |
| T29-006 | 0.2h |
| **合计** | **4h** |
