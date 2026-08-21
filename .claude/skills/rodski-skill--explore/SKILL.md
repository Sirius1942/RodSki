---
name: explore
description: RodSki AI 驱动的探索式测试能力。当用户要求"探索测试"、"智能探索"、"exploratory testing"、"发现边界问题"、"自动探索应用"时使用。基于已通过用例建立基线，探索合理业务边界线下的异常问题。框架无关，支持任何能加载 Markdown skill 的 Agent。
---

# RodSki Explore - 探索式测试

使用本 skill 时，将启用 RodSki 的 AI 驱动探索测试能力，让 AI Agent 基于已有测试资产，智能发现边界条件和隐藏问题。

## 核心理念

**探索式测试不是替代传统测试，而是互补增强。**

- **传统测试 (rodski run)**：固定脚本，100% 可重复，验证已知功能
- **探索式测试 (explore-step)**：AI 智能探索，动态路径，发现预期外问题

两种测试方式各有优势，共同构成完整的测试体系。

## 何时使用探索式测试

### ✅ 适用场景

1. **基于已有测试资产探索边界** - 已有通过的用例，想找出未覆盖的边界条件
2. **数值边界验证** - 探索 0、负数、超大值、非数字等边界输入
3. **数据唯一性测试** - 验证用户名重复、订单号冲突等唯一性约束
4. **并发场景探索** - 多标签页、多用户同时操作
5. **异常场景** - 网络中断、超时、后端异常时的表现
6. **安全边界** - XSS、SQL 注入尝试、特殊字符处理

### ❌ 不适用场景

1. **首次编写测试** - 应先用传统用例覆盖核心流程
2. **完全未知的应用** - 探索测试需要参考已有用例
3. **性能压测** - 应使用 `rodski run @plan --load-ui`
4. **纯功能验证** - 已知路径用传统用例更合适

---

## 执行纪律（分阶段）

### 阶段 0：建立探索基线（Baseline）

**目标**：理解"已知的正常行为"是什么，找到探索的起点。

```bash
# 1. 列出所有已通过的用例
cd product/cassmall/payment  # 进入模块目录
rodski run case/ --dry-run | grep PASS

# 或查看最近一次运行结果
cat result/latest/result.xml | grep 'status="PASS"'

# 示例输出：
# TC_PAY_001: 正常支付（余额充足）✓
# TC_PAY_002: 支付失败（余额不足）✓
# TC_PAY_003: 支付取消 ✓
```

```bash
# 2. 分析这些用例的覆盖范围
# 读取用例 XML，提取每个用例验证了什么：

# TC_PAY_001: 
#   - 金额=100, 余额=1000 → 支付成功
#   - 验证: 订单状态=已支付，余额=900
#
# TC_PAY_002:
#   - 金额=100, 余额=50 → 显示"余额不足"
#   - 验证: 订单状态=未支付，余额=50（未扣款）
#
# TC_PAY_003:
#   - 点击取消 → 返回上一页
#   - 验证: 订单状态=已取消
```

```bash
# 3. 提取"已验证的检查条件"（Oracle）
# 从这些用例中学到的正常行为：

# ✓ 余额充足时可以成功支付
# ✓ 余额不足时显示明确错误提示
# ✓ 取消流程不产生副作用（不扣款）
# ✓ 订单号唯一（TC_PAY_001 创建了 ORD20260821001）
```

```bash
# 4. 识别"盲区"（这些用例没测到的）

# 边界值：
#   - 金额=0（边界）
#   - 金额=0.01（最小单位）
#   - 金额=-100（跨界，负数）
#   - 金额=999999999999999（超大值）
#   - 金额="abc"（非数字）

# 并发场景：
#   - 多标签页同时支付同一订单

# 异常场景：
#   - 网络中断时的重试逻辑
#   - 支付超时处理

# 唯一性约束：
#   - 订单号重复（理论上不应出现，但需验证系统防护）
#   - 交易号冲突

# 安全场景：
#   - 金额输入 <script>alert(1)</script>
#   - SQL 注入尝试
```

