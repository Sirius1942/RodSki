# 迭代 01 - 视觉定位技术设计

**版本**: v1.2
**日期**: 2026-03-27
**对齐**: 核心设计约束 v3.6

---

## 架构设计

### 核心原则：统一关键字，不同驱动

```
┌─────────────────────────────────────────────────────────────────┐
│                        用例层 (Case XML)                         │
│                                                                  │
│   <test_step action="launch" model="App" data="L001"/>         │
│   <test_step action="type" model="LoginPage" data="T001"/>     │
│   <test_step action="verify" model="LoginPage" data="V001"/>   │
│                                                                  │
│              关键字统一，用例不区分平台                            │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                        关键字引擎                                │
│                                                                  │
│   type / verify / launch / navigate / send / close ...         │
│                                                                  │
│   解析模型 type 属性，分发到对应驱动                              │
└────────────────────────────────┬────────────────────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         ▼                       ▼                       ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Web Driver    │     │ Interface Driver│     │ Desktop Driver  │
│                 │     │                 │     │                 │
│  type=web       │     │  type=interface │     │  type=windows   │
│  Playwright     │     │  Requests       │     │  type=macos     │
│                 │     │                 │     │  pyautogui      │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                        定位器层                                  │
│                                                                  │
│   传统定位器: id / css / xpath / text / name / class / tag     │
│   视觉定位器: vision / ocr / vision_bbox                        │
│                                                                  │
│   格式统一: <location type="类型">值</location>                  │
└─────────────────────────────────────────────────────────────────┘
```

### 驱动与定位器对应关系

| 驱动类型 | 驱动实现 | 支持的定位器 |
|---------|---------|-------------|
| `web` | Playwright | id, css, xpath, text, name, class, tag, **vision, ocr, vision_bbox** |
| `interface` | Requests | static, field |
| `windows` | pyautogui + OmniParser | **vision, ocr, vision_bbox** |
| `macos` | pyautogui + OmniParser | **vision, ocr, vision_bbox** |

---

## 模块设计

### 1. 目录结构

```
rodski/
├── core/
│   ├── keyword_engine.py      # 关键字引擎（统一入口）
│   ├── driver_factory.py      # 驱动工厂（根据模型类型创建驱动）
│   └── model_parser.py        # 模型解析器
│
├── drivers/
│   ├── base_driver.py         # 驱动基类
│   ├── web_driver.py          # Web 驱动 (Playwright)
│   ├── interface_driver.py    # 接口驱动 (Requests)
│   └── desktop_driver.py      # Desktop 驱动 (pyautogui)
│
├── vision/
│   ├── __init__.py
│   ├── locator.py             # 视觉定位器统一入口
│   ├── image_matcher.py       # 图片匹配 (OpenCV)
│   ├── ocr_locator.py         # OCR 文字定位 (OmniParser)
│   ├── bbox_locator.py        # 坐标定位器
│   ├── omni_client.py         # OmniParser 客户端
│   ├── screenshot.py          # 截图工具
│   ├── coordinate_utils.py    # 坐标工具
│   ├── exceptions.py          # 异常定义
│   └── cache.py               # 结果缓存
│
└── schemas/
    └── model.xsd              # 模型 Schema（已更新定位器类型）
```

### 2. 驱动基类设计

```python
# rodski/drivers/base_driver.py

from abc import ABC, abstractmethod
from typing import Tuple, Optional

class BaseDriver(ABC):
    """驱动基类，定义统一接口"""

    @abstractmethod
    def launch(self, app_path: str = None, url: str = None) -> None:
        """启动应用或打开页面"""
        pass

    @abstractmethod
    def close(self) -> None:
        """关闭应用或浏览器"""
        pass

    @abstractmethod
    def locate_element(self, locator_type: str, locator_value: str) -> Optional[Tuple[int, int, int, int]]:
        """
        定位元素，返回边界框坐标 (x1, y1, x2, y2)

        Args:
            locator_type: 定位器类型 (id/css/xpath/vision/ocr/vision_bbox等)
            locator_value: 定位器值

        Returns:
            (x1, y1, x2, y2) 边界框坐标，未找到返回 None
        """
        pass

    @abstractmethod
    def click(self, x: int, y: int) -> None:
        """点击指定坐标"""
        pass

    @abstractmethod
    def type_text(self, x: int, y: int, text: str) -> None:
        """在指定坐标输入文字"""
        pass

    @abstractmethod
    def get_text(self, x1: int, y1: int, x2: int, y2: int) -> str:
        """获取指定区域的文字"""
        pass

    @abstractmethod
    def take_screenshot(self) -> str:
        """截图，返回截图路径"""
        pass
```

