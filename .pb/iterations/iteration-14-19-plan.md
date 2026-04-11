# 迭代14-19 总体规划

**规划日期**: 2026-04-09  
**当前版本**: v4.5.0  
**目标**: 将原迭代14-15的大任务（29.5h）拆分成6个小迭代，每个迭代4-6小时

---

## 拆分原则

1. **每个迭代独立可交付** - 完成后可以发布一个版本
2. **任务量控制在4-6小时** - 避免任务过大导致错误
3. **按依赖关系排序** - 先修复问题，再扩展功能
4. **每个迭代有独立分支** - 使用版本号命名分支
5. **避免任务冲突** - 不同迭代修改不同文件

---

## 版本与分支规划

| 迭代 | 版本号 | 分支名 | 预计工时 | 主要内容 |
|------|--------|--------|----------|----------|
| iteration-14 | v4.6.0 | release/v4.6.0 | 3h | P0问题修复（expect_fail + 路径修复 + tc_expect_fail） |
| iteration-15 | v4.7.0 | release/v4.7.0 | 4h | data目录清理 + 文档更新 + Python脚本 |
| iteration-16 | v4.8.0 | release/v4.8.0 | 5h | demosite扩展 + TC016定位器测试 |
| iteration-17 | v4.9.0 | release/v4.9.0 | 4h | TC017关键字覆盖 + TC018视觉定位 |
| iteration-18 | v4.10.0 | release/v4.10.0 | 4.5h | TC019桌面自动化 + TC020多窗口测试 |
| iteration-19 | v4.11.0 | release/v4.11.0 | 5.5h | TC021复杂引用 + TC022-024负面测试 + 文档 |

**总计**: 26h（比原计划减少3.5h，通过优化任务）

---

## Iteration 14: P0问题修复 (v4.6.0)

**分支**: `release/v4.6.0`  
**工时**: 3h  
**优先级**: P0

### 任务清单

| 任务 | 内容 | 预计 | 文件 |
|------|------|------|------|
| T14-001 | 添加 expect_fail 属性 | 0.5h | `case/demo_case.xml` |
| T14-002 | 修复 run_demo.sh 路径 | 0.5h | `run_demo.sh` |
| T14-003 | 补充 tc_expect_fail.xml | 2h | `model/model.xml`, `data/LoginForm.xml`, `data/ErrorMessage_verify.xml`, `demosite/app.py` |

### 验收标准
- TC012A、TC014A 显示为"预期失败"
- run_demo.sh 路径正确
- tc_expect_fail.xml 可以运行

### 交付物
- 修复后的测试用例
- 修复后的运行脚本
- 完整的 tc_expect_fail.xml 支持

---

## Iteration 15: 清理与文档 (v4.7.0)

**分支**: `release/v4.7.0`  
**工时**: 4h  
**优先级**: P1  
**前置依赖**: iteration-14

### 任务清单

| 任务 | 内容 | 预计 | 文件 |
|------|------|------|------|
| T15-001 | 清理 data 目录冗余文件 | 2h | `data/` 目录 |
| T15-002 | 更新 README 文档 | 1h | `README.md` |
| T15-003 | 添加 Python 运行脚本 | 1h | `run_demo.py` |

### 验收标准
- data 目录文件数量减少到30个以内
- README 内容准确完整
- run_demo.py 跨平台可用

### 交付物
- 清理后的 data 目录
- 更新的文档
- Python 运行脚本

---

## Iteration 16: demosite扩展 + 定位器测试 (v4.8.0)

**分支**: `release/v4.8.0`  
**工时**: 5h  
**优先级**: P0  
**前置依赖**: iteration-15

### 任务清单

| 任务 | 内容 | 预计 | 文件 |
|------|------|------|------|
| T16-001 | 扩展 demosite 测试页面 | 3h | `demosite/app.py`, `demosite/templates/` |
| T16-002 | TC016 定位器类型覆盖测试 | 2h | `case/tc016_locators.xml`, `model/model.xml`, `data/LocatorTest*.xml` |

### 新增页面
- `/locator-test` - 定位器测试页面
- `/upload` - 文件上传页面
- `/multi-window` - 多窗口测试页面
- `/iframe-test` - iframe 测试页面

### 验收标准
- 所有新页面可以访问
- TC016 测试通过
- 覆盖 XPath、Name、CSS 定位器

### 交付物
- 扩展的 demosite
- TC016 测试用例

---

## Iteration 17: 关键字覆盖 + 视觉定位 (v4.9.0)

**分支**: `release/v4.9.0`  
**工时**: 4h  
**优先级**: P0  
**前置依赖**: iteration-16

### 任务清单

| 任务 | 内容 | 预计 | 文件 |
|------|------|------|------|
| T17-001 | TC017 关键字完整覆盖测试 | 2.5h | `case/tc017_keywords.xml`, `model/model.xml`, `data/KeywordTest*.xml` |
| T17-002 | TC018 视觉定位功能测试 | 1.5h | `case/tc018_vision.xml`, `model/model.xml`, `data/VisionLogin*.xml` |

