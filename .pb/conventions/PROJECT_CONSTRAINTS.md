# 开发和测试工程相关的核心约束

**版本**: v3.7
**日期**: 2026-03-27

## 1. 项目结构说明

### 1.1 核心框架代码

**位置**：`rodski/`

**说明**：RodSki 测试框架的核心代码，包括：
- `core/` - 核心引擎（解析器、执行器、关键字引擎）
- `drivers/` - 驱动层（浏览器、接口、数据库）
- `data/` - 数据处理模块
- `schemas/` - XML Schema 定义

**开发约束**：
- 所有核心功能修改必须保持向后兼容
- 新增关键字需要同步更新 `schemas/case.xsd`
- 修改数据格式需要更新相关文档

### 1.2 Demo 演示项目

**位置**：`rodski-demo/DEMO/`

**目的**：通过简单的示例项目演示 RodSki 的各种用法和功能

**包含项目**：
- `demo_full/` - 完整功能演示（UI、接口、数据库、Return引用等）
- `demo_runtime_control/` - 运行时控制演示（暂停、插入、终止）

**约束**：
- Demo 项目必须简单易懂，代码量最小化
- 每个 Demo 必须有独立的 README.md 说明
- Demo 用例必须能够独立运行
- 不依赖外部真实业务系统

### 1.3 业务测试项目

**位置**：项目根目录下的独立目录（如 `cassmall/`）

**目的**：真实业务场景的自动化测试

**特点**：
- 独立于 Demo 项目
- 包含真实业务逻辑
- 可能依赖外部系统
- 测试数据来自真实业务

**当前项目**：
- `cassmall/thdh/` - Cassmall 同行调货业务测试

## 2. 功能发布测试流程

### 2.1 核心功能测试

**步骤**：

1. **单元测试**（如果有）
   ```bash
   python3 rodski/selftest.py
   ```

2. **Demo 项目验证**
   ```bash
   # 运行完整功能 Demo
   python3 -c "from rodski_cli import main; import sys; sys.argv = ['rodski', 'run', 'case.xml']; main()" -- case demo_case.xml

   # 运行运行时控制 Demo（通过 --insert-step 插入动态步骤）
   python3 -c "from rodski_cli import main; import sys; sys.argv = ['rodski', 'run', 'case.xml']; main()" -- case runtime_case.xml
   ```

3. **验收标准**
   - 所有 Demo 用例通过
   - 无异常错误
   - 结果文件正常生成

### 2.2 新功能测试

**添加新关键字时**：

1. 在 `schemas/case.xsd` 中添加关键字定义
2. 在 `demo_full/` 中添加演示用例
3. 更新相关文档（API_TESTING_GUIDE.md 等）
4. 运行完整测试验证

**添加新数据格式时**：

1. 更新相关 Schema 文件
2. 在 Demo 中添加示例
3. 更新 TEST_CASE_WRITING_GUIDE.md
4. 验证向后兼容性

### 2.3 回归测试

**每次发布前必须执行**：

```bash
# 1. 运行所有 Demo 项目
python3 -c "from rodski_cli import main; import sys; sys.argv = ['rodski', 'run', 'rodski-demo/DEMO/demo_full/case/']; main()"
python3 -c "from rodski_cli import main; import sys; sys.argv = ['rodski', 'run', 'rodski-demo/DEMO/demo_runtime_control/case/']; main()"

# 2. 检查结果
ls -la rodski-demo/DEMO/*/result/

# 3. 验证关键功能
# - 登录流程
# - 接口测试
# - 数据库操作
# - Return 引用
# - 步骤等待时间
```

## 3. 测试数据管理

### 3.1 Demo 项目数据

**原则**：
- 使用本地数据（SQLite、本地服务）
- 数据可重复初始化
- 不依赖外部网络

**示例**：
```bash
# demo_full 初始化数据库
cd rodski-demo/DEMO/demo_full
python3 init_db.py
```

### 3.2 业务项目数据

**原则**：
- 使用测试环境账号
- 在 `data/globalvalue.xml` 中配置
- 敏感信息不提交到代码库

**示例**：
```xml
<group name="test_account">
    <var name="username" value="test_user"/>
    <var name="password" value="test_pass"/>
</group>
```

## 4. 持续集成建议

### 4.1 CI 流程