### 3. Web 驱动扩展

```python
# rodski/drivers/web_driver.py

from playwright.sync_api import Page
from .base_driver import BaseDriver
from vision.locator import VisionLocator

class WebDriver(BaseDriver):
    """Web 驱动，基于 Playwright"""

    def __init__(self, page: Page):
        self.page = page
        self.vision_locator = VisionLocator()

    def locate_element(self, locator_type: str, locator_value: str) -> Optional[Tuple[int, int, int, int]]:
        """定位元素"""
        # 传统定位器
        if locator_type == "id":
            element = self.page.locator(f"#{locator_value}")
        elif locator_type == "css":
            element = self.page.locator(locator_value)
        elif locator_type == "xpath":
            element = self.page.locator(f"xpath={locator_value}")
        elif locator_type == "text":
            element = self.page.locator(f"text={locator_value}")
        # 视觉定位器
        elif locator_type in ("vision", "ocr", "vision_bbox"):
            screenshot_path = self.take_screenshot()
            return self.vision_locator.locate(
                locator_type, locator_value, screenshot_path
            )
        else:
            raise ValueError(f"Unsupported locator type: {locator_type}")

        # 传统定位器返回边界框
        if element.count() > 0:
            box = element.first.bounding_box()
            return (box['x'], box['y'], box['x'] + box['width'], box['y'] + box['height'])
        return None

    def click(self, x: int, y: int) -> None:
        """点击坐标（使用 Playwright mouse）"""
        self.page.mouse.click(x, y)

    def type_text(self, x: int, y: int, text: str) -> None:
        """点击坐标并输入文字"""
        self.page.mouse.click(x, y)
        self.page.keyboard.type(text)

    def get_text(self, x1: int, y1: int, x2: int, y2: int) -> str:
        """获取区域文字（使用 OCR）"""
        screenshot_path = self.take_screenshot()
        # 裁剪区域并 OCR
        return self.vision_locator.ocr_region(screenshot_path, x1, y1, x2, y2)
```

### 4. Desktop 驱动实现

```python
# rodski/drivers/desktop_driver.py

import pyautogui
import subprocess
from typing import Tuple, Optional
from .base_driver import BaseDriver
from vision.locator import VisionLocator

class DesktopDriver(BaseDriver):
    """Desktop 驱动，基于 pyautogui"""

    def __init__(self, platform: str = "windows"):
        """
        Args:
            platform: "windows" 或 "macos"
        """
        self.platform = platform
        self.vision_locator = VisionLocator()
        self.app_process = None

    def launch(self, app_path: str = None, app_name: str = None) -> None:
        """启动应用"""
        if app_path:
            self.app_process = subprocess.Popen(app_path)
        elif app_name:
            # macOS 使用 open 命令
            if self.platform == "macos":
                subprocess.run(["open", "-a", app_name])
            # Windows 需要其他方式

    def close(self) -> None:
        """关闭应用"""
        if self.app_process:
            self.app_process.terminate()

    def locate_element(self, locator_type: str, locator_value: str) -> Optional[Tuple[int, int, int, int]]:
        """定位元素（仅支持视觉定位器）"""
        if locator_type not in ("vision", "ocr", "vision_bbox"):
            raise ValueError(f"Desktop driver only supports vision locators, got: {locator_type}")

        screenshot_path = self.take_screenshot()
        return self.vision_locator.locate(
            locator_type, locator_value, screenshot_path
        )

    def click(self, x: int, y: int) -> None:
        """点击坐标"""
        pyautogui.click(x, y)

    def type_text(self, x: int, y: int, text: str) -> None:
        """点击坐标并输入文字"""
        pyautogui.click(x, y)
        pyautogui.typewrite(text)

    def get_text(self, x1: int, y1: int, x2: int, y2: int) -> str:
        """获取区域文字（OCR）"""
        screenshot_path = self.take_screenshot()
        return self.vision_locator.ocr_region(screenshot_path, x1, y1, x2, y2)

    def take_screenshot(self) -> str:
        """全屏截图"""
        return pyautogui.screenshot()
```

---

## 视觉定位器实现

### 1. 统一入口

