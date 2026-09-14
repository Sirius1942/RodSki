# RodSki 核心设计约束

**版本**: v11.3.0
**日期**: 2026-08-14

本文档记录 RodSki 框架的核心设计决策与约束规则，所有后续开发必须遵循。

> ⚠️ **不可违反约束**：本文档与 `TEST_CASE_WRITING_GUIDE.md` 是每个迭代的实现**绝对不能违反**的约束基准（详见附录 A）。

---

## 版本更新记录

| 版本 | 日期 | 主要变更 |
|------|------|---------|
| v11.3.0 | 2026-09-14 | iOS 真机纳入设备发现（devicectl）、真机+模拟器混跑约束（§11.5 追加）、移动端导航两条硬约束（§11.5 追加） |
| v11.2.0 | 2026-09-10 | 移动端多设备并发约束（§11.5）：计划不可拆分、动态领取、`--udid` 覆盖顺序、并发端口分槽 |
| v9.2.3 | 2026-08-14 | 探索式测试架构约束、ConfigManager 序列化规范、Playwright 驱动初始化规范 |
| v7.1.1 | 2026-05-29 | 移动端测试能力、录像架构 |
| v6.0.0 | 2026-03-15 | data.sqlite 统一数据源 |

---

## 1. 关键字职责划分

### 1.1 三大核心关键字

| 关键字 | 职责 | 适用范围 |
|--------|------|---------|
| **type** | UI 批量输入 | PC Web / Android / iOS / 桌面端 — 所有 UI 平台统一 |
| **send** | 接口请求发送 | REST API 接口测试 |
| **verify** | 批量验证 | UI 验证 + 接口响应验证 — 通用 |

**约束**：

- `type` 只做 UI，`send` 只做接口，二者不混用
- `verify` 是通用的，根据模型的 `driver_type`（web / interface）自动判断从界面读值还是从接口响应读值
- 不存在 `http_get`、`http_post`、`http_put`、`http_delete`、`assert_json`、`assert_status` 等独立 HTTP 关键字

### 1.2 UI 原子动作不作为独立关键字

以下操作**不出现在 Case XML 的 action 属性中**，只能作为数据表字段值，由 `type` 批量模式自动识别执行：

```
click / double_click / right_click / hover / select【值】
key_press【按键】 / drag【目标】 / scroll / scroll【x,y】
```

**约束**：`SUPPORTED` 列表中不包含这些关键字，测试用例中不允许写 `click` 或 `hover` 等作为动作。

### 1.3 navigate / launch — 应用启动（场景化双关键字）

**`navigate`** 和 **`launch`** 在功能上完全相同，都是"启动或切换到目标应用/页面"，只是适用场景不同：

| 关键字 | 适用场景 | 参数格式 | 行为 |
|--------|---------|---------|------|
| **navigate** | Web / Mobile | URL 地址或 App URI | 如果当前没有浏览器实例 → 自动通过 `driver_factory` 创建；如果已有浏览器实例 → 复用现有实例，导航到目标 URL。Mobile 场景下支持 App URI 格式启动原生 App |
| **launch** | Desktop (Windows/macOS) | 应用路径或应用名 | 如果应用未运行 → 启动应用；如果应用已运行 → 切换到该应用窗口 |

**Mobile App URI 格式（v7.0.0）**：
- `app://android/{package}/{activity}` — 启动 Android App 指定 Activity
- `app://android/{package}` — 启动 Android App 默认 Activity
- `app://ios/{bundleId}` — 启动 iOS App

**约束**：
- `navigate` 替代了 `open`（已废弃）
- `navigate` 和 `launch` 在关键字计数中**算作一个**（场景化变体，非独立关键字）
- 桌面端不使用 `navigate`，Web/Mobile 不使用 `launch`，避免语义混淆

### 1.4 run = 脚本调用能力

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

**in-process 内置函数扩展点（v6.7.6）**：

`run` 在执行脚本前会先查找内置函数注册表。如果 `data` 匹配已注册的内置函数名，则在当前进程内直接调用（不走子进程）。

已注册内置函数：
- `mock_route(url_pattern, status, body, content_type)` — Mock API 响应（仅 Playwright）
- `wait_for_response(url_pattern, timeout)` — 等待网络请求完成
- `clear_routes()` — 清除所有 mock route

用法示例：
```xml
<test_step action="run" model="" data="mock_route(url_pattern='/api/users', status=200, body='{&quot;users&quot;:[]}')"/>
```

**约束**：内置函数需要访问进程内 driver 实例，因此不走子进程。扩展新内置函数通过 `builtin_ops/` 模块注册。

---

## 2. 数据表命名与引用规则

### 2.1 数据表文件组织方式

> **版本说明**：v6.0.0 之前，测试数据通过 `data.xml` / `data_verify.xml` 编写；v6.0.0 起完全废弃，统一使用 `data.sqlite`。

**实际实现**：测试数据固定组织在以下文件中：

```
data/data.sqlite       ← 唯一测试数据文件（必须）
data/globalvalue.xml   ← 全局变量（独立）
```

**约束**：
- 模型名与逻辑表名（`rs_datatable.table_name`）必须一致
- `data.sqlite` 是唯一测试数据文件；`data.xml` / `data_verify.xml` 已在 v6.0.0 废弃
- 若 `data.xml` 或 `data_verify.xml` 存在，运行时报错，必须先执行 `rodski data import <module>` 迁移
- `globalvalue.xml` 不进入 SQLite，继续独立解析

### 2.2 验证数据表自动拼接 `_verify` 后缀

```
verify Login V001 → 自动查找表名为 "Login_verify" 的数据表
verify LoginAPI V001 → 自动查找表名为 "LoginAPI_verify" 的数据表
```

**注意**：验证数据表（`_verify` 后缀）与输入数据表统一存储在 `data.sqlite` 中，`table_kind='verify'`。

### 2.3 数据列只写 DataID

Case XML 的 data 属性中，只需要写 DataID，不需要写表名前缀：

```
✅ type  Login    L001      → 在逻辑表 `Login` 中查找 id="L001"
✅ send  LoginAPI D001      → 在逻辑表 `LoginAPI` 中查找 id="D001"
✅ verify Login    V001      → 在逻辑表 `Login_verify` 中查找 id="V001"

❌ type  Login    LoginData.L001   ← 不需要写表名
```

### 2.4 元素名 = 数据表字段名

模型 XML 中的 `element name` 必须与数据表 XML 中 `<field name="...">` 完全一致（区分大小写），这是 `type`/`send`/`verify` 批量模式的匹配基础。

### 2.4.1 SQLite 数据约束

- `data.sqlite` 是唯一测试数据文件，v6.0.0 起不再支持 XML 数据文件
- SQLite 中的同一逻辑表必须显式声明 schema，且所有数据行字段集合完全一致
- 若 `data.xml` 或 `data_verify.xml` 存在，运行时立即报错，不加载任何数据
- v6.7.6 起，缺字段不再静默跳过，而是直接报错。必须显式填写 BLANK/NULL/NONE 表示跳过。

---

## 2.5 定位器类型（完整）

RodSki 支持 12 种定位器类型，分为传统定位器和视觉定位器两大类。

### 2.5.1 传统定位器

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
| `predicate` | iOS NSPredicate 字符串 | **iOS 专用**，映射 Appium `IOS_PREDICATE` | `<location type="predicate" platform="ios">label == '登录'</location>` |
| `class_chain` | iOS XCUITest Class Chain | **iOS 专用**，映射 Appium `IOS_CLASS_CHAIN` | `<location type="class_chain" platform="ios">**/XCUIElementTypeButton[`label == '登录'`]</location>` |

**iOS 专用定位器说明（v7.2.x，WI-55）**：

- `predicate`：NSPredicate 字符串，功能与 Android resource-id 类似，可按属性精确匹配（`label == '登录'`、`type == 'XCUIElementTypeButton' AND enabled == true` 等），性能优于 XPath
- `class_chain`：XCUITest 原生路径语法，比 XPath 更快，支持索引和条件筛选

二者仅对 `platform="ios"` 的模型元素生效（通过 `location.platform="ios"` 声明），跨平台 `mobile` 模型可同时保留 Android id 定位器。

```xml
<!-- 跨平台模型示例：Android + iOS 并存 -->
<element name="loginBtn" type="mobile">
    <type>button</type>
    <location type="id" platform="android" priority="1">com.rodski.demo:id/loginBtn</location>
    <location type="id" platform="ios" priority="1">login_button</location>
    <location type="predicate" platform="ios" priority="2">label == '登录'</location>
    <location type="text" priority="3">登录</location>
</element>
```

### 2.5.2 视觉定位器

| 类型 | 格式 | 说明 | 示例 |
|------|------|------|------|
| `vision` | 语义描述 | 通过 rodski-perception 插件调用 VLM（默认 Qwen3-VL via ollama）语义匹配定位；移动端优先 Accessibility Tree 文本匹配 | `<location type="vision">登录按钮</location>` |
| `vision_image` | 参考图路径 | **rodski 核心** OpenCV 模板匹配（多尺度），离线、毫秒级、像素精确 | `<location type="vision_image">../assets/login_btn.png</location>` |
| `ocr` | 文字识别 | 通过本地 OCR 引擎（PaddleOCR/EasyOCR）识别文字定位 | `<location type="ocr">登录</location>` |
| `vision_bbox` | 坐标定位 | 直接使用坐标 `x1,y1,x2,y2`，零依赖 | `<location type="vision_bbox">100,200,150,250</location>` |

**视觉定位器说明**：

- **`vision` 语义定位器（v7.1.0 重构）**：
  - 值为语义描述文本（如"登录按钮"、"搜索输入框"）
  - 通过 rodski-perception 插件（LocalBackend / RemoteBackend）调用 VLM 定位
  - 移动端优先通过 Accessibility Tree 文本匹配（快速路径），失败后降级到 VLM
  - **需要安装 perception 插件**：`pip install rodski[perception]` + 本地 ollama
  - 适用于：动态 ID/class 的元素、无明显属性的元素、跨语言测试、缺少参考图

- **`vision_image` 图片模板匹配定位器（v7.1.0 新增）**：
  - 值为参考图路径（相对 model.xml 目录或绝对路径，支持 `${var}` 变量）
  - 通过 OpenCV `matchTemplate` + 多尺度匹配 (TM_CCOEFF_NORMED)
  - **rodski 核心实现**，仅依赖 opencv-python，不需要 perception 插件
  - 默认相似度阈值 0.85，匹配延迟 < 50ms（1920×1080）
  - 适用于：UI 稳定、有参考截图、需要极速且像素级精度
  - 副产物：每次成功匹配产生（截图, element_type, bbox）三元组，可作为后续训练自有 YOLO 的标注数据来源

- **`ocr` 文字定位器**：
  - 值为要识别的文字内容
  - 通过本地 OCR 引擎识别文字位置（rodski 核心，不需要 perception 插件）
  - 适用于：按钮文字、标签、链接文字

- **`vision_bbox` 坐标定位器**：
  - 值为坐标 `x1,y1,x2,y2`（逗号分隔）
  - 无任何 AI 调用，性能最高
  - Web 用页面像素坐标，Desktop 用屏幕绝对坐标
  - 适用于：坐标固定的元素、调试兜底

**视觉定位器与 rodski-perception 插件的关系**：

```
┌─────────────┬─────────────────────────┬───────────────────┐
│ 定位器       │ 实现位置                │ 需要 perception ? │
├─────────────┼─────────────────────────┼───────────────────┤
│ vision      │ rodski-perception 插件   │ ✅ 是              │
│ vision_image│ rodski 核心 (OpenCV)    │ ❌ 否              │
│ ocr         │ rodski 核心 (PaddleOCR) │ ❌ 否              │
│ vision_bbox │ rodski 核心 (坐标解析)  │ ❌ 否              │
└─────────────┴─────────────────────────┴───────────────────┘
```

**正交原则**：rodski 核心不依赖 perception 插件。未安装 perception 时，`vision_image` / `ocr` / `vision_bbox` 仍可正常使用；仅 `vision` 在执行时报 `PerceptionUnavailableError`。

### 2.5.3 定位器格式约束

**格式规范**：
1. 所有定位器使用 `<location type="类型">值</location>` 格式
2. `type` 属性必须为 LocatorType 枚举值之一
3. 值写在 location 标签内容中

**约束规则**：
```xml
<!-- ✅ 正确：完整格式（唯一支持的格式） -->
<element name="loginBtn" type="web">
    <type>button</type>
    <location type="id">loginBtn</location>
</element>

<!-- ❌ 已移除（v5.4.0）：简化格式不再支持 -->
<!-- <element name="loginBtn" type="id" value="loginBtn"/> -->

<!-- ❌ 错误：不要使用 locator 属性 -->
<!-- <element name="loginBtn" locator="vision:登录按钮"/> -->
```

> **⚠️ v5.4.0 变更**：简化格式 `type="定位类型" value="值"` 和 `locator="前缀:值"` 已从解析器中移除。所有定位器必须使用 `<location type="类型">值</location>` 子节点格式。

### 2.5.4 多定位器格式

每个元素可定义多个定位器。根据 `priority` 是否声明，**触发两种不同语义**：

#### 模式一：顺序回退（priority 各不相同，v6.x 已有）

```xml
<element name="loginBtn" type="button">
    <location type="vision_image" priority="1">../assets/login_btn.png</location>
    <location type="ocr"          priority="2">登录</location>
    <location type="vision"       priority="3">登录按钮</location>
</element>
```

**切换规则**：
1. 按 `priority` 从小到大依次尝试
2. 当前定位器定位失败时，自动切换到下一个
3. 所有定位器都失败时，抛出 `ElementNotFoundError`

**使用场景**：稳定主路径 + 柔性兜底。

#### 模式二：融合裁决（无 priority 或同 priority，v7.1.0 新增）

```xml
<element name="loginBtn" type="button">
    <location type="vision_image">../assets/login_btn.png</location>
    <location type="ocr">登录</location>
    <location type="vision">登录按钮</location>
</element>
```