```yaml
# 示例 CI 配置
test:
  script:
    - python3 rodski/selftest.py
    - python3 -c "from rodski_cli import main; import sys; sys.argv = ['rodski', 'run', 'rodski-demo/DEMO/demo_full/case/']; main()"
  artifacts:
    paths:
      - rodski-demo/DEMO/*/result/
```

### 4.2 测试报告

**位置**：`{project}/result/`

**格式**：XML 格式结果文件

**内容**：
- 用例执行状态
- 执行时间
- 错误信息
- 截图路径（失败时）

## 5. 开发规范

### 5.1 代码提交前检查

- [ ] 运行 Demo 项目验证
- [ ] 更新相关文档
- [ ] 检查向后兼容性
- [ ] 添加必要的注释

### 5.2 文档更新

**必须同步更新的文档**：
- `phoenixbear/design/CORE_DESIGN_CONSTRAINTS.md`（核心设计约束）
- `phoenixbear/design/TEST_CASE_WRITING_GUIDE.md`（用例编写指南）
- API_TESTING_GUIDE.md（接口相关）
- QUICKSTART.md（入门相关）

### 5.3 版本发布

**发布清单**：
1. 所有 Demo 测试通过
2. 文档已更新
3. CHANGELOG 已记录
4. 版本号已更新

## 6. 故障排查

### 6.1 Demo 失败排查

**常见问题**：
- 数据库未初始化 → 运行 `init_db.py`
- 端口被占用 → 检查 8000 端口
- 浏览器驱动问题 → 检查 Playwright 安装

### 6.2 业务测试失败排查

**常见问题**：
- 账号密码错误 → 检查 `globalvalue.xml`
- 网络连接问题 → 检查测试环境可访问性
- 页面元素变化 → 更新 `model.xml`

## 7. 最佳实践

### 7.1 Demo 项目开发

- 保持简单，一个 Demo 演示一个功能点
- 提供完整的运行脚本
- 包含详细的 README
- 数据可重复初始化

### 7.2 业务项目开发

- 独立目录，不混入 Demo
- 使用有意义的项目名称
- 配置文件与代码分离
- 定期维护测试数据

### 7.3 测试用例编写

- 用例 ID 有规律（TC001、TC002...）
- 标题清晰描述测试内容
- 添加 post_process 清理资源
- 合理使用全局等待时间

---

## 8. 核心文档不可违反约束

以下两份文档是每个迭代的实现**绝对不能违反**的约束基准：

| 文档 | 路径 | 说明 |
|------|------|------|
| **核心设计约束** | `../design/CORE_DESIGN_CONSTRAINTS.md` | 框架核心设计决策与约束规则 |
| **用例编写指南** | `../design/TEST_CASE_WRITING_GUIDE.md` | 用例编写规范 |

### 8.1 约束条款

1. **每次迭代的代码改动在上线前，必须逐一对照上述两份文档检查合规性**
2. **若发现文档描述与代码实现不一致，以文档为准**（文档是规范，代码必须服从）
3. **不允许在代码中实现与上述文档描述相矛盾的功能**
4. **新增关键字或变更关键字行为，必须同时更新** `CORE_DESIGN_CONSTRAINTS.md`
5. **新增或变更 XML Schema、XSD 约束，必须同时更新** `TEST_CASE_WRITING_GUIDE.md`

### 8.2 合规检查清单

每次代码提交前，对照核心设计约束检查：

- [ ] SUPPORTED 关键字列表与文档一致（§5）
- [ ] UI 原子动作（click/hover 等）不在 SUPPORTED 中（§1.2）
- [ ] 目录结构符合 `product/项目/模块` 规范（§6）
- [ ] 自检不使用 pytest（§9）
- [ ] 数据表格式符合规范（§7.3）
- [ ] 视觉定位器类型符合规范（§10）

---

**最后更新**: 2026-04-04

---

# 技术设计约束

以下是 RodSki 框架的核心技术设计约束，所有开发必须遵循。

## 9. 关键字职责划分

### 9.1 三大核心关键字

| 关键字 | 职责 | 适用范围 |
|--------|------|---------|
| **type** | UI 批量输入 | PC Web / Android / iOS / 桌面端 — 所有 UI 平台统一 |
| **send** | 接口请求发送 | REST API 接口测试 |
| **verify** | 批量验证 | UI 验证 + 接口响应验证 — 通用 |

