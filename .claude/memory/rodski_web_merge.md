---
name: rodski_web_merge
description: rodski-web 独立子目录已建立，作为 Agent 生成用例的人类辅助编辑工具
type: reference
---

**rodski-web 是独立子目录**，路径：`/Users/sirius05/Documents/project/RodSki/rodski-web/`。

**定位**：给人类工程师辅助查看/编辑 Agent 生成用例的工具。

**目录结构**：
```
rodski-web/
├── src/                          # Flask 应用入口
│   ├── app.py
│   ├── api/                      # API 层（cases/models/results/runner）
│   ├── services/                  # 业务逻辑层
│   └── parsers/                  # 独立 XML 解析器（不依赖 RodSki）
├── static/                       # CSS/JS
├── templates/                     # HTML 模板
├── config.yaml                   # ⭐ 已配置正确路径
├── requirements.txt              # flask>=2.3.0, pyyaml>=6.0
└── run.sh
```

**启动**：
```bash
cd rodski-web
pip install flask pyyaml
python src/app.py  # http://localhost:5002
```

**config.yaml 已更新**：
- `projects[].path` → `rod_ski_format` 测试用例目录
- `rodski.project_path` → `rodski/` 框架主体
