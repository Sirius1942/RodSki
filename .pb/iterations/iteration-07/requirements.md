# Iteration 07: 文档体系重构 — 需求文档

**周期**: 2026-05-18 ~ 2026-05-24 (1 周)  
**目标**: 建立完整的 RodSki 文档体系，支撑 AI Agent 集成和工程化落地

---

## 背景

RodSki 经过前 6 个迭代，功能已相对完善，但文档分散在多个文件中，缺乏系统整理：

1. **缺少 Agent 集成指南**: AI Agent（如 Claude Code、OpenCode）如何集成 RodSki 的指引不完整
2. **Skill 参考文档缺失**: RodSki 作为 OpenClaw skill 的集成方式未文档化
3. **最佳实践分散**: 错误处理、性能优化等最佳实践散落在各处
4. **文档结构不清晰**: 用户难以快速找到所需信息

Iteration 07 将对 RodSki 文档进行全面重构，建立清晰的文档结构。

---

## 功能需求

### F7-1: Agent 集成指南

#### F7-1.1: 核心集成接口文档
**文件**: `docs/agent-integration/AGENT_INTEGRATION.md` (重构)

完整的 Agent 集成指南，包含：

1. **RodSki 作为工具调用**: 将 RodSki 封装为 Agent 工具
   - CLI 工具调用接口
   - Python API 编程接口
   - 输入输出格式说明

2. **Agent ↔ RodSki 交互协议**:
   ```
   Agent → rodski run → Result XML/JSON
   Agent → rodski explain → 自然语言描述
   Agent → rodski stats → 统计报告
   ```

3. **多 Agent 场景**:
   - 单 Agent 控制 RodSki 执行
   - 多 Agent 协作（规划 Agent + 执行 Agent）
   - Agent 反馈驱动 RodSki 重试

#### F7-1.2: OpenClaw Skill 集成
**文件**: `docs/agent-integration/OPENCLAW_SKILL.md` (新)

RodSki 作为 OpenClaw skill 的集成方式：

```json
{
  "name": "rodski",
  "description": "SKI 自动化测试执行引擎",
  "commands": {
    "run": {
      "description": "运行测试用例",
      "args": ["case.xml"],
      "options": ["--env", "--output-format", "--parallel"]
    },
    "explain": {
      "description": "解释测试用例为自然语言",
      "args": ["case.xml"]
    },
    "stats": {
      "description": "聚合执行统计",
      "args": ["result_dir"]
    }
  }
}
```

#### F7-1.3: Claude Code / OpenCode 集成示例
**文件**: `examples/agent/claude_code_integration.py` (新)  
**文件**: `examples/agent/opencode_integration.py` (新)

提供完整的 Agent 集成代码示例，包括：
- 工具注册
- 执行结果解析
- 错误处理和重试
- 自然语言反馈生成

### F7-2: Skill 参考文档

#### F7-2.1: 关键字参考
**文件**: `docs/reference/KEYWORD_REFERENCE.md` (新)

完整的 17 个关键字参考，每个关键字包含：

```markdown
## click

**描述**: 点击页面元素

**参数**:
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| locator | string | 是 | 元素定位器（CSS/XPath/id）|
| timeout | integer | 否 | 超时时间（秒），默认 10 |

**示例**:
```xml
<step keyword="click">
  <param name="locator">#submit-btn</param>
  <param name="timeout">15</param>
</step>
```

**错误处理**:
- `ElementNotFoundError`: 元素未找到，增加等待或检查 locator
- `StaleElementError`: 元素已失效，重新定位元素

**可与以下关键字组合**: verify (前置验证), wait (等待动画), screenshot (记录)
```

#### F7-2.2: 配置项参考
**文件**: `docs/reference/CONFIG_REFERENCE.md` (新)

`config/default_config.yaml` 所有配置项的完整参考：

- 按模块分组（execution / recovery / result / vision 等）
- 每个配置项: 名称 / 类型 / 默认值 / 说明 / 示例
- 配置优先级说明（CLI > 环境变量 > 配置文件）
- 敏感配置加密方案

#### F7-2.3: CLI 命令参考
**文件**: `docs/reference/CLI_REFERENCE.md` (新)

`rodski` 所有子命令的完整参考：

```
rodski run        - 运行测试用例
rodski explain    - 解释测试用例
rodski validate   - 验证用例 XML
rodski stats      - 聚合统计报告
rodski replay     - 从快照重放执行
rodski compare    - 对比两次执行结果
```

每个子命令包含: 用法 / 参数 / 选项 / 示例 / 退出码

