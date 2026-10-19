# demosite/core_keywords

关键字基础示例（原 `rodski-demo/` 顶层模块，v11.8.1 重组时迁入）。依赖共享站点 `rodski-demo/_sites/demosite`（:8000）。

| 文件 | 用例 | 内容 |
|------|------|------|
| `case/tc_database.xml` | TC020~024 | SQLite 查询 / 插入 / 聚合；MySQL 示例（TC023/024，execute=否，需 MySQL 服务） |
| `case/tc_data_ref.xml` | TC025~027 | GlobalValue 引用导航、Return 值链、Set/Get |
| `case/tc_script.xml` | TC028~030 | run 运行 Python 脚本、evaluate、wait + screenshot |
| `case/tc_keywords.xml` | TC031~033 | assert 图片比对、clear、check |

- DB 用例使用模块内 `demo.db`（`python3 init_db.py` 重置），与站点自用库相互独立。
- 本模块与 `demosite/full` 有同名但定义不同的模型和数据表，因此保持独立模块，未合并。

```bash
python3 rodski-demo/_sites/demosite/app.py &
rodski run rodski-demo/demosite/core_keywords/case/ --headless
```
