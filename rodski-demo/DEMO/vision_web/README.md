# RodSki Web 视觉定位演示

## 概述

本演示展示 RodSki Web 端视觉定位能力，使用 `vision` 定位器进行语义定位。

## 前提条件

1. **OmniParser 服务**：`http://14.103.175.167:7862/parse/` 可访问
2. **LLM API**：配置 `ANTHROPIC_API_KEY` 环境变量
3. **浏览器驱动**：Chrome/Firefox WebDriver

## 运行命令

```bash
cd /Users/sirius05/Documents/project/RodSki
python rodski/ski_run.py rodski-demo/DEMO/vision_web/case/vision_demo.xml
```

## 预期结果

1. 打开百度首页
2. 通过视觉定位找到搜索输入框
3. 输入 "RodSki 测试框架"
4. 点击搜索按钮
5. 验证第一个搜索结果包含 "RodSki"

## 文件说明

- `model/model.xml` — 定义 vision 定位器
- `case/vision_demo.xml` — 测试用例
- `data/SearchPage.xml` — 数据表
- `data/SearchPage_verify.xml` — 验证数据表
