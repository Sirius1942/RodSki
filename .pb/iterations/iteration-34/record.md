# Iteration 34 执行记录

## 2026-05-01

### 已确认问题

- 主执行链没有启动/停止视频录制。
- Playwright 录制实现使用了非标准 page-level API。
- `ScreenRecorder` 默认使用 `sct.monitors[0]`，会录制所有屏幕组成的虚拟桌面。
- `ScreenRecorder` 使用不存在的 `cv2.array_to_img`。
- `assert[type=video,video_source=recording]` 通过最新 mp4 查找录制文件，存在跨用例污染。
- 结果 XML 没有 `recording_path`。

### 当前实现方向

- `recording.enabled` + `--record` 控制录制。
- `SKIExecutor` 统一管理 case 级录制生命周期。
- headless Playwright 使用原生 `record_video_dir`。
- headed/桌面使用 `ScreenRecorder`，默认目标/主屏。
- 录制产物统一输出到 run 目录 `recordings/`。

### 已完成实现

- `rodski/core/config_manager.py` 与 `rodski/config/config.json` 增加 recording 默认配置。
- `rodski/rodski_cli/run.py`、`rodski/ski_run.py`、`rodski/cli_main.py`、`rodski/rodski_cli/init.py`、`rodski/rodski_cli/data_import.py` 增加直接运行/包导入兼容与录制参数接入。
- `rodski/core/ski_executor.py` 在 case 生命周期中启动/停止录制，并将 `recording_path` 回填到结果。
- `rodski/drivers/playwright_driver.py` 支持 Playwright 原生 case 级录制。
- `rodski/vision/screen_recorder.py` 修复帧转换并支持 target/all_screens/monitor_id。
- `rodski/core/keyword_engine.py` 与 `rodski/core/assertion/video_analyzer.py` 改为绑定当前录制路径。
- `rodski/core/result_writer.py` 与 `rodski/schemas/result.xsd` 支持 `recording_path`。
- `rodski/requirements.txt` 补充了 `numpy`、`opencv-python`、`mss`。
- `.pb/iterations/iteration-34/` 已创建并登记。

### 单元测试结果

已通过：

```bash
PYTHONPATH=rodski pytest rodski/tests/unit/test_recording_integration.py \
  rodski/tests/unit/test_playwright_driver.py \
  rodski/tests/unit/test_screen_recorder.py \
  rodski/tests/unit/test_assertion.py \
  rodski/tests/unit/test_auto_screenshot.py \
  rodski/tests/unit/test_ski_executor.py -v
```

结果：`125 passed`

### Demo 验证结果

已通过 headless Playwright 原生录制验证：

```bash
python3 rodski/cli_main.py run \
  rodski-demo/DEMO/demo_full/case/demo_case.xml \
  --headless --record --record-mode playwright
```

结果目录：`rodski-demo/DEMO/demo_full/result/rodski_20260501_174135/`

关键证据：
- `result.xml` 中每个用例都有 `recording_path="recordings/...webm"`
- `recordings/` 目录下生成了 `.webm` 文件
- `execution.log` 中可见 `Playwright 原生录制已启动/已保存`

随后补充验证了 `rodski-demo/DEMO/demo_full/run_demo.py --case case/tc015_only.xml --headless --record`，同样生成了 `recording_path` 与 `.webm` 文件：

- 结果目录：`rodski-demo/DEMO/demo_full/result/rodski_20260501_174852/`
- `result.xml` 中 `TC015` 的 `recording_path="recordings/TC015_20260501_174852.webm"`

### 2026-05-01 留存问题

- headed 真实屏幕录制当日尚未实测。
- `selftest.py` 当日仍有历史失败点。

上述问题已在 2026-05-04 发布前收口中重新验证或修复。

## 2026-05-04 发布前收口

### 修复项

- 修复基础 `pip install rodski` 后 CLI 导入失败：视觉/视频断言延迟依赖检查，不再在未安装 `numpy/opencv` 时因类型注解崩溃。
- 修复 pip 安装后的源码布局导入问题：CLI 与核心运行路径优先使用包内相对导入，保留源码运行回退。
- 删除旧的 `rodski/setup.py`，以根目录 `pyproject.toml` 作为唯一打包入口；发布包不再包含旧 `setup.py` 与旧包内 README。
- 修复失败路径截图时机：用例阶段失败后先截图，再执行后处理，避免 `close` 后无法保留失败截图。
- 修复 SQLite schema 校验与契约不一致：每行字段集合必须与 schema 完全一致，缺字段/多余字段均报错。

### 验证结果

已通过：

```bash
PYTHONPATH=rodski python3 -m pytest rodski/tests/unit -q
```

结果：`1459 passed, 3 xfailed`

已通过 6.1.5 重点录制单测：

```bash
PYTHONPATH=rodski python3 -m pytest \
  rodski/tests/unit/test_recording_integration.py \
  rodski/tests/unit/test_playwright_driver.py \
  rodski/tests/unit/test_screen_recorder.py \
  rodski/tests/unit/test_assertion.py \
  rodski/tests/unit/test_auto_screenshot.py \
  rodski/tests/unit/test_ski_executor.py -q
```

结果：`125 passed`

已通过打包校验：

```bash
python3 -m build
python3 -m twine check dist/*
```

已通过隔离安装：

- wheel：`rodski --version`、`rodski run --help`、demo `--dry-run` 均通过。
- sdist：`rodski --version`、`rodski run --help` 均通过。

已通过 demo 验收：

- 默认关闭：`run_demo.py --case case/tc015_only.xml --headless`，结果 `recording_path=""`。
- Playwright 原生录制：`run_demo.py --case case/tc015_only.xml --headless --record --record-mode playwright`，生成 `.webm` 并回填 `recording_path`。
- 屏幕录制：`run_demo.py --case case/tc041_desktop_recording.xml --record --record-mode screen`，生成 `.mp4` 并回填 `recording_path`。
- 失败路径：通过 `--insert-step type,NonExistentModel,E001` 触发失败，`result.xml` 同时保留 `screenshot_path` 与 `recording_path`。
