# Iteration 03 设计文档

## 1. VisionLocator 导入修复

**问题**: `locator.py` 导入已删除的 `image_matcher.py`

**方案**:
- 更新 `VisionLocator.image_matcher` property
- 指向 `matcher.py` 中的 `VisionMatcher`

## 2. BaseDriver 接口重构

**问题**: 坐标接口与定位器接口混淆

**方案 A**: 分离接口
```python
# 坐标操作
def click_at(x: int, y: int)
def type_at(x: int, y: int, text: str)

# 定位器操作
def click(locator: str)
def type(locator: str, text: str)
```

**方案 B**: 统一为坐标接口
- 所有操作都基于坐标
- 定位器先转换为坐标

**选择**: 方案 B（符合核心设计约束）