**裁决规则**：
1. 所有定位器**并行**执行，各自得到 bbox + confidence
2. 计算两两 bbox 的 IoU，**IoU > 0.5 的归为一组（共识）**
3. 每组得分 = `Σ (confidence_i × weight[type_i])`
   - 默认权重：`vision_image`: 1.0，`ocr`: 0.8，`vision`: 0.6
   - element 的 `type` 属性（button/input/text/...）作为先验透传给 backend，与之一致的命中 +0.2 加成
4. 返回最高分聚类的中心点 + 综合 `confidence`
5. 所有定位器都失败 → `ElementNotFoundError`

**置信度判定**：
- 3 个定位器达成共识 → 高置信度（≥ 0.85）
- 2 个定位器共识 → 中置信度，记录偏离项供调优
- 0 个共识 → 取最高分单项，warning 日志

**使用场景**：UI 稳定性未知、需要更高定位精度、自动产出高质量标注数据用于未来训练 YOLO 等小模型。

**判定方法（解析层）**：
- 所有 `<location>` 都有显式 `priority` 且各不相同 → 模式一
- 全部缺省 `priority` 或全部相同 → 模式二
- 部分有部分无 → 校验失败（XSD），不允许混用

### 2.5.5 示例对比

同一个登录按钮的四种定位方式：

```xml
<!-- 方式1: vision_image 图片模板匹配（v7.1.0 新增，rodski 核心，离线、极速） -->
<element name="loginBtn" type="button">
    <location type="vision_image">../assets/login_btn.png</location>
</element>

<!-- 方式2: vision 语义定位（需要 rodski-perception 插件 + ollama VLM） -->
<element name="loginBtn" type="button">
    <location type="vision">登录按钮</location>
</element>

<!-- 方式3: OCR 文字识别 - 识别"登录"二字 -->
<element name="loginBtn" type="button">
    <location type="ocr">登录</location>
</element>

<!-- 方式4: 融合裁决（v7.1.0 新增）- 三种定位器并行，共识裁决 -->
<element name="loginBtn" type="button">
    <location type="vision_image">../assets/login_btn.png</location>
    <location type="ocr">登录</location>
    <location type="vision">登录按钮</location>
</element>

<!-- 方式5: 坐标定位 - 固定位置兜底 -->
<element name="loginBtn" type="button">
    <location type="vision_bbox">100,200,150,250</location>
</element>
```

---

## 2.6 Perception 插件机制（v7.1.0）

### 2.6.1 设计原则

**正交插件，rodski 核心不依赖**：

- rodski 核心**不依赖**任何 perception 实现。未安装任何 backend 时，rodski 其他能力（DB、Web、Mobile、Desktop、vision_image、ocr、vision_bbox）**全部正常**；仅 `<location type="vision">` 在执行时报 `PerceptionUnavailableError`。
- 未来新增 backend（如远程 omni、第三方 backend）**不需要修改 rodski 源码**——通过 Python `entry_points` 注册即可被发现。
- 接口契约稳定后，rodski 和 rodski-perception 可独立迭代版本。

### 2.6.2 抽象接口（rodski/vision/perception_interface.py）

```python
@dataclass
class PerceptionResult:
    bbox: tuple[int, int, int, int]   # 千分比 [0, 1000]
    coordinates: tuple[int, int]       # 像素坐标（中心点）
    target_description: str
    confidence: float | None = None
    consensus_count: int = 0           # 融合裁决中达成共识的 hint 数
    latency_ms: int = 0

class PerceptionBackend(ABC):
    name: str = "abstract"
    capabilities: set[str] = set()     # {"locate", "locate_many", "locate_fused"}

    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    def locate(self, image_path, description) -> PerceptionResult | None: ...

    def locate_many(self, image_path, descriptions) -> list[...]:
        """默认实现为多次 locate；backend 可重载为单次推理。"""

    def locate_fused(self, image_path, hints, element_type=None) -> PerceptionResult | None:
        """融合裁决：hints = [{'type': 'ocr'|'vision_image'|'vision', 'value': '...'}, ...]"""
```

### 2.6.3 插件发现（entry_points）

backend 项目通过 `pyproject.toml` 注册：

```toml
# rodski-perception/pyproject.toml
[project.entry-points."rodski.perception_backends"]
local = "rodski_perception.backend:LocalPerceptionBackend"

# 未来 - rodski-omni-client
[project.entry-points."rodski.perception_backends"]
remote = "rodski_omni_client.backend:RemotePerceptionBackend"
```

rodski 运行时通过 `importlib.metadata.entry_points(group="rodski.perception_backends")` 自动发现。

### 2.6.4 backend 选择策略

```
优先级：globalvalue.xml 显式指定 > local（自动发现） > remote（自动发现） > 报错
```

配置项（globalvalue.xml）：

```xml
<global>
    <var name="perception_backend"   value="local"/>          <!-- local | remote -->
    <var name="perception_model"     value="qwen3-vl:2b"/>    <!-- local 用 -->
    <var name="ollama_host"          value="http://localhost:11434"/>
    <var name="perception_server"    value="http://omni.example.com"/>  <!-- remote 用 -->
</global>
```

环境变量覆盖：`RODSKI_PERCEPTION_BACKEND`、`RODSKI_PERCEPTION_MODEL`、`OLLAMA_HOST`、`RODSKI_PERCEPTION_SERVER`

### 2.6.5 内置 backend

| backend | 来源项目 | 实现 | 状态 |
|---------|---------|------|------|
| `local` | rodski-perception | 本地 ollama + Qwen3-VL（默认 2B） | v7.1.0 交付 |
| `remote` | rodski-omni-client（独立项目） | HTTP 调用 omni 服务端 | v7.1.0 仅契约，实现后置 |

### 2.6.6 安装方式

```bash
# 仅核心（vision_image / ocr / vision_bbox 可用，vision 不可用）
pip install rodski

# 核心 + 本地 perception
pip install rodski[perception]
brew install ollama && brew services start ollama
ollama pull qwen3-vl:2b

# 核心 + 远程 perception（未来）
pip install rodski[perception-remote]
# 配置 perception_server 地址
```

### 2.6.7 与定位器的对应关系

| 定位器 | 是否走 backend | 走哪个接口 |
|--------|---------------|-----------|
| `vision_bbox` | ❌ 不走 | 直接解析坐标 |
| `vision_image` | ❌ 不走 | rodski 核心 ImageTemplateMatcher (OpenCV) |
| `ocr` | ❌ 不走 | rodski 核心 OCRLocator |
| `vision` (单 location) | ✅ 走 | `backend.locate()` |
| 多 location 顺序回退 (有 priority) | 各自走自己的路径 | 仅 vision 那一项走 backend |
| 多 location 融合裁决 (无 priority) | ✅ 走 | `backend.locate_fused(hints)` |

### 2.6.8 错误处理约束

- 未安装 backend + 用 `vision` → `PerceptionUnavailableError`（含安装指引），**不允许**抛 `ImportError` 栈
- 已安装 backend + ollama 不可达 → `OllamaUnreachableError`（含启动指引），CLI 退出码 3
- 融合裁决所有 hints 都失败 → 返回 `None`，由 driver 抛 `ElementNotFoundError`
- `vision_image` 参考图不存在 → 明确文件路径错误，**不允许**抛 OpenCV 底层栈

详细设计见 `.pb/specs/v7.1.0-perception-design.md`。

---

## 3. 接口测试设计约束

### 3.1 接口模型定义请求属性

接口模型在 model.xml 中通过特殊命名的元素定义 HTTP 请求属性：

| 元素名 | 作用 | 说明 |
|--------|------|------|
| `_method` | 请求方式 | GET / POST / PUT / DELETE，模型中定义默认值 |
| `_url` | 请求地址 | 绝对 URL 或相对路径 |
| `_header_*` | 请求头 | 如 `_header_Authorization`、`_header_Content-Type` |
| 其他元素 | 请求体字段 | POST/PUT → JSON body；GET/DELETE → 查询参数 |

### 3.2 send 的响应存储格式

`send` 的响应自动保存为字典，包含 `status` 和响应体字段：

```python
{"status": 200, "token": "abc123", "username": "admin", ...}
```

### 3.3 verify 的接口验证

`verify` 在接口场景下从 `${Return[-1]}`（即 `send` 的响应）读取实际值，与 `_verify` 数据表中的期望值逐字段比较。`_verify` 数据表中 `status` 列用于验证 HTTP 状态码。只要存在 `verify` 步骤，就必须按字段**严格全匹配**；任一字段不一致立即判定该步骤失败，并使 case FAIL。

---

## 4. 特殊值约定

### 4.1 数据表中的控制值

| 值 | UI 行为（type） | 接口行为（send） | 验证行为（verify） |
|----|----------------|-----------------|-------------------|
| 空值 | 跳过 | — | — |
| `BLANK` | 跳过 | 发送空字符串 | 期望空字符串 |
| `NULL` | 跳过 | 发送 null | 期望 null |
| `NONE` | 跳过 | 不发送该字段 | 跳过验证 |
| `.Password` 后缀 | 输入，日志脱敏 | — | — |

### 4.2 Return 引用

- `${Return[-1]}`、`${Return[0]}` 等只应出现在**数据表 XML 的 field 值中**
- 使用的标准格式是 `${Return[x]}` 其中x代表测试步骤，0是当前测试步骤，也就是当前测试步骤执行完成后保存的执行结果变量.-1代表上一个测试步骤的执行结果。以此类推。
- 不要写在 Case XML 的 data 属性，否则会在进入关键字前被替换成字符串
- **与动态步骤的关系**：在「固定 + 动态」混合执行模型下，`${Return[-1]}` 的语义**仅绑定固定步骤管线**（见第 8 节）；动态插入步骤**暂不参与** `Return` 解析链，数据表中亦**不得**依赖动态步骤上的 `${Return[...]}`（见第 8.4 节）,但是动态步骤每一步的返回值也需要保存，区别于静态步骤的返回值

**暂停 / 插入**不改变上述「固定管线」语义：`${Return[-1]}` 仍指「最近一次完成执行的固定步骤」的返回值（插入步是否入栈见 8.4；若未入栈，则与插入前一致）。

### 4.3 verify 数据表中 ${Return} 的使用限制

**禁止：接口/DB 模型的 _verify 表中使用 ${Return[-1]}**

verify 对接口和数据库模型的实际值**自动从 Return[-1] 提取**（按模型元素的 locator 字段匹配）。
如果期望值也写 ${Return[-1]}，则期望值和实际值取自同一数据源，比较结果永远相等，
断言失去验证价值（"空校验"）。

**v6.7.6 起，此检查为硬性约束：框架检测到接口/DB _verify 表中存在 ${Return[-1]} 时直接失败（不再仅警告）。**

```xml
<!-- 禁止：接口/DB verify 的期望值引用 Return[-1]（自己比自己） -->
<datatable name="LoginAPI_verify">
  <row id="V001">
    <field name="token">${Return[-1].token}</field>    <!-- 空校验 -->
  </row>
</datatable>

<!-- 正确：写明具体的期望字面值 -->
<datatable name="LoginAPI_verify">
  <row id="V001">
    <field name="token">demo_token_123</field>         <!-- 真正断言 -->
  </row>
</datatable>
```

**允许：UI 模型的 _verify 表中引用 ${Return[-N]}（N >= 2 或跨模型）**

UI verify 的实际值从页面元素读取（不从 Return 取），期望值引用前序步骤的
Return 做跨源比对，这是合法的断言。

```xml
<!-- 允许：UI verify 的期望值引用前序步骤结果做跨源比对 -->
<datatable name="PageDisplay_verify">
  <row id="V001">
    <field name="displayToken">${Return[-2].token}</field>  <!-- 页面值 vs 接口值 -->
  </row>
</datatable>
```

**判断规则**：
- verify 模型的 `__model_type__` 为 `interface` 或 `database` → 禁止 `${Return[-1]}`
- verify 模型的 `__model_type__` 为 `ui` → 允许（实际值来源不同）

### 4.4 内置函数（v11.0.0）

支持 `${函数名(参数...)}` 格式的内置函数调用，运行时动态求值。

**v11.0.0 新增 5 个文本处理函数，当前共 15 个函数**（清单以 `rodski/data/builtin_functions.py` 的注册表为准）。

#### 4.4.1 支持的内置函数清单

**数据生成**（每次求值都不同 → 不可写在 Case XML `data` 属性，见规则 5）：
- `random(type, ...)` - 生成随机数据
- `date(type, ...)` - 获取时间数据
- `timestamp()` - Unix 时间戳（秒）
- `timestamp_ms()` - Unix 时间戳（毫秒）
- `timestamp36()` - 毫秒时间戳的 36 进制大写

**文本处理**（纯函数 → 可写在 Case XML `data` 属性）：
- `encodeURI(value)` / `encodeURIComponent(value)` - URL 编码
- `decodeURI(value)` - URL 解码
- `toUpperCase(text)` / `upper(text)` - 转大写（`upper` 为旧名，保留兼容）
- `toLowerCase(text)` / `lower(text)` - 转小写（`lower` 为旧名，保留兼容）
- `toString36(number)` - 转 36 进制（大写）
- `urlencode(value)` - `encodeURI` 的旧名，保留兼容
- `concat(str1, str2, ...)` - 字符串拼接（推荐用模板语法代替）

#### 4.4.2 `random(type, ...)` 可用 type

| type | 参数 | 说明 |
|------|------|------|
| `int` | min, max 或 length（单参数=位数） | 随机整数 |
| `float` | min, max, precision（默认2） | 随机浮点数 |
| `str` | length（默认8） | 随机字母数字串 |
| `digits` | length（默认6） | 纯数字串 |
| `phone` | 无 | 随机中国手机号 |
| `email` | 无 | 随机邮箱 |
| `choice` | 候选值列表 | 随机选取一个 |
| `uuid` | 无 | UUID v4 |

