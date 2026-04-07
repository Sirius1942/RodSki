# Iteration 08: 微信桌面自动化 Demo + 驱动自动路由

**版本**: v4.0.1
**日期**: 2026-04-06
**分支**: V4.0.1

---

## 迭代目标

实现 RodSki 桌面端（macOS）自动化能力，以微信桌面版为 demo 验证端到端流程。同时修复框架层驱动自动路由问题，使模型 `type="macos"` 元素能自动路由到 DesktopDriver。

---

## 需求来源

- 核心设计约束 `CORE_DESIGN_CONSTRAINTS.md` 第 11 节：桌面端使用 `type="windows"` / `type="macos"` 标识
- 设计约束规定：**驱动类型由模型元素 type 属性决定**，不应通过 CLI 参数选择
- `ski_run.py` 原硬编码 `PlaywrightDriver`，无法自动切换到 DesktopDriver

---

## 设计决策

### D8-01: 驱动自动路由机制

**问题**: KeywordEngine._batch_type 直接调用 `self.driver.type_locator()`，无法根据元素的 driver_type 选择不同驱动。

**决策**: 在 KeywordEngine 中新增 `_get_driver_for_type(driver_type)` 方法：
- `driver_type in ("web", "interface")` → 返回 `self.driver`（PlaywrightDriver）
- `driver_type in ("macos", "windows", "other")` → 懒加载创建 DesktopDriver 并缓存
- DesktopDriver 实例通过 driver_factory 或直接 import 创建

**Why**: 遵循"模型决定驱动类型"的设计约束，用户无需关心驱动切换。

### D8-02: DesktopDriver locator 桥接

**问题**: DesktopDriver 只有 `click(x, y)` / `type_text(x, y)` 坐标方法，缺少 `click_locator(locator)` / `type_locator(locator, text)` 接口。

**决策**: 添加桥接方法，将 locator 字符串（如 `vision_bbox=100,200,150,250`）解析为坐标，计算中心点后委托给底层方法。

**Why**: 保持与 PlaywrightDriver 相同的接口签名，_batch_type 无需区分驱动类型即可统一调用。

### D8-03: 微信 demo 使用 run 脚本辅助

**问题**: run 关键字不传递参数（`subprocess.run([sys.executable, str(script_path)])`）。

**决策**: 创建专用脚本（activate_wechat.py、select_first_result.py），操作值硬编码在脚本内。type 关键字用于模型化操作（搜索、输入、发送）。

**Why**: 避免修改 run 关键字的既有行为，demo 阶段够用。

---

## 实施任务

### T8-001: DesktopDriver 添加 locator 桥接方法 ✅
- `click_locator(locator)`, `type_locator(locator, text)`, `screenshot(path)`, `navigate(url)`
- `_parse_locator()` 解析 `type=value` 格式
- `_locator_to_center()` 从 vision_bbox 直接计算坐标或通过 locate_element 定位

### T8-002: KeywordEngine 驱动自动路由 ✅
- 新增 `_get_driver_for_type(driver_type)` 方法，带缓存
- `_batch_type` 中根据 driver_type 路由到对应驱动
- `_execute_element_action` 添加 `driver` 参数

### T8-003: ski_run.py driver_factory 升级 ✅
- `create_driver()` 新增 `driver_type` 参数
- driver_factory lambda 支持 `driver_type` 传递

### T8-004: 微信桌面 demo ✅
- 目录：`CassMall_examples/wechat_desktop/`
- 模型：`model/model.xml`（type="macos" + vision_bbox 坐标）
- 用例：`wechat_screenshot.xml`（截图校准）、`wechat_basic.xml`（搜索→发消息）
- 脚本：`fun/desktop/activate_wechat.py`、`select_first_result.py`

### T8-005: 结果目录前缀 rename ✅
- `rodski/core/result_writer.py` 中 `run_` → `rodski_`

### T8-006: 高级技巧文档 ✅
- `rodski/docs/ADVANCED_TIPS.md` — 定位器自动切换功能介绍

---

## 验证结果

### Web 用例回归
- `CassMall_examples/login` → **1/1 通过** ✅
- 框架修改未破坏 Web 自动化功能

### 微信截图校准
- `wechat_screenshot.xml` → **1/1 通过** ✅
- AppleScript 成功激活微信窗口，pyautogui 截图正常

### 微信基本操作
- `wechat_basic.xml` → **1/1 通过** ✅
- 完整流程：激活微信 → 搜索"文件传输助手" → 选择 → 输入消息 → 点击发送

---

## 修改文件清单

| 操作 | 文件 | 说明 |
|------|------|------|
| 修改 | `rodski/core/result_writer.py` | 结果目录前缀 `run_` → `rodski_` |
| 修改 | `rodski/core/keyword_engine.py` | 驱动自动路由 + _execute_element_action driver 参数 |
| 修改 | `rodski/ski_run.py` | create_driver 支持 driver_type |
| 修改 | `rodski/drivers/desktop_driver.py` | locator 桥接方法 |
| 新建 | `rodski/docs/ADVANCED_TIPS.md` | 高级技巧指南 |
| 新建 | `CassMall_examples/wechat_desktop/` | 微信桌面 demo 全部文件 |

---

## 遗留与后续

1. **run 关键字参数传递**: 当前不支持传递参数，需要增强为 `subprocess.run([sys.executable, str(script_path)] + args)`
2. **OmniParser 集成**: 当前使用 vision_bbox 硬编码坐标，后续可接入 OmniParser 实现动态视觉定位
3. **坐标校准工具**: 可以开发一个交互式坐标拾取工具，替代手动校准
4. **DesktopDriver verify 支持**: 当前 verify 在桌面端的功能有限，需要增强
