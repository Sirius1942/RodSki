# RodSki 视觉断言能力技术设计

**版本**: v1.0
**日期**: 2026-03-31

---

## 1. 架构设计

### 1.1 模块结构

```
core/
├── keyword_engine.py              # 扩展 _kw_assert 方法
├── assertion/                     # 新增目录
│   ├── __init__.py
│   ├── base_assertion.py         # 断言基类
│   ├── image_matcher.py          # 图片匹配器
│   └── video_analyzer.py         # 视频分析器
```

### 1.2 依赖组件

| 组件 | 作用 | 状态 |
|------|------|------|
| **OpenCV** | 图像模板匹配（TM_CCOEFF_NORMED） | 已有 requirements.txt |
| **FFmpeg** | 视频帧提取 | 需确认 / 新增 |
| **Pillow** | 图像预处理（缩放、裁剪） | 已有 |

---

## 2. 断言模型 XML 格式

在 `model/model.xml` 中新增 `assertion` 类型模型：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<models>
    <!-- 图片断言模型 -->
    <model name="LoginSuccessAssert" type="assertion">
        <element name="modal_appear">
            <assertion type="image">
                <reference>img/expected_success_modal.png</reference>
                <threshold>0.85</threshold>
                <scope>full</scope>
                <wait>5</wait>
            </assertion>
        </element>
    </model>

    <!-- 视频断言模型 -->
    <model name="AnimationCompleteAssert" type="assertion">
        <element name="loading_animation">
            <assertion type="video">
                <reference>img/expected_loading_complete.png</reference>
                <threshold>0.75</threshold>
                <video_source>recording</video_source>
                <time_range>0~10</time_range>
                <position>any</position>
            </assertion>
        </element>
    </model>
</models>
```

---

## 3. Case XML 用法示例

```xml
<?xml version="1.0" encoding="UTF-8"?>
<cases>
    <case execute="是" id="TC010" title="登录成功弹窗断言">
        <pre_process>
            <test_step action="navigate" model="" data="GlobalValue.DefaultValue.URL/login"/>
        </pre_process>
        <test_case>
            <test_step action="type" model="LoginPage" data="L001"/>
            <test_step action="verify" model="LoginPage" data="V001"/>
            <test_step action="assert" model="" data="AAA"/>
        </test_case>
        <post_process>
            <test_step action="close" model="" data=""/>
        </post_process>
    </case>
</cases>
```

### 数据表定义

```xml
<?xml version="1.0" encoding="UTF-8"?>
<datatables>
    <datatable name="LoginSuccessAssert">
        <row id="AAA" remark="验证成功弹窗">
            <field name="modal_appear">assert[type=image,reference=img/expected_success_modal.png,threshold=0.85,wait=5]</field>
        </row>
    </datatable>

    <datatable name="AnimationCompleteAssert">
        <row id="BBB" remark="验证加载动画">
            <field name="loading_animation">assert[type=video,reference=img/expected_loading_complete.png,threshold=0.75,time_range=0~10]</field>
        </row>
    </datatable>
</datatables>
```

---

## 4. 返回值格式

```python
# type=image
{
    "matched": true,
    "similarity": 0.87,
    "threshold": 0.85,
    "screenshot": "path/to/actual.png",
    "reference": "img/expected_modal.png"
}

# type=video
{
    "matched": true,
    "frame_found": true,
    "timestamp": 3.5,
    "similarity": 0.82,
    "total_frames": 300,
    "reference": "img/expected_frame.png"
}
```

---

## 5. 录屏机制（`type=video` 且 `video_source=recording`）

| 配置项 | 说明 |
|--------|------|
| `config.recording.enabled` | 是否启用录屏，默认 `false` |
| `config.recording.output_dir` | 录屏文件输出目录 |
| `config.recording.format` | 视频格式，默认 `webm` |

---

## 6. 目录结构扩展

```
product/
└── {项目名}/
    └── {模块名}/
        ├── images/
        │   └── assert/              ← 新增：断言预期图片目录
        │       ├── expected_success_modal.png
        │       └── expected_loading_complete.png
        ├── case/
        ├── model/
        ├── data/
        └── result/
            └── recordings/          ← 新增：录屏文件目录（可配置保留）
```

---

## 7. 约束与限制

| 约束 | 说明 |
|------|------|
| **阈值合理性** | `type=image` 建议阈值 ≥ 0.75，`type=video` 建议阈值 ≥ 0.65 |
| **图片尺寸** | 预期图片与实际截图尺寸不一致时，自动按预期图片尺寸裁剪实际截图后比对 |
| **视频长度** | `time_range` 超出视频实际长度时，自动截断到有效范围 |
| **性能目标** | `type=image` 单次 < 2s，`type=video` 单次 < 5s |
| **资源清理** | 录屏文件执行完成后默认删除，可配置 `config.recording.keep=true` 保留 |