#### 4.4.3 `date(type, ...)` 可用 type

| type | 参数 | 说明 |
|------|------|------|
| `now` | format（可选） | 当前日期时间 |
| `today` | format（可选） | 当前日期 |
| `time` | format（可选） | 当前时间 |
| `timestamp` | 无 | Unix 时间戳（秒） |
| `timestamp_ms` | 无 | Unix 时间戳（毫秒） |
| `offset` | 偏移值, format（可选） | 日期偏移（数字=天，数字+h=小时） |

#### 4.4.4 新增函数使用示例

```xml
<!-- 1. URL 编码（高频场景） -->
<field name="_url">/api/list?store=${encodeURI(${storeId})}&amp;limit=50</field>

<!-- 2. 唯一编号生成（分步）—— 时间戳取自数据表，纯函数部分写在用例里 -->
<!--    data.sqlite 字段值： -->
<!--    orderId: ORD_${date(timestamp, %Y%m%d)}_${random(digits, 4)} -->
<!--    用例里再做纯函数加工： -->
<test_step action="set" model="" data="base36=${toString36(${Return[-1].orderId})}"/>
<test_step action="set" model="" data="uniqueId=${toUpperCase(${base36})}"/>

<!-- 3. 字符串拼接（现有能力） -->
<field name="orderId">ORD_${date(today, %Y%m%d)}_${random(digits, 4)}</field>
<!-- 输出示例：ORD_20260831_3847 -->

<!-- 4. URL 解码 -->
<field name="decodedUrl">${decodeURI(${encodedUrl})}</field>
```

> 注意示例 2：`${date(...)}` / `${random(...)}` 是**数据生成类**，不能写在 Case XML 的
> `data` 属性里（规则 5），所以它们留在数据表字段值中；`set` 只做纯函数加工。

#### 4.4.5 字符串拼接

`${...}` 可出现在字段值任意位置，前后可拼接静态文本，多个函数可串联：

```
user_${random(int, 4)}                    → user_3847
ORD_${date(today, %Y%m%d)}_${random(digits, 4)}  → ORD_20260512_3847
test_${random(str, 6)}@example.com        → test_aB3kP9@example.com
/api/search?q=${encodeURI(${keyword})}    → /api/search?q=hello%20world
```

#### 4.4.6 约束

1. **函数清单受控** — 当前 15 个函数（数据生成 5 + 文本处理 10），新增需架构评审
2. **不支持嵌套**（v11.0.0 强化） — `${encodeURI(${toUpperCase(x)})}` 不允许，使用分步 `set` 代替：
   ```xml
   <!-- 错误：嵌套函数 -->
   <!-- <field name="value">${encodeURI(${toUpperCase(${storeId})})}</field> -->
   
   <!-- 正确：分步替代 -->
   <test_step action="set" model="" data="upperStoreId=${toUpperCase(${storeId})}"/>
   <test_step action="set" model="" data="encodedStoreId=${encodeURI(${upperStoreId})}"/>
   ```
3. **纯函数无副作用** — 内置函数只生成值，不修改任何状态
4. **运行时求值** — 每次执行时重新计算，不缓存结果
5. **按确定性分域使用**（v11.3.0 明确） — 内置函数分两类，**能写在哪儿取决于它是否可复现**：

   | 类别 | 函数 | 性质 | 数据表字段值 | Case XML `data` 属性 |
   |------|------|------|:---:|:---:|
   | **数据生成** | `random` `date` `timestamp` `timestamp_ms` `timestamp36` | 每次求值都不同 | ✅ | ❌ **报错** |
   | **纯函数** | `encodeURI` `decodeURI` `toUpperCase` `toLowerCase` `toString36` `upper` `lower` `concat` | 同输入同输出 | ✅ | ✅ |

   **数据生成类为什么不能在 Case XML**：用例会不可复现。`loop` 每轮重新解析、失败重跑重新解析，同一用例两次跑出不同的值；而 `result.xml` 的步骤记录里 `data` 是空的（不落解析后的值），事后无从对账。它们应写在 data.sqlite 字段值中 —— 数据行本就是「执行时现取」的语义。

   **纯函数类为什么必须能在 Case XML**：`set` 的表达式只能来自 Case XML 的 `data` 属性（§4.4.4 示例 2/3、§4.4.6 规则 2 的分步写法都依赖它）。禁掉等于砍掉 v11.0.0 的表达式能力。

   对未注册的函数名（如 `${randomm(...)}`）本层不报错 —— 那是普通文本，见 §6.7.6_OLD_CASE_FAILURE_GUIDE 的说明。
6. **解析优先级** — `${Return[N]}` 优先于内置函数，内置函数优先于 `${var}` 变量引用
7. **转义** — 需要字面量 `${` 时使用 `$${` 转义（`$${random(int, 1, 9)}` 不会被当作调用，也不会因规则 5 报错）

### 4.5 数组路径访问（v11.0.0）

`${Return[-1]}` 引用支持数组访问语法，用于从接口返回值中提取数组元素。

#### 4.5.1 支持的语法

| 语法 | 说明 | 示例 |
|------|------|------|
| `[n]` | 数组下标（0-based，支持负索引） | `${Return[-1].data[0].name}` |
| `.first()` | 取第一个元素（等价 `[0]`） | `${Return[-1].data.first().id}` |
| `.last()` | 取最后一个元素（等价 `[-1]`） | `${Return[-1].items.last().price}` |
| `.length` | 数组长度（返回整数） | `${Return[-1].data.length}` |

#### 4.5.2 使用示例

```xml
<!-- 场景 1：查列表取第一个元素 -->
<test_step action="send" model="ListBrands" data="D001"/>
<test_step action="set" model="" data="brandId=${Return[-1].data.data[0].id}"/>
<!-- 或使用 .first() 简写 -->
<test_step action="set" model="" data="brandId=${Return[-1].data.data.first().id}"/>

<!-- 场景 2：数组长度判断（结合断言操作符） -->
<test_step action="send" model="ListBrands" data="D001"/>
<test_step action="verify" model="ListBrands_verify" data="V001"/>
<!-- _verify 表中：data.data.length 字段值为 {"$gt": 0} -->

<!-- 场景 3：多级嵌套 -->
<test_step action="send" model="GetOrders" data="D001"/>
<test_step action="set" model="" data="firstProductId=${Return[-1].orders[0].items.first().productId}"/>

<!-- 场景 4：取最后一个元素 -->
<test_step action="send" model="GetHistory" data="D001"/>
<test_step action="set" model="" data="latestTimestamp=${Return[-1].records.last().timestamp}"/>
```

#### 4.5.3 错误处理

- **索引越界**：返回 `None`（不抛异常），后续引用该值时可能导致空值错误
- **对非数组使用数组操作**：返回 `None`
- **空数组**：`.first()` 和 `.last()` 返回 `None`，`.length` 返回 `0`

```xml
<!-- 数组只有 2 个元素，访问 [5] -->
<test_step action="set" model="" data="value=${Return[-1].data[5]}"/>
<!-- value = None，后续使用会报错 -->

<!-- 正确做法：先判断长度 -->
<test_step action="verify" model="Response_verify" data="V001"/>
<!-- V001: data.length 字段值为 {"$gte": 6} -->
<test_step action="set" model="" data="value=${Return[-1].data[5]}"/>
```

### 4.6 断言操作符（v11.0.0）

`verify` 关键字支持断言操作符，用于非等值比较（数值比较、包含检查）。

#### 4.6.1 支持的操作符（5 个）

**数值比较**（4 个）：
- `$gt` - 大于 (greater than)
- `$gte` - 大于等于 (greater than or equal)
- `$lt` - 小于 (less than)
- `$lte` - 小于等于 (less than or equal)

**包含检查**（1 个）：
- `$contains` - 字符串包含或数组包含元素

#### 4.6.2 使用方式

操作符写在 `_verify` 数据表的字段值中，格式为 JSON 对象（单键字典）：

```sql
-- data.sqlite: ListBrands_verify 表
INSERT INTO rs_field (row_id, field_name, field_value) VALUES
  (1, 'data.data.length', '{"$gt": 0}'),        -- 数组长度 > 0
  (2, 'count', '{"$gte": 10}'),                 -- 计数 >= 10
  (3, 'price', '{"$lte": 1000}'),               -- 价格 <= 1000
  (4, 'names', '{"$contains": "TestBrand"}');   -- 数组包含指定元素
```

#### 4.6.3 使用示例

```xml
<!-- 场景 1：接口返回数组非空判断 -->
<test_step action="send" model="ListBrands" data="D001"/>
<test_step action="verify" model="ListBrands_verify" data="V001"/>
<!-- V001: data.data.length = {"$gt": 0} -->

<!-- 场景 2：数值范围检查 -->
<test_step action="send" model="GetProduct" data="D001"/>
<test_step action="verify" model="GetProduct_verify" data="V001"/>
<!-- V001: data.price = {"$gte": 100}, data.stock = {"$lte": 1000} -->

<!-- 场景 3：字符串包含 -->
<test_step action="send" model="GetNames" data="D001"/>
<test_step action="verify" model="GetNames_verify" data="V001"/>
<!-- V001: names = {"$contains": "TestBrand"} -->

<!-- 场景 4：数组包含元素 -->
<test_step action="send" model="GetIds" data="D001"/>
<test_step action="verify" model="GetIds_verify" data="V001"/>
<!-- V001: ids = {"$contains": 123} -->
```

#### 4.6.4 约束

1. **单操作符限制** — 每个字段值只能包含一个操作符，不支持 `$and` / `$or` / `$not` 组合
2. **类型要求** — 数值操作符要求可转数值类型，`$contains` 要求字符串或数组
3. **不支持嵌套** — 操作符值必须是字面量，不支持嵌套操作符
4. **字面量期望值** — 操作符右侧必须是具体值，不支持 `${Return[-1]}` 等引用（避免自引用）

```xml
<!-- 正确：操作符 + 字面量 -->
<field name="count">{"$gt": 0}</field>

<!-- 错误：操作符组合 -->
<!-- <field name="count">{"$gte": 10, "$lte": 100}</field> -->

<!-- 错误：嵌套操作符 -->
<!-- <field name="count">{"$gt": {"$add": 5}}</field> -->

<!-- 正确替代：多个字段分别验证 -->
<field name="count_gte">{"$gte": 10}</field>
<field name="count_lte">{"$lte": 100}</field>
```

### 4.7 部分字段匹配（v11.0.0）

`verify` 步骤支持 `match_mode` 属性，控制字段匹配策略。

#### 4.7.1 match_mode 属性

- `match_mode="strict"`（默认）— 严格模式，`_verify` 表必须包含模型的所有字段
- `match_mode="subset"` — 子集模式，只校验 `_verify` 表中声明的字段，忽略其他字段

#### 4.7.2 使用场景

**严格模式**（默认）：适用于响应结构稳定、需要全字段校验的场景。

```xml
<!-- 严格模式（默认）：必须验证所有模型字段 -->
<test_step action="verify" model="Login" data="V001"/>

<!-- Login_verify 表必须包含 Login 模型的所有字段 -->
<!-- 否则报错：字段 'xxx' 在验证数据行 'V001' 中缺失 -->
```

**子集模式**：适用于只关心部分字段、响应包含大量冗余字段的场景。

```xml
<!-- 子集模式：只验证部分字段 -->
<test_step action="verify" model="Login" data="V001" match_mode="subset"/>
```

```sql
-- Login_verify 表（子集模式）
-- 只声明关心的字段，响应中的其他字段会被忽略
INSERT INTO rs_field (row_id, field_name, field_value) VALUES
  (1, 'data.token', 'dummy_token'),       -- 只验证 token 存在
  (1, 'data.userId', 'dummy_user');       -- 只验证 userId 存在
  -- 响应中的 roles、timestamp、permissions 等字段会被忽略
```

#### 4.7.3 使用示例

```xml
<!-- 场景 1：登录响应包含大量字段，只关心 token 和 userId -->
<test_step action="send" model="Login" data="D001"/>
<test_step action="verify" model="Login" data="V001" match_mode="subset"/>
<!-- V001 只声明 data.token 和 data.userId -->

<!-- 场景 2：结合断言操作符使用 -->
<test_step action="send" model="ListBrands" data="D001"/>
<test_step action="verify" model="ListBrands_verify" data="V001" match_mode="subset"/>
<!-- V001 只声明 data.data.length = {"$gt": 0}，不验证具体元素内容 -->

<!-- 场景 3：严格模式（默认）保持向后兼容 -->
<test_step action="verify" model="GetProduct" data="V001"/>
<!-- V001 必须包含 GetProduct 模型的所有字段 -->
```

#### 4.7.4 约束

1. **默认向后兼容** — 不指定 `match_mode` 时默认 `strict`，保持 v10 行为
2. **仅适用于 verify** — `match_mode` 属性只对 `verify` 关键字有效，其他关键字忽略
3. **字段存在性检查** — `subset` 模式下，`_verify` 表中声明的字段必须在模型中存在（否则跳过该字段）
4. **不改变比较逻辑** — 两种模式使用相同的比较逻辑（等值或断言操作符），只影响迭代策略

---

## 5. 当前关键字清单（17 个）

```
SUPPORTED = [
    "close", "type", "verify", "wait", "navigate", "launch",
    "assert", "evaluate", "screenshot",
    "upload_file", "clear", "get_text", "get",
    "send", "set", "DB", "run",
]
```

加上兼容关键字：`check`（等同 `verify`）。

**设计原则**：关键字数量应保持精简，新增关键字前需评估是否可以通过现有批量模式（数据表字段值）实现。

**场景化关键字**：`navigate` 和 `launch` 功能完全相同，在计数中算作一个关键字（见 §1.3）。

---

## 6. 目录结构约束（强制）

### 6.1 产品目录层级

