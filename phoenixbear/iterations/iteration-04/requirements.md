# Iteration 04: 测试日志可读性增强

**版本**: v1.0
**日期**: 2026-04-03
**状态**: 规划中

---

## 1. 目标

提升测试日志可读性，完善日志体系，方便调试和问题定位。

### 核心目标
1. 每次测试执行生成独立的日志文件（与截图同目录）
2. 按 logger 日志等级梳理全部代码，补全日志
3. CLI 模式日志与文件日志保持同等级别和相同输出
4. 日志分级：INFO（日常执行）、DEBUG（调试）

---

## 2. 当前问题分析

### 2.1 结果目录结构问题

**当前结构**：
```
result/
└── result_20260321_100000.xml    # 仅有结果 XML
└── screenshots/                   # 截图散落
    ├── case1_01_step1.png
    └── case1_02_step2.png
```

**问题**：
- ❌ 无执行日志文件
- ❌ 截图与日志分离
- ❌ 多次执行结果混在一起

### 2.2 日志系统问题

**当前实现**（`core/logger.py`）：
```python
# 问题1：日志按日期命名（20260403.log），多次执行覆盖
log_file = self.log_dir / f"{datetime.now():%Y%m%d}.log"

# 问题2：日志目录固定为 logs/，与结果目录分离
self.log_dir = Path(log_dir)  # 默认 "logs"
```

**问题**：
- ❌ 同一天多次执行日志混在一个文件
- ❌ 日志与测试结果（XML、截图）分离
- ❌ 无法追溯某次执行的完整日志

### 2.3 日志等级使用混乱

**问题**：
- ❌ 大量 `print()` 直接输出，未使用 logger
- ❌ 日志等级使用不规范（INFO/DEBUG/WARNING/ERROR 混用）
- ❌ CLI 输出与文件日志不一致

---

## 3. 设计方案

### 3.1 结果目录结构重构

**新结构**：
```
result/
└── run_20260403_153045/           # 每次执行独立目录
    ├── result.xml                 # 测试结果 XML
    ├── execution.log              # 本次执行日志
    ├── screenshots/               # 本次执行截图
    │   ├── case1_01_step1.png
    │   └── case1_02_step2.png
    └── metadata.json              # 执行元信息（可选）
```

**优势**：
- ✅ 每次执行结果隔离
- ✅ 日志、截图、结果 XML 在同一目录
- ✅ 方便归档和问题追溯

### 3.2 日志等级规范

| 等级 | 用途 | 示例场景 |
|------|------|---------|
| **DEBUG** | 调试信息，详细执行流程 | 变量值、函数调用、条件判断、数据解析 |
| **INFO** | 日常执行信息 | 用例开始/结束、步骤执行、驱动创建、结果统计 |
| **WARNING** | 警告信息，不影响执行 | 配置缺失使用默认值、兼容性问题、性能警告 |
| **ERROR** | 错误信息，影响执行 | 用例失败、驱动异常、文件读取失败 |


### 3.3 日志输出设计

**双通道输出**：
```
┌─────────────┐
│  RodSki     │
│  Executor   │
└──────┬──────┘
       │
       ├─────────────┐
       │             │
       ▼             ▼
  ┌─────────┐  ┌──────────┐
  │ Console │  │ Log File │
  │ Handler │  │ Handler  │
  └─────────┘  └──────────┘
       │             │
       ▼             ▼
   终端输出      execution.log
```

**输出规则**：
- Console Handler: 根据 CLI 参数控制等级（默认 INFO）
- File Handler: 始终记录 DEBUG 及以上（完整日志）
- 两者格式一致，仅等级过滤不同

---

## 4. 实现任务

### 4.1 结果目录重构

**文件**: `core/result_writer.py`

**任务**：
- [ ] 修改 `ResultWriter.__init__`，创建 `run_YYYYMMDD_HHMMSS/` 目录
- [ ] 修改截图路径，保存到 `run_*/screenshots/`
- [ ] 修改 result.xml 路径，保存到 `run_*/result.xml`
- [ ] 添加 `metadata.json` 生成（可选）

### 4.2 日志系统重构

**文件**: `core/logger.py`

**任务**：
- [ ] 修改日志文件命名：`execution.log`（固定名称）
- [ ] 支持动态设置日志目录（与结果目录同步）
- [ ] 添加双 Handler：Console + File
- [ ] Console Handler 支持等级过滤（CLI 参数控制）
- [ ] File Handler 固定 DEBUG 等级（完整日志）

