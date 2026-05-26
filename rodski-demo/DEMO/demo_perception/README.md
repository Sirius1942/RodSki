# demo_perception — v7.1.0 纯 vision 定位验收

> 本目录是 **v7.1.0 增强图片识别能力** 迭代的端到端验收用例。
> 所有元素定位**只使用 `<location type="vision">语义描述</location>`**，不依赖
> id / xpath / css 等传统定位器，用来验证 rodski + rodski-perception 集成链路。

## 前置条件

```bash
# 1. ollama
brew install ollama
brew services start ollama
ollama pull qwen3-vl:2b

# 2. rodski-perception（v7.1.0 完成后可用）
pip install rodski[perception]

# 3. 启动测试目标应用
cd rodski-demo/test_app && python -m http.server 8000
```

## 目录结构

```
demo_perception/
├── case/
│   └── tc_vision_only.xml        # 4 个用例（3 个正向 + 1 个错误处理）
├── model/
│   └── model.xml                 # PerceptionLogin / PerceptionForm 模型
├── data/
│   ├── data.sqlite               # 测试数据（PerceptionLogin/Form ± _verify）
│   ├── globalvalue.xml           # backend / model / ollama_host 配置
│   └── build_data.py             # 重新生成 data.sqlite 的脚本
├── plan/
│   └── perception_smoke.xml      # 冒烟计划
├── fun/                          # （留空，TC003 的 run 脚本占位）
└── README.md
```

## 用例清单

| 用例 ID | 标题 | 定位方式 | 验证什么 |
|---------|------|----------|----------|
| TC001 | vision-VLM-单目标-Web 登录 | `vision` | 单元素 VLM locate 链路 |
| TC002 | vision-VLM-批量定位-表单填写 | `vision` × 4 | `locate_many` 批量推理 |
| TC003 | vision_image-模板匹配-离线登录 | `vision_image` × 4 | OpenCV 模板匹配，不依赖 ollama |
| TC004 | 混合优先级-vision_image 优先 VLM 兜底 | `vision_image` p1 + `vision` p2 | priority 顺序回退 |
| TC005 | vision-CLI 子进程-离线截图 | `run` 调 CLI | perception CLI 子进程链路 |
| TC006 | **融合裁决-OCR+vision_image+VLM 并行** | `ocr` + `vision_image` + `vision`（无 priority） | `locate_fused` 共识裁决 |
| TC007 | ollama 不可达-错误处理（默认不执行） | `vision` | 错误信息明确 |
| TC008 | vision_image 参考图不存在（默认不执行） | `vision_image` | 错误信息明确 |

## 运行方式

```bash
# 单文件
rodski run rodski-demo/DEMO/demo_perception/case/tc_vision_only.xml

# 计划方式
rodski run rodski-demo/DEMO/demo_perception/ \
  --plan-id perception_smoke
```

## 验收标准

1. TC001 / TC002 / TC003 全部通过
2. 未安装 rodski-perception 时：用例失败，错误信息含 `PerceptionUnavailableError` 和安装指引
3. 未启动 ollama 时：用例失败，错误信息含 `OllamaUnreachableError`（或 CLI 退出码 3）
4. 模型定义文件中**没有任何**非 vision 类型的 `<location>`（grep 验证）

## 与其他 vision 用例的关系

| 目录 | 用途 | 状态 |
|------|------|------|
| `demo_full/case/tc018_vision.xml` | 旧 OmniParser 服务版本 | `execute="否"`，保留作历史参考 |
| `vision_web/` | 旧 OmniParser + LLM 远程 | 不在 v7.1.0 验收范围 |
| `iteration-01-vision/` | 初代 vision 迭代实验目录 | 不再维护 |
| **`demo_perception/`** | **v7.1.0 LocalBackend 验收** | **当前** |