```bash
# 5. 识别唯一性字段（重要！避免探索时重复导致误判）

# 从已通过用例中识别哪些字段有唯一性约束：
#   - TC_PAY_001 创建订单，订单号 = "ORD20260821001" → 唯一
#   - TC_USER_001 创建用户，用户名 = "testuser" → 唯一
#   - TC_PAY_002 支付，交易号 = "TXN20260821001" → 唯一

# 探索时必须生成新的唯一值：
TIMESTAMP=$(date +%s)
ORDER_ID="ORD_explore_${TIMESTAMP}_$$"
USERNAME="testuser_explore_${TIMESTAMP}"
TXN_ID="TXN_explore_${TIMESTAMP}_$$"
```

```bash
# 6. 复用测试资产

# - model.xml: PaymentPage 的定位器（复用，不修改）
# - data.sqlite: NormalUser、InsufficientBalanceUser（复用现有数据）
#   注意：唯一性字段需动态生成，不能直接复用原值

rodski data list product/cassmall/payment
# 输出：
#   PaymentData (5 行)
#   UserData (10 行)
```

---

### 阶段 1：制定 Charter

**Charter** 是探索约章，定义探索目标、基线、范围、预算。

```json
{
  "goal": "探索支付模块在边界条件和异常场景下的健壮性",
  "baseline_cases": [
    "TC_PAY_001 (余额充足, 正常支付)",
    "TC_PAY_002 (余额不足, 错误提示)",
    "TC_PAY_003 (用户取消)"
  ],
  "verified_oracles": [
    "正常金额可以成功支付",
    "余额不足时有明确提示",
    "取消流程不产生副作用"
  ],
  "explore_dimensions": [
    "边界值（0、0.01、负数、超大、非数字）",
    "并发场景（多标签页同时支付）",
    "异常场景（网络中断、超时）",
    "唯一性约束（订单号重复、交易号冲突）",
    "安全场景（XSS、注入尝试）"
  ],
  "uniqueness_fields": {
    "order_id": "订单号（探索时需生成唯一值）",
    "transaction_id": "交易号（探索时需生成唯一值）"
  },
  "reuse_assets": {
    "model": "PaymentPage (from TC_PAY_001)",
    "data": "NormalUser, InsufficientBalanceUser (from TC_PAY_002)"
  },
  "budget": {
    "steps": 30,
    "duration": 600
  }
}
```

**关键点**：
- `baseline_cases`: 已通过的用例（告诉我们"什么是正常的"）
- `verified_oracles`: 从基线用例中学到的正常行为
- `explore_dimensions`: 基于基线识别出的盲区（要探索的方向），**重点是合理业务边界线下的异常问题**
- `uniqueness_fields`: 识别出的唯一性字段，探索时必须生成新值
- `reuse_assets`: 借用基线用例的测试资产（定位器、数据）

---

### 阶段 2：初始化探索会话

```bash
# 生成唯一会话 ID
SESSION_ID="explore_$(date +%s)_$$"
MODULE_DIR="product/cassmall/payment"

# 设置预算
BUDGET_STEPS=30
BUDGET_DURATION=600  # 10 分钟
```

---

### 阶段 3：执行探索循环

```bash
# 循环逻辑（伪代码）
while true; do
  # 3.1 分析当前状态
  # - 读取上一步的 evidence（截图路径、URL、浏览器错误）
  # - 读取 budget_status（剩余步数、时长）
  # - 回顾 Charter 的 Oracle
  
  # 3.2 推理下一步动作
  # 基于：
  #   - Charter 目标
  #   - 当前页面状态
  #   - 已执行的历史
  #   - 识别出的唯一性字段
  # 决定：继续探索 / 发现问题 / 停止
  
  # 3.3 生成唯一值（如果需要）
  if [[ "$需要唯一性字段" == "true" ]]; then
    TIMESTAMP=$(date +%s)
    ORDER_ID="ORD_explore_${TIMESTAMP}_$$"
  fi
  
  # 3.4 执行探索步骤
  RESULT=$(rodski explore-step \
    --module "$MODULE_DIR" \
    --session "$SESSION_ID" \
    --action type \
    --model PaymentPage \
    --data "order_id=${ORDER_ID},amount=-100" \
    --budget-steps $BUDGET_STEPS \
    --budget-duration $BUDGET_DURATION \
    --output json)
  
  # 3.5 分析结果
  SUCCESS=$(echo "$RESULT" | jq -r '.success')
  STOPPED=$(echo "$RESULT" | jq -r '.budget_status.stopped')
  BROWSER_ERRORS=$(echo "$RESULT" | jq -r '.evidence.browser_errors | length')
  
  # 3.6 记录 Finding（如果发现问题）
  if [ "$BROWSER_ERRORS" -gt 0 ]; then
    # 记录：发现 BUG - 浏览器 JS 错误
    echo "Finding: JS错误"
  fi
  
  if [ "$SUCCESS" = "false" ] && [ "$STOPPED" = "false" ]; then
    # 检查是否是真实 Bug 还是预期行为
    ERROR_MSG=$(echo "$RESULT" | jq -r '.errors[0]')
    if [[ "$ERROR_MSG" == *"余额不足"* ]]; then
      echo "预期行为：余额不足提示"
    else
      echo "Finding: 意外错误 - $ERROR_MSG"
    fi
  fi
  
  # 3.7 检查停止条件
  if [ "$STOPPED" = "true" ]; then
    REASON=$(echo "$RESULT" | jq -r '.budget_status.stopped_reason')
    echo "探索停止: $REASON"
    break
  fi
done
```

