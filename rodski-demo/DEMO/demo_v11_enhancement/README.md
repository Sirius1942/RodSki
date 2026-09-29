# demo_v11_enhancement - v11.x 增强特性演示

## 概述

演示 v11.x 系列版本引入的增强特性，包括但不限于：数据表高级引用、模型增强、错误诊断改进等。

## 环境要求

- demosite :8000

## 用例说明

| 用例文件 | 说明 |
|---------|------|
| `case/*.xml` | v11 新特性覆盖（4 个用例） |

具体特性需查看用例文件内的注释或 `model/model.xml` 中的标注。

## 运行方式

```bash
cd /path/to/rodski-demo/DEMO/demo_v11_enhancement
rodski run case/
```

## 验收标准

- 4 个用例通过
- v11 新特性按预期工作

## 相关文档

- CHANGELOG.md（v11.0.0 ~ v11.4.1 各版本的 Added/Changed 部分）
