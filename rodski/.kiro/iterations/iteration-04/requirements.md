# Iteration 04 需求文档

## 1. CLI 结构化输出

### 1.1 JSON 输出格式
**需求**: 支持 --output-format json 参数
**优先级**: P0

### 1.2 退出码规范
**需求**: 定义明确的退出码（0/1/2）
**优先级**: P0

## 2. 错误处理机制

### 2.1 结构化错误信息
**需求**: 错误信息包含类型、消息、上下文
**优先级**: P0

### 2.2 失败步骤定位
**需求**: 精确定位失败的步骤索引
**优先级**: P0

## 3. Skill 集成规范

### 3.1 Skill 定义
**需求**: 定义 skill 名称和参数格式
**优先级**: P1

### 3.2 集成示例
**需求**: 提供 OpenClaw 集成示例
**优先级**: P1

---

## 4. 测试用例可解释性（Test Case Explainability）

### 4.1 用例静态解读
**需求**: AI Agent 可直接阅读 XML 测试用例文件，生成人类可读的操作步骤说明
**优先级**: P1

**功能描述**:
- 给定一个 case XML 文件路径，自动解析并生成操作步骤说明
- 说明每个步骤的关键字含义、操作对象、使用的模型和数据
- 对批量 type/verify，自动展开字段列表并展示定位器
- 对敏感字段（password/pwd/secret/token）自动脱敏显示为 `***`

**输出示例**:
```
用例: TC_LOGIN_001 - 用户登录测试
阶段: test_case

步骤 1/4: navigate
  → 操作: 导航到网址 https://example.com/login
  → 模型: (无)
  → 数据: (无)

步骤 2/4: type (批量输入)
  → 操作: 使用模型 LoginModel 从数据 login_001 批量输入
  → 模型: LoginModel
  → 数据: DataID=login_001
  → 字段解析:
    - username: "testuser" → 输入到 [name=username]
    - password: "***"     → 输入到 [name=password] ← 敏感字段脱敏

步骤 3/4: click
  → 操作: 点击元素
  → 定位器: css=.login-btn

步骤 4/4: verify
  → 操作: 验证页面文本
  → 预期: "Welcome, testuser"
```

### 4.2 CLI explain 子命令
**需求**: 提供 `python3 cli_main.py explain <case.xml>` 命令
**优先级**: P1

### 4.3 Python API
**需求**: 提供 `TestCaseExplainer` 类供外部调用
**优先级**: P1

---

## 5. 异常处理与智能恢复（Exception Handling & Smart Recovery）

### 5.1 执行失败时的异常捕获
**需求**: Web 执行过程中发生异常（元素未找到、超时、断言失败等），框架能够捕获并分析
**优先级**: P0

**异常类型**:
| 类型 | 触发场景 | 捕获方式 |
|------|---------|---------|
| ElementNotFound | 元素定位失败 | Playwright TimeoutError / NoSuchElementException |
| NetworkError | 网络请求失败 | Playwright NetworkError |
| AssertionFailed | 断言不通过 | verify/assert 返回 False |
| StepTimeout | 步骤执行超时 | 单步骤超过 max_step_timeout |
| PageCrash | 页面崩溃 | Playwright PageCrash |

### 5.2 视觉辅助诊断
**需求**: 发生异常后，调用视觉分析能力判断用例卡在哪里、为什么失败
**优先级**: P0

**诊断流程**:
1. 捕获异常时截图（失败时刻）
2. 调用 AIScreenshotVerifier 分析截图内容
3. 结合错误上下文（URL、已执行步骤、预期行为）生成诊断报告

**诊断报告格式**:
```json
{
  "diagnosis": {
    "failure_point": "步骤 3/5 - click(loginBtn)",
    "failure_reason": "ElementNotFound",
    "visual_analysis": "页面上显示'加载中'，元素尚未渲染完成",
    "suggestion": "在 click 前插入 wait action，等待元素可见",
    "recovery_action": "dynamic_insert:wait[data=3]"
  }
}
```

### 5.3 动态用例执行（Dynamic Step Insertion）
**需求**: 诊断完成后，可通过动态插入测试步骤来绕过或修复当前问题，最大限度保证长时间用例执行不出错
**优先级**: P0

**使用场景**:
- 页面加载慢 → 动态插入 `wait` 步骤
- 弹窗阻挡 → 动态插入 `click(弹窗关闭按钮)` 步骤
- 网络抖动 → 动态插入 `refresh` 步骤
- 元素未渲染 → 动态插入 `wait_for_selector` 步骤

**动态插入语法**:
```
dynamic_insert:<action>[<params>]
```

**支持的动态插入**:
| 指令 | 说明 |
|------|------|
| `dynamic_insert:wait[data=3]` | 等待3秒 |
| `dynamic_insert:click[locator=xxx]` | 点击指定元素 |
| `dynamic_insert:screenshot` | 截图保存 |
| `dynamic_insert:refresh` | 刷新页面 |
| `dynamic_insert:goto[url=xxx]` | 跳转到指定URL |

### 5.4 执行保护机制
**需求**: 提供配置选项，在异常发生后自动尝试恢复执行
**优先级**: P1

**配置项**:
```yaml
execution:
  max_retries: 3           # 单步骤最大重试次数
  recovery_enabled: true    # 是否启用自动恢复
  recovery_max_attempts: 2  # 最大恢复尝试次数
  screenshot_on_failure: true  # 失败时自动截图
  video_recording: true     # 是否录制视频
```

### 5.5 长时间执行稳定性
**需求**: 支持数小时的长时测试运行（如冒烟测试、回归测试）
**优先级**: P0

**保障措施**:
- 定期保存执行快照（每 N 步保存一次状态）
- 浏览器定期回收（如每 50 步重启一次浏览器）
- 网络超时自动重试机制
- 内存泄漏监控（定期 GC）
