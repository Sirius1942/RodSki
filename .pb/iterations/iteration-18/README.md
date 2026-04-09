# Iteration 18: 桌面自动化 + 多窗口

**版本**: v4.10.0  
**分支**: release/v4.10.0  
**日期**: 2026-04-09  
**工时**: 4.5h  
**优先级**: P0  
**前置依赖**: iteration-17

---

## 目标

添加桌面自动化和多窗口测试功能：
1. 创建 TC019 桌面应用自动化测试
2. 创建 TC020 多窗口和 iframe 测试

---

## 任务清单

### T18-001: TC019 桌面应用自动化测试 (2.5h)

**文件**: 
- `rodski-demo/DEMO/demo_full/case/tc019_desktop.xml`
- `rodski-demo/DEMO/demo_full/fun/desktop_ops/type_text.py`
- `rodski-demo/DEMO/demo_full/fun/desktop_ops/key_combo.py`
- `rodski-demo/DEMO/demo_full/fun/desktop_ops/mouse_click.py`

**任务**:
1. 创建测试用例 TC019
2. 创建桌面操作脚本：
   - type_text.py - 输入文本
   - key_combo.py - 快捷键组合
   - mouse_click.py - 鼠标点击
3. 添加平台特定示例（Windows/macOS）

**验收**:
- launch 可以启动应用
- run 可以执行脚本
- 脚本支持 Windows/macOS
- 文档说明平台差异

---

### T18-002: TC020 多窗口和 iframe 测试 (2h)

**文件**: 
- `rodski-demo/DEMO/demo_full/case/tc020_windows.xml`
- `rodski-demo/DEMO/demo_full/fun/switch_window.py`
- `rodski-demo/DEMO/demo_full/fun/switch_frame.py`
- `rodski-demo/DEMO/demo_full/model/model.xml`
- `rodski-demo/DEMO/demo_full/data/WindowTest.xml`

**任务**:
1. 创建测试用例 TC020
2. 创建窗口切换脚本
3. 创建 iframe 切换脚本
4. 添加相关模型和数据

**验收**:
- 可以切换窗口
- 可以切换 iframe
- 验证通过

---

## 验收标准

- [ ] TC019 桌面自动化可用
- [ ] TC020 窗口切换正常
- [ ] iframe 切换正常
- [ ] 所有测试用例通过
- [ ] 无回归问题

---

## 工作流程

1. 确认 iteration-17 已完成
2. 创建分支: `git checkout -b release/v4.10.0`
3. 执行 T18-001
4. 执行 T18-002
5. 运行回归测试
6. 更新 record.md
7. 合并到 main: `git merge release/v4.10.0`
8. 打标签: `git tag v4.10.0`

---

## 参考文档

- `.pb/iterations/iteration-14-19-plan.md` - 总体规划
- `rodski/docs/TEST_CASE_WRITING_GUIDE.md` - 用例编写指南
