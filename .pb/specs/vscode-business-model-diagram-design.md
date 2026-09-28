# RodSki VSCode 业务模型图示设计 v0.1

**日期**：2026-09-27
**状态**：已实现首版，待在 VSCode Extension Host 中验收
**适用版本**：`rodski-vscode` `0.4.0`

---

## 1. 背景

RodSki 的业务模型是基于黑盒测试场景法的有向业务流程图：

- `node` 表示业务节点；
- `edge` 表示真实业务条件下的可达关系；
- `flow` 表示一条可被 Case 选择和断言的合法业务路径；
- 节点中的 `test_step` 仍由 RodSki Case 执行器执行；
- 输入和期望数据仍由普通 SQLite Data/Verify 表提供。

业务模型已经可以通过 CLI 校验、导出 JSON/Mermaid 和执行覆盖率统计，但只查看 XML 不利于评审流程结构。VSCode 插件需要提供一个只读的图形化投影，使测试设计人员能够在编辑业务模型 XML 时直接查看流程和场景路径。

---

## 2. 目标与非目标

### 2.1 目标

1. 在 VSCode 资源管理器中对 `business/` 目录下的业务模型 XML 右键打开业务模型图。
2. 一个 XML 文件可以包含多个 `business_model`，图面板提供模型切换。
3. 以有向图展示节点、边、边条件/标签和业务流路径。
4. 通过 flow 下拉框高亮一条业务流的节点和边，并显示路径、类型和覆盖语义。
5. 识别并显示开始节点、分支节点、终止节点；节点可点击查看步骤和说明。
6. 提供缩放、复位、适配视图、刷新和打开源文件能力。
7. XML 文件外部变化时，图面板自动刷新；非法 XML 显示可诊断错误，不让 Webview 崩溃。
8. 图示完全由 XML 实时生成，不产生第二份图形源文件，避免图与业务模型漂移。

### 2.2 非目标

- 不在图面板中编辑节点、边、flow 或 XML。
- 不在图面板中执行业务模型或测试 Case；执行仍由 Case 宿主和 CLI 负责。
- 不引入 Mermaid、Graphviz、React 或远程 CDN；首版使用浏览器原生 SVG，保证离线可用。
- 不改变业务模型 XML Schema、SQLite 数据表或业务模型执行语义。
- 不在图中展示 Data/Verify 表的字段值、凭证或敏感数据；只显示约定的表名。

---

## 3. 用户入口

### 3.1 命令

新增命令：

```text
RodSki: Open Business Model Diagram
```

命令 ID：`rodski.openBusinessModel`

命令可以从命令面板调用；资源管理器上下文菜单仅在路径包含 `business/` 且扩展名为 `.xml` 时显示。

### 3.2 面板生命周期

- 以文件绝对路径作为面板唯一键，同一文件重复打开时复用并聚焦已有面板。
- 面板关闭时释放文件监听器。
- 文件外部修改后通过 `loadXml` 消息重新解析并渲染。
- 面板不写回业务模型文件；`business.xml` 的唯一编辑入口仍是文本编辑器。

---

## 4. 图形语义

### 4.1 节点

| 图形语义 | 判定规则 | 展示 |
|---|---|---|
| 开始节点 | 没有入边 | 绿色圆角节点 |
| 分支节点 | 出边数量大于 1 | 琥珀色菱形 |
| 终止节点 | 没有出边 | 蓝色圆角节点 |
| 普通节点 | 其它节点 | 普通矩形 |
| 当前 flow 节点 | 节点 ID 出现在选中 flow.path | 加粗边框和高亮背景 |

节点显示 `title`（无 title 时回退到 `id`）和 `id`。点击节点后在详情区显示：

- 节点 ID、标题和类型；
- description；
- 节点内 `test_step` 的 action / model / data；
- 业务模型输入表和期望表不从节点中推断。

### 4.2 边

- 使用箭头表示 `from -> to` 的方向。
- `label` 优先显示；没有 label 但有 condition 时显示 condition。
- 选中 flow 中相邻节点之间的边高亮；其它边降低透明度，但仍可见。
- 点击边可查看 source、target、label 和 condition。

### 4.3 Flow

面板首项为“全部路径”，之后列出 XML 中的 flow：

```text
F_LOGIN_SUCCESS · basic
F_LOGIN_INVALID · alternative
F_LOGIN_LOCKED · exception
```

选中 flow 后显示：

- flow ID、类型；
- `path`；
- 路径节点和边高亮；
- 图例说明“选中 flow 只是评审/断言目标，不改变实际条件边的执行”。

### 4.4 布局