```
product/                           ← 产品根目录（顶层）
└── {测试项目名}/                   ← 测试项目（如 DEMO）
    └── {测试模块名}/               ← 测试模块/业务（如 demo_site）
        ├── case/                  ← 测试用例 XML 文件
        │   └── *.xml
        ├── model/                 ← 模型 XML 文件
        │   └── model.xml
        ├── fun/                   ← 代码工程目录（run 关键字使用）
        │   └── {工程名}/
        │       └── *.py
        ├── data/                  ← 测试数据 + 全局变量
        │   ├── globalvalue.xml    ← 全局变量（固定文件名）
        │   └── data.sqlite        ← 唯一测试数据文件（必须）
        ├── plan/                  ← 测试计划 XML 文件
        │   └── *.xml
        ├── result/                ← 测试结果 XML（框架自动生成）
        │   └── result_*.xml
        ├── perf/                  ← 可选：压测预编译产物（kind=load 时生成）
        └── knowledge/             ← 可选：首次写入漫游测试地图时自动生成
            ├── test_map.json
            └── test_map.json.lock
```

### 6.2 层级说明

| 层级 | 说明 | 示例 |
|------|------|------|
| product/ | 产品根目录，固定名称，是最顶层目录 | `product/` |
| 测试项目 | 按产品/项目组织，可有多个 | `DEMO/`、`ERP/` |
| 测试模块 | 按业务模块划分，可有多个 | `demo_site/`、`user_module/` |
| 标准文件夹 | 测试模块的 6 个固定命名目录；按能力按需存在 | `case/`、`model/`、`fun/`、`data/`、`plan/`、`result/` |

### 6.3 固定文件夹职责

| 目录 | 职责 | 文件类型 |
|------|------|---------|
| `case/` | 存放测试用例定义 | `*.xml`（符合 case.xsd） |
| `model/` | 存放页面/接口模型 | `model.xml`（符合 model.xsd） |
| `fun/` | 存放 run 关键字的代码工程 | `*.py` |
| `data/` | 存放数据表和全局变量 | `data.sqlite`（必须）、`globalvalue.xml`（符合 globalvalue.xsd） |
| `plan/` | 存放测试计划定义 | `*.xml`（符合 plan.xsd） |
| `result/` | 存放测试执行结果 | `result_*.xml`（符合 result.xsd，框架自动生成） |
| `perf/` | 性能压测功能专属的预编译产物目录，可选 | `{plan_id}.py`、`{plan_id}.py.meta` |
| `knowledge/` | 漫游测试功能专属的知识目录，首次写入时自动创建，可选 | `test_map.json`、`test_map.json.lock` |

`case/`、`model/`、`fun/`、`data/`、`plan/`、`result/` 是标准模块布局中的 6 个固定目录名，但当前 `directory_structure` 合规硬检查只要求 `case/`、`model/`、`data/`。`fun/` 在使用 `run` 工程时需要，`plan/` 在按计划执行时需要，`result/` 由框架按输出需要生成。`perf/` 与 `knowledge/` 都是功能专属目录；尤其不得要求用户为了未启用漫游而手工创建 `knowledge/`。

### 6.4 禁止变更

- **product 必须是最顶层目录**，不可将项目/模块提升到 product 之上
- **标准文件夹名称不可更改**（case/model/fun/data/plan/result）；是否必须存在按上一节能力与合规规则判断
- **固定文件夹只出现在测试模块层级下**，不可出现在测试项目层级
- **model.xml 是唯一的模型文件名**，不可改名
- **不得把 `perf/` 或 `knowledge/` 加入 `REQUIRED_MODULE_DIRS`**；它们按功能需要生成

---

## 7. XML 文件格式约束

### 7.0 运行时 XSD 校验（强制）

框架在**读取**各类测试相关 XML 时，会按类型对照 `rodski/schemas/*.xsd` 做一次 **XML Schema 校验**（依赖 Python 包 `xmlschema`，见 `requirements.txt`）：

| 读取时机 | 文档类型 | 不符合 Schema 时 |
|---------|---------|------------------|
| 解析 `case/*.xml` | 用例 | 抛出 `XmlSchemaValidationError`（错误码 `SKI204`） |
| 解析 `data/*.xml`（不含 globalvalue） | 数据表 | 同上 |
| 解析 `data/globalvalue.xml` | 全局变量 | 同上 |
| 解析 `plan/*.xml` | 测试计划 | 同上 |
| 加载 `model/model.xml` | 模型 | 同上 |
| 写入 `result/result_*.xml` 前 | 测试结果 | 同上（保证输出符合 `result.xsd`） |

公共类 **`RodskiXmlValidator`**（`core.xml_schema_validator`）封装校验逻辑，也可在工具链中单独调用：

```python
from core.xml_schema_validator import RodskiXmlValidator

RodskiXmlValidator.validate_file("path/to/case.xml", RodskiXmlValidator.KIND_CASE)
```

校验失败时，异常信息中包含 `xml_path`、`document_kind`、`schema_path` 及 `validation_errors` 明细（若有）。

### 7.1 文件类型与 Schema 对照

| 文件类型 | Schema 文件 | 存放目录 | 说明 |
|---------|------------|---------|------|
| 用例 XML | `schemas/case.xsd` | `case/` | 用例定义（三阶段容器 + test_step） |
| 模型 XML | `schemas/model.xsd` | `model/` | 元素定位模型 |
| 数据表 XML | `schemas/data.xsd` | `data/` | 输入数据表 + 验证数据表 |
| 全局变量 XML | `schemas/globalvalue.xsd` | `data/` | 全局变量定义 |
| 测试计划 XML | `schemas/plan.xsd` | `plan/` | 测试计划定义 |
| 结果 XML | `schemas/result.xsd` | `result/` | 测试结果 + 测试摘要 |
| 漫游测试地图 JSON | 无 XSD/JSON Schema；应用层校验 | `knowledge/` | `test_map.json`，固定 `schema_version=1`；更高版本只读 |

### 7.2 Case XML 格式约束（三阶段 · 多 `test_step`）

每个 `<case>` 下**固定三个 XML 阶段容器**（XSD 顺序：`pre_process` → `test_case` → `post_process`）。启用漫游时，执行器在成功的 `test_case` 与 `post_process` 之间增加一个同步运行时阶段：

```text
pre_process → test_case → roaming（可选）→ post_process
```

漫游不是新的 XML 容器，不写入 case 文件；`post_process` 无论是否漫游都恰好执行一次。

| 阶段容器 | XSD | 说明 |
|---------|-----|------|
| `<pre_process>` | 可选（0～1 个元素） | 预处理：内层 **0 个或多个** `<test_step>` |
| `<test_case>` | **必选且恰好 1 个** | 用例阶段：内层 **至少 1 个** `<test_step>`（原「测试步骤 + 预期验证」等均写在此阶段，按顺序多条步骤） |
| `<post_process>` | 可选（0～1 个元素） | 后处理：内层 **0 个或多个** `<test_step>` |

**执行语义（框架保证）**：

- 各阶段内按 `<test_step>` 出现顺序依次执行。
- **预处理**若某步失败：跳过**用例阶段**，**仍执行后处理**（便于清理）。
- **用例阶段**若某步失败：**仍执行后处理**（关闭浏览器、回滚等清理步骤）。
- **用例阶段成功且漫游三层开关均满足**：同步执行漫游后再进入后处理；漫游发现/失败不改变基础用例 PASS/FAIL。
- **后处理**若失败：整条用例记为失败。

```xml
<?xml version="1.0" encoding="UTF-8"?>
<cases>
  <case execute="是" id="c001" title="登录测试" description="..." component_type="界面" roam="是">
    <pre_process>
      <test_step action="navigate" model="" data="GlobalValue.DefaultValue.URL/login"/>
    </pre_process>
    <test_case>
      <test_step action="type" model="Login" data="L001"/>
      <test_step action="verify" model="Login" data="V001"/>
    </test_case>
    <post_process>
      <test_step action="close" model="" data=""/>
    </post_process>
  </case>
</cases>
```

| 属性/元素 | 必需 | 说明 |
|-----------|------|------|
| `case.execute` | 是 | `是` 或 `否`，只有 `是` 才执行 |
| `case.id` | 是 | 用例唯一编号 |
| `case.title` | 是 | 用例标题 |
| `case.description` | 否 | 用例描述 |
| `case.component_type` | 否 | `界面` / `接口` / `数据库` |
| `case.roam` | 否 | `是` / `否`，默认 `否`；仅 `component_type=""` 或 `界面` 可设为 `是`，非空且非 `界面` 时抛 `SKI803` |
| `pre_process` | 否 | 预处理阶段容器；可省略或为空容器 |
| `test_case` | **是** | **每个 case 必须且仅有 1 个**；内至少 1 个 `test_step` |
| `post_process` | 否 | 后处理阶段容器 |
| `test_step`（子元素） | 每步 | `action` / `model` / `data` 与原先单行步骤含义相同 |
| `test_step.action` | 是 | 关键字名称（见第5节） |
| `test_step.model` | 否 | 模型名；DB 场景下也填写数据库模型名，由模型的 `connection` 属性指向连接组 |
| `test_step.data` | 否 | 数据引用或直接值 |

### 7.3 数据格式约束（v6.0.0）

**固定文件组织**：
- `data.sqlite` 是唯一测试数据文件（必须）
- `data.xml` / `data_verify.xml` 已废弃；若存在则运行时报错
- `globalvalue.xml` 独立维护，不进入 SQLite

**SQLite EAV 元表结构**：

| 元表 | 说明 |
|------|------|
| `rs_datatable` | 逻辑表注册（table_name = 模型名） |
| `rs_datatable_field` | 字段 schema |
| `rs_row` | 数据行（data_id） |
| `rs_field` | 字段值 |

**约束**：
- `rs_datatable.table_name` 必须与模型名一致
- 同一逻辑表所有行的字段集合必须完全一致（与 schema 一致）
- `table_kind` 为 `'data'`（输入数据）或 `'verify'`（验证数据）

**多行多列表示**：
- **多行**：在同一 `<datatable>` 中定义多个 `<row>`，每个 row 有不同的 `id`
- **多列**：在同一 `<row>` 中定义多个 `<field>`，每个 field 有不同的 `name`
- XML-only 历史数据允许不同行字段数量不同；但迁移到 SQLite 或执行严格校验时必须统一为固定字段集合

**完整示例**：
```xml
<datatables>
  <datatable name="Login">
    <!-- 第1行：管理员登录（4个字段） -->
    <row id="L001" remark="管理员登录">
      <field name="username">admin</field>
      <field name="password">admin123</field>
      <field name="userType">select【admin】</field>
      <field name="loginBtn">click</field>
    </row>
    <!-- 第2行：普通用户登录（3个字段） -->
    <row id="L002" remark="普通用户">
      <field name="username">testuser</field>
      <field name="password">test123</field>
      <field name="loginBtn">click</field>
    </row>
  </datatable>

  <datatable name="Login_verify">
    <row id="V001">
      <field name="welcomeMsg">欢迎</field>
    </row>
    <row id="V002">
      <field name="errorMsg">登录失败</field>
    </row>
  </datatable>
</datatables>
```

### 7.4 GlobalValue XML 格式约束

```xml
<?xml version="1.0" encoding="UTF-8"?>
<globalvalue>
  <group name="DefaultValue">
    <var name="URL" value="http://127.0.0.1:5555"/>
    <var name="WaitTime" value="2"/>
  </group>
</globalvalue>
```

| 属性/元素 | 必需 | 说明 |
|-----------|------|------|
| `group.name` | 是 | 变量组名，组内唯一 |
| `var.name` | 是 | 变量名，组内唯一 |
| `var.value` | 是 | 变量值 |

### 7.5 Model XML 格式约束（不变）

model.xml 格式与之前版本保持一致，仅支持完整格式（`<location>` 子节点）。简化格式已于 v5.4.0 移除。详见 `schemas/model.xsd`。

### 7.6 Result XML 格式约束

```xml
<?xml version="1.0" encoding="UTF-8"?>
<testresult>
  <summary total="2" passed="1" failed="1" pass_rate="50.0%" .../>
  <results>
    <result case_id="c001" title="登录测试" status="PASS" execution_time="2.345" .../>
  </results>
</testresult>
```

结果 XML 由框架自动生成，用户不需要手动编写。

### 7.7 Test Plan XML 格式约束（v6.3.0）

测试计划是执行配置，不是测试数据。v6.3.0 起，测试计划固定放在 `plan/*.xml`，每个 XML 文件对应一个测试计划。

**事实来源边界**：

| 信息 | 唯一事实来源 |
|------|--------------|
| 测试计划执行范围 | `plan/{测试目的}_{测试类型}.xml` |
| 用例、场景、步骤定义 | `case/*.xml` |
| 模型定义 | `model/model.xml` |
| 测试数据 | `data/data.sqlite` |
| 全局变量 | `data/globalvalue.xml` |

**强制约束**：

- `plan/` 是测试模块下的固定目录，与 `case/`、`model/`、`data/` 同级。
- 一个测试计划一个 XML 文件，禁止使用单一 `plan/plan.xml` 聚合全部计划。
- 文件名采用 `{测试目的}_{测试类型}.xml`，文件名 stem 即计划 ID。
- `<test_plan id="...">` 必须与文件名 stem 一致。
- `plan/*.xml` 必须符合 `rodski/schemas/plan.xsd`。
- plan XML 只引用 case/scenario/step，不复制 title/group/tag/step 内容。
- plan XML 不得写入 `data/data.sqlite`，不得作为测试数据加载。
- 不新增 `rs_testsuite`、`rs_test_plan`、`rs_execution_plan` 等 SQLite 计划表。
- `rodski run` 未指定计划时，优先读取 `plan/project_full.xml`。
- 若不存在 `project_full.xml` 但 `plan/*_full.xml` 只有一个，可使用该 full 计划；若存在多个 full 计划，必须提示用户显式指定 `@plan_id`。

**执行入口约束**：

