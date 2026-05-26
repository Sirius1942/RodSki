# assets — vision_image 参考图

本目录存放 `vision_image` 定位器使用的参考图（小尺寸 PNG，从实际 UI 截图裁剪）。

## 当前参考图

| 文件 | 尺寸 | 用途 | 源截图 |
|------|------|------|--------|
| `username_input.png` | 680×100 | 用户名输入框（含 "admin" 文字） | `_sources/login_screen.png` |
| `password_input.png` | 680×100 | 密码输入框（含 "•••••"） | `_sources/login_screen.png` |
| `login_btn.png` | 680×100 | 紫色"登录"按钮 | `_sources/login_screen.png` |
| `welcome_msg.png` | 130×60 | 登录后右上角 "admin" 用户标识 | `_sources/after_login.png` |

## 工具

`crop_templates.py` — 批量裁剪工具。

### 用法

```bash
# 根据 manifest.yaml 批量裁剪
python3 crop_templates.py batch --manifest manifest.yaml --out-dir .
```

### manifest.yaml 格式

```yaml
source_images:
  login: _sources/login_screen.png
  after: _sources/after_login.png

crops:
  - name: username_input
    source: login
    bbox: [x1, y1, x2, y2]   # 原图像素坐标
```

## 重新采集流程

UI 变化（主题、分辨率、字体）后参考图可能失效，重新采集：

1. **更新源截图**：把新的登录页/Dashboard 截图放进 `_sources/`，覆盖原文件
2. **调整坐标**：编辑 `manifest.yaml` 中 `crops[].bbox`
3. **重跑工具**：`python3 crop_templates.py batch --manifest manifest.yaml --out-dir .`
4. **验证**：跑 TC003 / TC006 用例确认模板匹配命中

## 注意事项

- 源截图来自 `rodski-demo/DEMO/demo_full/result/.../TC001_*.png`（Retina @2x，3840×1800）
- 参考图尺寸建议 30×30 ~ 700×100，过大会拖慢 OpenCV 模板匹配
- 避免动态内容（时间、计数器）
- 本目录及参考图、manifest、source 全部纳入 git，方便复现

## 文件清单

```
assets/
├── README.md                    # 本文件
├── crop_templates.py            # 批量裁剪工具
├── manifest.yaml                # 裁剪配置
├── _sources/
│   ├── login_screen.png         # 登录页源截图
│   └── after_login.png          # 登录后 Dashboard 源截图
├── username_input.png           # 参考图（模型引用）
├── password_input.png
├── login_btn.png
└── welcome_msg.png
```
