# 迭代 01 - 开发任务列表

**版本**: v2.0
**日期**: 2026-03-27
**总计**: 20 任务, 约 45 小时

---

## 设计要点回顾

### 核心架构：统一关键字，不同驱动

```
用例层: type / verify / launch / run ...（关键字统一）
    ↓
关键字引擎: 根据模型 type 属性分发
    ↓
驱动层: Web(Playwright) / Desktop(pyautogui+OmniParser) / Interface(Requests)
    ↓
定位器层: id/css/xpath/vision/ocr/vision_bbox（格式统一）
```

### 三种视觉定位器

| 类型 | 格式 | 实现 | 平台 |
|------|------|------|------|
| `vision` | 图片路径 | OpenCV 模板匹配 | Web + Desktop |
| `ocr` | 文字内容 | OmniParser OCR | Web + Desktop |
| `vision_bbox` | 坐标 | 直接解析 | Web + Desktop |

---

## Wave 1 - 驱动层基础架构 (5任务, 10h)

### Task 1.1: 定义驱动基类接口

**优先级**: P0
**工作量**: 2h
**依赖**: 无

**工作内容**:
- [ ] 创建 `rodski/drivers/base_driver.py`
- [ ] 定义抽象基类 `BaseDriver`
- [ ] 定义核心接口方法

**接口定义**:
```python
class BaseDriver(ABC):
    # 生命周期
    @abstractmethod
    def launch(self, **kwargs) -> None: ...

    @abstractmethod
    def close(self) -> None: ...

    # 元素定位
    @abstractmethod
    def locate_element(self, locator_type: str, locator_value: str) -> tuple | None: ...

    # 操作方法
    @abstractmethod
    def click(self, x: int, y: int) -> None: ...

    @abstractmethod
    def type_text(self, x: int, y: int, text: str) -> None: ...

    @abstractmethod
    def get_text(self, x1: int, y1: int, x2: int, y2: int) -> str: ...

    # 截图
    @abstractmethod
    def take_screenshot(self) -> str: ...
```

**验收标准**:
```
✅ BaseDriver 抽象类定义完整
✅ 所有方法签名和文档清晰
✅ 可被其他驱动继承
```

**产出文件**:
- `rodski/drivers/__init__.py`
- `rodski/drivers/base_driver.py`

---

### Task 1.2: 重构驱动工厂

**优先级**: P0
**工作量**: 2h
**依赖**: Task 1.1

**工作内容**:
- [ ] 修改 `rodski/core/driver_factory.py`
- [ ] 支持 `windows` / `macos` 驱动类型
- [ ] 实现驱动缓存和生命周期管理

**验收标准**:
```
✅ DriverFactory.get_driver("web") 返回 WebDriver
✅ DriverFactory.get_driver("windows") 返回 DesktopDriver
✅ DriverFactory.get_driver("macos") 返回 DesktopDriver
✅ 单元测试通过
```

---

### Task 1.3: 创建 vision 模块框架

**优先级**: P0
**工作量**: 1h
**依赖**: 无

**工作内容**:
- [ ] 创建 `rodski/vision/` 目录
- [ ] 创建模块初始化文件
- [ ] 定义异常类型

**产出文件**:
```
rodski/vision/
├── __init__.py
└── exceptions.py
```

**异常定义**:
```python
class VisionError(Exception): """视觉定位基础异常"""
class ImageNotFoundError(VisionError): """图片未找到"""
class OCRFailedError(VisionError): """OCR识别失败"""
class InvalidBBoxError(VisionError): """坐标格式无效"""
class OmniParserError(VisionError): """OmniParser服务异常"""
```

---

### Task 1.4: 实现坐标工具模块

**优先级**: P1
**工作量**: 2h
**依赖**: Task 1.3

**工作内容**:
- [ ] 创建 `rodski/vision/coordinate_utils.py`
- [ ] 实现坐标解析函数
- [ ] 实现坐标转换函数
- [ ] 编写单元测试

**核心函数**:
```python
def parse_bbox(bbox_str: str) -> tuple[int, int, int, int]:
    """解析坐标字符串 "x1,y1,x2,y2" 返回 (x1, y1, x2, y2)"""

def calculate_center(x1: int, y1: int, x2: int, y2: int) -> tuple[int, int]:
    """计算边界框中心点"""

def normalize_to_pixel(bbox: list, width: int, height: int) -> tuple:
    """归一化坐标转像素坐标（OmniParser返回归一化坐标）"""
```