| 入口 | 示例 | 执行范围来源 | 是否落盘 |
|------|------|--------------|----------|
| 显式 plan | `rodski run @project_full` | `plan/project_full.xml` | 是 |
| 临时 selector | `rodski run --tag smoke` | `case/*.xml` 中的 scenario 元数据 | 否 |

`@plan_id` 与 `--tag` / `--group` / `--exclude-tag` / `--priority` 等执行范围 selector **固定互斥**。同一次 `rodski run` 只能选择一种执行范围来源，不能做隐式合并、交集过滤或优先级裁决。

```bash
# ✅ 显式 plan 模式
rodski run @project_full

# ✅ 临时 selector 模式
rodski run --tag smoke

# ❌ 不支持：plan 与 selector 同时使用
rodski run @project_full --tag smoke
rodski run @project_full --group negative
rodski run @project_full --priority P0
```

若 selector 结果需要长期复用，必须先生成 plan XML，再以显式 plan 模式执行：

```bash
rodski plan create invoice_tax_point_smoke --kind suite --from-tag smoke
rodski run @invoice_tax_point_smoke
```

**plan kind 约束**：

| kind | 用途 |
|------|------|
| `suite` | 常规测试计划，选择执行哪些 case/scenario/step |
| `scenario_debug` | 单用例按 scenario 调试 |
| `step_debug` | 单用例按 step 调试 |

**执行优先级约束**：

```text
case XML 中 <case execute="否">
  > test_plan.execute="否"
  > plan case execute="否"
  > plan scenario execute="否"
  > plan step execute="否"
  > test_plan.default_execute
```

只要上层关闭，下层即使显式开启也不得执行。

**v6.3.0 suite plan 执行语义**：

- `rodski run @plan_id` 从当前测试模块的 `plan/{plan_id}.xml` 读取显式计划，并把选择结果传入 `SKIExecutor`；`--dry-run` 必须输出 selected / skipped / stale references，不执行关键字。
- `default_execute="是"`：suite plan 中未显式配置的 case/scenario 默认执行。
- `default_execute="否"`：只执行 plan 中显式 `execute="是"` 的 case/scenario/step；未选中的 case 返回 `SKIP`，未选中的 scenario 记录 scenario 级 `SKIP`。
- plan 中 `case` / `scenario` / `step` 的 `execute="否"` 均不得执行，并应写入可追溯的 skip reason。
- stale 引用（不存在的 case/scenario/step）必须记录在 selection / dry-run 输出中，不得导致执行崩溃。
- step 选择的 `no` 是 scenario 内直接 `<test_step>` 的 1-based 序号；v6.3.0 首版只过滤 scenario 直接子步骤，不递归选择 `if` / `loop` 内部子步骤。
- 裸 `<test_step>` 维持兼容规则：只要其所属 case 被执行，裸步骤不受 scenario 选择过滤影响。

---

## 8. 固定与动态测试步骤（架构规划）

本节描述在「Case XML 固定步骤」与「CLI/运行时插入的动态步骤」并存时的**架构原则与约束**。实现可落在分支 `feature/dynamic-case-refactor` 上，落地前以本文为准。

### 8.1 目标与边界

| 能力 | 说明 |
|------|------|
| 固定步骤 | 来自 `case/*.xml` 的 `<test_step>`，顺序与内容在运行前已知 |
| 动态步骤 | 由 CLI 指令、扩展点或运行时策略在**执行过程中**插入的、与 Case 文件非一一对应的步骤 |
| 混合执行 | 同一用例阶段内，执行序列为「固定步骤流」与「动态步骤」的**可组合序列**（插入位置由策略决定，例如某固定步前后、或某关键字回调后） |
| 运行时控制 | 在固定步骤**执行过程中**，允许通过外部命令（如 CLI / 服务端下发）进行**暂停**、**插入**、**终止**，以改变后续执行路径（见 8.6） |

**非目标（首版可明确不做）**：在数据表 XML 中根据「动态步骤」解析 `Return[...]`（见 8.4）。

### 8.2 推荐设计模式（保障架构清晰）

| 模式 | 用途 |
|------|------|
| **Command（命令）** | 将单步执行抽象为统一对象（如 `StepCommand`）：携带 `action` / `model` / `data` 及元数据），`SKIExecutor` 只调用「执行一步」，不区分来源。 |
| **Strategy（策略）** | **步骤来源策略**：`StaticStepSource`（解析 XML）、`DynamicStepSource`（CLI/插件/钩子注入）。执行引擎依赖策略接口，而非具体来源。 |
| **Iterator / Pipeline（流水线）** | 对外表现为**统一的步骤迭代器**：先展开固定步骤，再在约定锚点**插入**动态步骤；遍历即执行，避免在执行循环里散落 `if cli` 分支。 |
| **Template Method（模板方法）** | `_run_steps` / `execute_case` 保持「阶段 → 遍历步骤 → 执行单步」骨架不变；**变化点**下放到「如何生成下一步」的策略与插入点配置。 |
| **Facade（可选）** | CLI / GUI 入口通过薄封装统一构造「策略组合 + 执行器」，避免调用方直接操作内部列表。 |

**原则**：执行主路径**只认「步骤序列」**，不认「文件行号」；XML 与 CLI 都**适配成同一套步骤描述结构**后再进入引擎。

### 8.3 步骤编号与结果留存（双轨）

为避免「动态插入」打乱追溯，采用**双轨编号**（实现时字段名可映射到代码/result 扩展）：

| 概念 | 含义 | 典型用途 |
|------|------|----------|
| **逻辑序号（固定）** | 仅针对 Case XML 中**固定** `<test_step>` 的顺序编号（如 1…N，可按阶段分别计数或全局计数，实现时需统一一种规则并文档化） | 与用例文件对齐、**Return 正索引**若表示「第 k 个固定步骤」则与此轨对齐 |
| **运行时序号** | 实际执行顺序的单调递增序号（1…M），**包含**所有固定 + 动态步骤 | 日志、自动截图命名、未来步骤级结果明细 |

**结果 XML（`result.xsd`）**：当前以**用例级**结果为主；若需步骤级追溯，应在后续版本中扩展 schema（例如每条用例下可选 `<steps>`，子节点带 `logical`、`runtime`、`source`），且须通过 XSD 校验。**不得**在未扩展 schema 的情况下写入非约定结构。

### 8.4 Return 关键字与 `-1` 语义（过渡期约束）

- **`${Return[-1]}`**：表示**固定步骤管线**中「上一步」的返回值（与当前 `KeywordEngine._return_values` 追加语义一致），**不**跨越动态插入步去指「物理上的上一步」，除非将来明确定义并实现「动态步是否入栈」。
- **动态步骤数据表**：**暂不支持**在数据表 XML 中使用 `${Return[...]}`引用动态步骤产生的数据；若需传参，首版应通过 **GlobalValue / 显式 set** 等既有机制传递。
- **正索引 `${Return[0]}` 等**：继续表示固定返回队列中的槽位；与动态步骤混跑时，**不得**假设与「运行时序号」一一对应。

### 8.5 CLI 与扩展点（约束）

- CLI 传入的动态命令应被解析为与 Case 同构的**步骤描述**（同一套关键字与参数规则），再进入 `StepCommand` 流水线。
- 插入点（在哪些固定步前后允许插入）应有**白名单或配置**，避免任意位置插入破坏预处理/用例/后处理语义。

### 8.6 运行时控制命令：暂停、插入、终止

在**固定步骤执行过程中**，执行器应支持一类**控制命令**（来源可为 CLI、本地 GUI、或**服务端**远程下发），用于改变测试执行行为。与「普通测试步骤」不同，控制命令属于**元操作**，不占用 Case XML 中的固定 `<test_step>` 行号。

| 命令 | 语义 | 实现要点 |
|------|------|----------|
| **暂停（pause）** | 当前执行流在**安全边界**（见 8.7）停住，不再继续执行后续步骤，直至收到**继续（resume）**或**终止** | 执行循环需可中断、可恢复；暂停期间可接受新命令（如插入） |
| **插入（insert）** | 在**当前固定步骤流**中插入一条或多条**新测试步骤**，立即执行或排队执行（由策略决定） | 插入的步骤**格式与现有 `<test_step>` 一致**（`action` / `model` / `data` 语义不变）；可附带**临时** `model` 片段与**临时**数据表（内存或临时目录中的 XML），经与正式模块相同的解析与校验流程后进入引擎 |
| **终止（terminate）** | 结束当前用例或当前执行会话 | 区分**正常终止**（在**当前步骤执行完成后**停止）与**强制终止**（见 8.7） |

**插入步骤的格式约束**：

- 与 Case XML 中 `test_step` **同一套**关键字与参数模型；不得引入第二套「动态专用」语法。
- 若使用临时模型 / 数据：应在执行上下文中**注册为临时资源**（生命周期限于本次插入或本会话），避免污染磁盘上的正式 `model/`、`data/`；或写入约定临时目录并在会话结束后清理。

### 8.7 服务端命令与「当前步骤执行中」的时序（默认排队）

当**服务端**（或远程控制端）下发控制命令，而**当前测试步骤正在执行**（例如一次 `type` 批量、一次 `send`、一次 `run` 子进程尚未返回）时：

| 情形 | 默认行为 |
|------|----------|
| **一般命令**（暂停、插入、非强制的终止） | **等待当前步骤执行结束**（进入关键字后的整步执行完成）后，再处理该命令。即命令进入**队列**，按到达顺序在**步骤边界**生效。 |
| **强制终止** | **不要求**等待当前步骤自然结束；执行器应在**安全前提下**尽快中止（如取消后续步骤、关闭浏览器/会话、必要时终止子进程）。具体可中断点与资源清理顺序需在实现中明确并文档化。 |

**设计理由**：

- 步骤内部往往是对驱动、子进程、数据库事务的**原子意图**；中途打断易导致状态不一致。
- 强制终止是**显式**的例外路径，用于卡死、超时或人工紧急停止。

**执行器侧**建议抽象「步骤边界」：单步 `execute_step` 前后为**可接受控制命令**的时机；步内除非强制终止，不处理队列中的暂停/插入。

---

### 8.8 动态机制中的多模态问题判别（规划，未来实现）

在动态用例机制下，框架应支持一个“问题判别器（Issue Classifier）”接口，用于判断失败根因，服务于自动处置策略。

#### 8.8.1 输入证据（可扩展）

- 步骤上下文：`case_id`、phase、action/model/data、运行时序号
- 执行证据：错误码、异常栈、日志片段
- 界面证据：失败截图（必要时可含前后对比）
- 网络/接口证据：请求与响应摘要（状态码、关键字段）
- 历史证据：同用例最近 N 次运行结果与变化趋势

#### 8.8.2 输出分类（标准化）

- `CASE_DEFECT`：用例/数据/断言定义问题
- `ENV_DEFECT`：环境或依赖服务异常
- `PRODUCT_DEFECT`：疑似产品缺陷
- `UNKNOWN`：证据不足，需人工确认

判别输出必须包含：

- `category`（上述分类）
- `confidence`（0~1）
- `evidence_refs`（引用的日志/截图/响应证据）
- `recommended_action`（建议动作：insert/pause/terminate/escalate）

#### 8.8.3 设计约束

- 判别器是**可替换组件**：可先规则引擎，再替换为多模态 LLM。
- 若接入多模态 LLM，必须保留“证据引用 + 置信度”，禁止裸结论。
- 低置信度（如 < 0.6）不得自动执行高风险动作（如 `force_terminate`），需降级为人工确认或仅 `pause`。
- 判别结果属于“策略输入”，不直接改写原始执行结果；最终状态仍由执行器语义决定（PASS/FAIL/SKIP/ERROR）。

---

### 8.9 漫游测试执行约束（v8.3.0）

漫游是成功 `test_case` 与恰好一次 `post_process` 之间的**同步可选阶段**，不是 §8.6 的外部运行时控制命令。进入漫游必须同时满足：

1. `globalvalue.xml` 中 `Roam.Enabled=是`
2. 当前 `case.roam="是"`
3. CLI 显式使用 `rodski roam --case` 或 `rodski run --roam`

单用例命令对找不到或不满足条件的目标分别报告 `SKI801`/`SKI802`；批量 `--roam` 对不满足条件的用例静默跳过。`case.roam="是"` 仅允许 `component_type` 为空或为 `界面`，否则抛 `SKI803`。

**决策引擎**（v8.4.0 架构解耦）：`rodski/core/` 不含任何具体决策引擎实现。进程内 `on_case_pass_roam_ready` Hook 必须注入决策引擎；没有有效 Handler 时以 `stopped_reason="no_handler"` 正常结束。CLI 可通过 `--roam-engine path/to/module.py` 加载引擎模块（模块须导出 `create_engine()` 工厂函数），适用于 subprocess 场景。

**步骤执行**：`_run_roam_session()` 把每个可执行动作转换为普通 test-step 字典，并同步调用 `_run_steps([step], "漫游")`。临时资源采用“快照 → `apply_insert_resources` → `_run_steps` → `finally` 恢复”流程。漫游步骤**不得**通过运行时控制命令的 insert 通道执行。

**安全守卫**：不可逆动作和低于 `MinConfidenceToAct` 的动作只记录不执行；同一 `(action, model, data)` 不重复执行；变体数、时长、token 或成本预算耗尽只写入 `stopped_reason`，不抛异常。核心默认引擎不调用 LLM，自定义引擎可回报 token/cost usage 并受同一预算约束。

**结果边界**：漫游 finding 或执行失败均不改变基础用例 PASS/FAIL。`roam_summary` 附加到结果字典并通过 JSON formatter 透传；v8.4.0 起同时写入 `CaseReport.roam`（`RoamReport` dataclass）；XSD 已定义 `RoamSummaryType`/`RoamFindingType`，HTML 报告扩展留后续迭代。

**测试地图**：`knowledge/` 只在首次写入时自动创建。`test_map.json` 使用 `schema_version=1`；标准库 Unix/Windows 文件锁超时 5 秒；锁内重新读取、按节点 `id` 和边 `(from,to,action)` 合并，再原子替换。读取到更高 schema 版本时只读，禁止旧实现覆盖。

