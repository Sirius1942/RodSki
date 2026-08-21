# Charter 设计最佳实践

## 什么是好的 Charter？

好的 Charter 具备以下特征：
- ✅ **目标明确** - 单句话说清探索什么
- ✅ **范围清晰** - 有界的探索空间
- ✅ **Oracle 具体** - 可验证的预期行为
- ✅ **预算合理** - 可控的执行时间
- ✅ **关注焦点** - 明确的重点区域

## Charter 模板

### 基础模板

```python
CharterCard(
    charter_id="唯一标识",
    goal="探索 [功能] 的 [方面]",
    scope={
        "entry_point": "起点 URL",
        "allowed_domains": ["域名白名单"],
        "focus_areas": ["重点区域列表"]
    },
    oracle=["预期行为列表"],
    allowed_actions=["允许的关键字"],
    budget={
        "max_steps": 20,
        "max_time_seconds": 300
    }
)
```

### 典型场景模板

#### 1. 探索新功能

```python
CharterCard(
    charter_id="EXPLORE_NEW_FEATURE",
    goal="探索 [功能名] 的核心流程和边界条件",
    scope={
        "entry_point": "功能入口 URL",
        "allowed_domains": ["localhost"],
        "focus_areas": ["主流程", "输入验证", "错误处理"]
    },
    oracle=[
        "主流程流畅完成",
        "输入验证正常工作",
        "错误提示友好",
        "无浏览器错误"
    ],
    allowed_actions=["navigate", "wait", "screenshot", "click", "type"],
    budget={"max_steps": 30, "max_time_seconds": 600}
)
```

#### 2. 集成测试

```python
CharterCard(
    charter_id="EXPLORE_INTEGRATION",
    goal="验证 [模块 A] 和 [模块 B] 的集成是否正常",
    scope={
        "entry_point": "集成入口 URL",
        "allowed_domains": ["localhost", "api.example.com"],
        "focus_areas": ["跨模块调用", "数据传递", "错误传播"]
    },
    oracle=[
        "模块间通信正常",
        "数据格式一致",
        "错误正确传播",
        "无资源泄露"
    ],
    allowed_actions=["navigate", "wait", "screenshot", "verify"],
    budget={"max_steps": 40, "max_time_seconds": 800}
)
```

#### 3. 边界探索

```python
CharterCard(
    charter_id="EXPLORE_BOUNDARY",
    goal="探索 [功能] 在边界条件下的行为",
    scope={
        "entry_point": "功能 URL",
        "allowed_domains": ["localhost"],
        "focus_areas": ["极限输入", "边界值", "异常场景"]
    },
    oracle=[
        "边界值正确处理",
        "错误信息准确",
        "系统保持稳定",
        "无崩溃或挂起"
    ],
    allowed_actions=["navigate", "type", "screenshot"],
    budget={"max_steps": 50, "max_time_seconds": 1000}
)
```

#### 4. 性能探索

```python
CharterCard(
    charter_id="EXPLORE_PERFORMANCE",
    goal="探索 [功能] 的性能表现和瓶颈",
    scope={
        "entry_point": "功能 URL",
        "allowed_domains": ["localhost"],
        "focus_areas": ["加载速度", "响应时间", "资源使用"]
    },
    oracle=[
        "页面加载时间 < 3s",
        "交互响应 < 500ms",
        "无内存泄露",
        "无资源阻塞"
    ],
    allowed_actions=["navigate", "wait", "screenshot"],
    budget={"max_steps": 25, "max_time_seconds": 500}
)
```

## Charter 设计指南

### 1. 目标 (goal) 设计

**✅ 好的目标：**
```python
"探索登录功能的输入验证和错误处理"
"验证购物车在多商品场景下的交互流畅性"
"发现搜索功能在边界输入下的问题"
```

**❌ 差的目标：**
```python
"测试网站"                    # 太模糊
"点击所有按钮"                 # 没有目的
"看看有没有问题"               # 不可衡量
```

**设计原则：**
- 使用"探索/验证/发现"等动词开头
- 明确探索的**功能点**和**关注方面**
- 保持在 15-30 个汉字
- 可衡量、可评估

### 2. 范围 (scope) 设计

#### entry_point