**验收标准**:
```
✅ parse_bbox("100,200,150,250") == (100, 200, 150, 250)
✅ calculate_center(100, 200, 200, 300) == (150, 250)
✅ 无效格式抛出 InvalidBBoxError
✅ 单元测试通过
```

---

### Task 1.5: 实现结果缓存模块

**优先级**: P2
**工作量**: 3h
**依赖**: Task 1.3

**工作内容**:
- [ ] 创建 `rodski/vision/cache.py`
- [ ] 实现基于 TTL 的内存缓存
- [ ] 支持截图 hash 作为 key

**核心类**:
```python
class VisionCache:
    def __init__(self, ttl: int = 30): ...

    def get(self, screenshot_hash: str) -> dict | None: ...

    def set(self, screenshot_hash: str, result: dict) -> None: ...

    def clear(self) -> None: ...
```

**验收标准**:
```
✅ 缓存可存储和读取 OmniParser 结果
✅ TTL 过期后自动失效
✅ 单元测试通过
```

---

## Wave 2 - 视觉定位器实现 (5任务, 12h)

### Task 2.1: 实现 OmniParser 客户端

**优先级**: P0
**工作量**: 4h
**依赖**: Task 1.3

**工作内容**:
- [ ] 创建 `rodski/vision/omni_client.py`
- [ ] 实现 HTTP 请求封装
- [ ] 实现超时和重试机制
- [ ] 实现响应解析

**核心类**:
```python
class OmniClient:
    def __init__(self, url: str, timeout: int = 10): ...

    def parse(self, screenshot) -> list[dict]:
        """
        调用 OmniParser 解析截图
        返回: [{"content": "登录", "type": "button", "bbox": [0.1, 0.2, 0.15, 0.25]}, ...]
        """

    def health_check(self) -> bool: ...
```

**验收标准**:
```
✅ 可调用 OmniParser 服务
✅ 返回结构化的元素列表
✅ 超时/失败抛出 OmniParserError
✅ 单元测试通过（Mock HTTP）
```

---

### Task 2.2: 实现坐标定位器

**优先级**: P0
**工作量**: 1h
**依赖**: Task 1.4

**工作内容**:
- [ ] 创建 `rodski/vision/bbox_locator.py`
- [ ] 实现坐标解析和校验

**核心类**:
```python
class BBoxLocator:
    def locate(self, bbox_str: str) -> tuple[int, int, int, int]:
        """解析坐标字符串，返回边界框"""
```

**验收标准**:
```
✅ 正确解析有效坐标
✅ 无效坐标抛出 InvalidBBoxError
✅ 单元测试通过
```

---

### Task 2.3: 实现图片匹配定位器

**优先级**: P0
**工作量**: 3h
**依赖**: Task 1.4

**工作内容**:
- [ ] 创建 `rodski/vision/image_matcher.py`
- [ ] 使用 OpenCV 实现模板匹配
- [ ] 支持阈值配置

**核心类**:
```python
class ImageMatcher:
    def __init__(self, images_dir: str = "images", threshold: float = 0.8): ...

    def match(self, template_path: str, screenshot) -> tuple[int, int, int, int] | None:
        """
        在截图中匹配模板图片
        返回: (x1, y1, x2, y2) 或 None
        """
```

**验收标准**:
```
✅ 匹配成功返回边界框
✅ 匹配失败返回 None
✅ 阈值可配置
✅ 单元测试通过
```

---

### Task 2.4: 实现 OCR 文字定位器

**优先级**: P0
**工作量**: 3h
**依赖**: Task 2.1

**工作内容**:
- [ ] 创建 `rodski/vision/ocr_locator.py`
- [ ] 调用 OmniParser 获取文字元素
- [ ] 实现文字匹配逻辑

**核心类**:
```python
class OCRLocator:
    def __init__(self, omni_client: OmniClient): ...

    def locate_text(self, text: str, screenshot) -> tuple[int, int, int, int] | None:
        """
        在截图中定位指定文字
        返回: (x1, y1, x2, y2) 或 None
        """
```

**验收标准**:
```
✅ 能定位页面中的文字
✅ 支持中英文
✅ 未找到返回 None
✅ 单元测试通过
```

---

### Task 2.5: 实现视觉定位器统一入口

**优先级**: P0
**工作量**: 1h
**依赖**: Task 2.2, Task 2.3, Task 2.4

**工作内容**:
- [ ] 创建 `rodski/vision/locator.py`
- [ ] 实现统一分发逻辑
- [ ] 集成缓存

