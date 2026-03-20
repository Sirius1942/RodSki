# RodSki CLI 设计文档

## 1. 架构概述

RodSki CLI 采用子命令模式，使用 `argparse` 实现轻量级命令行接口。

### 1.1 核心设计原则
- **简洁性**：最小化代码，直接调用现有核心模块
- **可扩展性**：子命令模式便于添加新功能
- **一致性**：统一的命令格式和输出风格
- **用户友好**：清晰的错误提示、进度可视化、预验证能力

## 2. 命令结构

```
ski [全局选项] <子命令> [子命令选项] [参数]
```

### 2.1 全局选项
- `--version, -v`: 显示版本信息
- `--help, -h`: 显示帮助信息
- `--verbose`: 详细输出模式（显示额外调试信息、堆栈跟踪）

## 3. 子命令设计

### 3.1 run - 执行测试用例
```bash
rodski run <case.xlsx> [--driver web|desktop] [--output report.html]
rodski run <case.xlsx> --dry-run          # 验证用例但不实际执行
rodski run <case.xlsx> --verbose          # 详细输出模式
rodski run <case.xlsx> --dry-run --verbose # 验证并显示详细参数
```

**功能**：
- 解析 Excel 用例文件
- 调用 TaskExecutor 执行步骤
- 生成执行报告
- `--dry-run`: 验证用例文件和步骤，显示步骤列表，但不启动驱动和执行
- `--verbose`: 显示每个步骤的参数详情、执行状态、失败原因等
- 进度条显示（使用 tqdm，若未安装则优雅降级）

**实现**：调用 `excel_parser.py` + `task_executor.py`

**选项**：
| 选项 | 说明 | 默认值 |
|------|------|--------|
| `--driver` | 驱动类型 (web/desktop) | web |
| `--sheet` | 工作表名称 | 第一个 sheet |
| `--headless` | 无头模式 | false |
| `--retry` | 失败重试次数 | 0 |
| `--output` | 报告输出路径 | - |
| `--dry-run` | 验证用例但不执行 | false |
| `--verbose` | 详细输出模式 | false |

### 3.2 model - 模型管理
```bash
rodski model create <name> <type>    # 创建模型
rodski model list                     # 列出所有模型
rodski model validate <name>          # 验证模型
```

**功能**：管理页面对象模型
**实现**：调用 `model_manager.py`

### 3.3 config - 配置管理
```bash
rodski config set <key> <value>       # 设置配置
rodski config get <key>               # 获取配置
rodski config list                    # 列出所有配置
```

**功能**：管理框架配置
**实现**：调用 `config_manager.py`

### 3.4 log - 日志管理
```bash
rodski log view [--lines 50]          # 查看日志
rodski log clear                      # 清空日志
```

**功能**：查看和管理日志
**实现**：读取 `logs/` 目录

### 3.5 report - 报告生成
```bash
rodski report generate [--format html|json]
```

**功能**：生成测试报告
**实现**：基于执行结果生成报告

## 4. 文件结构

```
rodski/
├── cli_main.py         # CLI 入口 (含 format_error 错误格式化)
├── rodski_cli/
│   ├── __init__.py
│   ├── run.py          # run 子命令 (含 dry-run/verbose/进度条)
│   ├── model.py        # model 子命令
│   ├── config.py       # config 子命令
│   ├── log.py          # log 子命令
│   ├── report.py       # report 子命令
│   └── profile.py      # profile 子命令
└── docs/
    └── CLI_DESIGN.md
```

## 5. 实现要点

### 5.1 最小化原则
- 每个子命令模块只包含参数解析和调用逻辑
- 复用现有 core 模块，不重复实现业务逻辑
- 保持代码简洁，避免过度封装

### 5.2 错误处理
- 统一的错误输出格式：`错误 [ErrorType]: 错误消息`
- 分类错误前缀：文件错误、解析错误、驱动错误、执行错误、验证错误
- 常见错误的友好提示（FileNotFoundError、ImportError、PermissionError 等）
- `--verbose` 模式下输出完整堆栈信息
- 返回合适的退出码（0=成功，1=失败，130=用户中断）

### 5.3 输出格式
- 默认：简洁的文本输出
- `--verbose`：详细的调试信息（步骤参数、执行状态、失败原因）
- `--json`：JSON 格式输出（便于集成）

### 5.4 Dry Run 模式
- 验证用例文件格式和结构
- 解析并列出所有步骤
- 显示驱动、重试等配置信息
- 不启动浏览器驱动，不实际执行用例
- 用于预检查和调试

### 5.5 进度条显示
- 使用 `tqdm` 库在执行过程中显示进度
- 显示已完成/总步骤数和预估剩余时间
- 失败步骤在进度条上标注
- 若 `tqdm` 未安装，优雅降级（不影响正常执行）

## 6. 安装方式

```bash
# 开发模式
pip install -e .

# 安装依赖 (含 tqdm)
pip install -r requirements.txt

# 使用
ski --help
```

## 7. 依赖
- Python 3.8+
- argparse（标准库）
- tqdm>=4.65.0（进度条显示，可选）
- 现有 core 模块