**✅ 好的起点：**
```python
"entry_point": "http://localhost:8000/login"          # 具体功能入口
"entry_point": "http://app.example.com/dashboard"    # 具体页面
```

**❌ 差的起点：**
```python
"entry_point": "http://localhost:8000"               # 太宽泛
"entry_point": "http://example.com"                  # 无法控制范围
```

#### allowed_domains

**✅ 好的域名白名单：**
```python
"allowed_domains": ["localhost"]                     # 仅本地
"allowed_domains": ["app.example.com", "api.example.com"]  # 应用域
```

**❌ 差的域名白名单：**
```python
"allowed_domains": []                                # 无限制（危险）
"allowed_domains": ["*"]                             # 过于宽松
```

#### focus_areas

**✅ 好的关注区域：**
```python
"focus_areas": ["表单验证", "提交流程", "错误提示"]   # 具体功能点
"focus_areas": ["导航菜单", "搜索框", "用户中心"]     # 具体 UI 区域
```

**❌ 差的关注区域：**
```python
"focus_areas": ["所有功能"]                          # 太宽泛
"focus_areas": ["测试一下"]                          # 不明确
```

### 3. Oracle (预期行为) 设计

**✅ 好的 Oracle：**
```python
[
    "登录表单可见且可操作",              # 可验证
    "输入错误凭证时显示错误提示",         # 具体条件
    "登录成功后跳转到首页",              # 明确结果
    "页面无 JavaScript 错误",            # 可检测
    "控制台无警告信息"                   # 可检测
]
```

**❌ 差的 Oracle：**
```python
[
    "系统正常",                          # 太模糊
    "用户满意",                          # 不可验证
    "看起来不错",                        # 主观判断
    "应该能用"                           # 不确定
]
```

**设计原则：**
- 每条 Oracle 都是**可验证**的陈述
- 使用**具体的**、**可观测的**指标
- 避免主观判断和模糊描述
- 涵盖**功能正确性**、**性能**、**错误处理**

### 4. 允许的动作 (allowed_actions) 设计

**按探索目标选择：**

**只读探索（安全）：**
```python
["navigate", "wait", "screenshot"]
```

**表单探索（中等风险）：**
```python
["navigate", "wait", "screenshot", "type", "click"]
```

**完整探索（高风险）：**
```python
["navigate", "wait", "screenshot", "type", "click", "verify", "get_text"]
```

**设计原则：**
- 从最小权限开始
- 根据探索目标逐步放开
- 避免不必要的写操作
- 生产环境限制更严格

### 5. 预算 (budget) 设计

**按探索深度选择：**

**快速扫描（5-10 分钟）：**
```python
{"max_steps": 15, "max_time_seconds": 300}
```

**标准探索（10-20 分钟）：**
```python
{"max_steps": 30, "max_time_seconds": 600}
```

**深度探索（20-40 分钟）：**
```python
{"max_steps": 50, "max_time_seconds": 1200}
```

**超长探索（慎用）：**
```python
{"max_steps": 100, "max_time_seconds": 2400}
```

**设计原则：**
- 从小预算开始试探
- 根据实际需要逐步增加
- 避免无限制探索
- 考虑 CI/CD 时间约束

## 常见反模式

### 反模式 1: 过于宽泛的 Charter

```python
# ❌ 反模式
CharterCard(
    goal="测试整个网站",
    scope={"entry_point": "http://example.com", "allowed_domains": []},
    oracle=["网站正常"],
    allowed_actions=["navigate", "click", "type"],
    budget={"max_steps": 1000}
)
```

**问题：**
- 目标不明确
- 范围无界
- Oracle 不可验证
- 预算失控

**修复：**
```python
# ✅ 修复
CharterCard(
    goal="探索用户登录和注册流程",
    scope={
        "entry_point": "http://example.com/login",
        "allowed_domains": ["example.com"],
        "focus_areas": ["登录表单", "注册表单", "密码重置"]
    },
    oracle=[
        "表单验证正常工作",
        "成功流程完整",
        "错误提示友好",
        "无浏览器错误"
    ],
    allowed_actions=["navigate", "type", "click", "screenshot"],
    budget={"max_steps": 30, "max_time_seconds": 600}
)
```

### 反模式 2: 空洞的 Oracle