**核心类**:
```python
class VisionLocator:
    def __init__(self, config: dict = None): ...

    def locate(self, locator_type: str, locator_value: str, screenshot) -> tuple[int, int, int, int] | None:
        """
        统一定位入口
        locator_type: vision / ocr / vision_bbox
        返回: (x1, y1, x2, y2) 或 None
        """
```

**验收标准**:
```
✅ 正确分发到对应定位器
✅ 返回统一格式
✅ 单元测试通过
```

---

## Wave 3 - Desktop 驱动实现 (4任务, 10h)

### Task 3.1: 实现 Desktop 驱动核心

**优先级**: P0
**工作量**: 4h
**依赖**: Task 1.1

**工作内容**:
- [ ] 创建 `rodski/drivers/desktop_driver.py`
- [ ] 实现 `launch()` 启动应用
- [ ] 实现 `close()` 关闭应用
- [ ] 实现 `take_screenshot()` 截图
- [ ] 处理 Windows/macOS 平台差异

**核心类**:
```python
class DesktopDriver(BaseDriver):
    def __init__(self, platform: str):  # "windows" or "macos"

    def launch(self, app_path: str = None, app_name: str = None) -> None:
        """启动应用"""

    def take_screenshot(self) -> str:
        """全屏截图（pyautogui）"""
```

**验收标准**:
```
✅ 可启动 Windows/macOS 应用
✅ 可关闭应用
✅ 全屏截图正常
✅ 单元测试通过
```

---

### Task 3.2: 实现 Desktop 定位器集成

**优先级**: P0
**工作量**: 2h
**依赖**: Task 3.1, Task 2.5

**工作内容**:
- [ ] 在 `locate_element()` 中集成视觉定位器
- [ ] 传统定位器抛出不支持异常

**实现**:
```python
def locate_element(self, locator_type: str, locator_value: str) -> tuple | None:
    if locator_type not in ("vision", "ocr", "vision_bbox"):
        raise ValueError(f"Desktop driver only supports vision locators, got: {locator_type}")

    screenshot = self.take_screenshot()
    return self.vision_locator.locate(locator_type, locator_value, screenshot)
```

**验收标准**:
```
✅ vision/ocr/vision_bbox 正常工作
✅ 传统定位器抛出明确错误
✅ 单元测试通过
```

---

### Task 3.3: 实现 Desktop 操作方法

**优先级**: P0
**工作量**: 2h
**依赖**: Task 3.1

**工作内容**:
- [ ] 实现 `click(x, y)` 使用 pyautogui
- [ ] 实现 `type_text(x, y, text)` 使用 pyautogui
- [ ] 实现 `get_text()` 使用 OCR

**实现**:
```python
def click(self, x: int, y: int) -> None:
    pyautogui.click(x, y)

def type_text(self, x: int, y: int, text: str) -> None:
    pyautogui.click(x, y)
    pyautogui.typewrite(text)

def get_text(self, x1: int, y1: int, x2: int, y2: int) -> str:
    # 裁剪截图区域，调用 OCR
```

**验收标准**:
```
✅ 点击正常
✅ 输入正常
✅ OCR 获取文字正常
✅ 单元测试通过
```

---

### Task 3.4: 扩展 Web 驱动支持视觉定位器

**优先级**: P0
**工作量**: 2h
**依赖**: Task 2.5

**工作内容**:
- [ ] 修改 `rodski/drivers/web_driver.py`
- [ ] 在 `locate_element()` 中添加视觉定位器支持
- [ ] 实现坐标点击（Playwright mouse）

**实现**:
```python
def locate_element(self, locator_type: str, locator_value: str) -> tuple | None:
    if locator_type in ("vision", "ocr", "vision_bbox"):
        screenshot = self.take_screenshot()
        return self.vision_locator.locate(locator_type, locator_value, screenshot)
    # 传统定位器...

def click(self, x: int, y: int) -> None:
    self.page.mouse.click(x, y)

def type_text(self, x: int, y: int, text: str) -> None:
    self.page.mouse.click(x, y)
    self.page.keyboard.type(text)
```

**验收标准**:
```
✅ Web 驱动支持 vision/ocr/vision_bbox
✅ 坐标点击和输入正常
✅ 单元测试通过
```

---

## Wave 4 - 关键字引擎集成 (3任务, 6h)

### Task 4.1: 实现 launch 关键字

**优先级**: P0
**工作量**: 2h
**依赖**: Task 3.1

**工作内容**:
- [ ] 修改 `rodski/core/keyword_engine.py`
- [ ] 添加 `launch` 关键字处理
- [ ] Web 模型 → 调用 navigate 逻辑
- [ ] Desktop 模型 → 调用 driver.launch()

