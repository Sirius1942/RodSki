# 性能分析指南

## 概述

RodSki 提供内置性能分析工具，帮助识别测试执行中的性能瓶颈。

## 使用方法

### 基本用法

```bash
rodski profile examples/demo_case.xlsx
```

### 指定输出目录

```bash
rodski profile examples/demo_case.xlsx --output logs/perf_report
```

## 报告内容

性能报告包含以下信息：

- **总操作数**: 执行的关键字总数
- **成功率**: 成功执行的操作百分比
- **总耗时**: 所有操作的累计时间
- **平均耗时**: 单个操作的平均执行时间
- **内存使用**: 测试执行期间的内存增长
- **关键字统计**: 每个关键字的详细性能数据

## 报告格式

生成两种格式的报告：

1. **JSON** (`profile.json`) - 机器可读，便于集成
2. **HTML** (`profile.html`) - 人类可读，可在浏览器中查看

## 性能优化建议

- 关注平均耗时 > 1s 的关键字
- 检查失败率高的操作
- 监控内存使用异常增长
- 优化频繁调用的慢操作

## 示例输出

```
🔍 开始性能分析: examples/demo_case.xlsx

✅ 性能分析完成
   总操作: 15
   总耗时: 8.45s
   平均耗时: 0.563s
   慢操作: 2

📊 报告已生成:
   JSON: logs/performance/profile.json
   HTML: logs/performance/profile.html
```
