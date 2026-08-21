# Finding 分类标准

## 分类体系

| 类型 | 说明 | 严重程度判断 |
|------|------|-------------|
| **BUG** | 功能不工作 | HIGH/CRITICAL |
| **PERFORMANCE** | 性能问题 | MEDIUM/HIGH |
| **USABILITY** | 可用性问题 | LOW/MEDIUM |
| **SECURITY** | 安全问题 | HIGH/CRITICAL |
| **COMPATIBILITY** | 兼容性问题 | MEDIUM |

## 严重程度

- **CRITICAL**: 资金安全、数据丢失、系统崩溃
- **HIGH**: 核心功能不可用、安全漏洞
- **MEDIUM**: 影响体验但有绕过方案
- **LOW**: 轻微问题

## Finding 模板

```
#### [SEVERITY] Title

**类型**: BUG/PERFORMANCE/...
**严重程度**: CRITICAL/HIGH/MEDIUM/LOW
**证据**: 截图路径、错误日志
**复现步骤**: 1. 2. 3.
**建议**: 修复建议
```
