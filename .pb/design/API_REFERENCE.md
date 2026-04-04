# OmniParser 远程服务 API 文档

本文档描述了 OmniParser 视觉解析服务的接口规范。

## 快速开始

- **接口地址**: `http://<server_ip>:7862/parse/`
- **请求方法**: `POST`
- **Content-Type**: `application/json`

### 最简请求示例 (推荐)

绝大多数情况下，您只需要发送图片即可，服务端会使用推荐的默认参数（Box=0.18, IOU=0.7）。

```json
{
  "base64_image": "iVBORw0KGgoAAAANSUhEUgAA..."
}
```

## 请求参数详解

### 1. 核心参数 (必填)

| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| `base64_image` | `string` | 待解析图片的 Base64 编码字符串。 |

### 2. 高级调优参数 (选填)

仅在默认效果不佳或需要特定功能（如提取输入框）时使用。

| 字段名 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `return_input_fields` | `false` | **是否提取输入框**。设为 `true` 时，响应中会额外包含 `input_fields` 字段，专门列出用户名/密码等输入框的坐标。 |
| `box_threshold` | `0.18` | **检测灵敏度** (0.0-1.0)。<br>• 调低 (e.g. 0.05)：能检出更多元素，但噪点变多。<br>• 调高 (e.g. 0.30)：只检出最明显的元素，可能漏检。 |
| `iou_threshold` | `0.7` | **重叠过滤** (0.0-1.0)。<br>• 控制重叠框的合并程度，通常保持默认即可。 |
| `merge_ocr_inside_icon` | `true` | **图标文字合并**。<br>• `true`: 将图标内的文字（如按钮上的字）视为图标的一部分。<br>• `false`: 图标和文字作为两个独立元素返回。 |
| `enable_caption` | `false` | **生成描述**。<br>• `true`: 对每个元素生成文字描述（速度较慢）。 |

## 响应结构 (Response)

响应体为 JSON 对象：

```json
{
  "som_image_base64": "...",       // 标注了红框的图片 Base64 (可直接在网页或工具中展示)
  "parsed_content_list": [         // 所有检测到的页面元素列表 (核心数据)
    {
      "type": "text",              // 元素类型: "text" (文本) 或 "icon" (图标)
      "bbox": [0.1, 0.2, 0.3, 0.4],// 归一化坐标 [x1, y1, x2, y2] (0.0~1.0)
      "content": "登录",            // 识别出的文本内容或图标描述
      "interactivity": false,      // 是否可交互 (点击等)
      "source": "box_ocr_content_ocr" // 识别来源
    },
    ...
  ],
  "input_fields": [ ... ],         // (可选) 专门提取的输入框列表，仅当 return_input_fields=true 时返回
  "latency": 0.85                  // 服务端处理耗时 (秒)
}
```

### 1. parsed_content_list 字段详解

这是服务返回的最核心数据，包含了页面上所有被识别出的 UI 元素。

| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| `type` | `string` | **元素类型**。<br>• `"text"`: 文字元素。<br>• `"icon"`: 图标或图片元素。 |
| `bbox` | `array` | **归一化坐标** `[x1, y1, x2, y2]`。<br>• 范围 0.0-1.0，表示相对于图片宽高的比例。<br>• 例如 `[0.5, 0.5, 0.6, 0.6]` 表示在图片中心区域。 |
| `content` | `string` | **识别内容**。<br>• 对于 `text` 类型，是 OCR 识别出的文字。<br>• 对于 `icon` 类型，如果启用了 `enable_caption`，则是图标的描述；否则可能为空或包含简单的分类标签。 |
| `interactivity` | `bool` | **交互性**。<br>• 指示该元素是否可能是一个可点击的控件（如按钮、链接）。 |

### 2. input_fields 字段详解

当请求中 `return_input_fields: true` 时返回，专用于自动化填表场景：

| 字段名 | 说明 |
| :--- | :--- |
| `content` | 输入框用途，如 `"输入框:①用户名/手机号"` |
| `bbox_px` | 像素坐标 `[x1, y1, x2, y2]` |
| `bbox_norm` | 归一化坐标 `[0.1, 0.2, 0.3, 0.4]` |

---

## 调试工具

如需调整参数测试效果，可使用提供的 PowerShell 脚本：

```powershell
# 示例：设置自定义阈值并测试
$env:OMNI_URL='http://14.103.175.167:7862/parse/'; $env:OMNI_IMG='E:\path\to\img.png'; $env:OMNI_BOX='0.18'; python tools/http_test_parse.py
```

## RodSki 集成说明

RodSki 调用 OmniParser 服务实现图像识别定位能力。详细设计请参考：[VISION_LOCATION.md](./VISION_LOCATION.md)
