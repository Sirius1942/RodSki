---
name: rodski_web_merge
description: rodski-web 已合并到主项目，作为 Agent 生成用例的人类辅助编辑工具
type: reference
---

**rodski-web 已合并到主项目**，路径：`/Users/sirius05/Documents/project/RodSki/`。

**定位**：给人类工程师辅助查看 Agent 生成的用例，并支持编辑的工具系统。

**项目结构**：
```
rodski/src/          # Flask 应用入口
rodski/src/api/      # API 层（cases/models/results/runner）
rodski/src/services/  # 业务逻辑层
rodski/src/parsers/  # 独立 XML 解析器（不依赖 RodSki 主项目）
rodski/static/       # CSS/JS
rodski/templates/      # HTML 模板
rodski/config.yaml    # ⭐ 配置文件（需更新数据路径）
rodski/requirements.txt # flask>=2.3.0, pyyaml>=6.0
```

**启动**：
```bash
cd rodski
pip install flask pyyaml
python src/app.py  # 启动在 localhost:5002
```

**config.yaml 需要修改**：
- `projects[].path` 改为 `/Users/sirius05/Documents/project/RodSki/rod_ski_format`
- `rodski.project_path` 改为 `/Users/sirius05/Documents/project/RodSki`

**注意**：
- rodski-web 的 `src/parsers/` 是独立实现的 XML 解析器，不复用 RodSki 主项目的解析器
- 它调用 RodSki CLI 执行用例
