# Agent 集成指南

## 概述

RodSki 提供 Agent 友好的 CLI 接口，支持结构化 JSON 输出和详细错误信息。

## JSON 输出格式

### 启用 JSON 输出

```bash
rodski run case.xml --output-format json
```

### 成功响应格式

```json
{
  "status": "success",
  "exit_code": 0,
  "summary": {
    "total_steps": 10,
    "executed": 10,
    "passed": 10,
    "failed": 0,
    "skipped": 0,
    "duration": "12.50s"
  },
  "steps": [
    {
      "index": 0,
      "case_id": "TC001",
      "title": "登录测试",
      "status": "pass",
      "duration": "2.30s",
      "error": null,
      "screenshot": null
    }
  ],
  "variables": {}
}
```

### 失败响应格式

```json
{
  "status": "failed",
  "exit_code": 1,
  "error": {
    "type": "ElementNotFoundError",
    "message": "无法定位元素: #login-button"
  },
  "failed_step": {
    "case_id": "TC001",
    "index": 5
  },
  "context": {
    "url": "https://example.com/login",
    "screenshot": "/path/to/screenshot.png"
  }
}
```

## 退出码

- `0`: 所有测试通过
- `1`: 测试失败或执行错误
- `130`: 用户中断 (Ctrl+C)

## 错误类型

常见错误类型及含义：

- `ElementNotFoundError`: 元素定位失败
- `TimeoutError`: 操作超时
- `DriverStoppedError`: 浏览器驱动停止
- `FileNotFoundError`: 文件不存在
- `ParseError`: XML 解析错误
