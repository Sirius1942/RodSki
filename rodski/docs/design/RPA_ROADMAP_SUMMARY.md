# RodSki RPA 能力提升路线图总结

**版本**: v1.0
**日期**: 2026-03-25

## 概述

本文档总结了 RodSki 与主流 RPA 系统的差距分析及补充方案。

---

## 📋 相关文档

1. **[RPA_GAP_ANALYSIS.md](./RPA_GAP_ANALYSIS.md)** - 差距分析
   - 与 UiPath/AA/Power Automate 的功能对比
   - 核心缺失功能清单
   - 优先级评估

2. **[PC_AUTOMATION_ENHANCEMENT.md](./PC_AUTOMATION_ENHANCEMENT.md)** - PC 自动化增强
   - Windows 增强方案 (PyWinAuto)
   - macOS 支持方案 (pyobjc + Accessibility API)
   - 实施计划 (4 周)

3. **[LLM_VISION_LOCATOR_DESIGN.md](./LLM_VISION_LOCATOR_DESIGN.md)** - LLM 视觉定位
   - 架构设计
   - 多提供商支持 (OpenAI/Anthropic/Google)
   - 成本优化策略

---

## 🎯 核心发现

### 主要差距
1. 🔴 **macOS 桌面自动化完全缺失**
2. 🔴 **图像识别和 LLM 视觉定位缺失**
3. 🟡 **Windows 桌面自动化功能过于基础**
4. 🟡 **缺少 OCR、剪贴板等高级功能**

### 竞争优势
- ✅ 轻量级、开源、Python 生态
- ✅ 关键字驱动，学习曲线平缓
- ✅ 多平台统一框架 (Web/Mobile/Desktop)

---

## 🚀 实施路线

### 短期 (1-2 个月)
- **Windows 增强**: 多种定位、键盘、剪贴板、窗口管理
- **macOS 基础**: 应用控制、元素定位、键盘操作

### 中期 (3-4 个月)
- **LLM 视觉定位**: OpenAI/Anthropic 集成
- **图像识别**: OpenCV 模板匹配
- **缓存优化**: 降低 LLM 调用成本

### 长期 (6+ 个月)
- **本地视觉模型**: 零成本方案
- **OCR 集成**: 文字识别能力
- **录制回放**: GUI 录制生成用例

---

## 💡 战略建议

1. **差异化竞争**: 以 AI-First 为核心，深度集成 LLM
2. **开源生态**: 建立插件体系，吸引社区贡献
3. **成本优势**: 提供本地模型选项，降低使用门槛

---

## 📊 投入估算

| 阶段 | 工作量 | 优先级 |
|------|--------|--------|
| Windows 增强 | 1 周 | P0 |
| macOS 基础 | 2.5 周 | P0 |
| LLM 视觉定位 | 4 周 | P1 |
| 图像识别 | 2 周 | P1 |
| OCR 集成 | 1 周 | P2 |

**总计**: 约 10.5 周 (2.5 个月)

---

## 下一步行动

1. 评审三份设计文档
2. 确定优先级和资源分配
3. 启动 Phase 1 开发 (Windows + macOS)