**实现逻辑**:
```python
def _execute_launch(self, model_name: str, data_id: str):
    model = self.get_model(model_name)
    driver_type = model.get_driver_type()

    if driver_type == "web":
        return self._execute_navigate(model_name, data_id)
    elif driver_type in ("windows", "macos"):
        driver = self.driver_factory.get_driver(driver_type)
        data = self.get_data(model_name, data_id)
        driver.launch(app_path=data.get("app_path"), app_name=data.get("app_name"))
        return {"status": "success"}
```

**验收标准**:
```
✅ launch Web 模型等同于 navigate
✅ launch Desktop 模型启动应用
✅ launch 与 navigate 在关键字计数中算一个
✅ 单元测试通过
```

---

### Task 4.2: 修改 type/verify 关键字支持视觉定位器

**优先级**: P0
**工作量**: 2h
**依赖**: Task 3.2, Task 3.4

**工作内容**:
- [ ] 修改 `type` 关键字实现
- [ ] 修改 `verify` 关键字实现
- [ ] 支持多定位器自动切换
- [ ] 统一处理 Web 和 Desktop

**多定位器切换逻辑**:
```python
def _try_locators(self, element, driver):
    locators = element.get_locations()  # 按 priority 排序
    for locator in locators:
        bbox = driver.locate_element(locator.type, locator.value)
        if bbox:
            return bbox
    return None
```

**验收标准**:
```
✅ type/verify 支持 vision/ocr/vision_bbox
✅ 多定位器按 priority 自动切换
✅ Web 和 Desktop 行为一致
✅ 集成测试通过
```

---

### Task 4.3: 更新模型解析器支持视觉定位器

**优先级**: P1
**工作量**: 2h
**依赖**: 无

**工作内容**:
- [ ] 修改 `rodski/core/model_parser.py`
- [ ] 解析 `vision/ocr/vision_bbox` 定位器类型
- [ ] 解析 `priority` 属性
- [ ] 支持多 location 元素

**验收标准**:
```
✅ 正确解析视觉定位器
✅ 正确解析 priority 属性
✅ 多定位器按 priority 排序
✅ 单元测试通过
```

---

## Wave 5 - 测试与文档 (3任务, 7h)

### Task 5.1: 创建 Web 视觉定位 Demo

**优先级**: P1
**工作量**: 2h
**依赖**: Wave 4 完成

**工作内容**:
- [ ] 创建 `rodski-demo/DEMO/vision_web/` 目录结构
- [ ] 编写模型 XML（包含视觉定位器）
- [ ] 编写测试用例
- [ ] 准备测试图片
- [ ] 编写 README.md

**目录结构**:
```
vision_web/
├── case/
│   └── test_vision.xml
├── model/
│   └── model.xml
├── data/
│   └── *.xml
├── images/
│   └── *.png
└── README.md
```

**验收标准**:
```
✅ 目录结构完整
✅ XML 通过 Schema 验证
✅ README 清晰
```

---

### Task 5.2: 创建 Desktop 视觉定位 Demo

**优先级**: P1
**工作量**: 3h
**依赖**: Wave 4 完成

**工作内容**:
- [ ] 创建 `rodski-demo/DEMO/vision_desktop/` 目录结构
- [ ] 编写 Desktop 应用模型
- [ ] 编写测试用例
- [ ] 编写 README.md

**验收标准**:
```
✅ 目录结构完整
✅ Desktop 用例可执行
✅ README 清晰
```

---

### Task 5.3: 更新核心设计文档

**优先级**: P1
**工作量**: 2h
**依赖**: 无

**工作内容**:
- [ ] 更新 `核心设计约束.md` 驱动层相关内容
- [ ] 更新 `TEST_CASE_WRITING_GUIDE.md` 添加视觉定位器说明
- [ ] 添加 Desktop 平台用例编写指南

**验收标准**:
```
✅ 文档与实现一致
✅ 示例代码正确
```

---

## 验收检查表

### 功能验收

```
□ 驱动层
  □ BaseDriver 接口定义完整
  □ DesktopDriver 可用
  □ WebDriver 支持视觉定位器

□ 视觉定位器
  □ vision 图片匹配可用
  □ ocr 文字定位可用
  □ vision_bbox 坐标定位可用

□ 关键字
  □ launch 关键字可用
  □ type/verify 支持视觉定位器
  □ 多定位器自动切换正常
```

### 质量验收

```
□ 单元测试通过率 100%
□ 集成测试通过
□ Demo 项目可执行
□ 文档完整更新
```

---

**创建日期**: 2026-03-27
**最后更新**: 2026-03-27