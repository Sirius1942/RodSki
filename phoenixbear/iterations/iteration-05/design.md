# Iteration 05: 设计文档

**版本**: v1.0
**日期**: 2026-04-03

---

## 1. 审计工具设计

### 1.1 日志扫描脚本

```python
# tools/audit_logger.py
"""日志使用审计工具"""

import ast
from pathlib import Path
from typing import Dict, List

class LoggerAuditor:
    """日志审计器"""
    
    def scan_file(self, file_path: Path) -> Dict:
        """扫描单个文件的日志使用情况"""
        return {
            'file': str(file_path),
            'logger_calls': [],      # logger.info/debug/warning/error
            'print_calls': [],       # print() 残留
            'missing_logs': [],      # 缺失日志的位置
            'level_issues': [],      # 等级使用不当
        }
    
    def scan_directory(self, dir_path: Path) -> List[Dict]:
        """扫描目录下所有 Python 文件"""
        pass
    
    def generate_report(self, results: List[Dict]) -> str:
        """生成审计报告"""
        pass
```

### 1.2 审计报告格式

```markdown
# 日志审计报告

**日期**: 2026-04-03
**审计范围**: rodski/

## 统计摘要

- 总文件数: 45
- logger 调用: 320
- print 残留: 12
- 缺失日志: 28
- 等级问题: 15

## 问题清单

### P0（严重）

1. `ski_executor.py:123` - 用例执行无日志
2. `keyword_engine.py:456` - 异常未记录

### P1（重要）

1. `case_parser.py:78` - print 残留
2. `driver_factory.py:234` - 日志等级不当（INFO → DEBUG）

### P2（一般）

1. `data_manager.py:90` - 日志格式不统一
```

---

## 2. 优化方案

### 2.1 日志模板

```python
# 用例执行
logger.info(f"开始执行用例: {case_id} - {title}")
logger.debug(f"用例配置: {config}")
logger.info(f"用例执行完成: {case_id} - {status} (耗时 {elapsed:.2f}s)")

# 步骤执行
logger.info(f"  步骤 {idx}: {action} {model} {data}")
logger.debug(f"  解析后数据: {resolved_data}")

# 驱动操作
logger.info(f"创建驱动: {driver_type}")
logger.debug(f"驱动配置: {config}")
logger.info(f"驱动操作: {action} {locator}")

# 异常处理
logger.error(f"操作失败: action={action}, locator={locator}, error={e}")
logger.debug(f"异常堆栈: {traceback.format_exc()}")
```

---

## 3. 实施策略

### 3.1 优先级

**P0（立即修复）**：
- 关键流程缺失日志
- 异常未记录
- print 残留

**P1（重要）**：
- 日志等级不当
- 格式不统一

**P2（可选）**：
- 日志优化
- 性能优化

### 3.2 修复流程

1. 运行审计脚本
2. 生成问题清单
3. 按优先级修复
4. 验证测试
5. 更新报告

---

## 4. 验证方法

### 4.1 自动验证

```bash
# 扫描 print 残留
grep -r "print(" rodski/ --include="*.py" | grep -v "# print"

# 统计 logger 使用
grep -r "logger\." rodski/ --include="*.py" | wc -l

# 检查日志等级
grep -r "logger\.info.*debug\|logger\.debug.*info" rodski/
```

### 4.2 手动验证

- 执行测试用例
- 检查 execution.log
- 验证日志完整性
- 验证日志可读性