```python
# ❌ 反模式
oracle=["系统正常", "用户满意", "看起来不错"]
```

**问题：**
- 无法验证
- 主观判断
- 不可衡量

**修复：**
```python
# ✅ 修复
oracle=[
    "页面加载时间 < 3 秒",
    "表单提交成功率 100%",
    "错误提示在 2 秒内显示",
    "无 JavaScript 错误",
    "无 Console 警告"
]
```

### 反模式 3: 不受控的探索

```python
# ❌ 反模式
CharterCard(
    goal="随便看看",
    scope={"entry_point": "http://example.com"},
    oracle=[],
    allowed_actions=["navigate", "click", "type"],
    budget={"max_steps": 500}
)
```

**问题：**
- 无目标
- 无约束
- 无预期
- 预算过大

**修复：**
```python
# ✅ 修复
CharterCard(
    goal="探索首页主要功能的可用性",
    scope={
        "entry_point": "http://example.com",
        "allowed_domains": ["example.com"],
        "focus_areas": ["导航菜单", "搜索功能", "内容浏览"]
    },
    oracle=[
        "导航菜单正常工作",
        "搜索结果准确",
        "内容正常加载",
        "无明显性能问题"
    ],
    allowed_actions=["navigate", "click", "screenshot"],
    budget={"max_steps": 25, "max_time_seconds": 500}
)
```

## Charter 迭代优化

### 第一次探索

```python
# v1 - 保守的 Charter
charter_v1 = CharterCard(
    goal="初步探索登录功能",
    scope={
        "entry_point": "http://localhost:8000/login",
        "allowed_domains": ["localhost"],
        "focus_areas": ["登录表单"]
    },
    oracle=["表单可见", "可以提交"],
    allowed_actions=["navigate", "screenshot"],
    budget={"max_steps": 10, "max_time_seconds": 180}
)
```

### 根据结果调整

```python
# v2 - 扩展的 Charter
charter_v2 = CharterCard(
    goal="深入探索登录功能的输入验证",
    scope={
        "entry_point": "http://localhost:8000/login",
        "allowed_domains": ["localhost"],
        "focus_areas": ["登录表单", "输入验证", "错误提示"]  # 扩展
    },
    oracle=[
        "表单验证正常工作",
        "错误提示友好准确",
        "边界输入正确处理",
        "无前端错误"
    ],  # 更具体
    allowed_actions=["navigate", "type", "click", "screenshot"],  # 更多动作
    budget={"max_steps": 25, "max_time_seconds": 500}  # 更大预算
)
```

### 聚焦发现的问题

```python
# v3 - 针对性 Charter
charter_v3 = CharterCard(
    goal="验证登录功能的 SQL 注入防护",
    scope={
        "entry_point": "http://localhost:8000/login",
        "allowed_domains": ["localhost"],
        "focus_areas": ["输入验证", "安全防护"]  # 聚焦
    },
    oracle=[
        "SQL 注入被正确拦截",
        "错误提示不泄露信息",
        "日志记录异常尝试"
    ],  # 安全关注
    allowed_actions=["navigate", "type", "screenshot"],
    budget={"max_steps": 15, "max_time_seconds": 300}  # 更短
)
```

## Charter 质量检查清单

在运行探索测试前，用这个清单验证 Charter 质量：

- [ ] **目标明确** - 单句话说清探索什么
- [ ] **范围有界** - entry_point 具体，allowed_domains 受限
- [ ] **关注点清晰** - focus_areas 具体明确
- [ ] **Oracle 可验证** - 每条都是可观测的陈述
- [ ] **动作受控** - allowed_actions 最小必需
- [ ] **预算合理** - max_steps 和 max_time 可控
- [ ] **charter_id 唯一** - 便于追溯和管理

## 总结

**好的 Charter 的三个特征：**
1. **明确性** - 目标、范围、预期都清晰明确
2. **可控性** - 预算、动作、域名都受控
3. **可验证性** - Oracle 都是可验证的陈述

**Charter 设计的三个原则：**
1. **从小到大** - 先小范围试探，再逐步扩展
2. **从简到繁** - 先限制动作，再逐步放开
3. **从粗到细** - 先广度扫描，再深度挖掘