### F7-3: 错误处理最佳实践

#### F7-3.1: 错误处理模式
**文件**: `docs/best-practices/ERROR_HANDLING.md` (重构)

扩展现有的 `docs/user-guides/EXCEPTION_HANDLING.md`，新增：

1. **分层错误处理策略**:
   - 步骤级: 单步失败时的重试和恢复
   - 用例级: 单用例失败时的处理策略
   - 套件级: 批量执行时的容错策略

2. **常见错误场景与解决方案**:
   | 场景 | 原因 | 解决方案 |
   |------|------|---------|
   | 元素定位失败 | 页面加载慢/定位器错误 | 添加 wait / 检查 locator |
   | 断言失败 | 预期值错误/UI 变化 | 更新预期值 / 使用 AI 诊断 |
   | 超时 | 网络慢/页面无响应 | 增加 timeout / 检查死循环 |
   | 内存泄漏 | 长时间运行 | 浏览器回收 / GC 触发 |

3. **RecoveryEngine 最佳实践**:
   - 恢复动作优先级
   - 恢复次数限制
   - 避免恢复动作本身失败

#### F7-3.2: 性能优化指南
**文件**: `docs/best-practices/PERFORMANCE.md` (新)

- 浏览器复用策略（共享模式 vs 独立模式）
- 元素定位优化（CSS > XPath > 文字）
- 等待策略（显式等待 > 隐式等待 > 固定 sleep）
- 并行执行策略
- 内存管理（快照频率、清理策略）

---

## 文档结构重构

### 目标结构

```
docs/
├── README.md                    # 文档首页，导航入口
├── getting-started/
│   ├── INSTALL.md               # 安装指南
│   ├── QUICKSTART.md            # 快速开始
│   └── FIRST_TEST.md            # 编写第一个测试用例
├── user-guides/
│   ├── TEST_CASE_WRITING.md     # 用例编写指南
│   ├── EXCEPTION_HANDLING.md    # 异常处理（重构）
│   ├── DYNAMIC_EXECUTION.md     # 动态执行（Iteration-06）
│   ├── RESULT_REPORT.md         # 结果报告解读
│   ├── PARALLEL_EXECUTION.md   # 并行执行
│   └── TROUBLESHOOTING.md       # 故障排查
├── agent-integration/           # (新增)
│   ├── AGENT_INTEGRATION.md    # Agent 集成指南
│   └── OPENCLAW_SKILL.md       # OpenClaw Skill 集成
├── reference/                   # (新增)
│   ├── KEYWORD_REFERENCE.md    # 关键字参考
│   ├── CONFIG_REFERENCE.md     # 配置项参考
│   └── CLI_REFERENCE.md        # CLI 命令参考
└── best-practices/             # (新增)
    ├── ERROR_HANDLING.md       # 错误处理最佳实践
    └── PERFORMANCE.md          # 性能优化指南
```

### 文档首页
**文件**: `docs/README.md` (重构)

提供清晰的文档导航：

```
# RodSki 文档

[Getting Started] → [User Guides] → [Agent Integration] → [Reference] → [Best Practices]

## 我想...

🚀 **快速开始** → `docs/getting-started/QUICKSTART.md`
✍️ **编写测试用例** → `docs/user-guides/TEST_CASE_WRITING.md`
🤖 **集成到 AI Agent** → `docs/agent-integration/AGENT_INTEGRATION.md`
📊 **查看测试结果** → `docs/user-guides/RESULT_REPORT.md`
🔧 **排查问题** → `docs/user-guides/TROUBLESHOOTING.md`
📖 **了解所有关键字** → `docs/reference/KEYWORD_REFERENCE.md`
```

---

## 非功能需求

### 可维护性
- 所有示例代码必须经过实际运行验证
- 文档与代码同步更新（PR 时同步检查）
- 使用 Markdownlint 保证格式一致性

### 可发现性
- 文档内交叉引用使用相对链接
- 文档顶部包含"相关文档"导航
- 关键词在文档中多次出现（SEO 友好）

### 国际化
- 文档以英文为主（面向国际用户）
- 中文翻译放在 `docs/zh/` 目录（可选）

---

## 里程碑

| 阶段 | 交付物 | 目标日期 |
|------|--------|---------|
| M7-1 | 文档目录结构重构 + 导航首页 | 2026-05-19 |
| M7-2 | Agent Integration 文档 | 2026-05-21 |
| M7-3 | Reference 参考文档 | 2026-05-22 |
| M7-4 | Best Practices + 文档审查 | 2026-05-24 |
