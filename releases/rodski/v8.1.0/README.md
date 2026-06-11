# RodSki v8.1.0 Release

## 更新内容

### 新功能

#### iOS 自动化测试能力（Appium XCUITest）

- **`--platform ios` 参数**：自动加载 `data/globalvalue_ios.xml`，覆盖平台特有变量（BundleId/AppTarget/UDID 等），实现 Android/iOS 一键切换，用例无需修改
- **IOSDriver 完整实现**：`predicate` / `class_chain` / `accessibility-id` 三种 iOS 专属定位器；`scroll`、`swipe`、`key_press`（home/volumeup/volumedown）、`long_press`、`hide_keyboard` 等 iOS 手势
- **跨平台定位器**：`<location>` 支持 `platform="ios"` / `platform="android"` 属性，同一 model 跨平台复用，OCR/text 定位器两端通用
- **iOS Schema 扩展**：`model.xsd` 新增 `LocatorType` 枚举值 `predicate` / `class_chain`，`DriverType` 新增 `mobile`
- **SwiftUI Demo App**：`rodski-demo/DEMO/mobile_app/demo_ios_app/` — 4 个页面与 Android Demo 对齐，含 `build_ios_app.sh` 构建脚本
- **iOS smoke 计划**：`rodski-demo/DEMO/mobile_app/plan/ios_app_smoke.xml`

#### evaluate 关键字增强（v8.0.3 已包含）

- 执行期间捕获浏览器 `console.warn` / `console.error` 并输出到执行日志
- 慢步骤检测：超过阈值（默认 5s）自动输出 `[SLOW]` 警告
- 支持 `engine.slow_step_threshold` 外部设置及 case XML `slow_threshold` 属性覆盖

### 验收结果

| 验收项 | 结果 |
|--------|------|
| 单元测试 | **2077 passed**, 2 skipped, 3 xfailed |
| demo_full（Web）| **57/57 通过** |
| demo_runtime_control | **1/1 通过** |
| mobile_app（iOS Simulator iPhone 16）| **3/3 通过** |

## 安装方式

```bash
pip install rodski-8.1.0-py3-none-any.whl
```

## iOS 快速上手

```bash
# 配置 data/globalvalue_ios.xml 后：
rodski run product/myapp/mobile/case/ --platform ios
```

## 文件说明

| 文件 | 说明 |
|------|------|
| `rodski-8.1.0-py3-none-any.whl` | Python wheel 包，推荐安装 |
| `rodski-8.1.0.tar.gz` | 源码包 |
| `SHA256SUMS` | 文件校验和 |

## 校验

```bash
shasum -a 256 -c SHA256SUMS
```
