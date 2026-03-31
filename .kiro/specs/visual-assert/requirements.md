# RodSki 视觉断言能力需求

**版本**: v1.0
**日期**: 2026-03-31
**状态**: 待开发

---

## 1. 背景与目标

### 1.1 业务场景

当前 RodSki 的 `verify` 关键字主要用于**数据值比对**（文本、属性、接口字段），但在实际测试中存在两类场景无法覆盖：

| 场景 | 描述 | 示例 |
|------|------|------|
| **图片断言** | 通过截图/图片识别判断用例是否完成 | 验证弹窗出现、验证图片加载成功、验证图标正确 |
| **视频断言** | 通过视频帧分析判断用例是否成功 | 验证动画播放完成、验证录屏回放正确、验证视频广告播放 |

### 1.2 目标

在 RodSki 框架中新增 `assert` 关键字的**视觉断言能力**，使测试用例能够通过图像/视频内容判定执行结果。

---

## 2. 功能需求

### 2.1 关键字：`assert` — 视觉断言

**功能**：对当前页面/应用截图，或对执行录屏进行帧分析，验证预期画面是否出现。

**参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | string | 是 | 断言类型：`image`（图片）/ `video`（视频） |
| `reference` | string | 是 | 预期图片路径（相对于 `images/assert/` 目录） |
| `threshold` | float | 否 | 匹配度阈值，范围 0.0~1.0，默认 0.8 |
| `scope` | string | 否 | 断言范围：`full`（全屏截图）/ `element`（指定元素区域），仅 `type=image` 生效，默认 `full` |
| `wait` | int | 否 | 等待图片出现的最大秒数，默认 0（即立即断言），仅 `type=image` 生效 |
| `video_source` | string | 否 | 视频来源：`recording`（自动录屏）/ `file:path`（指定视频文件），仅 `type=video` 生效，默认 `recording` |
| `time_range` | string | 否 | 检查时间范围，格式 `start~end`（秒），默认整个视频，仅 `type=video` 生效 |
| `position` | string | 否 | 帧位置：`any`（任意位置）/ `start`/`end`/`middle`，默认 `any`，仅 `type=video` 生效 |

**数据表字段格式**：

```
# 图片断言
assert[type=image,reference=img/expected_modal.png,threshold=0.85,scope=full,wait=5]

# 视频断言
assert[type=video,reference=img/expected_frame.png,threshold=0.75,video_source=recording,time_range=0~10,position=any]
```

---

## 3. 约束（设计原则）

1. **关键字数量不增加**：`assert` 已在 `SUPPORTED` 列表中，扩展其参数支持视觉断言，不新增独立关键字
2. **用 `type` 参数区分类型**：通过 `type=image` / `type=video` 区分，不出现 `image_assert`、`video_assert` 等关键字
3. **语义正交**：`verify` 回答"值对不对"，`assert` 回答"画面对不对"，职责分离
4. **扩展性预留**：未来可扩展 `type=audio`（声音断言）等，不破坏现有设计

---

## 4. 验收标准

| 用例 | 验收条件 |
|------|---------|
| `assert[type=image]` 匹配成功 | 关键字返回 `matched=true`，用例标记 `PASS` |
| `assert[type=image]` 匹配失败 | 自动截图保存，用例标记 `FAIL` |
| `assert[type=video]` 找到帧 | 返回 `frame_found=true`，记录时间戳，用例 `PASS` |
| `assert[type=video]` 未找到帧 | 保存可疑帧片段，用例 `FAIL` |
| `wait` 参数生效 | 图片未出现时等待，最长等待 `wait` 秒 |

---

## 5. 优先级

| 阶段 | 范围 |
|------|------|
| **Phase 1** | `assert[type=image]` 核心能力 + 全屏截图匹配 |
| **Phase 2** | `assert[type=image]` 元素区域截取 + `wait` 参数 |
| **Phase 3** | `assert[type=video]` 核心能力 + 录屏集成 |

---

**负责人**: 热破 (Hot Rod)
**审查人**: 大黄蜂 (Bumblebee)
