# 迭代 01 - 视觉定位技术设计

**版本**: v1.0
**日期**: 2026-03-20
**对齐**: 核心设计约束 v3.6

## 架构设计

### 整体架构

```
┌─────────────────────────────────────────────────┐
│           RodSki Keyword Engine                 │
│  (type/verify 关键字识别 vision 定位器)         │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│           VisionLocator (统一入口)              │
│  - 解析 locator 格式                            │
│  - 分发到 vision 或 vision_bbox 分支            │
└────────────┬────────────────────────────────────┘
             │
    ┌────────┴────────┐
    ▼                 ▼
┌─────────┐      ┌──────────┐
│ vision: │      │vision_bbox│
│ 语义分支 │      │ 坐标分支  │
└────┬────┘      └─────┬────┘
     │                 │
     ▼                 ▼
  截图+AI          直接计算中心点
```

## 模块划分

### 核心模块 (rodski/vision/)

| 模块 | 文件 | 职责 |
|------|------|------|
| 统一入口 | `locator.py` | 解析 locator，分发到不同分支 |
| OmniParser客户端 | `omni_client.py` | 调用 OmniParser HTTP 服务 |
| LLM分析器 | `llm_analyzer.py` | 多模态 LLM 语义识别 |
| 语义匹配器 | `matcher.py` | 匹配目标元素 |
| 截图工具 | `screenshot.py` | Web/Desktop 截图 |
| 坐标工具 | `coordinate_utils.py` | 坐标转换和计算 |
| 桌面驱动 | `desktop_driver.py` | pyautogui 封装 |
| 异常处理 | `exceptions.py` | 视觉定位专用异常 |
| 缓存 | `cache.py` | 结果缓存（30s TTL）|

## 接口设计

### VisionLocator 核心接口

```python
class VisionLocator:
    def __init__(self, config=None, global_vars=None):
        """初始化视觉定位器"""

    def is_vision_locator(self, locator_str: str) -> bool:
        """判断是否为视觉定位器"""

    def locate(self, locator_str: str, driver=None) -> tuple[int, int]:
        """定位元素，返回 (cx, cy) 坐标"""
```

### LLMAnalyzer 接口

```python
class LLMAnalyzer:
    def __init__(self, config=None, global_vars=None):
        """支持 Claude/OpenAI/Qwen"""

    def analyze(self, screenshot_path: str, elements: list) -> list:
        """为元素添加语义标签"""
```

## 数据结构

### OmniParser 返回格式

```python
{
    "parsed_content_list": [
        {
            "content": "Login",
            "type": "button",
            "bbox": [0.1, 0.2, 0.15, 0.25]  # 归一化坐标
        }
    ]
}
```

### LLM 增强后格式

```python
{
    "content": "Login",
    "type": "button",
    "bbox": [0.1, 0.2, 0.15, 0.25],
    "semantic_label": "登录按钮"  # LLM 添加
}
```

## 关键决策

### 1. 定位器格式统一
- 使用 `locator` 属性，不新增关键字
- 格式：`vision:描述` 和 `vision_bbox:x1,y1,x2,y2`

### 2. 桌面操作通过 run
- 不为桌面操作新增关键字
- 脚本放在 `fun/desktop/` 目录

### 3. launch 关键字
- 与 navigate 功能相同，场景不同
- 算作一个关键字（场景化变体）

### 4. 配置优先级
- 全局变量 > 环境变量 > yaml > 默认值
- 支持多种 LLM 自动切换

---

**创建日期**: 2026-03-27