```python
# rodski/vision/locator.py

from typing import Tuple, Optional
from .image_matcher import ImageMatcher
from .ocr_locator import OCRLocator
from .bbox_locator import BBoxLocator

class VisionLocator:
    """视觉定位器统一入口"""

    def __init__(self, config: dict = None):
        self.image_matcher = ImageMatcher(config)
        self.ocr_locator = OCRLocator(config)
        self.bbox_locator = BBoxLocator()

    def locate(self,
               locator_type: str,
               locator_value: str,
               screenshot) -> Optional[Tuple[int, int, int, int]]:
        """
        定位元素

        Args:
            locator_type: vision / ocr / vision_bbox
            locator_value: 定位器值
            screenshot: 截图（路径或 PIL Image）

        Returns:
            (x1, y1, x2, y2) 边界框坐标
        """
        if locator_type == "vision":
            return self.image_matcher.match(locator_value, screenshot)
        elif locator_type == "ocr":
            return self.ocr_locator.locate_text(locator_value, screenshot)
        elif locator_type == "vision_bbox":
            return self.bbox_locator.parse(locator_value)
        else:
            raise ValueError(f"Unknown vision locator type: {locator_type}")
```

### 2. 图片匹配器

```python
# rodski/vision/image_matcher.py

import cv2
import numpy as np
from typing import Tuple, Optional

class ImageMatcher:
    """OpenCV 模板匹配"""

    def __init__(self, config: dict = None):
        self.threshold = config.get("threshold", 0.8) if config else 0.8
        self.images_dir = config.get("images_dir", "images") if config else "images"

    def match(self,
              template_path: str,
              screenshot) -> Optional[Tuple[int, int, int, int]]:
        """
        在截图中匹配模板图片

        Args:
            template_path: 模板图片路径（相对于 images/ 目录）
            screenshot: 截图（路径或 PIL Image）

        Returns:
            (x1, y1, x2, y2) 匹配区域，未找到返回 None
        """
        # 加载模板
        template = cv2.imread(f"{self.images_dir}/{template_path}")
        if template is None:
            raise FileNotFoundError(f"Template not found: {template_path}")

        # 转换截图
        if isinstance(screenshot, str):
            screenshot_img = cv2.imread(screenshot)
        else:
            screenshot_img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

        # 模板匹配
        result = cv2.matchTemplate(screenshot_img, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        if max_val < self.threshold:
            return None

        # 计算边界框
        h, w = template.shape[:2]
        x1, y1 = max_loc
        x2, y2 = x1 + w, y1 + h

        return (x1, y1, x2, y2)
```

### 3. OCR 定位器

```python
# rodski/vision/ocr_locator.py

from typing import Tuple, Optional
from .omni_client import OmniClient

class OCRLocator:
    """OCR 文字定位器"""

    def __init__(self, config: dict = None):
        self.omni_client = OmniClient(config)

    def locate_text(self,
                    text: str,
                    screenshot) -> Optional[Tuple[int, int, int, int]]:
        """
        在截图中定位指定文字

        Args:
            text: 要定位的文字
            screenshot: 截图

        Returns:
            (x1, y1, x2, y2) 文字区域，未找到返回 None
        """
        # 调用 OmniParser 获取所有文字元素
        elements = self.omni_client.parse(screenshot)

        # 匹配目标文字
        for elem in elements:
            if text in elem.get("content", ""):
                bbox = elem["bbox"]  # 归一化坐标 [x1, y1, x2, y2]
                # 转换为像素坐标
                # ... 坐标转换逻辑
                return (px_x1, px_y1, px_x2, px_y2)

        return None
```

### 4. 坐标定位器

```python
# rodski/vision/bbox_locator.py

from typing import Tuple

class BBoxLocator:
    """坐标定位器"""

    def parse(self, bbox_str: str) -> Tuple[int, int, int, int]:
        """
        解析坐标字符串

        Args:
            bbox_str: "x1,y1,x2,y2" 格式

        Returns:
            (x1, y1, x2, y2) 整数坐标
        """
        try:
            parts = bbox_str.split(",")
            if len(parts) != 4:
                raise ValueError(f"Invalid bbox format: {bbox_str}")

            x1, y1, x2, y2 = [int(p.strip()) for p in parts]

            if x1 >= x2 or y1 >= y2:
                raise ValueError(f"Invalid bbox coordinates: {bbox_str}")

            return (x1, y1, x2, y2)

        except Exception as e:
            raise ValueError(f"Failed to parse bbox: {bbox_str}, error: {e}")
```

---

## 关键字引擎修改

### launch 关键字实现