---

## 9. 测试分层约束

### 9.1 原则

RodSki 的测试必须严格区分为两层：

1. **单元测试**：允许使用 `pytest`
2. **验收测试**：必须使用 `rodski-demo` 编写示例用例进行验收

**强制约束**：
- 单元测试只能用于验证局部实现、边界条件、异常语义、内部数据结构
- 验收测试必须通过 `rodski-demo` 的真实 Case / Model / Data 组织方式验证完整功能链路
- 一个迭代如果只有单元测试通过、没有 `rodski-demo` 验收用例，则**不能判定为验收完成**
- 迭代需求中的 `acceptance_tests.md` 必须在 `rodski-demo` 中落地为可执行或明确预留的示例用例

### 9.2 单元测试约束

| 规则 | 说明 |
|------|------|
| 允许 `pytest` | 可用于 `rodski/tests/` 下的单元测试 |
| 关注点 | 函数/类/模块级行为验证，不替代真实验收 |
| Mock | 允许使用 `unittest.mock` |
| 断言 | 使用 `pytest` / `assert` 均可 |

### 9.3 验收测试约束

| 规则 | 说明 |
|------|------|
| **必须使用 rodski-demo** | 验收测试必须落在 `rodski-demo/` 示例工程中 |
| **必须有 Case** | 至少补充或修改 `case/*.xml` 示例用例 |
| **必须有配套模型/数据** | 涉及新能力时，必须补充 `model/`、`data/` |
| **必须体现真实链路** | 必须以关键字 + 模型 + 数据的真实执行链路进行验证 |
| **可以分阶段启用** | 若 demo 页面/接口尚未准备好，可先 `execute="否"` 预留，但不能视为“已动态验收通过” |

### 9.4 完成判定

一个迭代要判定“开发完成”，至少需要同时满足：

1. 代码实现完成
2. 单元测试通过（如有）
3. `rodski-demo` 验收示例用例已补齐
4. 可执行的 `rodski-demo` 验收用例已实际运行并通过；若存在 `execute="否"` 的预留用例，则这些用例对应能力仅视为“示例已补齐，动态验收未完成”

---

## 10. 视觉定位设计约束

### 10.1 OmniParser 作为图像坐标识别核心

**设计决策**: RodSki 使用 **OmniParser** 作为图像坐标识别的核心能力。

**架构原则**:
- OmniParser 提供页面元素的坐标和内容识别
- 多模态 LLM（Claude/GPT-4V/Qwen-VL）提供语义理解
- 视觉定位作为**定位器类型**，不是独立关键字

### 10.2 视觉定位器类型（统一格式）

视觉定位通过扩展模型 `location type` 属性实现，不新增关键字：

| 定位器类型 | 格式 | 说明 | 示例 |
|-----------|------|------|------|
| `vision` | `<location type="vision">语义描述</location>` | OmniParser + LLM 语义匹配定位 | `<location type="vision">登录按钮</location>` |
| `ocr` | `<location type="ocr">文字</location>` | OCR文字识别定位 | `<location type="ocr">登录</location>` |
| `vision_bbox` | `<location type="vision_bbox">x1,y1,x2,y2</location>` | 坐标定位（Agent 探索生成） | `<location type="vision_bbox">100,200,150,250</location>` |

### 10.3 模型定义格式

```xml
<!-- 语义定位（OmniParser + LLM 匹配） -->
<element name="loginBtn" type="web">
    <type>button</type>
    <location type="vision">登录按钮</location>
</element>

<!-- OCR文字定位 -->
<element name="loginBtn" type="web">
    <type>button</type>
    <location type="ocr">登录</location>
</element>

<!-- 坐标定位（Agent 探索后生成） -->
<element name="submitBtn" type="web">
    <type>button</type>
    <location type="vision_bbox">100,200,150,250</location>
</element>
```

**约束**：
- 使用 `<location type="类型">值</location>` 格式，与传统定位器一致
- `vision` 值为图片路径（相对于 `images/` 目录）
- `ocr` 值为要识别的文字内容
- `vision_bbox` 坐标为像素坐标（Web）或屏幕绝对坐标（Desktop）

### 10.4 使用现有关键字

视觉定位复用现有关键字，不新增 `vision_click` 等：

```xml
<!-- 使用 type 关键字 -->
<test_step action="type" model="LoginPage" data="L001"/>
```

数据表：
```xml
<row id="L001">
  <field name="loginBtn">click</field>
  <field name="username">admin</field>
</row>
```

### 10.5 Agent 与 RodSki 的职责划分

**RodSki 的职责**：
- ✅ 执行 XML 定义的操作
- ✅ 支持视觉定位器类型（vision/vision_bbox）
- ✅ 返回结构化的执行结果
- ✅ 提供工具辅助 Agent 生成 XML

**Agent 的职责**：
- ✅ 探索页面/应用（使用自己的视觉能力）
- ✅ 生成模型 XML（使用 LLM 能力）
- ✅ 决策执行策略（选择用例、插入步骤）
- ✅ 处理执行结果并调整

**协作模式**：
```
1. Agent 探索 → 发现元素和操作路径
2. Agent 生成 XML → 记录为活文档
3. Agent 调用 RodSki → 执行 XML
4. RodSki 返回结果 → Agent 分析并决策下一步
```

### 10.6 辅助工具（可选）

RodSki 可提供工具辅助 Agent 生成 XML：

```bash
# 验证模型 XML 格式
rodski validate-model model/model.xml

# 从元素信息生成模型 XML 模板
rodski generate-model --elements elements.json \
                      --model-name LoginPage \
                      --output model_template.xml
```

**注意**：这些是辅助工具，不是探索功能。探索由 Agent 完成。

1. 框架读取模型定义，识别 `type="vision"` 或 `type="vision_bbox"`
2. 调用 OmniParser 服务获取页面元素坐标
3. 使用 LLM 进行语义匹配（仅 `vision` 类型）
4. 返回目标元素坐标
5. 使用坐标驱动器执行操作（点击/输入）

### 10.7 约束规则

- ❌ 不新增 `vision_click`、`vision_input` 等关键字
- ❌ 不在 Case XML 中直接写坐标
- ✅ 视觉定位作为模型定位器类型
- ✅ 复用现有关键字（见 §5）
- ✅ 坐标信息记录在模型 XML 中

---

## 11. 桌面平台约束

### 11.1 平台标识

桌面平台使用操作系统类型作为 `driver_type`：

| driver_type | 说明 | 适用场景 |
|------------|------|---------|
| `windows` | Windows 桌面应用 | Win10/Win11 桌面自动化 |
| `macos` | macOS 桌面应用 | macOS 桌面自动化 |

移动端平台的 `driver_type` 枚举（见 `rodski/schemas/model.xsd` `DriverType`）：

| driver_type | 说明 | 适用场景 |
|------------|------|---------|
| `android` | Android 设备（Appium + UiAutomator2） | Android 真机 / AVD |
| `ios` | iOS 设备（Appium + XCUITest） | iPhone / iPad 真机 / Simulator |
| `mobile` | 平台无关移动端标记，运行期通过 `globalvalue.xml Mobile.Platform` 解析为 `android` 或 `ios` | 跨平台共用模型 |

**`mobile` 平台解析规则（v7.0.0）**：

运行期 `_resolve_mobile_platform()` 读取顺序：
1. `globalvalue.xml` `Mobile.Platform` 组变量
2. `globalvalue.xml` `DefaultValue.Platform` 变量
3. `--platform ios|android` CLI 参数（覆盖 globalvalue，最高优先级）
4. 默认回退 `android`

CLI 用法示例：
```bash
# 切换到 iOS Simulator 验收（不改 globalvalue.xml）
rodski run @ios_app_smoke --platform ios
```

### 11.2 桌面端设计原则

**核心原则**：
- ✅ 关键字统一：type/verify/launch 与 Web 平台完全相同
- ✅ 驱动分离：桌面使用 pyautogui + OmniParser 驱动
- ✅ 视觉定位为主（vision/ocr/vision_bbox）
- ❌ 不支持接口测试（`send` 关键字不适用于桌面端）

**统一关键字示例**：

```xml
<!-- Web 平台 -->
<test_step action="navigate" model="WebApp" data="L001"/>
<test_step action="type" model="LoginPage" data="T001"/>

<!-- Desktop 平台（关键字完全相同） -->
<test_step action="launch" model="DesktopApp" data="L001"/>
<test_step action="type" model="LoginPage" data="T001"/>
```

**模型定义驱动类型**：
```xml
<!-- Web 模型 -->
<element name="loginBtn" type="web">
    <location type="id">loginBtn</location>
</element>

<!-- Desktop 模型 -->
<element name="loginBtn" type="windows">
    <location type="ocr">登录</location>
</element>
```

### 11.3 vision_bbox 坐标约定

桌面场景下 `vision_bbox` 使用**屏幕绝对坐标**：

```xml
<!-- 桌面应用元素 -->
<element name="closeBtn" type="windows">
    <type>button</type>
    <location type="vision_bbox">1850,50,1900,100</location>
</element>
```

**约束**：
- 坐标为屏幕绝对像素坐标（左上角为 0,0）
- 桌面应用执行时**默认全屏**，避免窗口位置变化导致坐标偏移
- 非全屏应用需在模型中记录窗口位置信息

### 11.4 Desktop 驱动实现

桌面驱动基于 pyautogui + OmniParser：

| 功能 | 实现方式 |
|------|---------|
| 启动应用 | pyautogui 或 subprocess |
| 截图 | pyautogui.screenshot() |
| 定位元素 | vision(OpenCV) / ocr(OmniParser) / vision_bbox(坐标) |
| 点击 | pyautogui.click(x, y) |
| 输入 | pyautogui.typewrite(text) |
| 获取文字 | OmniParser OCR |

**约束**：
- 桌面驱动仅支持视觉定位器（vision/ocr/vision_bbox）
- 传统定位器（id/css/xpath）在桌面端不可用

### 11.5 移动端多设备并发约束（v11.2.0）

**核心约束（不可违反）**：

1. **默认单设备执行**：模块未配置任何 `Device*` 变量（或显式 `DeviceCount=1`）时，
   移动端行为与 v11.1.0 **逐字节相同** —— 不自动转队列、不注入并发端口。
   （v11.3.0 起，配置要求多设备时 `rodski run @plan` 会**自动转 `rodski queue`**；
   见下方「设备选择」。）
2. **一个 plan 只用一个 app 设备**：计划是调度的最小单元，**不得**把一条计划的 case/step 拆到多台设备上执行。该约束由 `PlanQueue` 的粒度**结构性保证**（队列只装 `PlanTask`，无任何 case 级发放 API），不是运行时校验。
3. **多 plan 动态领取**：多设备并行时，每台设备从队列领取**整个计划**，先跑完的设备回头领下一个。**不得**采用静态均分（预先给每台设备分配固定数量的计划）。
4. **跨平台计划不得入队**：一条计划同时需要 `android` 与 `ios` 模型时拒绝入队（`--allow-cross-platform-plan` 可显式放行）。`driver_type="mobile"` 视为**平台无关**，两种队列平台均兼容。
5. **`kind=load` 计划不得混入设备队列**：设备×计划 与 VU×时长 是两个正交的执行模型，串在一起会产生无意义的压测数据。

**`Mobile.UDID` 覆盖顺序（硬约束）**：

`--udid` 的写入**必须晚于** `--platform` 的平台 globalvalue 合并。`globalvalue_ios.xml` 自身带 `Mobile.UDID`，写早了会被静默改回文件里的设备——**不报错，只是打错机器**。实现集中在 `rodski/rodski_cli/run.py` 的 `_apply_mobile_cli_overrides()`。

**并发端口（v11.2.0）**：

`wdaLocalPort`（iOS）/ `systemPort`（Android）/ `mjpegServerPort` 的 Appium 默认值**与设备无关**（8100/8200/9100）。同机两个并发会话会**复用第一台设备的 WebDriverAgent**，表现为随机的元素定位失败。故**显式指定 UDID 时**必须按 UDID 分槽注入端口（`mobile_port_slot()`，基址 + 10×槽位）；**未指定 UDID 时不得注入**（保持单设备路径不变）。

**设备选择（v11.2.0 起，v11.3.0 扩展为执行层配置）**：

- 设备发现不得回落到 `devices[0]`。发现 0 台设备 → **硬报错并给出排查提示**，非 0 退出。
- 显式给 `--devices` 却给不出 `--platform` → **报错**，不得探测猜测（Android UDID 给 iOS 用不会报错，只会打错机器）。
- 「用几台、什么类别的设备」是**用例执行层配置**，写在模块 `data/globalvalue.xml`
  （或平台专属 `globalvalue_<platform>.xml`）的 `Mobile` 组里，随用例/计划一起版本化：

  | 变量 | 取值 | 语义 |
  |---|---|---|
  | `DeviceCount` | 正整数 | 期望设备数。**不写 = 用上全部发现的设备**（与 v11.2.0 逐字节相同） |
  | `DeviceMix` | `real,simulator` | 组合偏好，逗号分隔、**顺序即优先级**。是偏好不是门槛 |
  | `DeviceScope` | `all`\|`real`\|`simulator` | 只在某个设备类别里挑 |
  | `DeviceList` | UDID 或设备名列表 | 显式设备池，给定时跳过自动发现 |

  设备条目可以是 **UDID 或设备名**（设备名在同一个 target 上稳定，UDID 换台机器就失效）。
  Android 侧的类别由 adb serial 前缀判定（见下方「Android 设备发现」）。

- **零设备是唯一的硬失败**：发现结果为空才报错。数量不足、组合凑不齐、
  `DeviceScope` 过滤后为空 —— 一律**降级并打印 `[WARN]`**，交回过滤前的设备池继续执行。
  用户要求原话：「至少有一个模拟器或真机可以执行情况下就可以自动执行」。
  **不得**为凑组合而拒绝执行，也**不得**静默降级。
