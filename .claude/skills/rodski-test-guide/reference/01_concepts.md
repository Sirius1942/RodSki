<!-- 自动生成 from rodski/docs/TEST_CASE_WRITING_GUIDE.md  请勿手工编辑 -->

## 1. 核心概念：关键字 + 模型 + 数据

RodSki 的用例由三部分组成：

```
用例 = 关键字（做什么动作） + 模型（对哪些元素） + 数据（用什么值）
```

| 组成部分 | 作用 | 存储位置 |
|---------|------|---------|
| 关键字 | 定义操作类型（type UI输入 / send 接口请求 / verify 批量验证 …） | Case XML 的 `action` 属性 |
| 模型 | 定义页面元素 / 接口字段的定位信息 | model.xml 文件 |
| 数据 | 定义输入值 / 期望值 / 配置参数 | `data/` 目录下的 `data.sqlite`（必须） + `globalvalue.xml` |

这三者的协作方式：

- **type（UI 写入）**：关键字 `type` + 模型 `Login` + 数据 `L001` → 框架遍历 Login 模型的每个元素，从逻辑表 `Login` 取对应字段的值（来源为 `data.sqlite`），逐一输入到界面
- **send（接口请求）**：关键字 `send` + 模型 `LoginAPI` + 数据 `D001` → 框架从 LoginAPI 模型获取请求方式和 URL，从逻辑表 `LoginAPI` 取字段值（来源为 `data.sqlite`），发送 HTTP 请求
- **verify（验证）**：关键字 `verify` + 模型 `Login` + 数据 `V001` → 框架遍历 Login 模型的每个元素，从界面/接口读取实际值，与逻辑表 `Login_verify` 中的期望值逐字段比较（来源为 `data.sqlite`）

**关键规则：模型元素 name = 数据表字段 name**。这是整个框架运转的基础。

---
