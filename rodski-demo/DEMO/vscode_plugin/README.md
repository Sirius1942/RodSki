# vscode_plugin - VS Code 扩展集成演示

## 概述

演示 RodSki 与 VS Code 扩展（`rodski-vscode`）的集成：通过扩展提供的 API 读取工作区配置、操作编辑器、执行命令等，验证框架在 IDE 扩展场景下的自动化能力。

## 环境要求

- **VS Code** 已安装
- **rodski-vscode 扩展** 已安装并启用
  - 扩展位置：`/path/to/rodski-vscode`（或已发布到 Marketplace）
  - 安装方式：开发环境下 `code --install-extension /path/to/rodski-vscode.vsix`
- **VS Code 需处于运行状态**

## 用例说明

| 用例文件 | 说明 |
|---------|------|
| `case/*.xml` | 扩展 API 调用验证（5 个用例） |

典型覆盖：
- 读取工作区文件列表
- 打开/关闭编辑器
- 执行扩展命令
- 读取扩展配置

## 运行方式

```bash
# 1. 启动 VS Code 并打开一个工作区

# 2. 运行用例
cd /path/to/rodski-demo/DEMO/vscode_plugin
rodski run case/
```

## 验收标准

- TC_PLUGIN_001 ~ TC_PLUGIN_004：通过
- TC_PLUGIN_005：如报错"缺少已安装扩展文件"，属预期（需补充测试扩展资源）

## 注意事项

- 扩展 API 依赖 VS Code 运行时，关闭 VS Code 后用例会失败
- TC_PLUGIN_005 需要扩展的 webview 资源文件（`src/webview/case.html`），仓库中可能缺失

## 相关文档

- 扩展源码：`rodski-vscode/` 仓库
- CORE §14.2：Demo 项目清单
