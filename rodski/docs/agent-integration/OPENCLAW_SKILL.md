# OpenClaw Skill 集成指南

## 概述

OpenClaw Skill 是一种轻量级的任务封装规范，允许将 RodSki 的能力以标准化的方式暴露给 OpenClaw Agent。通过 Skill，Agent 可以用自然语言调用 RodSki 的各项功能。

## Skill 文件结构

每个 Skill 是一个包含 `SKILL.md` 的目录：

```
rodski-skill/
├── SKILL.md          # Skill 定义文件 (必需)
├── scripts/          # 辅助脚本 (可选)
└── references/       # 参考文档 (可选)
```

## SKILL.md 格式

```markdown
# SKILL.md - Skill 定义文件

## 基本信息

**Name**: rodski-executor
**Description**: 执行 RodSki 关键字驱动测试用例
**Version**: 1.0.0

## 触发条件

当用户请求匹配以下模式时触发：
- "执行 RodSki 用例"
- "运行测试用例"
- "execute RodSki case"
- "运行 case.xml"

## 命令注册

### rodski:run
执行单个测试用例

**参数**:
- case_path (string, 必需): 用例文件路径
- variables (map, 可选): 变量键值对
- output_format (string, 可选): 输出格式 (json/text)

**示例**:
```
rodski:run case.xml
rodski:run case.xml -v env=staging
rodski:run case.xml --output-format json
```

### rodski:explain
解释测试用例为自然语言

**参数**:
- case_path (string, 必需): 用例文件路径
- sensitive (boolean, 可选): 是否脱敏敏感字段

**示例**:
```
rodski:explain case.xml
rodski:explain case.xml --sensitive
```

### rodski:stats
统计分析测试结果

**参数**:
- result_dir (string, 必需): 结果目录路径
- flaky_only (boolean, 可选): 仅显示不稳定用例
- top_slow (int, 可选): 显示最慢用例数量

**示例**:
```
rodski:stats output/results
rodski:stats output/results --flaky-only
rodski:stats output/results --top-slow 10
```

### rodski:validate
验证用例 XML 格式

**参数**:
- case_path (string, 必需): 用例文件路径

**示例**:
```
rodski:validate case.xml
```

## 实现脚本

实现脚本通过 CLI 调用 RodSki：

```bash
#!/bin/bash
# scripts/rodski_run.sh

CASE_PATH="$1"
OUTPUT_FORMAT="${2:-text}"
VARIABLES="${3:-}"

CMD="rodski run $CASE_PATH --output-format $OUTPUT_FORMAT"

if [ -n "$VARIABLES" ]; then
    # 解析变量 (格式: key1=value1,key2=value2)
    IFS=',' read -ra VARS <<< "$VARIABLES"
    for var in "${VARS[@]}"; do
        CMD="$CMD -v $var"
    done
fi

eval $CMD
```

## 参数映射规则

| Skill 参数 | CLI 参数 | 类型 |
|-----------|---------|------|
| case_path | positional | string |
| variables | -v | map |
| output_format | --output-format | string |
| sensitive | --sensitive | boolean |
| flaky_only | --flaky-only | flag |
| top_slow | --top-slow | int |
| date_from | --from | date |
| date_to | --to | date |

## 与 OpenClaw Gateway 的集成

### 1. 安装 Skill

将 Skill 目录复制到 OpenClaw 的 skills 目录：

```bash
cp -r rodski-skill ~/.openclaw/workspace/skills/
```

### 2. 配置 Gateway

在 `~/.openclaw/config.yaml` 中注册 Skill：

```yaml
skills:
  - name: rodski-executor
    path: ~/.openclaw/workspace/skills/rodski-skill
    enabled: true
```

### 3. 使用 Skill

Agent 通过自然语言调用：

```
用户: 运行 login.xml 用例
Agent: 调用 rodski:run(login.xml)

用户: 查看测试统计
Agent: 调用 rodski:stats(output/results, flaky_only=true)
```

## 高级配置

### 自定义关键字注册

在 Skill 中注册自定义 RodSki 关键字：

```yaml
# SKILL.md 中扩展
## Custom Keywords

### rodski:custom_keyword
注册自定义关键字到 KeywordEngine

**参数**:
- keyword_name (string, 必需): 关键字名称
- script_path (string, 必需): 实现脚本路径

**示例**:
```
rodski:custom_keyword my_action scripts/my_action.py
```
```

### 多环境配置

```yaml
## Environment Support

支持多环境切换：
- production: 生产环境
- staging: 预发布环境
- test: 测试环境

**示例**:
```
rodski:run case.xml -v env=staging
```
```

## 开发指南

### 1. 创建新 Skill

```bash
mkdir -p my-rodski-skill
cd my-rodski-skill
mkdir -p scripts references
touch SKILL.md
```

### 2. 编写 SKILL.md

参考上方格式，定义：
- 名称和描述
- 触发条件（自然语言模式）
- 命令注册（参数、类型、默认值）
- 示例用法

### 3. 实现脚本

在 `scripts/` 目录实现每个命令：

```python
#!/usr/bin/env python3
# scripts/run.py

import sys
import subprocess
import json

def main():
    case_path = sys.argv[1] if len(sys.argv) > 1 else None
    if not case_path:
        print("Error: case_path required", file=sys.stderr)
        sys.exit(1)

    result = subprocess.run(
        ["rodski", "run", case_path, "--output-format", "json"],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print(result.stdout)
    else:
        print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)

if __name__ == "__main__":
    main()
```

### 4. 测试 Skill

```bash
# 本地测试
python scripts/run.py case.xml

# 使用 rodski CLI 测试
rodski run case.xml
```

## 示例 Skill 配置

完整的 rodski-executor Skill 目录结构：

```
rodski-executor/
├── SKILL.md
├── scripts/
│   ├── run.py
│   ├── explain.py
│   ├── stats.py
│   └── validate.py
└── references/
    └── keywords.md
```

## 常见问题

### Q: 如何传递复杂变量？
A: 使用 JSON 格式：`rodski:run case.xml -v 'data={"users":["a","b"]}'`

### Q: 如何处理超时？
A: 在 SKILL.md 中配置 timeout 参数，Gateway 会在超时后自动终止。

### Q: 如何调试 Skill？
A: 设置 `log_level: debug` 在 Gateway 配置中，查看详细执行日志。