**约束**：
- `type` 只做 UI，`send` 只做接口，二者不混用
- `verify` 是通用的，根据模型的 `driver_type`（web / interface）自动判断从界面读值还是从接口响应读值
- 不存在 `http_get`、`http_post`、`http_put`、`http_delete`、`assert_json`、`assert_status` 等独立 HTTP 关键字

### 9.2 UI 原子动作不作为独立关键字

以下操作**不出现在 Case XML 的 action 属性中**，只能作为数据表字段值，由 `type` 批量模式自动识别执行：

```
click / double_click / right_click / hover / select【值】
key_press【按键】 / drag【目标】 / scroll / scroll【x,y】
```

**约束**：`SUPPORTED` 列表中不包含这些关键字，测试用例中不允许写 `click` 或 `hover` 等作为动作。

### 9.3 navigate / launch — 应用启动（场景化双关键字）

**`navigate`** 和 **`launch`** 在功能上完全相同，都是"启动或切换到目标应用/页面"，只是适用场景不同：

| 关键字 | 适用场景 | 参数格式 | 行为 |
|--------|---------|---------|------|
| **navigate** | Web / Mobile | URL 地址 | 如果当前没有浏览器实例 → 自动通过 `driver_factory` 创建；如果已有浏览器实例 → 复用现有实例，导航到目标 URL |
| **launch** | Desktop (Windows/macOS) | 应用路径或应用名 | 如果应用未运行 → 启动应用；如果应用已运行 → 切换到该应用窗口 |

**约束**：
- `navigate` 替代了 `open`（已废弃）
- `navigate` 和 `launch` 在关键字计数中**算作一个**（场景化变体，非独立关键字）
- 桌面端不使用 `navigate`，Web/Mobile 不使用 `launch`，避免语义混淆

### 9.4 run = 脚本调用能力

`run` 是与 `type`/`verify`/`send` 同级的通用关键字，为框架提供脚本调用能力：

**定义**：
- 在独立子进程中执行 Python 脚本
- 代码以工程形式组织在 `fun/` 目录下（与 `case/` 同级）
- 脚本 stdout 自动保存为步骤返回值（优先 JSON 解析）
- 目前仅支持 Python

**定位**：
- 是用例执行时预留的扩展能力
- 与其他关键字级别相同，任何平台都可使用
- 用于处理框架内置关键字无法覆盖的场景

**使用示例**：
```xml
<test_step action="run" model="" data="fun/utils/data_process.py"/>
```

## 10. 数据表命名与引用规则

### 10.1 数据表文件组织方式

**实际实现**：所有数据表合并在两个固定文件中：

```
data/data.xml          ← 所有操作数据表（type/send 使用）
data/data_verify.xml   ← 所有验证数据表（verify 使用，可选）
```

**约束**：
- 模型名与数据表名（`datatable.name`）必须一致
- 不需要为每个模型创建独立的 XML 文件
- `data_verify.xml` 是可选的，可以将验证数据也放在 `data.xml` 中

### 10.2 验证数据表自动拼接 `_verify` 后缀

```
verify Login V001 → 自动查找表名为 "Login_verify" 的数据表
verify LoginAPI V001 → 自动查找表名为 "LoginAPI_verify" 的数据表
```

### 10.3 数据列只写 DataID

Case XML 的 data 属性中，只需要写 DataID，不需要写表名前缀：

```
✅ type  Login    L001      → 在 Login.xml 中查找 id="L001"
✅ send  LoginAPI D001      → 在 LoginAPI.xml 中查找 id="D001"
✅ verify Login    V001      → 在 Login_verify.xml 中查找 id="V001"

❌ type  Login    LoginData.L001   ← 不需要写表名
```

### 10.4 元素名 = 数据表字段名

模型 XML 中的 `element name` 必须与数据表 XML 中 `<field name="...">` 完全一致（区分大小写），这是 `type`/`send`/`verify` 批量模式的匹配基础。

## 11. 定位器类型（完整）

RodSki 支持 12 种定位器类型，分为传统定位器和视觉定位器两大类。

### 11.1 传统定位器

