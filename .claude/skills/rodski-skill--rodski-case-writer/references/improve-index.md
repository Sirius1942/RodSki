# RodSki Improve 笔记索引

`$HOME/TestCase/improve` 是历史笔记和失败复盘归档，不是实时编写来源。

默认不要读取这些文件，也不要用它们编写新用例。优先顺序如下：

1. 将 `$HOME/TestCase/TEST_CASE_WRITING_GUIDE.md` 作为只读参考材料和用例编写核心约束
2. 当前 RodSki CLI/schema/help、CLI 暴露时的可选 capabilities 输出，以及必要时的最窄 dry-run
3. 目标模块现有 `case/`、`model/`、`data/` 和 `plan/` 文件
4. `references/style.md`

只有当用户要求历史经验笔记，或在已经检查实时 guide、当前 CLI/schema、目标模块文件和最新运行证据后调查失败模式时，才使用本索引。如果使用，只读取单个相关文件。

## 可选映射

| 问题 | 可选文件 |
|---|---|
| API 登录或 `send` 加 `verify` 模式 | `LOGIN_AND_INTERFACE_CASE_EXPERIENCE.md` |
| 授权测试环境滑块处理 | `LOGIN_SLIDER_CAPTCHA_EXPERIENCE.md` |
| DB 模型、DB 查询或全局 DB 连接 | `DB_DISTRIBUTE_CASE_EXPERIENCE.md` |
| Handsontable/表格编辑 | `CUSTOMER_GROUP.md` |
| 询价决策表或隐藏 radio 行为 | `INQUIRY_CASE_EXPERIENCE.md` |
| 长订单链路 | `ORDER_CASE_EXPERIENCE.md` |
| 配置管理菜单/弹窗/toast 流程 | `CONFIG_MANAGE_CASE_EXPERIENCE.md` |
| 区块限定的报价回填 | `PEER_QUOTE_FILLBACK_CASE_EXPERIENCE.md` |
| 添加产品流程 | `ADD_PRODUCT_CASE_EXPERIENCE.md` |
| 区域客户定价 | `REGION_CUSTOMER_PRICING_CASE_EXPERIENCE.md` |
| 发票税点流程 | `INVOICE_TAX_POINT_CASE_EXPERIENCE.md` |
| 跨账号 E2E 询价/订单/售后链路 | `E2E_INQUIRY_ORDER_AFTER_SALE_EXPERIENCE.md` |
| 分流 UI 定位器 fallback 慢等待 | `DISTRIBUTE_UI_LOCATOR_FALLBACK_EXPERIENCE.md` |

当这些笔记与 guide、当前 schema、RodSki CLI 校验、最新运行证据或目标模块实际风格冲突时，不要把它们当权威。
