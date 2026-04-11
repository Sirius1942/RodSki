# TC018 视觉定位功能测试说明

## 概述

TC018 展示 RodSki 的视觉定位能力，包括语义定位和坐标定位两种模式。

## 前置要求

**重要**: TC018 需要 OmniParser 服务支持，默认不执行（execute="否"）。

### OmniParser 服务

OmniParser 是基于 YOLO 实现的视觉解析服务，提供页面元素坐标识别能力。

**启动方式**:
```bash
# 启动 OmniParser 服务（默认端口 8080）
python -m omniparser.server --port 8080
```

**服务配置**:
在 RodSki 配置文件中设置 OmniParser 服务地址：
```yaml
vision:
  omniparser_url: http://localhost:8080
  llm_provider: claude  # 或 gpt4v, qwen-vl
```

## 测试内容

### 1. 语义定位 (vision)

使用自然语言描述定位元素：

```xml
<model name="VisionLogin" type="ui" servicename="">
    <element name="username" type="input">
        <location type="vision">用户名输入框</location>
    </element>
    <element name="password" type="input">
        <location type="vision">密码输入框</location>
    </element>
    <element name="loginBtn" type="button">
        <location type="vision">登录按钮</location>
    </element>
</model>
```

**工作流程**:
1. 截图当前页面
2. 调用 OmniParser 获取所有元素坐标
3. 使用多模态 LLM 进行语义匹配
4. 返回目标元素坐标并执行操作

### 2. 坐标定位 (vision_bbox)

直接使用坐标定位元素：

```xml
<model name="VisionCoordinate" type="ui" servicename="">
    <element name="username" type="input">
        <location type="vision_bbox">100,200,300,230</location>
    </element>
    <element name="submitBtn" type="button">
        <location type="vision_bbox">150,250,250,280</location>
    </element>
</model>
```

**坐标格式**: `x1,y1,x2,y2` (左上角x, 左上角y, 右下角x, 右下角y)

## 执行测试

### 启用 TC018

修改 `tc018_vision.xml`：
```xml
<case execute="是" id="TC018" title="视觉定位功能测试" component_type="界面">
```

### 运行测试

```bash
cd rodski-demo/DEMO/demo_full
python -m rodski.main --case case/tc018_vision.xml
```

## 适用场景

### 语义定位适用于：
- 动态页面（元素 ID 经常变化）
- 无明确定位器的元素
- 跨平台测试（Web/Desktop）
- 快速原型开发

### 坐标定位适用于：
- 固定布局的页面
- 性能要求高的场景（跳过 LLM 调用）
- 桌面应用自动化
- 游戏 UI 测试

## 注意事项

1. **性能**: 视觉定位比传统定位器慢，建议仅在必要时使用
2. **稳定性**: 页面布局变化会影响坐标定位准确性
3. **成本**: 语义定位需要调用多模态 LLM，有 API 成本
4. **依赖**: 确保 OmniParser 服务可用且网络连接正常

## 参考文档

- `rodski/docs/VISION_LOCATION.md` - 视觉定位设计文档
- `rodski/docs/SKILL_REFERENCE.md` - 关键字参考
