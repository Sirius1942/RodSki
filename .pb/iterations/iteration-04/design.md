# Iteration 04 设计文档

## 1. CLI JSON 输出格式

```json
{
  "status": "success|failed|partial",
  "exit_code": 0,
  "summary": {
    "total_steps": 10,
    "executed": 10,
    "passed": 10,
    "failed": 0,
    "duration": "12.5s"
  },
  "steps": [...],
  "variables": {...}
}
```

## 2. 错误信息格式

```json
{
  "status": "failed",
  "failed_step": {
    "index": 5,
    "action": "type",
    "model": "Login"
  },
  "error": {
    "type": "ElementNotFound",
    "message": "无法定位元素"
  },
  "context": {
    "url": "...",
    "screenshot": "..."
  }
}
```
