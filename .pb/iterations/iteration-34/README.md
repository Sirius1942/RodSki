# Iteration 34: 视频录制运行时接入

**版本**: v6.1.5  
**分支**: v6.1.5  
**优先级**: P0  
**状态**: ✅ 已完成  
**日期**: 2026-05-01

---

## 背景

RodSki 已存在 Playwright 录屏器、屏幕录制器与 `assert[type=video]`，但没有统一接入执行生命周期。当前问题包括：录制没有总开关、主执行链不启动录制、Playwright 录制 API 使用不符合原生模式、屏幕录制默认多屏虚拟桌面、视频断言通过“最新 mp4”绑定录制文件。

## 设计问题与决策

1. **总开关**：新增 `recording.enabled`，默认关闭；CLI 提供 `--record` 作为本次执行覆盖。
2. **录制范围**：默认 `scope=target`，无法识别目标时退回主屏；`all_screens` 只允许显式配置。
3. **无头浏览器**：headless + Playwright 使用原生 `record_video_dir`，输出 `.webm`。
4. **真实屏幕**：headed/桌面模式使用 `ScreenRecorder`，输出 `.mp4`。
5. **键盘鼠标**：本迭代不采集原始输入，仅保留结构化事件时间线配置占位。
6. **文件归属**：录制输出到 `result/rodski_*/recordings/`，结果 XML 回填 `recording_path`。
7. **视频断言**：`video_source=recording` 绑定当前用例录制路径，不扫描全局最新文件。

## 范围

- 配置、CLI 与 demo runner 接入
- Executor case 生命周期启动/停止录制
- Playwright 原生录制封装
- ScreenRecorder 多屏选择与帧转换修复
- 结果 XML 记录录制路径
- 单元测试与 rodski-demo 验收

## 非目标

- 不实现 OS 级键盘/鼠标原始输入采集
- 不实现视频叠加事件字幕
- 不强制所有历史 demo 用例加入视频断言

## 验收标准

- ✅ 默认不开启录制时行为不变
- ✅ `--record` 开启后每个用例产生 `recording_path`
- ✅ headless Playwright 使用原生视频录制
- ✅ headed 屏幕录制默认不录所有屏幕
- ✅ `rodski-demo` 可验证录制文件实际生成
- ✅ `video_source=recording` 不再依赖最新文件扫描
