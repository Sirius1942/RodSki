# Iteration 34 任务清单

**版本**: v6.1.5  
**分支**: v6.1.5

---

## T34-001: 配置与 CLI 接入

- 新增 `recording` 默认配置
- `run` / `ski_run.py` 增加 `--record` 与录制参数
- demo runner 透传 `--record`

验证：
```bash
python3 rodski/cli_main.py run --help
python3 rodski-demo/DEMO/demo_full/run_demo.py --help
```

## T34-002: 结果目录与结果 XML

- 每次运行创建 `recordings/`
- case result 写入 `recording_path`
- result.xsd 允许 `recording_path`

验证：
```bash
pytest rodski/tests/unit/test_recording_integration.py -v
```

## T34-003: Playwright 原生录制

- 支持 context 级 `record_video_dir`
- 用例结束时保存 `.webm`
- close 关键字触发时仍能 finalize

验证：
```bash
pytest rodski/tests/unit/test_playwright_driver.py -v
```

## T34-004: 屏幕录制 backend

- 修复 mss 帧到 OpenCV 图像转换
- 支持 `target/full_screen/all_screens` 与 `monitor_id`
- 默认主屏/目标屏，不默认全屏虚拟桌面

验证：
```bash
pytest rodski/tests/unit/test_screen_recorder.py -v
```

## T34-005: 视频断言绑定当前录制

- `KeywordEngine` 注入当前录制路径
- `VideoAnalyzer` 不再扫描最新 mp4
- 失败结果回填当前录制路径

验证：
```bash
pytest rodski/tests/unit/test_assertion.py -v
```

## T34-006: rodski-demo 验收

- 使用 demo_full 稳定 Web 用例验证 headless Playwright 原生录制
- 使用 `tc041_desktop_recording.xml` 验证 macOS 桌面屏幕录制
- 可选使用 `tc040_vscode_plugin.xml` 做桌面复杂场景补充

验证：
```bash
python3 rodski-demo/DEMO/demo_full/run_demo.py --case case/tc015_only.xml --headless --record
python3 rodski-demo/DEMO/demo_full/run_demo.py --case case/tc041_desktop_recording.xml --record --record-mode screen
```