| 类型 | 格式 | 说明 | 示例 |
|------|------|------|------|
| `id` | CSS ID | 转换为 `#值` | `<location type="id">username</location>` → `#username` |
| `class` | CSS Class | 转换为 `.值` | `<location type="class">btn-submit</location>` → `.btn-submit` |
| `css` | CSS 选择器 | 原样使用 | `<location type="css">input[name="user"]</location>` |
| `xpath` | XPath | 原样使用 | `<location type="xpath">//input[@id='user']</location>` |
| `text` | 文本匹配 | Playwright `text=...` | `<location type="text">登录</location>` → `text=登录` |
| `tag` | 标签名 | HTML 标签 | `<location type="tag">button</location>` |
| `name` | name 属性 | 按 name 属性定位 | `<location type="name">username</location>` |
| `static` | 静态值 | 字面量，不定位 | 用于接口 `_method` 等 |
| `field` | 字段映射 | 接口请求字段 | 用于接口 body/query |

### 11.2 视觉定位器

| 类型 | 格式 | 说明 | 示例 |
|------|------|------|------|
| `vision` | 图片匹配 | 通过截图/图片模板匹配定位 | `<location type="vision">img/login_btn.png</location>` |
| `ocr` | 文字识别 | 通过 OCR 识别文字定位 | `<location type="ocr">登录</location>` |
| `vision_bbox` | 坐标定位 | 直接使用坐标 `x1,y1,x2,y2` | `<location type="vision_bbox">100,200,150,250</location>` |

### 11.3 多定位器格式

每个元素可定义多个定位器，失败时自动切换：

```xml
<element name="loginBtn" type="web">
    <type>button</type>
    <location type="id" priority="1">loginBtn</location>
    <location type="xpath" priority="2">//button[@class='login']</location>
    <location type="ocr" priority="3">登录</location>
</element>
```

## 12. 接口测试设计约束

### 12.1 接口模型定义请求属性

| 元素名 | 作用 | 说明 |
|--------|------|------|
| `_method` | 请求方式 | GET / POST / PUT / DELETE，模型中定义默认值 |
| `_url` | 请求地址 | 绝对 URL 或相对路径 |
| `_header_*` | 请求头 | 如 `_header_Authorization`、`_header_Content-Type` |
| 其他元素 | 请求体字段 | POST/PUT → JSON body；GET/DELETE → 查询参数 |

### 12.2 send 的响应存储格式

`send` 的响应自动保存为字典，包含 `status` 和响应体字段：

```python
{"status": 200, "token": "abc123", "username": "admin", ...}
```

## 13. 特殊值约定

| 值 | UI 行为（type） | 接口行为（send） | 验证行为（verify） |
|----|----------------|-----------------|-------------------|
| 空值 | 跳过 | — | — |
| `BLANK` | 跳过 | 发送空字符串 | 期望空字符串 |
| `NULL` | 跳过 | 发送 null | 期望 null |
| `NONE` | 跳过 | 不发送该字段 | 跳过验证 |
| `.Password` 后缀 | 输入，日志脱敏 | — | — |

## 14. Return 引用

- `${Return[-1]}`、`${Return[0]}` 等只应出现在**数据表 XML 的 field 值中**
- 使用的标准格式是 `${Return[x]}` 其中x代表测试步骤，0是当前测试步骤，也就是当前测试步骤执行完成后保存的执行结果变量.-1代表上一个测试步骤的执行结果。以此类推。
- 不要写在 Case XML 的 data 属性，否则会在进入关键字前被替换成字符串

## 15. 当前关键字清单（15 个）

```
SUPPORTED = [
    "close", "type", "verify", "wait", "navigate", "launch",
    "assert",
    "upload_file", "clear", "get_text", "get",
    "send", "set", "DB", "run",
]
```

加上 1 个兼容关键字 `check`（等同 `verify`）。

**设计原则**：关键字数量应保持精简，新增关键字前需评估是否可以通过现有批量模式（数据表字段值）实现。

## 16. 目录结构约束（强制）

### 16.1 产品目录层级

```
product/                           ← 产品根目录（顶层）
└── {测试项目名}/                   ← 测试项目（如 DEMO）
    └── {测试模块名}/               ← 测试模块/业务（如 demo_site）
        ├── case/                  ← 测试用例 XML 文件
        ├── model/                 ← 模型 XML 文件
        ├── fun/                   ← 代码工程目录（run 关键字使用）
        ├── data/                  ← 数据 XML 文件 + 全局变量
        └── result/                ← 测试结果 XML（框架自动生成）
```