### 关键字覆盖
- wait (等待)
- clear (清空)
- screenshot (截图)
- assert (断言)
- upload_file (文件上传)

### 验收标准
- TC017 测试通过
- TC018 模型定义完整（可选运行）
- 关键字覆盖率提升

### 交付物
- TC017 测试用例
- TC018 视觉定位示例

---

## Iteration 18: 桌面自动化 + 多窗口 (v4.10.0)

**分支**: `release/v4.10.0`  
**工时**: 4.5h  
**优先级**: P0  
**前置依赖**: iteration-17

### 任务清单

| 任务 | 内容 | 预计 | 文件 |
|------|------|------|------|
| T18-001 | TC019 桌面应用自动化测试 | 2.5h | `case/tc019_desktop.xml`, `fun/desktop_ops/` |
| T18-002 | TC020 多窗口和 iframe 测试 | 2h | `case/tc020_windows.xml`, `fun/switch_window.py`, `fun/switch_frame.py` |

### 桌面操作脚本
- `type_text.py` - 输入文本
- `key_combo.py` - 快捷键组合
- `mouse_click.py` - 鼠标点击

### 验收标准
- TC019 桌面自动化可用（Windows/macOS）
- TC020 窗口切换正常
- iframe 切换正常

### 交付物
- TC019 桌面自动化测试
- TC020 多窗口测试
- 桌面操作脚本

---

## Iteration 19: 复杂引用 + 负面测试 + 文档 (v4.11.0)

**分支**: `release/v4.11.0`  
**工时**: 5.5h  
**优先级**: P1  
**前置依赖**: iteration-18

### 任务清单

| 任务 | 内容 | 预计 | 文件 |
|------|------|------|------|
| T19-001 | TC021 复杂数据引用测试 | 1.5h | `case/tc021_data_ref.xml`, `model/model.xml`, `data/DataRefTest*.xml` |
| T19-002 | TC022-024 负面测试集合 | 1.5h | `case/tc022_negative.xml`, `model/model.xml`, `data/ErrorTest*.xml` |
| T19-003 | 更新文档 | 1.5h | `README.md`, `COVERAGE.md` |
| T19-004 | 完整回归测试 | 1h | 所有测试用例 |

### 复杂引用覆盖
- GlobalValue 引用
- Return 嵌套引用
- 命名变量访问

### 负面测试
- TC022: 元素不存在 (expect_fail)
- TC023: API错误响应 (expect_fail)
- TC024: SQL语法错误 (expect_fail)

### 验收标准
- TC021 数据引用正确
- TC022-024 负面测试通过
- 功能覆盖率达到 90%+
- 文档完整

### 交付物
- TC021-024 测试用例
- COVERAGE.md 覆盖率文档
- 完整回归测试报告

---

## 工作流程

### 每个迭代的标准流程

1. **创建分支**
   ```bash
   git checkout main
   git pull
   git checkout -b release/vX.X.0
   ```

2. **创建迭代目录**
   ```bash
   mkdir -p .pb/iterations/iteration-XX
   cd .pb/iterations/iteration-XX
   touch record.md tasks.md acceptance_tests.md
   ```

3. **执行任务**
   - 按 tasks.md 顺序执行
   - 记录过程到 record.md
   - 遇到问题立即记录

4. **验收测试**
   - 运行所有测试用例
   - 检查验收标准
   - 记录到 acceptance_tests.md

5. **合并发布**
   ```bash
   git add .
   git commit -m "release: RodSki vX.X.0 — 迭代描述"
   git checkout main
   git merge release/vX.X.0
   git tag vX.X.0
   git push origin main --tags
   ```

6. **清理分支**
   ```bash
   git branch -d release/vX.X.0
   ```

---

## 风险控制

### 任务失败处理
- 如果任务失败，记录原因到 record.md
- 评估是否需要调整任务范围
- 不要强行推进，先解决问题

### 冲突避免
- 每个迭代修改不同的文件
- 按顺序执行迭代，不要并行
- 合并前确保 main 分支最新

### 质量保证
- 每个迭代都要运行回归测试
- 验收标准必须全部通过
- 文档必须同步更新

---

## 进度跟踪

| 迭代 | 状态 | 开始日期 | 完成日期 | 实际工时 | 备注 |
|------|------|----------|----------|----------|------|
| iteration-14 | 待开始 | - | - | - | P0问题修复 |
| iteration-15 | 待开始 | - | - | - | 清理与文档 |
| iteration-16 | 待开始 | - | - | - | demosite扩展 |
| iteration-17 | 待开始 | - | - | - | 关键字覆盖 |
| iteration-18 | 待开始 | - | - | - | 桌面自动化 |
| iteration-19 | 待开始 | - | - | - | 复杂引用 + 文档 |

---

## 参考文档

- `.pb/iterations/iteration-14/record.md` - 原迭代14记录
- `.pb/iterations/iteration-15/record.md` - 原迭代15记录
- `rodski/docs/TEST_CASE_WRITING_GUIDE.md` - 用例编写指南
- `rodski/docs/CORE_DESIGN_CONSTRAINTS.md` - 核心设计约束
