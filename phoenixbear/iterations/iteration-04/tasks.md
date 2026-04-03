# Iteration 04: 任务清单

**版本**: v1.0
**日期**: 2026-04-03

---

## 任务列表

### 阶段 1：结果目录重构（2h）

- [ ] **Task 1.1**: 修改 `ResultWriter.__init__`，创建 `run_YYYYMMDD_HHMMSS/` 目录
  - 文件: `core/result_writer.py`
  - 估时: 0.5h
  
- [ ] **Task 1.2**: 修改截图保存路径到 `run_*/screenshots/`
  - 文件: `core/ski_executor.py`, `core/result_writer.py`
  - 估时: 0.5h
  
- [ ] **Task 1.3**: 修改 result.xml 保存路径到 `run_*/result.xml`
  - 文件: `core/result_writer.py`
  - 估时: 0.5h
  
- [ ] **Task 1.4**: 测试验证结果目录结构
  - 估时: 0.5h

---

### 阶段 2：日志系统重构（3h）

- [ ] **Task 2.1**: 重构 `Logger` 类，支持双 Handler
  - 文件: `core/logger.py`
  - 估时: 1h
  
- [ ] **Task 2.2**: 添加 `set_log_dir()` 方法，支持动态设置日志目录
  - 文件: `core/logger.py`
  - 估时: 0.5h
  
- [ ] **Task 2.3**: 修改日志文件命名为 `execution.log`
  - 文件: `core/logger.py`
  - 估时: 0.5h
  
- [ ] **Task 2.4**: 集成到 `ResultWriter`，同步日志目录
  - 文件: `core/result_writer.py`, `ski_run.py`
  - 估时: 0.5h
  
- [ ] **Task 2.5**: 测试验证日志输出
  - 估时: 0.5h

---

### 阶段 3：日志等级梳理（8h）

- [ ] **Task 3.1**: 梳理 `ski_executor.py`
  - 替换 print → logger
  - 补全关键步骤日志
  - 估时: 2h
  
- [ ] **Task 3.2**: 梳理 `keyword_engine.py`
  - 替换 print → logger
  - 补全关键字执行日志
  - 估时: 2h
  
- [ ] **Task 3.3**: 梳理 `case_parser.py`
  - 补全解析日志
  - 估时: 1h
  
- [ ] **Task 3.4**: 梳理 `driver_factory.py`
  - 补全驱动管理日志
  - 估时: 1h
  
- [ ] **Task 3.5**: 梳理 `dynamic_executor.py`
  - 补全条件评估日志
  - 估时: 1h
  
- [ ] **Task 3.6**: 梳理其他文件
  - `data_manager.py`, `model_parser.py`, `result_writer.py`
  - 估时: 1h

---

### 阶段 4：CLI 参数支持（1h）

- [ ] **Task 4.1**: 添加 `--log-level` 参数
  - 文件: `ski_run.py`
  - 估时: 0.3h
  
- [ ] **Task 4.2**: 添加 `--verbose` 参数（等同 DEBUG）
  - 文件: `ski_run.py`
  - 估时: 0.2h
  
- [ ] **Task 4.3**: 添加 `--quiet` 参数（仅 ERROR）
  - 文件: `ski_run.py`
  - 估时: 0.2h
  
- [ ] **Task 4.4**: 测试验证 CLI 参数
  - 估时: 0.3h

---

### 阶段 5：测试验证（2h）

- [ ] **Task 5.1**: 单元测试（Logger 类）
  - 估时: 0.5h
  
- [ ] **Task 5.2**: 集成测试（完整用例执行）
  - 估时: 1h
  
- [ ] **Task 5.3**: 验收测试（对照验收标准）
  - 估时: 0.5h

---

## 总计

**总工时**: 16h
**任务数**: 20 个