### 16.2 禁止变更

- **product 必须是最顶层目录**，不可将项目/模块提升到 product 之上
- **5 个固定文件夹名称不可更改**（case/model/fun/data/result）
- **固定文件夹只出现在测试模块层级下**，不可出现在测试项目层级
- **model.xml 是唯一的模型文件名**，不可改名

## 17. XML 文件格式约束

### 17.1 运行时 XSD 校验（强制）

框架在**读取**各类测试相关 XML 时，会按类型对照 `rodski/schemas/*.xsd` 做一次 **XML Schema 校验**。

### 17.2 Case XML 格式约束（三阶段）

每个 `<case>` 下**固定三个阶段容器**：

| 阶段容器 | 说明 |
|---------|------|
| `<pre_process>` | 预处理：内层 0 个或多个 `<test_step>` |
| `<test_case>` | **必选且恰好 1 个**：内层至少 1 个 `<test_step>` |
| `<post_process>` | 后处理：内层 0 个或多个 `<test_step>` |

## 18. 固定与动态测试步骤（架构规划）

### 18.1 目标与边界

| 能力 | 说明 |
|------|------|
| 固定步骤 | 来自 `case/*.xml` 的 `<test_step>`，顺序与内容在运行前已知 |
| 动态步骤 | 由 CLI 指令、扩展点或运行时策略在**执行过程中**插入的步骤 |
| 混合执行 | 同一用例阶段内，执行序列为「固定步骤流」与「动态步骤」的可组合序列 |

### 18.2 运行时控制命令

| 命令 | 语义 |
|------|------|
| **暂停（pause）** | 当前执行流停住，直至收到继续或终止 |
| **插入（insert）** | 在当前固定步骤流中插入新测试步骤 |
| **终止（terminate）** | 结束当前用例或当前执行会话 |

## 19. 自检约束 — 不依赖外部测试框架

### 19.1 原则

RodSki 的**框架自身测试（自检）不得依赖任何外部测试框架**（`pytest`、`nose`、`unittest` runner 等）。

### 19.2 自有测试执行器

| 文件 | 作用 |
|------|------|
| `core/test_runner.py` | **`RodskiTestRunner`** — 自动发现并执行测试 |
| `selftest.py` | 入口脚本，自动设置 `sys.path` |

### 19.3 禁止事项

- ❌ `requirements.txt` 中列出 `pytest` / `pytest-cov` 等
- ❌ 测试文件中使用 `@pytest.fixture`、`pytest.raises` 等
- ❌ 需要 `PYTHONPATH=.` 才能运行测试

## 20. 视觉定位设计约束

### 20.1 OmniParser 作为图像坐标识别核心

**设计决策**: RodSki 使用 **OmniParser** 作为图像坐标识别的核心能力。

**架构原则**:
- OmniParser 提供页面元素的坐标和内容识别
- 多模态 LLM（Claude/GPT-4V/Qwen-VL）提供语义理解
- 视觉定位作为**定位器类型**，不是独立关键字

### 20.2 约束规则

- ❌ 不新增 `vision_click`、`vision_input` 等关键字
- ❌ 不在 Case XML 中直接写坐标
- ✅ 视觉定位作为模型定位器类型
- ✅ 复用现有 15 个关键字
- ✅ 坐标信息记录在模型 XML 中

## 21. 桌面平台约束

### 21.1 平台标识

| driver_type | 说明 | 适用场景 |
|------------|------|---------|
| `windows` | Windows 桌面应用 | Win10/Win11 桌面自动化 |
| `macos` | macOS 桌面应用 | macOS 桌面自动化 |

### 21.2 桌面端设计原则

**核心原则**：
- ✅ 关键字统一：type/verify/launch 与 Web 平台完全相同
- ✅ 驱动分离：桌面使用 pyautogui + OmniParser 驱动
- ✅ 视觉定位为主（vision/ocr/vision_bbox）
- ❌ 不支持接口测试（`send` 关键字不适用于桌面端）

---

*文档版本: v3.8 | 最后更新: 2026-04-04*
