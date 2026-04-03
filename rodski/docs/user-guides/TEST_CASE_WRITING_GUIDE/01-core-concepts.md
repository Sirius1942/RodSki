# 1. 核心概念：关键字 + 模型 + 数据

> **来源**: RodSki 测试用例编写指南 v3.4  
> 本文档为独立章节，完整指南请见 [TEST_CASE_WRITING_GUIDE.md](../TEST_CASE_WRITING_GUIDE.md)

---


RodSki 的用例由三部分组成：

```
用例 = 关键字（做什么动作） + 模型（对哪些元素） + 数据（用什么值）
```

| 组成部分 | 作用 | 存储位置 |
|---------|------|---------|
| 关键字 | 定义操作类型（type UI输入 / send 接口请求 / verify 批量验证 …） | Case XML 的 `action` 属性 |
| 模型 | 定义页面元素 / 接口字段的定位信息 | model.xml 文件 |
| 数据 | 定义输入值 / 期望值 / 配置参数 | data/ 目录下的 XML 文件 + globalvalue.xml |

这三者的协作方式：

- **type（UI 写入）**：关键字 `type` + 模型 `Login` + 数据 `L001` → 框架遍历 Login 模型的每个元素，从 Login.xml 取对应字段的值，逐一输入到界面
- **send（接口请求）**：关键字 `send` + 模型 `LoginAPI` + 数据 `D001` → 框架从 LoginAPI 模型获取请求方式和 URL，从 LoginAPI.xml 取字段值，发送 HTTP 请求
- **verify（验证）**：关键字 `verify` + 模型 `Login` + 数据 `V001` → 框架遍历 Login 模型的每个元素，从界面/接口读取实际值，与 Login_verify.xml 的期望值逐字段比较

**关键规则：模型元素 name = 数据表字段 name**。这是整个框架运转的基础。

---