### 4.3 日志等级梳理

**范围**: 全部 `rodski/core/*.py` 文件

**任务**：
- [ ] 替换所有 `print()` 为 `logger.info()` 或 `logger.debug()`
- [ ] 梳理现有 logger 调用，按规范调整等级
- [ ] 补全缺失日志（关键步骤、分支判断、异常处理）

**重点文件**：
- `ski_executor.py` - 用例执行主流程
- `keyword_engine.py` - 关键字执行
- `case_parser.py` - 用例解析
- `driver_factory.py` - 驱动管理
- `dynamic_executor.py` - 条件评估

### 4.4 CLI 参数支持

**文件**: `ski_run.py`

**任务**：
- [ ] 添加 `--log-level` 参数（DEBUG/INFO/WARNING/ERROR）
- [ ] 添加 `--quiet` 参数（仅输出 ERROR）
- [ ] 添加 `--verbose` 参数（等同 DEBUG）


---

## 5. 日志规范示例

### 5.1 用例执行流程

```python
# ski_executor.py
logger.info(f"开始执行用例: {case_id} - {title}")
logger.debug(f"用例配置: execute={execute}, component_type={component_type}")

logger.info(f"  [预处理] 执行 {len(pre_steps)} 个步骤")
logger.debug(f"  预处理步骤: {[s['action'] for s in pre_steps]}")

logger.info(f"  [用例阶段] 执行 {len(test_steps)} 个步骤")
for step in test_steps:
    logger.info(f"    步骤 {idx}: {step['action']} {step['model']} {step['data']}")
    logger.debug(f"    解析后数据: {resolved_data}")

logger.info(f"用例执行完成: {case_id} - {status} (耗时 {elapsed:.2f}s)")
```

### 5.2 条件判断

```python
# dynamic_executor.py
logger.debug(f"[IF] 评估条件: {condition}")
logger.debug(f"[IF] 条件类型: {condition_type}, 参数: {params}")

if evaluated:
    logger.info(f"[IF] 条件为 True，执行 then 分支")
else:
    logger.info(f"[IF] 条件为 False，执行 else 分支")
```

### 5.3 错误处理

```python
# keyword_engine.py
try:
    result = driver.click(locator)
    logger.info(f"点击成功: {locator}")
except Exception as e:
    logger.error(f"点击失败: {locator}, 错误: {e}")
    logger.debug(f"异常堆栈: {traceback.format_exc()}")
    raise
```

---

## 6. 验收标准

### 6.1 功能验收

- [ ] 每次执行生成独立 `run_*/` 目录
- [ ] `execution.log` 包含完整执行日志
- [ ] 截图保存到 `run_*/screenshots/`
- [ ] CLI 输出与日志文件内容一致（仅等级过滤不同）

### 6.2 日志质量验收

- [ ] 无 `print()` 直接输出
- [ ] 所有关键步骤有 INFO 日志
- [ ] 所有分支判断有 DEBUG 日志
- [ ] 所有异常有 ERROR 日志
- [ ] 日志等级使用符合规范

### 6.3 可读性验收

- [ ] 日志格式统一（时间戳 + 等级 + 消息）
- [ ] 日志层级清晰（缩进、前缀）
- [ ] 关键信息突出（用例 ID、状态、耗时）
- [ ] 错误信息完整（错误类型、位置、堆栈）

---

## 7. 风险与依赖

### 7.1 风险

- 日志过多影响性能（缓解：异步日志、批量写入）
- 日志文件过大（缓解：日志轮转、压缩归档）
- 现有代码改动量大（缓解：分批次重构）

### 7.2 依赖

- 无外部依赖
- 需要测试验证日志输出正确性

---

## 8. 时间估算

| 任务 | 工时 |
|------|------|
| 结果目录重构 | 2h |
| 日志系统重构 | 3h |
| 日志等级梳理（全部文件） | 8h |
| CLI 参数支持 | 1h |
| 测试验证 | 2h |
| **总计** | **16h** |

---

## 9. 后续优化

- 日志轮转（按大小或时间）
- 日志压缩归档
- 日志查询工具（CLI）
- 日志可视化（Web UI）
- 结构化日志（JSON 格式）
