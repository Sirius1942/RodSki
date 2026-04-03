# Iteration 05: 需求文档

**版本**: v1.0
**日期**: 2026-04-03

---

## 1. 审计标准

### 1.1 日志完整性标准

**必须有日志的场景**：
- ✅ 函数/方法入口（关键函数）
- ✅ 关键步骤执行（用例、步骤、驱动操作）
- ✅ 分支判断（if/else、switch）
- ✅ 循环迭代（重要循环）
- ✅ 异常捕获（try/except）
- ✅ 资源创建/释放（驱动、文件、连接）
- ✅ 状态变更（用例状态、驱动状态）

**可选日志的场景**：
- 简单赋值
- 内部辅助函数
- 性能敏感的循环

### 1.2 日志等级标准

| 等级 | 使用场景 | 反例 |
|------|---------|------|
| **DEBUG** | 变量值、函数调用、条件判断、数据解析 | ❌ 用例开始/结束 |
| **INFO** | 用例/步骤执行、驱动创建、结果统计 | ❌ 变量赋值 |
| **WARNING** | 配置缺失、兼容性问题、性能警告 | ❌ 正常的可选配置 |
| **ERROR** | 用例失败、驱动异常、文件读取失败 | ❌ 预期内的验证失败 |

### 1.3 日志格式标准

**统一格式**：
```python
# ✅ 好的日志
logger.info(f"开始执行用例: {case_id} - {title}")
logger.debug(f"解析数据: model={model}, data={data}")
logger.error(f"驱动操作失败: action={action}, locator={locator}, error={e}")

# ❌ 不好的日志
logger.info("开始执行")  # 缺少上下文
logger.debug(f"data: {data}")  # 格式不统一
logger.error(str(e))  # 缺少场景信息
```

**格式要求**：
- 包含必要上下文（ID、名称、参数）
- 使用 f-string 格式化
- 关键信息在前，细节在后
- 错误日志包含：场景 + 参数 + 错误

---

## 2. 审计检查清单

### 2.1 核心模块（core/）

| 文件 | 检查项 |
|------|--------|
| `ski_executor.py` | 用例执行流程、步骤执行、异常处理 |
| `keyword_engine.py` | 关键字执行、批量操作、驱动调用 |
| `case_parser.py` | XML 解析、数据提取、异常处理 |
| `model_parser.py` | 模型解析、元素提取 |
| `data_manager.py` | 数据加载、数据解析 |
| `driver_factory.py` | 驱动创建、驱动释放、异常处理 |
| `result_writer.py` | 结果写入、目录创建 |
| `dynamic_executor.py` | 条件评估、循环执行 |

### 2.2 驱动模块（drivers/）

| 文件 | 检查项 |
|------|--------|
| `playwright_driver.py` | 浏览器操作、元素定位、异常处理 |
| `appium_driver.py` | 移动端操作、元素定位 |
| `interface_driver.py` | HTTP 请求、响应处理 |
| `db_driver.py` | 数据库连接、SQL 执行 |

### 2.3 其他模块

| 模块 | 检查项 |
|------|--------|
| `api/` | API 接口、请求处理 |
| `utils/` | 工具函数、辅助方法 |
| 顶层脚本 | CLI 入口、参数解析 |

---

## 3. 常见问题与修复

### 3.1 缺失日志

**问题**：关键步骤无日志
```python
# ❌ 问题代码
def execute_step(self, step):
    action = step['action']
    self.keyword_engine.execute(action, params)
```

**修复**：
```python
# ✅ 修复后
def execute_step(self, step):
    action = step['action']
    logger.info(f"执行步骤: {action} {step.get('model', '')} {step.get('data', '')}")
    logger.debug(f"步骤详情: {step}")
    self.keyword_engine.execute(action, params)
```

### 3.2 等级不当

**问题**：INFO 用于调试信息
```python
# ❌ 问题代码
logger.info(f"变量值: x={x}, y={y}")
```

**修复**：
```python
# ✅ 修复后
logger.debug(f"变量值: x={x}, y={y}")
```

### 3.3 格式混乱

**问题**：格式不统一
```python
# ❌ 问题代码
logger.info("开始")
logger.info(f"case: {case_id}")
logger.info("执行: " + action)
```

**修复**：
```python
# ✅ 修复后
logger.info(f"开始执行用例: {case_id}")
logger.info(f"执行步骤: {action}")
```

### 3.4 异常处理

**问题**：异常无日志
```python
# ❌ 问题代码
try:
    driver.click(locator)
except Exception:
    pass
```

**修复**：
```python
# ✅ 修复后
try:
    driver.click(locator)
    logger.info(f"点击成功: {locator}")
except Exception as e:
    logger.error(f"点击失败: locator={locator}, error={e}")
    raise
```

---

## 4. 审计流程

1. **自动扫描**：使用脚本扫描所有 Python 文件
2. **人工审查**：逐文件检查日志使用
3. **记录问题**：记录到 audit-report.md
4. **修复问题**：按优先级修复
5. **验证测试**：执行测试验证日志输出

---

## 5. 验收标准

- [ ] 所有核心模块审计完成
- [ ] 关键步骤都有日志
- [ ] 日志等级使用合理
- [ ] 日志格式统一
- [ ] 异常都有错误日志
- [ ] 审计报告完整