首版使用确定性的 DAG 分层布局：

1. 以无入边节点作为第 0 层；
2. 按拓扑顺序计算目标节点层级；
3. 同一层按 XML 节点顺序垂直排列；
4. 使用 SVG 曲线连接层间节点。

业务模型 Schema/Validator 已要求 DAG。即使用户在编辑过程中暂时输入环，面板仍以稳定的兜底层级显示，并在状态区提示“图包含环，请运行业务模型校验”。

---

## 5. Webview 与 Extension Host 边界

### 5.1 Extension Host

`src/businessModelPanel.ts` 负责：

- 读取 XML 文件；
- 创建和复用 WebviewPanel；
- 生成 nonce 和 CSP；
- 注入初始 XML 数据；
- 监听文件变化并发送 `loadXml`；
- 处理 `ready`、`openSource` 消息；
- 不解析业务 XML，不维护第二套业务模型执行逻辑。

### 5.2 Webview

`src/webview/business.html` 和 `business.js` 负责：

- 使用浏览器原生 `DOMParser` 读取 XML；
- 映射成图渲染模型；
- 使用原生 SVG 创建节点、边、箭头和标签；
- 处理 flow 切换、节点/边选择、缩放和拖拽；
- 只接收 XML，不写文件。

不使用远程脚本、外部字体或 CDN。所有显示文字通过 `textContent` 和 SVG 属性写入，避免 XML 描述内容造成 HTML 注入。

### 5.3 消息协议

| 消息 | 方向 | 说明 |
|---|---|---|
| `ready` | Webview -> Host | Webview 初始化完成，请发送 XML |
| `loadXml` | Host -> Webview | `{ xml, filePath }`，重新加载图 |
| `openSource` | Webview -> Host | 在 VSCode 文本编辑器中打开原始 XML |

---

## 6. 文件和构建变更

```text
rodski-vscode/
├── src/
│   ├── businessModelPanel.ts
│   ├── extension.ts                 # 注册命令
│   └── webview/
│       ├── business.html
│       └── business.js
├── test/webview/
│   └── business-webview.test.js
└── esbuild.mjs                       # 复制 HTML，打包 business.js
```

`package.json`：

- 版本从 `0.3.1` 调整为 `0.4.0`；
- 增加 `rodski.openBusinessModel` 命令；
- 增加 `business/` XML 右键菜单；
- 保持 VSCode 最低版本和现有依赖不变。

---

## 7. 安全与兼容约束

1. Webview 使用 `default-src 'none'`，仅允许 nonce 脚本和内联样式。
2. 初始数据注入时将 `<` 编码为 `\\u003c`，防止 XML 内容提前结束 `<script>`。
3. 不执行 XML 中的任何内容；condition 只作为文字显示。
4. 图示使用标准 `business.xsd` 的节点、边和 flow 子集；未知属性被忽略，不影响向前兼容。
5. 不依赖 Python、RodSki CLI 或本地 SQLite，打开图只需要编辑器插件自身。
6. 缺失 `nodes`、`edges` 或 `flows` 时显示可读错误；单个模型错误不会让扩展宿主进程退出。

---

## 8. 验收标准

### 8.1 入口

- [x] `business/*.xml` 右键显示“Open Business Model Diagram”。
- [x] 命令面板可以执行 `rodski.openBusinessModel`。
- [x] 同一文件重复打开只保留一个面板。

### 8.2 图形

- [x] 正确显示模型、节点、边、箭头和条件/标签。
- [x] 正确显示开始、分支、终止节点。
- [x] flow 切换后正确高亮路径。
- [x] 节点详情显示步骤和说明。
- [x] 缩放、复位、适配和拖拽可用。

### 8.3 稳定性

- [x] 外部修改 XML 后自动刷新。
- [x] 非法 XML 显示错误状态。
- [x] XML 文本中的 `<`、`&`、引号等内容不会注入 Webview。
- [x] 不读取或显示业务 Data/Verify 行内容。

### 8.4 工程质量

- [x] TypeScript typecheck 通过。
- [x] ESLint 通过（允许仓库现有 warning 规则）。
- [x] Webview 单元测试覆盖模型解析、节点/边渲染、flow 高亮和交互。
- [x] `npm run compile`、`npm test` 通过。

---

## 9. 后续迭代

- 从正式 `result.xml` 加载已执行节点/边，叠加实际覆盖率颜色；
- 业务模型与 Case 的双向导航；
- 面板内选择 flow 后生成 Case `business_call` 模板；
- 可选的只读 Mermaid/SVG 导出；
- 大图的折叠子流程和搜索。
