# SKI 报告功能指南

**版本**: v1.2.3  
**更新日期**: 2026-03-20  
**作者**: 热破 (Hot Rod) 🏎️

---

## 概述

RodSki 提供了强大的测试报告生成功能，支持多种格式和丰富的可视化特性。

## 报告格式

### 1. HTML 报告（默认）

现代化的 HTML 报告，包含：
- 📊 执行统计摘要
- 📈 通过率可视化
- ⏱️ 执行时间线
- 🎨 响应式设计
- 🌙 暗色模式支持

**生成命令**：
```bash
rodski report --input logs/latest_results.json --output report.html
```

### 2. JSON 报告

原始 JSON 格式，便于程序化处理。

**生成命令**：
```bash
rodski report --format json --output report.json
```

### 3. PDF 报告

将 HTML 报告导出为 PDF 格式。

**依赖安装**：
```bash
# 方案 1: pdfkit (需要 wkhtmltopdf)
pip install pdfkit
# macOS: brew install wkhtmltopdf
# Ubuntu: sudo apt-get install wkhtmltopdf

# 方案 2: weasyprint (纯 Python)
pip install weasyprint
```

**生成命令**：
```bash
rodski report --format pdf --output report.pdf
```

---

## 趋势分析

### 启用趋势图表

使用 `--trend` 参数启用历史趋势分析：

```bash
rodski report --trend --output report_with_trends.html
```

### 趋势图表功能

启用趋势分析后，报告将包含：

1. **通过率趋势图**
   - 显示最近 10 次执行的通过率变化
   - 折线图可视化
   - 帮助识别稳定性趋势

2. **执行时间趋势图**
   - 显示最近 10 次执行的耗时变化
   - 柱状图可视化
   - 帮助识别性能回归

### 历史记录管理

**历史记录存储位置**：`logs/history/`

**文件命名格式**：`result_YYYYMMDD_HHMMSS.json`

**管理建议**：
- 定期清理旧历史记录（保留最近 20-30 次）
- 使用 CI/CD 自动归档历史报告

**清理示例**：
```bash
# 保留最近 20 次执行记录
cd logs/history
ls -t result_*.json | tail -n +21 | xargs rm -f
```

---

## 报告内容

### 1. 执行摘要

- 总用例数
- 通过数量
- 失败数量
- 执行耗时

### 2. 通过率可视化

- 进度条显示通过/失败比例
- 百分比精确显示

### 3. 执行时间线

- 每个步骤的执行时间可视化
- 通过/失败状态颜色标识
- 悬停显示详细信息

### 4. 详细结果表格

- 步骤编号
- 步骤名称
- 使用的关键字
- 执行结果
- 详细信息（错误消息等）

---

## 使用示例

### 基本用法

```bash
# 生成 HTML 报告
rodski report

# 指定输入输出
rodski report --input custom_results.json --output custom_report.html

# 生成 PDF 报告
rodski report --format pdf --output report.pdf
```

### 趋势分析

```bash
# 启用趋势图表
rodski report --trend

# 指定历史记录目录
rodski report --trend --history-dir /path/to/history
```

### CI/CD 集成

```bash
# 在 CI/CD 中生成带趋势的报告
rodski report --trend --format html --output test_report.html

# 生成 PDF 用于存档
rodski report --trend --format pdf --output test_report_$(date +%Y%m%d).pdf
```

---

## 最佳实践

### 1. 定期查看趋势

每周查看趋势图表，识别：
- 通过率下降趋势
- 执行时间增长
- 不稳定的测试用例

### 2. 归档重要报告

对重要版本的测试报告进行归档：
```bash
mkdir -p reports/archive/v1.2.0
rodski report --output reports/archive/v1.2.0/test_report.html
rodski report --format pdf --output reports/archive/v1.2.0/test_report.pdf
```

### 3. 团队分享

- HTML 报告可通过 Web 服务器共享
- PDF 报告适合邮件发送
- JSON 报告适合集成到仪表板

### 4. 性能优化

- 定期清理历史记录
- 对大型测试集使用并发执行
- 在 CI/CD 中缓存依赖

---

## 故障排查

### PDF 导出失败

**问题**：`PDF 导出失败，请确保已安装 pdfkit 或 weasyprint`

**解决方案**：
```bash
# 安装 weasyprint（推荐，纯 Python）
pip install weasyprint

# 或安装 pdfkit + wkhtmltopdf
pip install pdfkit
brew install wkhtmltopdf  # macOS
```

### 趋势图表不显示

**问题**：启用 `--trend` 但没有显示趋势图表

**原因**：历史记录不足（需要至少 2 次执行）

**解决方案**：
1. 多次运行测试用例
2. 检查 `logs/history/` 目录是否有数据

### 报告样式异常

**问题**：HTML 报告样式显示不正常

**解决方案**：
- 检查浏览器是否支持现代 CSS 特性
- 尝试使用最新版本的 Chrome/Firefox/Safari
- 检查是否有网络连接（Chart.js 需要 CDN）

---

## 未来规划

### P3 优化方向

1. **邮件发送**
   - SMTP 配置界面
   - HTML 邮件格式
   - 附件支持

2. **报告定制**
   - 自定义模板
   - Logo 和品牌定制
   - 多语言支持

3. **仪表板集成**
   - 实时测试监控
   - 历史数据查询
   - 团队协作功能

---

## 更新日志

### v1.2.3 (2026-03-20)
- ✅ 添加趋势分析功能
- ✅ 支持 PDF 导出
- ✅ 改进 HTML 报告设计
- ✅ 添加历史记录管理

---

**需要帮助？**
- 查看 [用户手册](README.md)
- 访问 [GitHub Issues](https://github.com/your-repo/rodski/issues)
- 联系热破 (Hot Rod) 🏎️
