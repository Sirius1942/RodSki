# Iteration 34 验收测试

## A1 默认关闭

步骤：运行任意现有用例，不加 `--record`。  
期望：不启动录制；结果 XML 中 `recording_path` 为空；既有截图行为不变。

## A2 headed 屏幕录制

步骤：运行 `rodski-demo/DEMO/demo_full/run_demo.py --case case/demo_case.xml --record`。  
期望：`result/rodski_*/recordings/` 下生成 `.mp4`；录制范围不是默认全显示器拼接。

## A3 桌面场景录制

步骤：在带图形界面的桌面环境中运行 `rodski-demo/DEMO/demo_full/case/tc041_desktop_recording.xml`，并指定 `--record --record-mode screen`。如需扩展场景，再跑 `tc040_vscode_plugin.xml`。  
期望：桌面操作期间生成 `.mp4`；`result.xml` 回填 `recording_path`；不会因为只录屏幕而丢失桌面场景。

## A4 headless Playwright 原生录制

步骤：运行 `python3 rodski/cli_main.py run rodski-demo/DEMO/demo_full/case/demo_case.xml --headless --record`。  
期望：`result/rodski_*/recordings/` 下生成 `.webm`；result.xml 回填 `recording_path`。

## A5 失败路径

步骤：执行一个失败用例且开启 `--record`。  
期望：失败截图和录制路径都保留；录制失败本身不导致用例失败原因被覆盖。

## A6 视频断言绑定

步骤：构造 `assert[type=video,video_source=recording]` 单元测试。  
期望：断言使用当前用例录制路径，不读取 `images/assert/recordings` 下最新文件。

## 验收结果

**日期**: 2026-05-04  
**状态**: ✅ 通过

| 验收项 | 结果 | 证据 |
|---|---|---|
| A1 默认关闭 | ✅ 通过 | `run_demo.py --case case/tc015_only.xml --headless`，`recording_path=""` |
| A2/A3 屏幕录制 | ✅ 通过 | `tc041_desktop_recording.xml --record --record-mode screen`，生成 `.mp4` 且 result 回填 |
| A4 headless Playwright 录制 | ✅ 通过 | `tc015_only.xml --headless --record --record-mode playwright`，生成 `.webm` 且 result 回填 |
| A5 失败路径 | ✅ 通过 | 注入失败步骤后 `screenshot_path` 与 `recording_path` 均存在 |
| A6 视频断言绑定 | ✅ 通过 | `test_assertion.py::TestVideoAssertIntegration::test_video_assert_uses_current_recording_path` |