- `rodski run @plan` 检测到 `Mobile` 组里有非默认设备配置（`DeviceCount>=2`、
  `DeviceMix`、`DeviceScope`、`DeviceList` 任一）时，**自动转 `rodski queue`** 调度
  （复用同一条 handle，不复制调度逻辑）。`--udid` 或 `--no-queue` 显式退出该转换
  —— 点名一台设备就是不要并行。写死 `DeviceCount=1` 等同不写，**不得**触发转换。
- 显式设备池优先于自动发现；`--devices` CLI 覆盖优先于 `DeviceList` 配置。
- **未写 `DeviceMix` 时真机优先**（v11.3.0）：真机是更稀缺、更接近真实用户的资源，
  插上就该用上。若按发现顺序截断，本机 20+ 台模拟器会把真机挤出前 N 台 ——
  配置里明明有真机可用，实际一台都没用上。故无 `mix` 时排序键为
  （真机在前，同类内已就绪的在前）。`DeviceScope=simulator` 是显式排除真机，
  该优先级**不得**越过 scope。
- 模拟器排序必须**优先取已就绪的**（`Booted` 优先于 `Shutdown`）：本机常有 30+ 台
  Shutdown 模拟器，按枚举序截断会挑到需要现 boot 的那几台。

**iOS 设备发现必须覆盖真机（v11.3.0）**：

`discover_devices("ios")` 必须**同时**枚举模拟器（`simctl`）与真机（`devicectl`）。
只用 `simctl` 会把 USB 真机完全排除在自动发现之外，而「真机 + 模拟器同机混跑」
是常规场景 —— 真机不该被迫由调用方手动喂 UDID。

- `devicectl` 的输出必须读 `--json-output` 写出的 **JSON 文件**。stdout 面向人眼、
  Apple 不保证跨版本稳定，**不得**解析 stdout。
- 真机过滤条件：`platform == iOS` + `reality == physical` +
  `transportType == wired` + `pairingState == paired`。
- **`tunnelState` 不得作为可用性判据**：开发者模式刚打开、CoreDevice 隧道尚未建立
  时它是 `disconnected`；开发者模式**关闭**时它同样是 `disconnected` —— 两者无法
  靠 tunnelState 区分，用它过滤会把正常设备误杀。
- `devicectl` 不可用（未装 / 无真机）时必须**静默降级**为「只有模拟器」，
  不得报错 —— 只跑模拟器的既有环境不受影响。
- `simctl` 枚举必须**只保留 iOS 运行时**：同一份输出里还有 watchOS / tvOS 模拟器
  （本机有十几台 Apple Watch），它们装不了 iOS 应用，混进设备池会让
  `DeviceMix=simulator` 选中一台注定建不起会话的设备。

**Android 设备发现（v11.3.0）**：

`adb` 对实体设备与 AVD 用的是同一套通道，但两者在混跑里是**不同类别**，
`DeviceMix=real,simulator` 依赖这个区分才有意义。

- 判定**必须**按 adb serial 前缀：`emulator-`（如 `emulator-5554`）是 AVD，
  其余（`JTK5T19929003495`、`192.168.1.9:5555`）是实体设备。
- **不得**用 `model:` / `product:` 限定符或设备名当判据 —— 那些由设备端上报，
  换镜像或改名就没了；serial 的形式由 adb 保证。
- **不得**把所有 adb 设备一律标成真机：那会让 AVD 在 `--list-devices` 里显示成
  `[真机]`，混跑配置永远凑不出「一台真机 + 一台模拟器」。

**异构设备混跑（v11.3.0）**：

真机与模拟器**平台相同但设备类别不同**，走 Appium 内部两条不同的 XCUITest 路径
（真机需签名并部署 WebDriverAgent）。混跑是比双模拟器更强的验收，且必须验证：

- 两台设备都被实际调度到（不得出现「给两台但只用一台」）；
- 跨设备计划的时间区间**重叠 > 5s**（串行不可能产生重叠，这是并行唯一诚实的证据）；
- 真机与模拟器拿到**不同的并发端口槽**（iOS 同槽会复用对方的 WDA，Android 同槽会
  复用对方的 UiAutomator2 会话端口，均表现为偶发的建会话/定位失败）；
- 真机至少完整执行 1 个计划（真机链路真实生效，不是空跑）。

真机首次跑 XCUITest 需现编译并部署 WDA（数分钟），验收脚本必须把这次预热放在
**计时窗口之外**，否则测到的是「首次部署」而不是「调度」。

Android 侧另有一条易误判的失败：被测 App 的 `API_BASE_URL` 是**编译期常量**
`http://127.0.0.1:8000`，设备上的 `127.0.0.1` 不是宿主机，必须对**每一台**设备
各做一次 `adb reverse`。漏掉任何一台，那台上的用例会在登录页超时失败，而错误
信息看起来像「应用 bug」。设备侧端口固定 8000（改不了），宿主机侧端口可变 ——
脚本据此与占用 8000 的其它服务共存。

详见 `.pb/specs/v11.2.0-multi-device-plan-queue-design.md`。

**移动端导航的两条硬约束（v11.3.0，混跑实地暴露）**：

1. **`navigate app://android/...` 内部的 adb 调用必须带 `-s <serial>`**。
   `AppiumDriver.start_app` 走 `adb shell am start` —— 这是**独立于 Appium session
   的第二条通道**，adb 不知道当前 session 绑定的是哪台设备。多设备同时在线时，
   不带 `-s` 会被 adb 直接拒绝：

   ```
   $ adb shell am start -n com.rodski.demo/.LoginActivity
   adb: more than one device/emulator          # exit=1
   ```

   症状极具误导性：Appium 会话**建得好好的**，只有这一个跳转失效，后续表现为
   元素找不到。故 `AppiumDriver` 必须持有 `self.udid`（各平台驱动从 `kwargs["udid"]`
   写入）；无 udid 时不写 `-s`，单设备路径逐字节不变。

2. **`am start` 的退出码不可靠，且 `start_app` 失败不得被吞**。
   Activity 不存在时 `am start` 照样 `exit=0`，只在 stderr 打印 `Error type 3` ——
   判据必须是「退出码非 0 **或** stderr 命中失败标记（`Error type` /
   `does not exist` / `Permission Denial` / `SecurityException`）」。
   **不得**退化成裸的 `"Error" in stderr`：目标 Activity 已在最前时 `am start` 会打
   `Warning: ...` 且 `exit=0`，那是正常情况，宽判据会把成功的重复导航误判成失败。
   同时 `_kw_navigate` 在 `start_app` 返回假值时必须抛 `DriverError`：
   历史上它写的是 `result = start_app(...); store_return(True); return result`，
   于是日志里出现「`adb am start 失败`」与「`navigate 成功 status=OK`」相邻，
   真正的起因（没跳转）藏在几百行之前，人看到的是「元素定位失败」。

   **放大器是 `NoReset=true`**：UiAutomator2 建会话时会先查 `adb.processExists`，
   进程还在就跳过启动。于是同一台设备上的第二个计划（App 停在上一轮的页面上）
   完全依赖 `am start` 把它带回登录页 —— 这条链路一断，只有第二个计划失败，
   第一个因停在正确页面而侥幸通过。

详见 `.pb/specs/v11.3.0-real-device-mixed-demo-design.md` §9.5。

---

## 12. 流程控制：if/else 条件分支

### 12.1 设计决策

RodSki DSL 支持 `<if>/<else>` 条件分支。这是**声明式 DSL 的扩展，不是退化**。理由：
- 一个用例能看到完整业务流程，方便人类阅读
- Agent 探索结果直接沉淀到用例，不需要维护 case + 决策脚本两套
- 与 Karate/Gherkin 等业界 DSL 的条件语法一致

**核心约束**：if/else 只在 XML 结构层扩展，不污染 SUPPORTED 关键字列表。

### 12.2 XML 语法

```xml
<case id="inquiry_create" execute="是">
  <test_case>
    <test_step action="send" model="InquiryAPI" data="I001"/>
    <test_step action="verify" model="Inquiry_verify" data="V001"/>

    <if condition="element_exists(#append_dialog)">
      <test_step action="type" model="AppendDialog" data="A001"/>
    </if>
  </test_case>
</case>
```

**带 else 分支**：
```xml
<if condition="${Return[-1].msg contains '追加对话框'">
  <test_step action="type" model="AppendDialog" data="A001"/>
  <test_step action="verify" model="Inquiry_verify" data="V002"/>
<else>
  <test_step action="screenshot" data="success.png"/>
</else>
```

**多条件分支（elif）**：
```xml
<if condition="${Return[-1].status} == 200">
  <test_step action="send" model="OrderAPI" data="D001"/>
</if>
<elif condition="${Return[-1].status} == 401">
  <test_step action="send" model="LoginAPI" data="D001"/>
</elif>
<else>
  <test_step action="set" model="" data="error_msg=unknown"/>
</else>
```

**嵌套 if（最多 2 层）**：
```xml
<if condition="${total} > 0">
  <test_step action="type" model="NavMenu" data="N001"/>
  <if condition="${total} >= 3">
    <test_step action="type" model="TestForm" data="T001"/>
  </if>
</if>
```

### 12.3 条件表达式语法

| condition 语法 | 说明 | 示例 |
|-------------|------|------|
| `verify_fail` | 上一步 verify 失败 | `<if condition="verify_fail">` |
| `${Return[N].field == 值` | Return 值等于比较 | `condition="${Return[-1].status == 200"` |
| `${Return[N].field contains 文本` | Return 值包含判断 | `condition="${Return[-1].msg contains '追加'` |
| `element_exists(locator)` | 页面元素可见 | `condition="element_exists(#dialog)` |
| `element_not_exists(locator)` | 页面元素不可见 | `condition="element_not_exists(.toast-error)` |
| `text_contains(文本)` | 页面包含文字 | `condition="text_contains('成功')` |
| `text_not_contains(文本)` | 页面不包含文字 | `condition="text_not_contains('失败')` |
| `AND` / `OR` | 逻辑组合 | `condition="verify_fail AND element_exists(#dialog)` |

**Locator 格式**：`type=value`，如 `#dialog`（CSS）、`.error`（class）、`xpath=//button[@id='btn'`、纯 CSS 选择器。

### 12.4 执行语义

1. **解析阶段**：`<if>/<else>` 作为结构容器解析为 `{'type': 'if', 'condition': '...', 'steps': [...], 'else_steps': [...]}`
2. **执行阶段**：条件评估 → True 执行 `<test_step>` 分支，False 执行 `<else>` 分支
3. **条件评估失败**：条件无法解析或评估出错时，打印友好警告 + 截图，跳过该条件块，继续下一步

### 12.5 条件评估失败时的 Agent 提示

框架在以下情况给出详细提示：
- 条件语法无法解析
- 条件依赖的页面元素定位失败
- 条件引用的 Return 值不存在

```text
[IF] ⚠️ 条件无法评估: text_contains('追加对话框')
   错误: page_text() 返回 None
   截图: result/.../condition_failed_xxx.png
   页面URL: https://...
   建议:
   1. 检查条件语法是否正确
   2. 确认页面是否已加载
   3. 考虑使用 element_not_exists() 兜底
   4. 插入 cleanup 步骤重试
```

### 12.6 约束规则

1. `<if>` 容器**必须有** `condition` 属性
2. `<else>` 是可选的，最多出现一次，紧跟 `<if>` 或 `<elif>` 后
3. `<elif>` 可出现 0～n 次，紧跟 `<if>` 后、`<else>` 前
4. `<if>` 内可嵌套 `<if>`，**最多 2 层**（内层 if 不可再嵌套，XSD 强制校验）
5. 条件表达式**不超过 200 字符**
6. 条件不评估为 True 也不评估为 False 时，**默认 False**（不执行）

---

## 13. 智能等待机制

### 13.1 设计目标

自动处理 UI 元素的加载延迟，提高测试用例的稳定性和容错性。

### 13.2 工作原理

智能等待机制在 BaseDriver 层实现，所有驱动自动继承：

- **首次立即尝试**：定位元素时首次不等待，快速响应
- **失败后自动重试**：如果失败，按配置间隔重试（默认 30 次，间隔 300ms）
- **元素出现立即返回**：一旦元素出现，立即停止重试并执行后续操作
- **超时后返回失败**：达到最大重试次数后返回 None

### 13.3 配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `smart_wait_enabled` | `True` | 启用/禁用智能等待 |
| `smart_wait_max_retries` | `30` | 最大重试次数 |
| `smart_wait_retry_interval` | `0.3` | 重试间隔（秒）|
| `smart_wait_log_retry` | `True` | 记录重试日志 |

**配置方式 1：通过 config.json**
```json
{
  "smart_wait_enabled": true,
  "smart_wait_max_retries": 30,
  "smart_wait_retry_interval": 0.3,
  "smart_wait_log_retry": true
}
```

**配置方式 2：通过代码**
```python
from rodski.core.config_manager import ConfigManager

config = ConfigManager()
config.set("smart_wait_max_retries", 50)
config.set("smart_wait_retry_interval", 0.5)
```

### 13.4 使用场景

- ✅ 页面加载较慢的 Web 应用
- ✅ 动态渲染的 UI 元素（React、Vue 等前端框架）
- ✅ 移动应用的异步加载
- ✅ 桌面应用的窗口切换
- ✅ 网络延迟导致的元素延迟出现

### 13.5 性能说明

- **快速响应元素**：无额外延迟（首次立即尝试）
- **慢速加载元素**：最多等待 9 秒（30 × 0.3s）
- **总执行时间**：实际等待时间 = 元素出现时间（≤ 最大等待时间）

**示例：**
- 元素立即存在：0ms 延迟
- 元素 1 秒后出现：约 1 秒等待
- 元素不存在：9 秒超时

### 13.6 与现有机制的关系