```python
# rodski/core/keyword_engine.py (部分)

def _execute_launch(self, model_name: str, data_id: str) -> dict:
    """
    执行 launch 关键字

    根据模型类型分发到对应驱动：
    - web 模型 → navigate（打开浏览器）
    - windows/macos 模型 → desktop_driver.launch（启动应用）
    """
    model = self.model_parser.get_model(model_name)
    driver_type = model.get("driver_type", "web")

    if driver_type == "web":
        # Web 平台，等同于 navigate
        return self._execute_navigate(model_name, data_id)

    elif driver_type in ("windows", "macos"):
        # Desktop 平台，启动应用
        driver = self.driver_factory.get_driver(driver_type)
        data = self.data_parser.get_data(model_name, data_id)

        app_path = data.get("app_path")
        app_name = data.get("app_name")

        driver.launch(app_path=app_path, app_name=app_name)

        return {"status": "success", "action": "launch"}

    else:
        raise ValueError(f"Unsupported driver type for launch: {driver_type}")
```

### type 关键字修改

```python
def _execute_type(self, model_name: str, data_id: str) -> dict:
    """
    执行 type 关键字

    统一处理 Web 和 Desktop 平台
    """
    model = self.model_parser.get_model(model_name)
    driver_type = model.get("driver_type", "web")
    driver = self.driver_factory.get_driver(driver_type)
    data = self.data_parser.get_data(model_name, data_id)

    results = {}

    for field_name, field_value in data.items():
        element = model.get_element(field_name)
        if not element:
            continue

        # 获取定位器列表（支持多定位器）
        locators = element.get("locations", [])

        # 按优先级尝试定位
        element_found = False
        for locator in sorted(locators, key=lambda x: x.get("priority", 1)):
            locator_type = locator["type"]
            locator_value = locator["value"]

            bbox = driver.locate_element(locator_type, locator_value)

            if bbox:
                element_found = True
                x1, y1, x2, y2 = bbox
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

                # 执行操作
                if field_value == "click":
                    driver.click(cx, cy)
                elif field_value == "double_click":
                    driver.click(cx, cy)
                    driver.click(cx, cy)
                else:
                    # 输入文字
                    driver.type_text(cx, cy, field_value)

                results[field_name] = "success"
                break

        if not element_found:
            results[field_name] = "element_not_found"

    return {"status": "success", "results": results}
```

---

## 坐标约定

### Web 平台

- 坐标系：页面像素坐标
- 原点：浏览器视口左上角 (0, 0)
- vision_bbox：相对于页面左上角

### Desktop 平台

- 坐标系：屏幕绝对坐标
- 原点：屏幕左上角 (0, 0)
- vision_bbox：屏幕绝对坐标
- 注意：多显示器环境下坐标需注意

---

## 配置管理

### 全局变量

```xml
<group name="VisionConfig">
    <var name="OMNIPARSER_URL" value="http://localhost:8001"/>
    <var name="OMNIPARSER_TIMEOUT" value="10"/>
    <var name="OPENCV_MATCH_THRESHOLD" value="0.8"/>
    <var name="VISION_CACHE_TTL" value="30"/>
    <var name="IMAGES_DIR" value="images"/>
</group>
```

### 配置优先级

```
全局变量 > 环境变量 > 默认值
```

---

## 文件清单

### 需要创建的文件

| 文件 | 说明 |
|------|------|
| `rodski/drivers/base_driver.py` | 驱动基类 |
| `rodski/drivers/desktop_driver.py` | Desktop 驱动 |
| `rodski/vision/__init__.py` | 模块初始化 |
| `rodski/vision/locator.py` | 视觉定位器入口 |
| `rodski/vision/image_matcher.py` | 图片匹配器 |
| `rodski/vision/ocr_locator.py` | OCR 定位器 |
| `rodski/vision/bbox_locator.py` | 坐标定位器 |
| `rodski/vision/omni_client.py` | OmniParser 客户端 |
| `rodski/vision/screenshot.py` | 截图工具 |
| `rodski/vision/coordinate_utils.py` | 坐标工具 |
| `rodski/vision/exceptions.py` | 异常定义 |
| `rodski/vision/cache.py` | 缓存模块 |

### 需要更新的文件

| 文件 | 更新内容 |
|------|---------|
| `rodski/core/keyword_engine.py` | 添加 launch 关键字，修改 type/verify 支持视觉定位器 |
| `rodski/core/driver_factory.py` | 添加 Desktop 驱动创建逻辑 |
| `rodski/drivers/web_driver.py` | 添加视觉定位器支持 |
| `rodski/schemas/model.xsd` | 已更新（添加 vision/ocr/vision_bbox）|

---

**创建日期**: 2026-03-27
**最后更新**: 2026-03-27