---

### 阶段 4：总结与报告

```markdown
# 探索测试报告 - 支付模块边界条件验证

## 基线（已验证的正常行为）

参考用例：
- TC_PAY_001: 余额充足，正常支付 ✓
- TC_PAY_002: 余额不足，显示错误 ✓
- TC_PAY_003: 用户取消支付 ✓

已验证的 Oracle：
- ✓ 正常金额可以成功支付
- ✓ 余额不足时有明确提示
- ✓ 取消流程不产生副作用

## 探索结果

- 会话 ID: explore_1724220000_12345
- 执行步数: 4
- 探索维度: 边界值、并发、安全
- 发现问题: **4 个**

### 发现的问题（按严重程度排序）

#### 1. [CRITICAL] 并发支付导致重复扣款

**类型**: BUG  
**严重程度**: CRITICAL  
**证据**: 
- 截图: `result/explore/session_xxx_step_3.png`
- 日志: 两次扣款记录

**复现步骤**:
1. 使用测试账号登录（NormalUser, 余额 1000）
2. 进入支付页，选择商品（金额 100）
3. 打开两个浏览器标签页
4. 在两个标签页同时点击"支付"按钮
5. 观察：账户余额被扣除 200（应为 100）

**建议**: 紧急修复 - 添加订单锁机制，防止并发提交

---

#### 2. [HIGH] 负数金额未验证

**类型**: BUG  
**严重程度**: HIGH  

**复现步骤**:
1. 进入支付页
2. 在金额输入框输入 `-100`
3. 点击支付
4. 观察：后端崩溃，返回 500 错误

**建议**: 前端增加金额验证（>= 0），后端增加防御性检查

---

## 总结

**探索有效性**:
- 基于 3 个已通过用例，探索了 4 个维度
- 发现 4 个新问题（基线用例未覆盖）
- 严重问题占比: 50% (2/4 为 HIGH/CRITICAL)

**建议优先级**:
1. **紧急修复**: 并发支付重复扣款（CRITICAL）
2. **高优先级**: 负数金额验证（HIGH）
3. **体验优化**: 其他问题

**覆盖增强**:
建议将这 4 个场景补充为新的自动化用例
```

---

## 命令参考

### `rodski explore-step`

**基本用法**:
```bash
rodski explore-step \
  --module <module_dir> \
  --session <session_id> \
  --action <action> \
  --model <model_name> \
  --data <data_id> \
  [--budget-steps <int>] \
  [--budget-duration <seconds>] \
  [--output json|text]
```

**参数说明**:
- `--module`: 测试模块目录（必需）
- `--session`: 会话 ID（必需，首次调用创建会话）
- `--action`: 关键字动作（type/click/navigate/verify/...）
- `--model`: 模型名称（默认空）
- `--data`: 数据 ID 或值（默认空）
- `--budget-steps`: 最大步数（默认 50）
- `--budget-duration`: 最大时长（秒，默认 300）
- `--output`: 输出格式（json/text，默认 json）

