# browser_plugin - 浏览器插件集成演示

## 概述

演示 RodSki 与浏览器插件（`rodski-web`，:5002）的集成能力：通过插件 API 注入自定义 JavaScript、捕获网络请求、控制页面行为等。

## 环境要求

- **插件服务**：需启动 `web/src/app.py`（默认 :5002）
- **被测站点**：demosite :8000

## 用例说明

| 用例文件 | 说明 |
|---------|------|
| `case/plugin_inject.xml` | 测试插件注入 JS 脚本能力 |
| `case/plugin_network.xml` | 测试插件捕获网络请求 |
| 其他 24 个用例 | 覆盖插件核心 API（共 24 个用例） |

## 运行方式

```bash
# 1. 启动插件服务（需在项目根目录）
cd /path/to/rodski/web && python src/app.py

# 2. 在另一个终端运行用例
cd /path/to/rodski-demo/DEMO/browser_plugin
rodski run case/ --headless
```

## 验收标准

- 全部 24 个用例通过
- 插件 API 调用成功且有响应
- 网络拦截/注入能力正常

## 相关文档

- 插件 API 设计：`web/API.md`（如有）
- CORE §1.4：`run` 关键字与内置函数
