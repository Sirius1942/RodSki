# RodSki CLI 命令手册

## 命令结构

```
rodski [全局选项] <子命令> [子命令选项] [参数]
```

全局选项：

- `--version`：显示版本
- `--verbose`：详细输出（调试信息 + 堆栈跟踪）

## run — 执行测试用例

```bash
rodski run <case.xlsx> [选项]

# 示例
rodski run product/DEMO/demo_site/case/demo_test_case.xlsx
rodski run case.xlsx --model path/to/model.xml
rodski run case.xlsx --headless
rodski run case.xlsx --dry-run --verbose
rodski run case.xlsx --output results.json
```

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `--model` | model.xml 路径（不指定则自动推断） | case 同级的 `../model/model.xml` |
| `--browser` | 浏览器类型：chromium / firefox / webkit | chromium |
| `--headless` | 无头模式 | false |
| `--dry-run` | 验证用例但不执行 | false |
| `--verbose` | 详细输出 | false |
| `--output` | 结果 JSON 输出路径 | — |

也可以直接用 `ski_run.py`（不需要安装）：

```bash
python ski_run.py case.xlsx [--headless] [--browser chromium]
```

## model — 模型管理

```bash
rodski model list                     # 列出所有模型
rodski model create <name> <type>     # 创建模型
rodski model validate <name>          # 验证模型
```

## config — 配置管理

```bash
rodski config list                    # 列出所有配置
rodski config get <key>               # 获取配置
rodski config set <key> <value>       # 设置配置
```

配置文件：`config/config.json`

## log — 日志管理

```bash
rodski log view [--lines 50]          # 查看日志
rodski log clear                      # 清空日志
```

## report — 报告生成

```bash
rodski report [选项]

# 示例
rodski report                                      # 默认 HTML
rodski report --format json --output results.json
rodski report --input custom_results.json
rodski report --trend                              # 启用趋势图表
```

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `--format` | 报告格式：html / json / pdf | html |
| `--input` | 输入结果文件 | logs/latest_results.json |
| `--output` | 输出文件路径 | report.html |
| `--trend` | 包含历史趋势图表 | false |
| `--history-dir` | 历史记录目录 | logs/history |

## profile — 性能分析

```bash
rodski profile [选项]
```

## 错误处理

- 统一输出格式：`错误 [ErrorType]: 错误消息`
- `--verbose` 输出完整堆栈
- 退出码：0 = 成功，1 = 失败，130 = 用户中断