**输出格式（JSON）**:
```json
{
  "success": true,
  "evidence": {
    "screenshot": "result/explore/session_S001_step_3.png",
    "url": "http://localhost:8000/products",
    "page_title": "产品列表",
    "page_ready": true,
    "return_value": null,
    "browser_errors": []
  },
  "session_state": {
    "session_id": "S001",
    "step_count": 3,
    "started_at": 1724220000.0,
    "duration_seconds": 12.5
  },
  "budget_status": {
    "steps": {"used": 3, "limit": 50, "remaining": 47},
    "duration": {"used": 12.5, "limit": 300.0, "remaining": 287.5},
    "stopped": false,
    "stopped_reason": ""
  },
  "errors": []
}
```

---

## 最佳实践

### 1. 证据分析

- 每步后检查 `evidence.browser_errors`（浏览器错误 = 潜在 Bug）
- 分析截图，识别页面错误提示
- 对比 URL，确认导航路径是否符合预期

### 2. 数据唯一性处理（重要）

**问题**: 探索测试重复执行时，唯一性字段冲突导致误判

**示例**:
```bash
# 基线用例 TC_USER_001 创建用户
# data: username=testuser, email=test@example.com
# 第一次执行: PASS ✓

# 探索测试尝试相同数据
rodski explore-step --action type --model RegisterPage --data "username=testuser"
# 结果: FAIL（用户名已存在）
# 这不是 Bug！是探索逻辑问题
```

**解决方案**: 识别唯一性字段，动态生成唯一值

```bash
# 1. 从基线用例识别唯一性字段
# - username: 唯一 ✓
# - email: 唯一 ✓
# - phone: 唯一 ✓
# - order_id: 唯一 ✓

# 2. 探索时生成唯一值
TIMESTAMP=$(date +%s)
UNIQUE_SUFFIX="_explore_${TIMESTAMP}_$$"

rodski explore-step \
  --action type \
  --model RegisterPage \
  --data "username=testuser${UNIQUE_SUFFIX}"
# 实际值: testuser_explore_1724220000_12345

# 3. 常见唯一性字段模式
# - 用户名/账号: ${base_name}_explore_${timestamp}
# - 邮箱: ${base}+explore_${timestamp}@example.com
# - 订单号: ${prefix}_explore_${timestamp}_${random}
# - 手机号: ${prefix}${timestamp}（后10位）
```

**识别唯一性字段的方法**:
- 从基线用例的断言中识别："用户名已存在"、"邮箱重复"
- 从 model.xml 注释中识别：`<!-- unique field -->`
- 从业务规则中识别：注册、创建订单等操作通常有唯一性约束

### 3. 预算管理

- 定期检查 `budget_status.remaining`
- 去重机制：相同命令（action+model+data）只执行一次
- 预算耗尽时停止，不强行继续

### 4. Finding 分类

根据问题类型分类：

| 类型 | 说明 | 示例 |
|------|------|------|
| **BUG** | 功能不工作 | 负数金额未验证、并发重复扣款 |
| **PERFORMANCE** | 性能问题 | 支付超时 > 10s |
| **USABILITY** | 可用性问题 | 错误提示不清晰 |
| **SECURITY** | 安全问题 | XSS、SQL 注入 |

---

## 框架无关性

本 skill 是纯 Markdown 文档，**不依赖任何特定 Agent 框架**：

- ✅ Claude Code（通过 `.claude/skills/` 加载）
- ✅ OpenAI Codex
- ✅ AutoGPT
- ✅ 任何支持 Markdown skill 的 Agent

所有指令都是"自然语言描述 + bash 命令"，任何 Agent 都能执行。

---

## 参考资料

- **PRD**: `.pb/requirements/v10-explore-testing-prd.md`
- **Charter 设计指南**: `references/charter-design.md`
- **Finding 分类标准**: `references/finding-classification.md`
- **预算调优**: `references/budget-tuning.md`

---

## 注意事项

1. **探索测试不替代传统测试** - 两者互补，不可偏废
2. **Charter 设计是关键** - 好的 Charter 决定探索质量
3. **唯一性字段必须处理** - 避免误判
4. **预算控制很重要** - 避免探索会话失控
5. **Finding 需要人工复核** - AI 分类可能有误判
6. **版本兼容性** - 需要 rodski>=10.0.0

---

## 完整示例

见 `references/complete-example.md` - 支付模块探索的完整会话（从 Charter 到报告）。
