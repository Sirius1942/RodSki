# $HOME/TestCase 的 RodSki 风格锚点

仅在需要快速查看本地风格锚点时读取本文。完整契约仍以 `TEST_CASE_WRITING_GUIDE.md` 为准。

## 实时事实来源

- 将 `$HOME/TestCase/TEST_CASE_WRITING_GUIDE.md` 视为只读参考材料和 RodSki 用例编写的核心约束。RodSki 用例工作前先读取它，按其要求设计用例，并且不要在用例工作期间修改、同步覆盖、追加笔记或以其他方式编辑它。
- 将当前 RodSki CLI 输出、schema/help、目标模块文件，以及最小有意义校验作为实时事实。受支持关键字、定位器类型和特殊值以 `rodski capabilities` 为权威清单（当前 CLI 顶层 `--help` 列出 `capabilities` 时调用，取其 `supported_keywords`/`locator_types`/`special_values`）。
- 将 `$HOME/TestCase/improve` 仅视为历史笔记归档。不要把它作为新用例编写来源；只有用户要求历史笔记，或已检查实时证据后继续调试失败模式时才查阅。

## 现有示例

- 简单 UI 登录：`$HOME/TestCase/00 Pass/登录/ec-admin-login/case/ui_login.xml`
- 场景决策表：`$HOME/TestCase/00 Pass/询价/case/inquiry_decision_table.xml`
- API send/verify 套件：`$HOME/TestCase/00 Pass/平台促销活动/case/platform_promotion_positive_api.xml`

## 本地风格

- XML 改动保持小范围。保留目标文件周围的引号风格、自闭合标签空格和既有排序。
- 优先使用中文业务标题和简洁描述。ID 应遵循目标模块现有族系：登录风格 ID、`IQ_001` 场景 ID，或 `TC-API-001` API ID。
- Case 文件名遵循目标模块现有约定。不要只为了改变中文/英文命名、大小写或 snake_case 而重命名稳定文件。
- UI 用例通常把导航和登录放在 `pre_process`，业务断言链放在 `test_case`，`close` 放在 `post_process`。
- 决策表用例保留一个物理 case，并在 `test_case` 内用 `scenario` 块拆分组合。
- API 套件使用重复的 `send` 加 `verify` 对。不要发明一次性的 HTTP action。
- 长 `evaluate` 步骤只适合作为 UI 就绪、源系统轮询或缺失内置能力的定向桥接。只要存在 model/data 驱动的 `type`、`send` 和 `verify` 路径，就优先使用它们。
- 注释适合大型 scenario/API 矩阵，但不要给每个普通步骤都写注释。

## UI 定位器锚点

Web UI `model.xml` 元素使用 guide 的多定位器机制：多个 `<location>` 子节点可以使用 `priority`，RodSki 会先尝试较小的 priority 值。只写入已经检查、由用户提供，或有充分依据确认的定位器。

推荐定位器阶梯：

1. 测试专用数据属性：用 CSS selector 表达 `data-testid`、`data-test`、`data-qa`。
2. 稳定且唯一的 `id`。
3. 可访问性语义：用 CSS selector 表达 `aria-label`、`aria-labelledby`，或 `role` 加 accessible name。
4. 稳定的业务 `data-*` 属性，使用 CSS selector。
5. 稳定的 `name`。
6. 稳定的 CSS 结构或 class selector；除非 DOM 固定，否则避免生成/hash class 和脆弱的 `nth-child`。
7. 只有当 CSS 无法清楚表达关系时才使用 XPath。
8. 稳定且唯一的可见文本。
9. 视觉模板匹配 fallback：`vision_image`（OpenCV 模板匹配，本机开箱可用，需提供参考图）。DOM 无稳定属性但外观稳定时用。详见 `vision-locators.md`。
10. 语义/文字视觉定位：`vision`（需先装 perception backend，本机默认零 backend）或 `ocr`（需先接 OCR provider，本机默认未接）——两者默认不可用，启用前先确认。
11. 固定坐标：`vision_bbox` 作为最后手段。

`data-testid`、`aria-label`、`role` 和任意 `data-*` 都不是 RodSki locator type。应将它们编码到 `<location type="css">...</location>` 中。

## 审查锚点

完成前，对照 guide、目标模块风格和以下高风险检查点确认改动面：

- 每个改动过的 case 恰好有一个可执行测试容器；如果存在 `component_type`，其值有效：`界面`、`接口` 或 `数据库`。
- API 流程使用 `send` 后接 `verify`；UI 流程优先使用 `navigate`、`type`、`verify` 和 `close`。
- 决策表只在 `test_case` 内使用 `scenario`。
- Case 文件名匹配目标模块现有命名约定；避免无关重命名。
- 新增或修改的 Web UI model 元素使用 `<location type="...">...</location>`，并在存在多个定位器时显式添加 `priority`。
- `$HOME/TestCase/improve` 没有用于新用例编写；如果用于失败历史，只能通过 `references/improve-index.md` 到达某一个具体笔记。
- 最终答复说明校验命令和结果。
