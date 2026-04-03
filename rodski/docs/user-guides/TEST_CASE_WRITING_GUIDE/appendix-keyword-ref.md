# 附录：关键字速查清单

> **来源**: RodSki 测试用例编写指南 v3.4  
> 本文档为独立章节，完整指南请见 [TEST_CASE_WRITING_GUIDE.md](../TEST_CASE_WRITING_GUIDE.md)

---


下列 **`action` 取值**与 `rodski/schemas/case.xsd` 中 **`ActionType` 枚举**一致（共 16 个；`check` 为合法枚举值，语义上等同 `verify`）。

### A. UI 与通用

| 关键字 | 用途 |
|--------|------|
| `navigate` | 导航到 URL（无浏览器时自动创建） |
| `close` | 关闭浏览器 |
| `type` | UI 批量输入（PC/移动端统一） |
| `verify` | 批量验证（UI + 接口通用） |
| `check` | 与 `verify` 等价（XSD 枚举中的兼容项） |
| `assert` | 断言元素值 |
| `wait` | 等待指定秒数 |
| `upload_file` | 上传文件 |
| `clear` | 清空输入框 |
| `get_text` | 获取元素文本 |
| `get` | `get_text` 的别名 |
| `screenshot` | 手动截图 |

### B. 接口关键字

| 关键字 | 用途 |
|--------|------|
| `send` | 发送接口请求（模型 + 数据），响应含 status + body |

### C. 数据与高级关键字

| 关键字 | 用途 |
|--------|------|
| `set` | 设置变量 |
| `DB` | 执行数据库操作（query/execute） |
| `run` | 沙箱执行 Python 代码，stdout → Return |

> UI 原子动作（click、select 等）**不是**独立 `action`，而是写在数据表 `field` 值中，由 `type` 批量模式识别（见 [5.4](#54-批量输入时的特殊值)）。  
> 接口测试通过 `send` + `verify`（或 `check`）完成，与 UI 的 `type` + `verify` 对称。

---

