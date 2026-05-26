# rodski-perception

GUI 元素感知 — rodski v7.1.0 的 perception backend，基于本地 **ollama + VLM (Qwen3-VL)** 实现"截图 + 自然语言 → 元素坐标"的定位能力。

## 定位

`rodski-perception` 是 **rodski** 的可选插件，通过 Python `entry_points` 注册一个 `LocalPerceptionBackend`，被 rodski 在运行时自动发现。也可以独立作为 CLI / Python 工具使用，用于截图分析、模型评测等场景。

> 同迭代相关接口契约在 rodski 主仓 `rodski/vision/perception_interface.py`，参见 [设计文档](../.pb/specs/v7.1.0-perception-design.md)。

## 前置依赖

需要先安装并启动 ollama，并 pull 一个支持视觉的模型：

```bash
# macOS
brew install ollama
brew services start ollama
ollama pull qwen3-vl:2b      # 1.9GB，M4 Pro 推理约 5-8s

# Linux
curl -fsSL https://ollama.com/install.sh | sh
ollama serve &
ollama pull qwen3-vl:2b
```

`rodski-perception` 本身**不会**主动启动 ollama，运行时仅做可达性检查。

## 安装

```bash
# 从源码（与 rodski 同仓时）
pip install -e ./rodski-perception/

# 或与 rodski 一起：
pip install "rodski[perception]"
```

安装后会自动注册：
- 命令行：`rodski-perception`
- entry_point：`rodski.perception_backends` 下的 `local` 项

## Python API

```python
from rodski_perception import VLMAgent, ImageParser

agent = VLMAgent(model="qwen3-vl:2b", ollama_host="http://localhost:11434")

# 单目标定位
result = agent.locate(prompt="登录按钮", image="screenshot.png", element_type="button")
print(result.bbox)         # (x1, y1, x2, y2) 千分比 [0, 1000]
print(result.coordinates)  # (x, y) 像素中心点
print(result.latency_ms)   # 本次 ollama 推理耗时

# 批量定位（单次推理拿 N 个 bbox）
results = agent.locate_many(
    prompts=["用户名输入框", "密码输入框", "登录按钮"],
    image="screenshot.png",
)
for r in results:
    if r:
        print(f"{r.target_description}: {r.coordinates}")
    else:
        print("not found")

# 全量解析（不带 prompt，列出所有可交互元素）
parsed = ImageParser(model="qwen3-vl:2b").parse("screenshot.png")
for e in parsed.elements:
    print(f"[{e.kind}] {e.label} bbox={e.bbox}")
```

`import rodski_perception` 是廉价的：构造 `VLMAgent` 不联网、不加载模型；首次 `locate()` 调用才会触发 ollama HTTP 请求。

## CLI

```bash
# 列出 ollama 中已安装的 VL 模型
rodski-perception models

# 单目标定位
rodski-perception locate --image screenshot.png \
  --prompt "登录按钮" \
  --element-type button \
  --output json

# 批量定位（多个 --prompt 或 --prompts-file）
rodski-perception locate --image screenshot.png \
  --prompt "用户名" --prompt "密码" --prompt "登录" \
  --output json

# 从文件批量
rodski-perception locate --image screenshot.png \
  --prompts-file prompts.txt --output json

# 全量解析
rodski-perception parse --image screenshot.png --output json

# 版本
rodski-perception --version
```

### 输出格式（locate 单目标）

```json
{
  "target_description": "登录按钮",
  "bbox": [550, 720, 970, 780],
  "coordinates": [760, 750],
  "image_size": [1080, 1920],
  "label": "login",
  "confidence": null,
  "latency_ms": 5800,
  "model": "qwen3-vl:2b"
}
```

### 输出格式（locate 多目标）

```json
{
  "image_size": [1080, 1920],
  "latency_ms": 6200,
  "model": "qwen3-vl:2b",
  "results": [
    {"target_description": "用户名", "bbox": [...], "coordinates": [...]},
    {"target_description": "密码",   "bbox": [...], "coordinates": [...]},
    {"target_description": "提交",   "bbox": null, "coordinates": null, "error": "not found"}
  ]
}
```

### 退出码

| 退出码 | 含义 |
|--------|------|
| `0`    | 成功（即使部分目标未找到，只要请求完成都算成功） |
| `1`    | 推理失败：模型输出无法解析，stderr 含原始响应 |
| `2`    | 参数错误：缺少必填参数 / 文件不存在 / `--prompt` 与 `--prompts-file` 互斥 |
| `3`    | ollama 服务不可达：连接错误或非 200 响应 |
| `4`    | 模型未安装：请运行 `ollama pull <model>` |

## 与 rodski 集成

rodski 通过 `PerceptionRegistry.discover()` 扫描 `rodski.perception_backends` entry_points 自动发现本包注册的 `LocalPerceptionBackend`：

```toml
# rodski-perception/pyproject.toml
[project.entry-points."rodski.perception_backends"]
local = "rodski_perception.backend:LocalPerceptionBackend"
```

rodski 用例 XML 中使用 `<location type="vision">语义描述</location>` 即可触发本 backend：

```xml
<element name="loginBtn" type="button">
    <location type="vision">登录按钮</location>
</element>
```

`element.type` 会作为 `element_type` 先验传给 backend，注入到 VLM prompt 中以改善定位精度。

## 测试

```bash
# 单元测试（CI 友好，mock ollama）
pytest tests/unit/ -v

# 集成测试（需要 ollama 在跑 + qwen3-vl:2b 已安装）
pytest tests/integration/ -v

# 全部
pytest tests/ -v
```

`tests/conftest.py` 在 ollama 不可达时会自动跳过带 `@pytest.mark.requires_ollama` 标记的集成测试。

## 配置项

| 配置 | 默认 | 说明 |
|------|------|------|
| `model` / `perception_model` | `qwen3-vl:2b` | ollama 中已 pull 的 VLM 模型名 |
| `ollama_host` / `perception_server` | `http://localhost:11434` | ollama 服务地址 |
| `RODSKI_PERCEPTION_MODEL` (env) | — | 覆盖默认模型 |
| `OLLAMA_HOST` (env) | — | 覆盖默认服务地址 |

CLI 接受 `--model` / `--ollama-host`；rodski 通过 `globalvalue.xml` 的 `perception_model` / `ollama_host` 变量透传。

## 错误处理

| 场景 | 抛出 |
|------|------|
| ollama 未启动 / 连不上 | `OllamaUnreachableError` |
| 模型未 pull | `ModelNotFoundError` |
| 模型输出非 JSON / 不含 bbox | `InvalidResponseError` |
| 图片文件不存在 | `FileNotFoundError` |

CLI 把上述异常映射为对应退出码（见上表），rodski 侧统一转成 `PerceptionUnavailableError`（含可操作的修复指引）。

## 架构边界

- **不暴露 HTTP 服务**：本包只是 CLI + Python 库
- **不提供 UI**
- **不主动管理 ollama 进程**：假设外部已启动
- **不实现融合裁决**：`locate_fused` 留给 iteration-54d；本迭代 backend 继承父类默认实现

## 路线图

- `v0.2.0` (iteration-54c) — 本版本，CLI + Python API + LocalBackend ✓
- `v0.3.0` (iteration-54d) — 融合裁决 `FusionLocator`、`rodski-perception eval` 实现
- `v0.x`   — RemoteBackend（独立项目 `rodski-omni-client`）

## 许可

MIT。归属 RodSki 项目，与 rodski 主仓共生命周期。
