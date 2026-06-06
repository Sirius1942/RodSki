# 视觉定位器现状（覆盖 guide 11.4 的过时信息）

仅当传统 DOM 定位器无法表达元素（动态 canvas、无稳定属性、跨语言 UI、桌面端），或用户明确要求
视觉定位时读本文。默认走 `element-probe.md` + `style.md` 阶梯的传统定位器。

## 重要：guide 11.4 已过时

`TEST_CASE_WRITING_GUIDE.md` §11.4 描述的 **OmniParser 服务 + `vision_config.yaml`** 配置方式，
在 RodSki **v7.1.0 已删除**。本机实测（rodski 7.1.5，安装于
`$HOME/.local/share/rodski/venv`）：

- `vision/locator.py` 加载配置时会**直接丢弃 `omniparser` 段**（源码注释：v7.1.0 起 OmniClient 已删除）。
- `vision_config.yaml` 在本机**不存在**，跑的是源码内置默认值。
- guide 是只读参考，不要去改它；以本文和当前 CLI/源码为准。

语义 `vision` 现在改走 **PerceptionRegistry entry_points 机制**（group `rodski.perception_backends`，
实现位于 `rodski.vision.registry`），rodski 核心不再硬编码任何 backend。

## 本机视觉定位器可用性（实测）

`rodski capabilities` 暴露 4 种视觉 locator type，本机实际状态：

| type | 机制 | 本机状态 | 用法 |
|------|------|---------|------|
| `vision` | 语义描述 → PerceptionBackend.locate | ❌ **无 backend** | 需先装 perception backend，否则抛 `PerceptionUnavailableError` |
| `vision_image` | OpenCV 模板匹配 | ✅ 可用（cv2 已装） | `<location type="vision_image">images/login_btn.png</location>` + 提供参考图 |
| `vision_bbox` | 固定像素坐标 | ✅ 可用 | `<location type="vision_bbox">x1,y1,x2,y2</location>`，脆，仅最后手段 |
| `ocr` | 文字识别 | ⚠️ 需注入 OCR provider | 当前未接 provider，调用会报清晰错误 |

`PerceptionRegistry.discover()` 本机返回**零个 backend**（7.1.5 复测，`importlib.metadata` entry_points group `rodski.perception_backends` 为空），所以语义 `vision` 现在不能直接用。

## 启用语义 vision（如果用户要走方向 B）

语义视觉定位需要安装一个 perception backend 并注册 entry_point：

```toml
[project.entry-points."rodski.perception_backends"]
local = "rodski_perception.backend:LocalPerceptionBackend"
```

候选：`rodski[perception]` extra，或本地 ollama 多模态 backend。装好后用
`RODSKI_PERCEPTION_BACKEND` 环境变量或 model 配置选 backend。启用前先和用户确认，因为每次
locate 都有模型推理开销，比 DOM 定位慢。这属于显式环境配置，不是普通用例编写。

## vision_image（开箱可用的视觉兜底）

无需 backend，纯 OpenCV：

1. 截目标控件的参考图，存到模块下 `images/`（默认 `images_dir`）。
2. `<location type="vision_image">images/<name>.png</location>`。
3. 默认匹配阈值 `match_threshold=0.85`。

适合：图标按钮、固定外观控件、传统定位器全失败但外观稳定的元素。
不适合：随主题/分辨率/缩放变化外观的元素。

## 选型顺序

1. 传统 DOM 定位器（探查后写 css/id/text）—— 默认。
2. `vision_image` —— DOM 无属性但外观稳定。
3. `vision`（语义）—— 需先装 backend；动态/跨语言/canvas。
4. `ocr` —— 需先接 provider；纯文字定位。
5. `vision_bbox` —— 固定坐标，最后手段。

不要因为单次 locate 失败就跳到视觉定位；先按 `element-probe.md` 探查，确认不是选择器错或页面未就绪。
