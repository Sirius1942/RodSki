# browser_plugin_baidu - 百度搜索插件演示

## 概述

通过浏览器插件 API 在百度搜索页面执行自动化操作，演示插件在真实网站上的实用场景。

## 环境要求

- **插件服务**：需启动 `web/src/app.py`（:5002）
- **外部依赖**：访问 `https://www.baidu.com`（需网络连接）

## 用例说明

| 用例文件 | 说明 |
|---------|------|
| `case/search_basic.xml` | 基础搜索操作 |
| `case/search_suggestion.xml` | 搜索建议交互 |
| 其他用例 | 插件能力在真实网站的验证（共 5 个用例） |

## 运行方式

```bash
# 1. 启动插件服务
cd /path/to/rodski/web && python src/app.py

# 2. 运行用例
cd /path/to/rodski-demo/DEMO/browser_plugin_baidu
rodski run case/
```

## 验收标准

- 5 个用例通过
- 能正常访问百度并完成搜索
- 插件注入的脚本能在真实网站生效

## 注意事项

- 百度页面结构变化可能导致定位器失效
- 需稳定的网络连接
