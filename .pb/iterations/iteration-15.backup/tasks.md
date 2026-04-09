# Iteration 15: rodski-demo 全功能覆盖 — 任务清单

## 阶段一: P0 核心功能补充

### T15-001: 扩展 demosite 测试页面
**文件**: `rodski-demo/DEMO/demo_full/demosite/app.py`

- 添加文件上传页面 (`/upload`)
- 添加定位器测试页面 (`/locator-test`)
- 添加多窗口测试页面 (`/multi-window`)
- 添加 iframe 测试页面 (`/iframe-test`)

**预计**: 3h | **Owner**: 待分配

---

### T15-002: TC016 - 定位器类型覆盖测试
**文件**: 
- `rodski-demo/DEMO/demo_full/case/tc016_locators.xml`
- `rodski-demo/DEMO/demo_full/model/model.xml`
- `rodski-demo/DEMO/demo_full/data/LocatorTest*.xml`

- 创建测试用例 TC016
- 添加 XPath、Name、CSS 定位器模型
- 添加测试数据和验证数据

**预计**: 2h | **Owner**: 待分配

---

### T15-003: TC017 - 关键字完整覆盖测试
**文件**: 
- `rodski-demo/DEMO/demo_full/case/tc017_keywords.xml`
- `rodski-demo/DEMO/demo_full/model/model.xml`
- `rodski-demo/DEMO/demo_full/data/KeywordTest*.xml`

- 创建测试用例 TC017
- 覆盖 wait、clear、screenshot、assert、upload_file
- 添加相关模型和数据

**预计**: 2.5h | **Owner**: 待分配

---

### T15-004: TC018 - 视觉定位功能测试（可选）
**文件**: 
- `rodski-demo/DEMO/demo_full/case/tc018_vision.xml`
- `rodski-demo/DEMO/demo_full/model/model.xml`
- `rodski-demo/DEMO/demo_full/data/VisionLogin*.xml`

- 创建测试用例 TC018
- 添加 vision 和 vision_bbox 定位器模型
- 添加说明文档（需要 OmniParser 服务）

**预计**: 1.5h | **Owner**: 待分配

---

### T15-005: TC019 - 桌面应用自动化测试
**文件**: 
- `rodski-demo/DEMO/demo_full/case/tc019_desktop.xml`
- `rodski-demo/DEMO/demo_full/fun/desktop_ops/`

- 创建测试用例 TC019
- 创建桌面操作脚本（type_text.py、key_combo.py、mouse_click.py）
- 添加平台特定示例（Windows/macOS）

**预计**: 2.5h | **Owner**: 待分配

---

## 阶段二: P1 高级特性补充

### T15-006: TC020 - 多窗口和 iframe 测试
**文件**: 
- `rodski-demo/DEMO/demo_full/case/tc020_windows.xml`
- `rodski-demo/DEMO/demo_full/fun/switch_window.py`
- `rodski-demo/DEMO/demo_full/fun/switch_frame.py`

- 创建测试用例 TC020
- 创建窗口切换脚本
- 创建 iframe 切换脚本

**预计**: 2h | **Owner**: 待分配

---

### T15-007: TC021 - 复杂数据引用测试
**文件**: 
- `rodski-demo/DEMO/demo_full/case/tc021_data_ref.xml`
- `rodski-demo/DEMO/demo_full/model/model.xml`
- `rodski-demo/DEMO/demo_full/data/DataRefTest*.xml`

- 创建测试用例 TC021
- 覆盖 GlobalValue、Return 嵌套、命名变量访问
- 添加相关模型和数据

**预计**: 1.5h | **Owner**: 待分配

---

### T15-008: TC022-024 - 负面测试集合
**文件**: 
- `rodski-demo/DEMO/demo_full/case/tc022_negative.xml`
- `rodski-demo/DEMO/demo_full/model/model.xml`
- `rodski-demo/DEMO/demo_full/data/ErrorTest*.xml`

- TC022: 元素不存在测试 (expect_fail="是")
- TC023: 接口错误响应测试 (expect_fail="是")
- TC024: SQL 语法错误测试 (expect_fail="是")

**预计**: 1.5h | **Owner**: 待分配

---

## 阶段三: 文档与验证

### T15-009: 更新文档
**文件**: 
- `rodski-demo/DEMO/demo_full/README.md`
- `rodski-demo/DEMO/demo_full/COVERAGE.md` (新建)

- 更新 README.md（补充新增用例、功能覆盖矩阵）
- 创建 COVERAGE.md（详细功能覆盖说明）

**预计**: 1.5h | **Owner**: 待分配

---

### T15-010: 完整回归测试
**文件**: 所有测试用例

- 运行所有现有测试用例（TC001-TC015）
- 运行所有新增测试用例（TC016-TC024）
- 验证功能覆盖率达到 90%+
- 检查测试报告

**预计**: 2h | **Owner**: 待分配

---

### T15-011: 更新迭代文档
**文件**: `.pb/iterations/iteration-15/record.md`

- 记录所有新增内容
- 记录实施过程问题和解决方案
- 记录验收测试结果
- 总结功能覆盖情况

**预计**: 0.5h | **Owner**: 待分配

---

## 任务汇总

| 任务 | 名称 | 预计 | 阶段 | 优先级 |
|------|------|------|------|--------|
| T15-001 | 扩展 demosite 测试页面 | 3h | 1 | P0 |
| T15-002 | TC016 定位器类型覆盖 | 2h | 1 | P0 |
| T15-003 | TC017 关键字完整覆盖 | 2.5h | 1 | P0 |
| T15-004 | TC018 视觉定位功能 | 1.5h | 1 | P0 |
| T15-005 | TC019 桌面应用自动化 | 2.5h | 1 | P0 |
| T15-006 | TC020 多窗口和iframe | 2h | 2 | P1 |
| T15-007 | TC021 复杂数据引用 | 1.5h | 2 | P1 |
| T15-008 | TC022-024 负面测试 | 1.5h | 2 | P1 |
| T15-009 | 更新文档 | 1.5h | 3 | P1 |
| T15-010 | 完整回归测试 | 2h | 3 | P0 |
| T15-011 | 更新迭代文档 | 0.5h | 3 | P1 |

**总预计**: 20.5h