| 机制 | 层级 | 职责 | 触发时机 |
|------|------|------|---------|
| **智能等待** | 驱动层 (BaseDriver) | 元素定位的自动重试 | 调用 `locate_element_with_retry()` 时 |
| **KeywordEngine 重试** | 关键字层 | 关键字执行的重试（处理异常） | 关键字执行失败时 |
| **wait 关键字** | 用例层 | 显式等待固定时间 | 用例中使用 `<test_step action="wait">` |

**职责分离：**
- 智能等待：解决"元素尚未加载"问题
- KeywordEngine 重试：解决"临时异常"问题（网络抖动、StaleElement 等）
- wait 关键字：解决"需要明确等待"问题（动画完成、数据处理等）

三者互补，不冲突。

### 13.7 实现细节

**核心方法：**
```python
def locate_element_with_retry(
    self,
    locator_type: str,
    locator_value: str
) -> Optional[Tuple[int, int, int, int]]:
    """定位元素（带智能等待）"""
    # 读取配置
    enabled = self.config.get("smart_wait_enabled", True)
    max_retries = self.config.get("smart_wait_max_retries", 30)
    retry_interval = self.config.get("smart_wait_retry_interval", 0.3)
    
    # 首次立即尝试
    bbox = self.locate_element(locator_type, locator_value)
    if bbox is not None:
        return bbox
    
    # 重试循环
    for attempt in range(1, max_retries + 1):
        time.sleep(retry_interval)
        bbox = self.locate_element(locator_type, locator_value)
        if bbox is not None:
            return bbox
    
    return None
```

**便捷方法自动使用：**
- `click_element()` → 调用 `locate_element_with_retry()`
- `type_at_element()` → 调用 `locate_element_with_retry()`
- `get_element_text()` → 调用 `locate_element_with_retry()`
- `get_element_center()` → 调用 `locate_element_with_retry()`

### 13.8 日志输出

**DEBUG 级别（重试过程）：**
```
Element not found, starting smart wait: id=submit-btn, max_retries=30, interval=0.3s
Element found after 5 retries: id=submit-btn
```

**WARNING 级别（最终失败）：**
```
Element not found after 30 retries (9.0s): id=submit-btn
```

### 13.9 约束规则

- ❌ 不修改 `locate_element()` 接口（保持向后兼容）
- ✅ 新增 `locate_element_with_retry()` 方法
- ✅ 便捷方法（`click_element` 等）自动使用智能等待
- ✅ 直接调用 `locate_element()` 不触发智能等待（用于特殊场景）
- ✅ 所有驱动（Playwright、Appium、Desktop 等）自动继承智能等待能力
- ✅ 配置参数可在运行时动态调整

### 13.10 最佳实践

**推荐做法：**
1. 保持默认配置（30 次 × 0.3s = 9 秒）适用于大多数场景
2. 对于特别慢的页面，可增加 `max_retries` 或 `retry_interval`
3. 对于性能敏感场景，可减少重试次数或禁用智能等待
4. 使用 `log_retry: false` 减少日志噪音（生产环境）

**不推荐做法：**
1. ❌ 将 `retry_interval` 设置过小（< 0.1s），可能导致 CPU 占用过高
2. ❌ 将 `max_retries` 设置过大（> 100），可能导致测试执行时间过长
3. ❌ 依赖智能等待替代所有显式 `wait` 关键字（某些场景仍需显式等待）

---

## 14. 项目结构说明

### 14.1 核心框架代码

**位置**：`rodski/`

**包含模块**：
- `core/` - 核心引擎（解析器、执行器、关键字引擎）
- `drivers/` - 驱动层（浏览器、接口、数据库）
- `data/` - 数据处理模块
- `schemas/` - XML Schema 定义

**开发约束**：
- 所有核心功能修改必须保持向后兼容
- 新增关键字需要同步更新 `schemas/case.xsd`
- 修改数据格式需要更新相关文档

### 14.2 Demo 演示项目

**位置**：`rodski-demo/DEMO/`

**包含项目**：
- `demo_full/` - 完整功能演示（UI、接口、数据库、Return引用等）
- `demo_runtime_control/` - 运行时控制演示（暂停、插入、终止）

**约束**：
- Demo 项目必须简单易懂，代码量最小化
- 每个 Demo 必须有独立的 README.md 说明
- Demo 用例必须能够独立运行
- 不依赖外部真实业务系统

### 14.3 业务测试项目

**位置**：项目根目录下的独立目录（如 `cassmall/`）

**特点**：
- 独立于 Demo 项目
- 包含真实业务逻辑
- 可能依赖外部系统
- 测试数据来自真实业务

**当前项目**：
- `cassmall/thdh/` - Cassmall 同行调货业务测试

---

## 15. 功能发布测试流程

### 15.1 核心功能测试

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

### 15.2 新功能测试

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

### 15.3 回归测试

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

---

## 16. 测试数据管理

### 16.1 Demo 项目数据

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

### 16.2 业务项目数据

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

---

## 17. 持续集成建议

### 17.1 CI 流程

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

### 17.2 测试报告

**位置**：`{project}/result/`

**格式**：
- XML 格式结果文件（默认）
- HTML 报告（`rodski run case/ --report html` 或 `rodski report generate <result_dir>`）

**HTML 报告功能**（`rodski/report/`）：
- 通过率进度条 + 执行时间线可视化
- 步骤级详情表（PASS/FAIL 状态、耗时、错误信息）
- 单文件模式（`--single-file`，内联所有资源，便于邮件分发）
- 历史趋势（`rodski report trend --last 10`）
- 支持 Dark Mode

**内容**：
- 用例执行状态
- 执行时间
- 错误信息
- 截图路径（失败时）

---

## 18. 开发规范

### 18.1 代码提交前检查

- [ ] 运行 Demo 项目验证
- [ ] 更新相关文档
- [ ] 检查向后兼容性
- [ ] 添加必要的注释

### 18.2 文档更新

**必须同步更新的文档**：
- `rodski/docs/CORE_DESIGN_CONSTRAINTS.md`（核心设计约束）
- `rodski/docs/TEST_CASE_WRITING_GUIDE.md`（用例编写指南）
- `rodski/docs/DATA_FILE_ORGANIZATION.md`（数据文件组织）
- `README.md`（入门相关）

### 18.3 版本发布

**发布清单**：
1. 所有 Demo 测试通过
2. 文档已更新
3. CHANGELOG 已记录
4. 版本号已更新

---

## 19. 故障排查

### 19.1 Demo 失败排查

**常见问题**：
- 数据库未初始化 → 运行 `init_db.py`
- 端口被占用 → 检查 8000 端口
- 浏览器驱动问题 → 检查 Playwright 安装

### 19.2 业务测试失败排查

**常见问题**：
- 账号密码错误 → 检查 `globalvalue.xml`
- 网络连接问题 → 检查测试环境可访问性
- 页面元素变化 → 更新 `model.xml`

---

## 20. 最佳实践

### 20.1 Demo 项目开发

- 保持简单，一个 Demo 演示一个功能点
- 提供完整的运行脚本
- 包含详细的 README
- 数据可重复初始化

### 20.2 业务项目开发

- 独立目录，不混入 Demo
- 使用有意义的项目名称
- 配置文件与代码分离
- 定期维护测试数据

### 20.3 测试用例编写

- 用例 ID 有规律（TC001、TC002...）
- 标题清晰描述测试内容
- 添加 post_process 清理资源
- 合理使用全局等待时间

---

## Agent 契约摘要

本节汇总 Agent 在生成和消费 RodSki XML 时必须遵循的契约。

### 输入契约

| 项目 | 规范 |
|------|------|
| 用例格式 | XML（`case/*.xml`） |
| 模型格式 | XML（`model/model.xml`） |
| 数据格式 | SQLite（`data/data.sqlite`，唯一数据文件） |
| 测试计划格式 | XML（`plan/*.xml`，每个文件一个测试计划） |
| 定位器格式 | `<location type="类型">值</location>`（唯一格式，v5.4.0 起） |
| 关键字集合 | navigate / launch / type / send / verify / assert / run / DB / get / set / wait / clear / upload_file / screenshot / evaluate |

### 输出契约

| 项目 | 规范 |
|------|------|
| 结果文件 | `execution_summary.json` |
| 截图 | `result/screenshots/`（见下方截图目录规则） |
| 日志 | `result/execution.log` |
| Return 值 | 通过 `${Return[-1]}` 在数据表中引用 |

#### 截图目录规则

| 场景 | 存放路径 | 文件名格式 |
|------|---------|-----------|
| 非场景步骤（预处理/后处理/普通用例步骤） | `screenshots/` | `{caseid}_{stepindex}_{phase}_{timestamp}.png` |
| 场景步骤（`test_case` 内 `<scenario>` 容器中的步骤） | `screenshots/{caseid}_{scenarioid}_{scenariotitle}/` | `{stepindex}_{timestamp}.png` |
| 失败截图 | `screenshots/` | `{caseid}_{timestamp}_failure.png` |

**约束**：
- 场景截图必须保存在以 `{caseid}_{scenarioid}_{scenariotitle}` 命名的子目录中，同一用例的同一场景所有步骤截图集中在该目录
- 非场景步骤截图直接存放在 `screenshots/` 根目录，不创建额外子目录
- 截图路径中不允许出现 `/` 等路径分隔符（`phase` 字段中的 `/` 必须在生成文件名前替换为 `_`）

### 版本兼容性

| 框架版本 | 契约变更 |
|---------|---------|
| v5.4.0 | 移除简化定位器格式、移除 Excel 支持 |
| v5.6.0 | LLM 能力统一到 LLMClient |
| v5.7.0 | 文档叙事统一为执行引擎定位 |
| v6.3.0 | 新增 `plan/*.xml` 测试计划；显式 plan 与 selector 固定互斥 |

---

## 附录 A：核心文档不可违反约束

以下两份文档是每个迭代的实现**绝对不能违反**的约束基准：

| 文档 | 路径 | 说明 |
|------|------|------|
| **核心设计约束** | `rodski/docs/CORE_DESIGN_CONSTRAINTS.md`（本文档） | 框架核心设计决策与约束规则 |
| **用例编写指南** | `rodski/docs/TEST_CASE_WRITING_GUIDE.md` | 用例编写规范 |

### A.1 约束条款

1. **每次迭代的代码改动在上线前，必须逐一对照上述两份文档检查合规性**
2. **若发现文档描述与代码实现不一致，以文档为准**（文档是规范，代码必须服从）
3. **不允许在代码中实现与上述文档描述相矛盾的功能**
4. **新增关键字或变更关键字行为，必须同时更新** `CORE_DESIGN_CONSTRAINTS.md`
5. **新增或变更 XML Schema、XSD 约束，必须同时更新** `TEST_CASE_WRITING_GUIDE.md`

### A.2 合规检查清单

每次代码提交前，对照核心设计约束检查：

- [ ] SUPPORTED 关键字列表与文档一致（§5）
- [ ] UI 原子动作（click/hover 等）不在 SUPPORTED 中（§1.2）
- [ ] 目录结构符合 `product/项目/模块` 规范（§6）
- [ ] `directory_structure` 硬检查只要求 `case/model/data`；`fun/plan/result` 按能力需要，`perf/knowledge` 保持功能专属目录（§6）
- [ ] 测试计划只存放在 `plan/*.xml`，不进入 `data.sqlite`（§7.7）
- [ ] `@plan_id` 与 tag/group/priority selector 固定互斥（§7.7）
- [ ] 自检不使用 pytest（§9）
- [ ] 数据表格式符合规范（§7.3）
- [ ] 视觉定位器类型符合规范（§10）
- [ ] `case.roam` 仅用于 UI case，三层开关、四阶段时序和基础 PASS/FAIL 语义符合 §7.2/§8.9
- [ ] 漫游动作复用现有关键字和 `_run_steps`，未新增关键字或借用外部运行时 insert 通道
- [ ] `rodski/core/` 不含具体决策引擎实现；`on_case_pass_roam_ready` 或 `--roam-engine` 提供引擎（§8.9）
- [ ] `CaseReport.roam`（`RoamReport`）已在 `data_model.py` 声明，XSD 已定义 `RoamSummaryType`

---

*文档版本: v7.0.2 | 最后更新: 2026-05-21*

## 21. 性能压测模式约束（v8.0）

### 21.1 独立执行模式
kind=load 与 kind=suite 是完全独立的执行路径：
- 功能测试 -> SKIExecutor；性能压测 -> LocustLoadEngine
- 切换依据：plan.xml 的 kind 属性

### 21.2 压测 plan.xml 必须存在
- 禁止无 plan 的临时压测（不支持 rodski run --load --concurrency N）
- 所有负载参数只在 plan/<plan_id>.xml 的 load_profile 中声明

### 21.3 预编译产物持久化（perf/）
- 产物存放在 perf/{plan_id}.py，可纳入版本管理
- perf/{plan_id}.py.meta 记录 hash，source=manual 时跳过自动覆盖
- 产物是标准 Locust locustfile.py，可脱离 RodSki 独立运行

### 21.4 api 模式约束
- mode=api 计划只能引用 component_type=接口 的 case（违规 -> SKI602）
- 不引入新关键字（send/verify 语义不变）
- 压测时不截图，不执行 post_process 阶段

### 21.5 目录结构新增 perf/
`perf/` 是 v8.0 新增的性能压测功能专属目录，仅在需要预编译压测计划时生成；它不改变 §6 定义的标准目录布局或 `case/model/data` 硬检查。漫游的 `knowledge/` 同样遵循这一可选/自动生成先例。

## 统一运行时上下文约束（§10）

- 每个 case 独立一个 `RuntimeContext`，不跨 case 共享
- 所有关键字执行后必须写入 `history`（步骤链连续约束）
- `named` 通过 `set` 写入，通过 `get`（命名访问模式）读取
- `auto_capture` 是模型能力，规则定义在模型文件中，不在 case 步骤中声明
- 返回值来源优先级：auto_capture > get_named > evaluate > keyword_result
- `evaluate` 仅支持 Web 驱动，是低优先级逃生舱，不替代主路径能力
