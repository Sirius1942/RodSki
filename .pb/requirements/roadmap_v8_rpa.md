# RodSki v8.0 路线图 — RPA 支持

**版本**: v8.0  
**日期**: 2026-04-16  
**状态**: 待讨论  
**前置**: v7.0（Agent 优化）完成后再启动  
**来源**: 从 `roadmap_v7_design_review.md` 拆分，RPA 方向独立为 v8

---

## 目录

1. [背景与目标](#1-背景与目标)
2. [Phase 4: RPA 驱动层能力融合](#2-phase-4-rpa-驱动层能力融合)
3. [Phase 5: RPA Agent 方向](#3-phase-5-rpa-agent-方向)
4. [项目归属划分](#4-项目归属划分)
5. [全局依赖关系图](#5-全局依赖关系图)
6. [工作量总览](#6-工作量总览)
7. [风险分析](#7-风险分析)
8. [验证方案](#8-验证方案)

---

> **说明**：本文档中的 Phase 编号沿用原始设计评审中的编号（Phase 4-5），实际在 v8 版本中的排期和编号待确定。工作项编号 WI-20 ~ WI-34 保持原编号不变，便于追溯。

---

## 1. 背景与目标

### 1.1 v8 定位

v8 的核心目标：**让 RodSki 从"测试引擎"升级为"测试+自动化双栖引擎"，具备 RPA 能力。**

RPA（Robotic Process Automation）方向涉及两个层面：
1. **驱动层融合**（Phase 4）：在 rodski 核心引擎中补全 RPA 所需的系统级操作能力
2. **RPA Agent**（Phase 5）：在 rodski-agent 中新增 RPA Agent，实现跨应用流程自动化

### 1.2 为什么推到 v8

- v7 聚焦「优化 Agent」，让 test agent 和 design agent 先做好做准
- RPA 方向需要新增关键字（switch）、扩展驱动层、创建全新的 RPA Agent，工作量大且方向独立
- RPA 的落地需要更充分的需求调研和场景验证，当前标记为「待讨论」
- v7 的报告系统和 KPI 体系建成后，可以更好地度量 RPA Agent 的效果

### 1.3 核心认知

**核心认知：RPA 和自动化测试是同一套能力，测试只是多了断言。**

实际盘点后发现，`type` 关键字通过 `_execute_element_action()` 已支持 **8 种 UI 操作**（click / double_click / right_click / hover / scroll / key_press / select / drag），而非仅输入文本。加上其他关键字（navigate / launch / close / wait / get / set / send / DB / run），RPA 与测试的重叠度 **超过 90%**。

**真正的差异只有两处**：
1. 测试多了 `verify` / `assert`（断言关键字）
2. RPA 需要少量系统级操作（剪贴板、窗口切换、文件/进程），当前关键字未覆盖

### 1.4 现有能力统一矩阵

| 操作 | 关键字 / 写法 | Desktop | Playwright | RPA | 测试 |
|------|-------------|---------|------------|-----|------|
| 输入文本 | `type` field value = `admin123` | pyautogui | keyboard.type | 共用 | 共用 |
| 点击 | `type` field value = `click` | pyautogui.click | page.click | 共用 | 共用 |
| 双击 | `type` field value = `double_click` | pyautogui.doubleClick | mouse.dblclick | 共用 | 共用 |
| 右键 | `type` field value = `right_click` | pyautogui.rightClick | mouse.click(right) | 共用 | 共用 |
| 悬停 | `type` field value = `hover` | pyautogui.moveTo | page.hover | 共用 | 共用 |
| 滚动 | `type` field value = `scroll【0,300】` | pyautogui.scroll | mouse.wheel | 共用 | 共用 |
| 按键/组合键 | `type` field value = `key_press【ctrl+c】` | keyboard.hotkey | keyboard.press | 共用 | 共用 |
| 下拉选择 | `type` field value = `select【value】` | **缺实现** | page.selectOption | 共用 | 共用 |
| 拖拽 | `type` field value = `drag【target】` | pyautogui.drag | mouse drag | 共用 | 共用 |
| 打开页面 | `navigate` | N/A | page.goto | 共用 | 共用 |
| 启动应用 | `launch` | subprocess.Popen | page.goto | 共用 | 共用 |
| 关闭 | `close` | process.terminate | browser.close | 共用 | 共用 |
| 等待 | `wait` | time.sleep | time.sleep | 共用 | 共用 |
| 读取值 | `get` / `get_text` | OCR | DOM text | 共用 | 共用 |
| 设置变量 | `set` | context.named | context.named | 共用 | 共用 |
| API 请求 | `send` | -- | -- | 共用 | 共用 |
| 数据库 | `DB` | -- | -- | 共用 | 共用 |
| 上传文件 | `upload_file` | -- | input.setFiles | 共用 | 共用 |
| 清空输入 | `clear` | -- | fill('') | 共用 | 共用 |
| 截图 | `screenshot` | pyautogui | page.screenshot | 共用 | 共用 |
| 执行脚本 | `run` | subprocess | -- | 共用 | 共用 |
| **批量断言** | **`verify`** | -- | -- | **不需要** | **测试独有** |
| **视觉断言** | **`assert`** | -- | -- | **不需要** | **测试独有** |

**未覆盖的能力（需扩展）**：

| 操作 | 统一方案 | 说明 |
|------|---------|------|
| 读写剪贴板 | 扩展 `set` / `get` | `set clipboard=xxx` / `get clipboard` |
| 窗口切换 | 新增 `switch` 关键字 | 唯一新增的关键字（16->17） |
| 文件操作 | 保留 `run` | `run file_read(...)` -- 无 UI 元素概念 |
| 进程管理 | 保留 `run` | `run process_start(...)` -- 无 UI 元素概念 |

**设计原则**：
1. **不新增关键字爆炸** -- 仅新增 `switch`（16->17），其余扩展现有关键字语义
2. **有 locator 的操作 -> keyword + model**（type/get/verify 等）
3. **无 locator 的系统操作 -> set/get 扩展 或 run 兜底**
4. RPA 和测试使用 **完全相同的 Case XML 格式**，仅 `mode` 属性区分行为

---

## 2. Phase 4: RPA 驱动层能力融合

### 2.1 工作项

#### WI-20: BaseDriver 扩展 RPA 抽象方法 [M]

**目标**：在 BaseDriver 中定义 RPA 操作的统一接口。

**改动文件**：
- `rodski/drivers/base_driver.py`

**新增抽象方法**：

```python
# ---- 键盘增强 ----
@abstractmethod
def hotkey(self, *keys: str) -> None:
    """组合键操作。keys 示例: ('ctrl', 'c'), ('cmd', 'shift', 's')"""

@abstractmethod
def press_key(self, key: str, count: int = 1) -> None:
    """单键按压。key: enter/escape/tab/f1-f12/up/down/left/right 等"""

# ---- 鼠标增强 ----
@abstractmethod
def drag(self, from_x: int, from_y: int, to_x: int, to_y: int, duration: float = 0.5) -> None:
    """拖拽操作"""

@abstractmethod
def get_mouse_position(self) -> tuple[int, int]:
    """获取当前鼠标位置"""

# ---- 剪贴板 ----
@abstractmethod
def clipboard_get(self) -> str:
    """读取系统剪贴板文本内容"""

@abstractmethod
def clipboard_set(self, text: str) -> None:
    """设置系统剪贴板文本内容"""

# ---- 窗口管理 ----
@abstractmethod
def get_active_window(self) -> dict:
    """获取当前活动窗口信息 -> {title, pid, position, size}"""

@abstractmethod
def switch_window(self, title: str = None, pid: int = None) -> bool:
    """切换到指定窗口（按标题模糊匹配或 PID）"""

@abstractmethod
def list_windows(self) -> list[dict]:
    """列出所有可见窗口 -> [{title, pid, position, size}, ...]"""

# ---- 进程管理 ----
@abstractmethod
def get_process_info(self, name: str = None, pid: int = None) -> list[dict]:
    """查询进程信息 -> [{name, pid, status, memory}, ...]"""

@abstractmethod
def kill_process(self, pid: int = None, name: str = None) -> bool:
    """终止指定进程"""
```

**兼容策略**：所有新方法在 BaseDriver 中提供 `NotImplementedError` 默认实现，非 RPA 场景的 driver 不受影响。PlaywrightDriver 的剪贴板/窗口操作通过浏览器 API 实现（有限支持）。

**验证**：`pytest rodski/tests/unit/test_base_driver.py`

---

#### WI-21: DesktopDriver 对齐 RPA 抽象方法 [M]

**依赖**：WI-20

**目标**：DesktopDriver 已有大部分底层能力，对齐到新接口并补全缺失部分。

**改动文件**：
- `rodski/drivers/desktop_driver.py`

**已有能力对齐**（改签名/返回值）：

| 方法 | 现状 | 改动 |
|------|------|------|
| `hotkey(*keys)` | 已有 (keyboard.hotkey) | 对齐签名，加异常处理 |
| `press_key(key)` | 已有 (keyboard.press) | 加 count 参数 |
| `drag(from, to)` | 已有 (pyautogui.moveTo + drag) | 对齐签名 |
| `get_mouse_position()` | 已有 (pyautogui.position) | 返回 tuple |

**新增实现**：

| 方法 | 实现方案 | 依赖 |
|------|---------|------|
| `clipboard_get()` | pyperclip.paste() | pyperclip |
| `clipboard_set(text)` | pyperclip.copy(text) | pyperclip |
| `get_active_window()` | Windows: pygetwindow / macOS: AppleScript | pygetwindow (可选) |
| `switch_window(title)` | Windows: pygetwindow / macOS: osascript | 同上 |
| `list_windows()` | Windows: pygetwindow / macOS: osascript | 同上 |
| `get_process_info()` | psutil.process_iter() | psutil (已有) |
| `kill_process()` | psutil.Process(pid).terminate() | psutil (已有) |

**新增依赖**：
- `pyperclip>=1.8.0`（剪贴板，跨平台）
- `pygetwindow>=0.0.9`（窗口管理，Windows；macOS 用 subprocess + osascript）

**验证**：`pytest rodski/tests/unit/test_desktop_driver.py`

---

#### WI-22: PlaywrightDriver 有限 RPA 支持 [S]

**依赖**：WI-20

**目标**：Web 场景下的有限 RPA 支持。

**改动文件**：
- `rodski/drivers/playwright_driver.py`

**实现范围**：

| 方法 | 实现 | 说明 |
|------|------|------|
| `hotkey(*keys)` | `page.keyboard.press('Control+c')` | Playwright 键盘组合 |
| `press_key(key, count)` | `page.keyboard.press(key)` * count | 已有 key_press 重构 |
| `clipboard_get()` | `page.evaluate('navigator.clipboard.readText()')` | 需 HTTPS 或 --allow-clipboard |
| `clipboard_set(text)` | `page.evaluate(...)` | 同上限制 |
| `drag(from, to)` | `page.mouse.move + down + move + up` | 像素级拖拽 |
| 窗口/进程方法 | `raise NotImplementedError` | Web 不适用 |

**验证**：`pytest rodski/tests/unit/test_playwright_driver.py`

---

#### WI-23: 新增 `switch` 关键字 [M]

**依赖**：WI-21

**目标**：跨应用窗口切换，测试和 RPA 共用。

**改动文件**：
- `rodski/core/keyword_engine.py` -- 新增 `_kw_switch()`
- `rodski/schemas/case.xsd` -- action enum 新增 `switch`
- `rodski/docs/SKILL_REFERENCE.md` -- 文档补充
- `rodski/docs/CORE_DESIGN_CONSTRAINTS.md` -- SUPPORTED 列表更新

**语法**：

```xml
<!-- 按窗口标题切换 -->
<test_step action="switch" model="" data="title=记事本"/>

<!-- 按 PID 切换 -->
<test_step action="switch" model="" data="pid=12345"/>

<!-- 切换到最近窗口 -->
<test_step action="switch" model="" data="recent"/>

<!-- 列出所有窗口（Return 返回窗口列表） -->
<test_step action="switch" model="" data="list"/>
```

**Return 值**：
- title/pid 模式 -> `{title, pid, position, size}` (切换到的窗口信息)
- list 模式 -> `[{title, pid, position, size}, ...]`

**验证**：rodski-demo 新增 `switch_window` 示例用例

---

#### WI-24: set/get 扩展剪贴板 + run 内置系统函数 [M]

**依赖**：WI-21

**目标**：
1. 扩展 `set`/`get` 关键字支持剪贴板读写
2. `run` 关键字内置系统级操作函数（文件/进程/环境变量）

#### Part A: set/get 剪贴板扩展

**改动文件**：
- `rodski/core/keyword_engine.py` -- `_kw_set()` / `_kw_get()` 增加 `clipboard` 识别

**语法**：

```xml
<!-- 写剪贴板 -->
<test_step action="set" model="" data="clipboard=Hello World"/>
<test_step action="set" model="" data="clipboard=${Return[-1].orderNo}"/>

<!-- 读剪贴板 -> Return 值 -->
<test_step action="get" model="" data="clipboard"/>

<!-- 读剪贴板 -> 存到命名变量 -->
<test_step action="set" model="" data="my_var=${clipboard}"/>
```

#### Part B: run 内置系统函数

**新建目录**：`rodski/builtins/`（框架内置函数，非用户 fun/ 脚本）

**新建文件**：

```
rodski/builtins/
├── __init__.py          # 注册表：所有内置函数名 -> 模块
├── file_ops.py          # 文件/目录操作
├── process_ops.py       # 进程管理
├── system_ops.py        # 系统信息/环境变量/时间戳
├── text_ops.py          # 文本处理/正则/JSON
└── excel_ops.py         # Excel 读写（可选依赖 openpyxl）
```

**调用方式（无前缀，直接函数名）**：

```xml
<!-- 文件操作 -->
<test_step action="run" model="" data="file_read('/tmp/config.txt')"/>
<test_step action="run" model="" data="file_write('/tmp/out.txt', 'hello')"/>
<test_step action="run" model="" data="file_copy('/tmp/a.txt', '/tmp/b.txt')"/>
<test_step action="run" model="" data="file_exists('/tmp/a.txt')"/>

<!-- 进程管理 -->
<test_step action="run" model="" data="process_start('notepad.exe')"/>
<test_step action="run" model="" data="process_kill(12345)"/>
<test_step action="run" model="" data="process_list('chrome')"/>

<!-- 系统 -->
<test_step action="run" model="" data="env_get('HOME')"/>
<test_step action="run" model="" data="timestamp('%Y%m%d')"/>

<!-- Excel -->
<test_step action="run" model="" data="excel_read('report.xlsx', 'Sheet1', 'A1:D10')"/>

<!-- 文本 -->
<test_step action="run" model="" data="regex_match('order-123-abc', 'order-(\d+)')"/>
```

**函数清单**：

| 模块 | 函数 | 返回 | 说明 |
|------|------|------|------|
| file_ops | `file_read(path, encoding='utf-8')` | str | 读文件内容 |
| file_ops | `file_write(path, content, mode='w')` | bool | 写文件 |
| file_ops | `file_copy(src, dst)` | str | 复制，返回目标路径 |
| file_ops | `file_move(src, dst)` | str | 移动 |
| file_ops | `file_delete(path)` | bool | 删除 |
| file_ops | `file_exists(path)` | bool | 存在检查 |
| file_ops | `dir_list(path, pattern='*')` | list | 列出文件 |
| file_ops | `dir_create(path)` | str | 创建目录 |
| process_ops | `process_start(cmd, *args, wait=False)` | dict | 启动，返回 {pid, name} |
| process_ops | `process_kill(pid_or_name)` | bool | 终止 |
| process_ops | `process_list(name_filter=None)` | list | 列出进程 |
| process_ops | `process_wait(pid, timeout=30)` | int | 等待结束，返回 exit_code |
| system_ops | `env_get(name)` | str | 读环境变量 |
| system_ops | `env_set(name, value)` | bool | 设环境变量（进程级） |
| system_ops | `system_info()` | dict | {os, version, hostname, user} |
| system_ops | `timestamp(format)` | str | 格式化时间戳 |
| text_ops | `regex_match(text, pattern)` | list | 正则匹配 |
| text_ops | `text_replace(text, old, new)` | str | 文本替换 |
| text_ops | `json_parse(text)` | dict/list | JSON 解析 |
| text_ops | `json_format(data)` | str | JSON 格式化 |
| excel_ops | `excel_read(path, sheet, range)` | list[list] | 读 Excel 区域 |
| excel_ops | `excel_write(path, sheet, data, cell)` | bool | 写 Excel |
| excel_ops | `excel_create(path, sheets)` | str | 创建 Excel |

**KeywordEngine 改动**：
- `_kw_run()` 优先查 `rodski/builtins/` 注册表，命中则调用内置函数
- 未命中则按原逻辑执行 `fun/` 下的用户脚本
- 内置函数在受限上下文中执行

**验证**：
- 每个模块独立 pytest
- rodski-demo 新增 `builtin_file_ops`、`builtin_process` 示例

---

#### WI-25: DriverFactory 注册 DesktopDriver [S]

**依赖**：WI-21

**目标**：解决当前 DesktopDriver 不在 DriverFactory 中注册的问题。

**改动文件**：
- `rodski/core/driver_factory.py` -- 新增 desktop/windows/macos 类型注册
- `rodski/core/keyword_engine.py` -- 移除手动创建 DesktopDriver 的临时代码

**映射关系**：

| driver_type | 实例化类 | 说明 |
|-------------|---------|------|
| `web` | PlaywrightDriver | 不变 |
| `interface` | InterfaceDriver | 不变 |
| `windows` | DesktopDriver(platform='windows') | 新增 |
| `macos` | DesktopDriver(platform='macos') | 新增 |
| `desktop` | DesktopDriver(platform=auto_detect) | 新增（自动检测 OS） |
| `android` | AndroidDriver | 不变 |
| `ios` | IOSDriver | 不变 |

**验证**：`pytest rodski/tests/unit/test_driver_factory.py`

---

#### WI-26: case.xsd / SUPPORTED 列表更新 [S]

**依赖**：WI-23

**改动文件**：
- `rodski/schemas/case.xsd` -- action enum 新增 `switch`
- `rodski/core/keyword_engine.py` -- SUPPORTED 列表新增 `switch`
- `rodski-agent/src/rodski_agent/common/rodski_knowledge.py` -- 同步更新

**更新后 SUPPORTED 列表**（16 关键字）：

```python
SUPPORTED = [
    "close", "type", "verify", "wait", "navigate", "launch",
    "assert",
    "upload_file", "clear", "get_text", "get",
    "send", "set", "DB", "run",
    "switch",  # 新增：窗口/应用切换
]
```

**验证**：XSD schema 验证通过 + rodski-agent 约束知识库与核心同步

---

### 2.2 Phase 4 改动汇总

| WI | 名称 | 大小 | 依赖 |
|----|------|------|------|
| WI-20 | BaseDriver 扩展（剪贴板/窗口/进程） | M | 无 |
| WI-21 | DesktopDriver 对齐新接口 | M | WI-20 |
| WI-22 | PlaywrightDriver 有限扩展 | S | WI-20 |
| WI-23 | 新增 switch 关键字 | M | WI-21 |
| WI-24 | set/get 扩展 + run 内置系统函数 | M | WI-21 |
| WI-25 | DriverFactory 注册 Desktop | S | WI-21 |
| WI-26 | Schema / SUPPORTED 更新 | S | WI-23 |

---

## 3. Phase 5: RPA Agent 方向

### 3.1 背景与目标

**行业趋势**：2025-2026 年 RPA 行业的核心架构范式已经收敛为：

```
用户意图 -> LLM 推理层 -> 编排器/规划器
    -> 确定性执行层（RPA bot / API / 关键字步骤）
    -> 反思/自愈 -> 记忆/状态
```

- **UiPath** 已从 "RPA 厂商" 转型为 "Agentic Automation Platform"（Agent Builder + Maestro 编排 + Autopilot）
- **Automation Anywhere** 核心是 Process Reasoning Engine (PRE)，目标导向而非步骤导向
- **Microsoft** Power Automate 2026 Wave 1 新增 MCP 服务器支持 + 自愈桌面流

**RodSki 的独特位置**：
- RodSki 的关键字驱动确定性引擎 = 行业架构中的 "执行层"
- rodski-agent 的 LangGraph 图 = "推理层"
- Phase 4 后，同一套关键字（17 个）+ 内置函数统一覆盖测试和 RPA
- **差距**：缺少 RPA 编排能力（跨应用流程、条件分支、循环、异常处理）

**目标**：在 rodski-agent 中新增 RPA Agent，复用 rodski 核心的统一驱动能力（Phase 4），实现跨应用流程自动化。RPA Agent 与 Execution/Design Agent 共享同一套关键字体系，区别仅在于编排逻辑和流程规划。

### 3.2 RPA Agent 架构

```
                    +-------------------------------------------+
                    |            rodski-agent                    |
                    |                                           |
                    |  +---------+  +----------+  +--------+   |
                    |  | Design  |  |Execution |  | RPA    |   |
                    |  | Agent   |  | Agent    |  | Agent  |   |
                    |  +----+----+  +-----+----+  +---+----+   |
                    |       |            |            |         |
                    |  +----+-----------+------------+-------+ |
                    |  |          共享基础设施                 | |
                    |  |  LLM Bridge / Config / Contracts      | |
                    |  |  RodSki Knowledge / XML Builder       | |
                    |  |  + RPA Flow Planner (NEW)             | |
                    |  |  + Process Memory Store (NEW)         | |
                    |  +------------------+--------------------+ |
                    +---------------------+----------------------+
                                          |
                    +---------------------+----------------------+
                    |              rodski core                    |
                    |                                            |
                    |  KeywordEngine (17 kw + 内置系统函数)       |
                    |  +-- PlaywrightDriver (Web + 有限 RPA)     |
                    |  +-- DesktopDriver (完整 RPA)              |
                    |  +-- AppiumDriver (Mobile)                 |
                    |  +-- InterfaceDriver (API)                 |
                    +--------------------------------------------+
```

### 3.3 RPA Agent vs 已有 Agent 对比

| 维度 | Execution Agent | Design Agent | RPA Agent (NEW) |
|------|----------------|-------------|-----------------|
| 输入 | 已有的 case XML | 自然语言需求 | 自然语言流程描述 / 录制的操作序列 |
| 输出 | 执行结果 JSON | 生成的 XML 文件 | 流程执行结果 + 状态快照 |
| 编排 | 单 case 顺序执行 | 单次设计 | **多步骤跨应用编排** |
| 自愈 | wait/locator/data | validate-retry | + navigation fix + app restart |
| 记忆 | 无 | 无 | **流程执行记忆**（成功路径 / 失败模式） |
| 目标 | 执行既定测试 | 生成测试用例 | **达成业务流程目标** |

### 3.4 工作项

#### WI-30: RPA Agent StateGraph 设计与实现 [L]

**新建文件**：

```
rodski-agent/src/rodski_agent/rpa/
├── __init__.py
├── graph.py           # RPA Agent StateGraph
├── nodes.py           # 8 个节点实现
├── planner.py         # 流程规划器（LLM）
├── executor.py        # 步骤执行器（调用 rodski）
├── state_tracker.py   # 流程状态跟踪
└── prompts.py         # RPA 专用 LLM Prompt
```

**RPA Agent Graph**：

```
analyze_flow -> plan_steps -> [acquire_context] -> execute_step -> check_result
     ^                                                |
     |                                          +-----+------+
     |                                     [success]     [failure]
     |                                          |            |
     |                                    next_step    diagnose_rpa
     |                                          |            |
     |                                    (loop back)   retry_or_adapt
     |                                                       |
     +--------------------------------- [replan if needed]---+
                                                       |
                                                  final_report
```

**节点说明**：

| 节点 | 职责 | 输入 -> 输出 |
|------|------|------------|
| `analyze_flow` | LLM 解析自然语言流程 -> 结构化步骤 | flow_description -> `{goal, steps[], apps_involved}` |
| `plan_steps` | LLM 规划每步的 RodSki 关键字映射 | steps -> `[{action, model, data, app, pre_condition}]` |
| `acquire_context` | 截图当前状态 + OmniParser 解析 | app -> `{screenshot, elements[], active_window}` |
| `execute_step` | 调用 rodski run 执行单步 | step -> `{result, screenshot_after}` |
| `check_result` | 验证步骤是否达成预期 | result + expected -> `{success, evidence}` |
| `next_step` | 推进到下一步 | step_index++ |
| `diagnose_rpa` | RPA 专用失败诊断 | failure -> `{category, root_cause, fix_strategy}` |
| `retry_or_adapt` | 决定重试/修改计划/放弃 | diagnosis -> `{action: retry|adapt|replan|abort}` |
| `final_report` | 汇总流程执行结果 | all_results -> report |

**RPA 诊断分类**（扩展 Execution Agent 的分类）：

| 类别 | 说明 | 修复策略 |
|------|------|---------|
| `APP_NOT_READY` | 目标应用未启动/未响应 | launch 或 process_start |
| `WRONG_WINDOW` | 当前焦点不在目标窗口 | switch 到目标窗口 |
| `PAGE_NOT_EXPECTED` | 页面状态不符合前置条件 | navigation fix (重新导航) |
| `ELEMENT_NOT_FOUND` | 定位器失效 | locator fix (继承 Execution Agent) |
| `TIMEOUT` | 操作超时 | wait fix (继承) |
| `DATA_MISMATCH` | 数据/格式不匹配 | data fix (继承) |
| `EXTERNAL_DEPENDENCY` | 外部系统不可用 | 等待 + 重试 |

**RPA State**（TypedDict）：

```python
class RPAState(TypedDict, total=False):
    # 输入
    flow_description: str          # 自然语言流程描述
    flow_config: dict              # 配置（超时、重试、目标应用等）

    # 规划
    flow_plan: list[dict]          # 结构化步骤列表
    current_step_index: int        # 当前执行到第几步
    apps_involved: list[str]       # 涉及的应用列表

    # 执行
    step_results: list[dict]       # 每步执行结果
    screenshots: list[str]         # 截图路径列表
    context_snapshots: list[dict]  # 每步执行前的上下文快照

    # 诊断
    diagnosis: dict                # 当前失败诊断
    retry_count: int
    adaptations: list[dict]        # 计划修改记录

    # 输出
    report: dict
    status: str                    # success / partial / failure / error
    error: str
```

**验证**：rodski-agent 单元测试 + 端到端 RPA 示例

---

#### WI-31: RPA Flow Planner（流程规划器）[M]

**依赖**：WI-30

**新建文件**：
- `rodski-agent/src/rodski_agent/rpa/planner.py`

**核心能力**：

1. **自然语言 -> 结构化流程**
2. **跨应用流程编排**
3. **前置条件推理**：每步自动推断需要哪些前置条件

**LLM Prompt 结构**：
- System: RodSki 统一关键字能力（17 关键字 + 内置系统函数）
- System: 当前可用应用列表
- User: 自然语言流程
- Output: JSON 格式的步骤列表

---

#### WI-32: Process Memory Store（流程执行记忆）[M]

**依赖**：WI-30

**目标**：跨会话持久化流程执行经验，提升 Agent 自愈和规划质量。

**新建文件**：
- `rodski-agent/src/rodski_agent/common/memory_store.py`

**存储结构**（SQLite）：

```sql
CREATE TABLE flow_executions (
    id INTEGER PRIMARY KEY,
    flow_hash TEXT,           -- 流程描述的语义哈希
    plan_json TEXT,           -- 规划的步骤
    result_status TEXT,       -- success/failure
    total_steps INTEGER,
    completed_steps INTEGER,
    failures_json TEXT,       -- 失败详情
    fixes_json TEXT,          -- 成功修复记录
    duration_seconds REAL,
    created_at TIMESTAMP
);

CREATE TABLE fix_patterns (
    id INTEGER PRIMARY KEY,
    failure_pattern TEXT,     -- 失败模式
    fix_strategy TEXT,        -- 修复策略 JSON
    success_count INTEGER,
    fail_count INTEGER,
    confidence REAL,
    last_used TIMESTAMP
);

CREATE TABLE app_models (
    id INTEGER PRIMARY KEY,
    app_name TEXT,
    window_title TEXT,
    model_xml TEXT,
    screenshot_path TEXT,
    last_verified TIMESTAMP,
    reliability REAL
);
```

**使用场景**：

| 场景 | 查询 | 效果 |
|------|------|------|
| 规划阶段 | 查 flow_executions 中类似流程的历史 | 复用已验证的计划 |
| 修复阶段 | 查 fix_patterns 中匹配的修复 | 优先尝试高置信度修复 |
| 设计阶段 | 查 app_models 中已知的应用模型 | 复用 model XML，减少探索 |
| 回顾阶段 | 统计成功率、耗时趋势 | 识别退化和优化点 |

**记忆淘汰策略**：
- fix_patterns: `confidence < 0.3 AND last_used < 30d` -> 自动清理
- app_models: `last_verified < 7d` -> 标记 stale，下次使用前重新验证

**验证**：`pytest rodski-agent/tests/test_memory_store.py`

---

#### WI-33: RPA Agent CLI 集成 [S]

**依赖**：WI-30

**改动文件**：
- `rodski-agent/src/rodski_agent/cli.py` -- 新增 `rpa` 子命令

**CLI 接口**：

```bash
# 从自然语言执行 RPA 流程
rodski-agent rpa run --flow "打开记事本, 输入Hello, 保存" --headless false

# 从 YAML 流程定义执行
rodski-agent rpa run --flow-file process.yaml

# 查看历史执行记录
rodski-agent rpa history [--flow-hash xxx] [--status success|failure]

# 清理记忆
rodski-agent rpa memory clean [--older-than 30d]
```

**流程定义 YAML 格式**：

```yaml
name: "月度订单导出"
description: "从 ERP 导出订单到 Excel"
apps:
  - name: chrome
    url: "https://erp.company.com"
  - name: excel
timeout: 300
max_retry: 3
steps:
  - description: "登录 ERP"
    action: navigate
    data: "https://erp.company.com/login"
  - description: "输入账号密码"
    action: type
    model: ERPLogin
    data: LOGIN_001
```

**验证**：CLI 帮助文档 + 示例流程执行

---

#### WI-34: RPA + 测试双模式支持 [S]

**依赖**：WI-30, WI-23

**目标**：同一个 case XML 既可作为测试用例（有断言）也可作为 RPA 流程（无断言、有实际业务操作）。

**设计**：case XML 新增 `mode` 属性：

```xml
<!-- 测试模式（默认）：执行 + 验证，失败不改实际数据 -->
<case id="c001" mode="test" execute="是" title="订单流程测试">
  ...verify steps...
</case>

<!-- RPA 模式：执行实际业务操作，无需验证 -->
<case id="c001" mode="rpa" execute="是" title="订单自动化处理">
  ...no verify, real business actions...
</case>

<!-- 混合模式：执行 + 关键检查点验证 -->
<case id="c001" mode="hybrid" execute="是" title="订单处理含检查">
  ...some verify steps at checkpoints...
</case>
```

**行为差异**：

| 行为 | mode=test | mode=rpa | mode=hybrid |
|------|-----------|----------|-------------|
| verify 失败 | case FAIL | 仅警告 | case FAIL |
| 截图 | 失败时自动 | 每步都截 | 失败+检查点 |
| Return 记录 | 完整 | 完整 | 完整 |
| 日志级别 | INFO | DEBUG（更详细） | INFO |
| post_process | 清理为主 | 可含业务操作 | 灵活 |

**改动文件**：
- `rodski/schemas/case.xsd` -- case 元素新增 `mode` 属性（test|rpa|hybrid，默认 test）
- `rodski/core/ski_executor.py` -- 根据 mode 调整失败处理逻辑
- `rodski/core/keyword_engine.py` -- RPA 模式下 verify 失败不中断

**验证**：rodski-demo 新增 RPA 模式示例

---

### 3.5 Phase 5 改动汇总

| WI | 名称 | 大小 | 依赖 |
|----|------|------|------|
| WI-30 | RPA Agent StateGraph | L | WI-23, WI-24 |
| WI-31 | RPA Flow Planner | M | WI-30 |
| WI-32 | Process Memory Store | M | WI-30 |
| WI-33 | RPA Agent CLI | S | WI-30 |
| WI-34 | RPA + 测试双模式 | S | WI-30, WI-23 |

---

## 4. 项目归属划分

| WI | 名称 | 项目 | 说明 |
|----|------|------|------|
| | **Phase 4: RPA 驱动层融合** | | |
| WI-20 | BaseDriver 扩展 | **rodski** | `drivers/base_driver.py` 新增抽象方法 |
| WI-21 | DesktopDriver 对齐 | **rodski** | `drivers/desktop_driver.py` 实现 |
| WI-22 | PlaywrightDriver 有限扩展 | **rodski** | `drivers/playwright_driver.py` 实现 |
| WI-23 | 新增 switch 关键字 | **rodski** | `core/keyword_engine.py` + `schemas/case.xsd` |
| WI-24 | set/get 扩展 + run 内置函数 | **rodski** | `core/keyword_engine.py` + 新建 `builtins/` |
| WI-25 | DriverFactory 注册 Desktop | **rodski** | `core/driver_factory.py` |
| WI-26 | Schema / SUPPORTED 更新 | **rodski** | `schemas/case.xsd` + SUPPORTED 列表 |
| | **Phase 5: RPA Agent** | | |
| WI-30 | RPA Agent StateGraph | **rodski-agent** | 新建 `rpa/graph.py` + `rpa/nodes.py` |
| WI-31 | RPA Flow Planner | **rodski-agent** | 新建 `rpa/planner.py`，LLM 驱动 |
| WI-32 | Process Memory Store | **rodski-agent** | 新建 `common/memory_store.py`，SQLite |
| WI-33 | RPA Agent CLI | **rodski-agent** | `cli.py` 新增 `rpa` 子命令 |
| WI-34 | RPA + 测试双模式 | **rodski** | `schemas/case.xsd` + `core/ski_executor.py` |

---

## 5. 全局依赖关系图

```
Phase 4 (RPA 驱动层融合) <- 全部 rodski:
    WI-20 (BaseDriver) --+-- WI-21 (Desktop) --+-- WI-23 (switch kw) -- WI-26 (schema)
                         |                      +-- WI-24 (set/get扩展 + 内置函数)
                         |                      +-- WI-25 (Factory)
                         +-- WI-22 (Playwright)

Phase 5 (RPA Agent) <- 主要 rodski-agent:
    WI-23 + WI-24 -- WI-30 (RPA Graph, agent) --+-- WI-31 (Planner, agent)
                                                  +-- WI-32 (Memory, agent)
                                                  +-- WI-33 (CLI, agent)
                                                  +-- WI-34 (双模式, rodski)
```

---

## 6. 工作量总览

### 按 Phase + 项目汇总

| Phase | 内容 | 工作项数 | rodski | agent | 关键路径 |
|-------|------|---------|--------|-------|---------|
| Phase 4 | RPA 驱动层融合 | 7 | 7 | 0 | WI-20 -> WI-21 -> WI-24 |
| Phase 5 | RPA Agent | 5 | 1 | 4 | WI-30 -> WI-31/32 |
| **总计** | | **12** | **8** | **4** | |

### 全量工作项索引

| WI | Phase | 名称 | 大小 | 项目 |
|----|-------|------|------|------|
| WI-20 | 4 | BaseDriver 扩展（剪贴板/窗口/进程） | M | rodski |
| WI-21 | 4 | DesktopDriver 对齐新接口 | M | rodski |
| WI-22 | 4 | PlaywrightDriver 有限扩展 | S | rodski |
| WI-23 | 4 | 新增 switch 关键字 | M | rodski |
| WI-24 | 4 | set/get 扩展 + run 内置系统函数 | M | rodski |
| WI-25 | 4 | DriverFactory 注册 Desktop | S | rodski |
| WI-26 | 4 | Schema / SUPPORTED 更新 | S | rodski |
| WI-30 | 5 | RPA Agent StateGraph | L | rodski-agent |
| WI-31 | 5 | RPA Flow Planner | M | rodski-agent |
| WI-32 | 5 | Process Memory Store | M | rodski-agent |
| WI-33 | 5 | RPA Agent CLI | S | rodski-agent |
| WI-34 | 5 | RPA + 测试双模式 | S | rodski |

---

## 7. 风险分析

| 风险 | 影响 | Phase | 缓解措施 |
|------|------|-------|---------|
| DesktopDriver 窗口管理跨平台兼容 | 高 | 4 | macOS/Windows 分别实现，先做 macOS 验证 |
| RPA 函数库安全沙箱不足 | 高 | 4 | 受限执行上下文 + 白名单模块 |
| RPA Agent 流程规划幻觉 | 高 | 5 | 规划后必须验证（截图确认状态） |
| switch 关键字跨平台窗口标题编码 | 低 | 4 | UTF-8 统一 + 模糊匹配 |
| Process Memory Store 膨胀 | 低 | 5 | 自动淘汰策略 + 容量上限 |

---

## 8. 验证方案

### 8.1 Phase 4 验证

1. **单元测试**：每个 WI 的 pytest
2. **集成测试**：
   - DesktopDriver: 在 macOS 上执行 hotkey/clipboard/window_switch 序列
   - PlaywrightDriver: 在 Web 上执行 hotkey/clipboard/drag 序列
3. **rodski-demo 新增示例**：
   - `rodski-demo/DEMO/desktop_ops/` -- 桌面操作示例（记事本 + 窗口切换 + 剪贴板）
   - `rodski-demo/DEMO/builtin_funcs/` -- 内置函数示例（文件/进程/Excel）
4. **switch 关键字验证**：多窗口切换 + 窗口列表获取

### 8.2 Phase 5 验证

1. **RPA Agent 端到端**：
   - 输入自然语言 -> 规划 -> 执行 -> 完成
   - 至少 3 个流程场景（单应用、跨应用、含异常恢复）
2. **Memory Store 验证**：
   - 首次执行记录写入
   - 二次执行命中记忆
   - 修复模式置信度计算
3. **双模式验证**：同一 case 分别以 test/rpa 模式执行

---

## 附录 A: RPA 框架对比

| 能力 | RodSki (Phase 4+5 后) | UiPath | Power Automate | Robot Framework RPA |
|------|----------------------|--------|---------------|-------------------|
| 键盘组合 | type key_press【ctrl+c】 | Keyboard Activities | Desktop flows | rpaframework |
| 窗口管理 | switch 关键字 | Window Activities | Window actions | 有限 |
| 剪贴板 | set/get clipboard | Clipboard Activities | Clipboard actions | 有限 |
| 文件操作 | run file_read/write/copy | File Activities | File actions | rpaframework |
| 进程管理 | run process_start/kill | Process Activities | Process actions | 无 |
| Excel 操作 | run excel_read/write | Excel Activities (原生) | Excel actions | rpaframework |
| AI 驱动规划 | RPA Agent (LLM) | Autopilot | Copilot | 无 |
| 流程记忆 | Memory Store | Insights 分析 | 无 | 无 |
| 视觉定位 | vision/ocr/bbox | Computer Vision | AI Builder | 无 |
| 开源 | 是 | 否 (商业) | 否 (SaaS) | 是 |
| 测试+RPA 双用 | 是 (唯一) | Agentic Testing | 无 | 部分 |
