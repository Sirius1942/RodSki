# RodSki 视觉断言能力开发任务

**版本**: v1.0
**日期**: 2026-03-31

---

## 开发流程

1. **Phase 1**: 热破开发 `assert[type=image]` 核心能力
2. **Phase 1 完成后**: 大黄蜂审查
3. **Phase 2**: 热破开发 `assert[type=image]` 增强能力（scope=element + wait）
4. **Phase 2 完成后**: 大黄蜂审查
5. **Phase 3**: 热破开发 `assert[type=video]` + 录屏集成
6. **Phase 3 完成后**: 大黄蜂审查
7. **全部完成后**: 棘轮基于新功能改写 cassmall 测试用例

---

## Phase 1 - 图片断言核心能力

### Task 1.1: 创建断言模块目录 ✅
- **文件**: `core/assertion/`
- **内容**: 创建 `__init__.py`、`base_assertion.py`、`image_matcher.py`
- **工作量**: 15min
- **依赖**: 无
- **状态**: ✅ 完成 (2026-03-31)

### Task 1.2: 实现 ImageMatcher 类 ✅
- **文件**: `core/assertion/image_matcher.py`
- **内容**:
  - `match(screenshot, reference, threshold)` 方法
  - 使用 OpenCV TM_CCORR_NORMED 模板匹配（注：TM_CCOEFF_NORMED 在 OpenCV 4.11+ 对纯色图有 bug，改用 TM_CCORR_NORMED）
  - 返回匹配度、是否匹配的结构化结果
  - 浮点精度处理：四位小数截断
  - 尺寸不一致时自动中心裁剪
- **工作量**: 30min
- **依赖**: Task 1.1
- **状态**: ✅ 完成 (2026-03-31)

### Task 1.3: 扩展 keyword_engine.py 的 _kw_assert 方法 ✅
- **文件**: `core/keyword_engine.py`
- **内容**:
  - 解析 `assert[type=image,...]` 参数（支持 `assert[...]` 包装格式）
  - 调用 ImageMatcher 执行匹配
  - `_parse_kv_args` 解析 key=value,key=value 格式
  - 失败时截图并记录
  - 返回结构化结果（存入 Return[-1]）
- **工作量**: 45min
- **依赖**: Task 1.2
- **状态**: ✅ 完成 (2026-03-31)

### Task 1.4: 添加 model.xsd 扩展（assertion 类型） ✅
- **文件**: `schemas/model.xsd`
- **内容**: 新增 `assertion` 类型的元素定义（AssertionElementType、AssertionDetailType、相关枚举）
- **工作量**: 15min
- **依赖**: 无
- **状态**: ✅ 完成 (2026-03-31)

### Task 1.5: 编写自测试用例 ✅
- **文件**: `tests/unit/test_assertion.py`
- **内容**: 为 ImageMatcher 编写 12 个单元测试
  - 相同图片匹配、不同图片区分、阈值边界
  - 尺寸裁剪、位置返回、灰度转换、类型检查
  - 缺失文件异常、结构完整性
- **工作量**: 30min
- **依赖**: Task 1.2
- **状态**: ✅ 完成 (2026-03-31) — 24/24 测试通过（Phase 1: 12个 + Phase 2: 12个）

---

## Phase 1 完成 → 大黄蜂审查 ✅

**Phase 1 完成时间**: 2026-03-31
**自测结果**: 24/24 测试通过
**审查状态**: 待大黄蜂审查

---

## Phase 2 - 图片断言增强能力

### Task 2.1: 实现 scope=element 元素区域截取 ✅
- **文件**: `core/assertion/image_matcher.py`
- **内容**:
  - 支持截取指定元素区域
  - 使用 Playwright/Appium 截图 API 的元素截图能力
- **工作量**: 30min
- **依赖**: Phase 1 完成
- **状态**: ✅ 完成 (2026-03-31)

### Task 2.2: 实现 wait 参数（轮询等待） ✅
- **文件**: `core/assertion/image_matcher.py`
- **内容**:
  - 定时截屏重试匹配
  - 直到匹配成功或超时
  - 轮询间隔可配置
- **工作量**: 30min
- **依赖**: Task 2.1
- **状态**: ✅ 完成 (2026-03-31)

### Task 2.3: 更新自测试用例 ✅
- **文件**: `tests/unit/test_assertion.py`
- **内容**: 补充 scope=element 和 wait 的测试用例
- **工作量**: 20min
- **依赖**: Task 2.1, Task 2.2
- **状态**: ✅ 完成 (2026-03-31) — 24/24 测试通过

---

## Phase 2 完成 → 大黄蜂审查 ✅

**Phase 2 完成时间**: 2026-03-31
**自测结果**: 24/24 测试通过

---

## Phase 3 - 视频断言能力

### Task 3.1: 创建 VideoAnalyzer 类
- **文件**: `core/assertion/video_analyzer.py`
- **内容**:
  - 提取视频关键帧
  - 逐帧与预期图片匹配
  - 支持 time_range 和 position 参数
- **工作量**: 45min
- **依赖**: Phase 2 完成

### Task 3.2: 实现录屏机制
- **文件**: `core/recording/` (新增目录)
- **内容**:
  - Playwright 录屏集成
  - 录屏配置（enabled、output_dir、format）
  - 录屏文件管理
- **工作量**: 45min
- **依赖**: Task 3.1

### Task 3.3: 扩展 _kw_assert 支持 type=video
- **文件**: `core/keyword_engine.py`
- **内容**:
  - 解析 `assert[type=video,...]` 参数
  - 调用 VideoAnalyzer 执行帧匹配
  - 支持 video_source=recording/file:path
- **工作量**: 30min
- **依赖**: Task 3.1, Task 3.2

### Task 3.4: 编写自测试用例
- **文件**: `tests/unit/test_assertion.py`
- **内容**: 补充视频断言的单元测试
- **工作量**: 30min
- **依赖**: Task 3.3

---

## Phase 3 完成 → 大黄蜂审查

---

## 交付物检查清单

- [ ] `core/assertion/` 目录完整
- [ ] `core/keyword_engine.py` 扩展完成
- [ ] `schemas/model.xsd` 更新完成
- [ ] 自测试用例覆盖三个 Phase
- [ ] 文档更新（ARCHITECTURE.md、用户手册）
- [ ] 大黄蜂审查通过

---

## 后续：棘轮改写 cassmall 测试用例

Phase 1-3 全部审查通过后，启动 cassmall 测试用例改写任务：
- 为 cassmall 的关键流程添加 `assert` 断言
- 覆盖：小李询价流程、小辉报价流程、订单跟踪流程
