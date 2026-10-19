# demosite/data_driven：计划级数据驱动（v11.9.0）

同一个用例流程用多组数据各执行一次、每组得到独立结果。规则见 `rodski/docs/CORE_DESIGN_CONSTRAINTS.md` §7.8，需求见 `.pb/requirements/REQ-013-data-driven-testing.md`。

## 三个角色

| 角色 | 位置 | 本模块示例 |
|------|------|-----------|
| 用例（流程 + 基础 DataID，不声明数据驱动） | `case/*.xml` | `DD_FORM`：登录 `L001` → 表单 `T001` → 校验 `V001` |
| 数据驱动表（计划 / 用例 / 步骤对应关系表，只存 DataID） | `data/data.sqlite`，`table_kind='driver'` | `FormMatrix`：列 `TestForm.T001`、`TestForm_verify.V001` |
| 计划（只写驱动表名） | `plan/*.xml` | `<case file="form_flow.xml" id="DD_FORM" data_driven="FormMatrix"/>` |

```text
FormMatrix（绑定 form_flow.xml::DD_FORM）
| DataID | 备注（实例标题）         | TestForm.T001 | TestForm_verify.V001 |
|--------|------------------------|---------------|----------------------|
| alice  | 普通用户 alice（role=user） | T101          | V101                 |
| bob    | 管理员 bob（role=admin）   | T102          | V102                 |
| base   | BLANK：沿用用例基础 DataID  | BLANK         | BLANK                |
| carol  | 访客 carol（被引用数据行未写备注 → WARN） | T103 | V103          |
```

- 登录步骤 `LoginForm.L001` 不在驱动表中，所有实例都用 `L001`。
- 实例 ID 为 `DD_FORM[alice]` 等；结果 XML 带 `template_case_id / driver / data_id / instance_title / replacements`。
- 单独运行用例（`rodski run case/form_flow.xml --case-id DD_FORM`）只执行一次，全部使用基础 DataID。

## 运行

```bash
python3 rodski-demo/_sites/demosite/app.py &                  # 共享站点 :8000（验收脚本未检测到时会自行启动）
python3 rodski-demo/demosite/data_driven/run_acceptance.py    # 全部验收
cd rodski-demo/demosite/data_driven
rodski run @data_driven_suite --headless                       # 11 个实例
rodski run @data_driven_suite --data-id alice,DD_API[bad]      # 只跑指定实例
rodski run @failure_isolation_suite --exclude-data-id wrong
```

数据由 `data/init_data.py` 生成（每次验收前重建，含只读订单库 `data/orders.db`）。

## 验收项

| 编号 | 内容 |
|------|------|
| DD-01 | 展开为 11 个实例，结果字段齐全 |
| DD-02 | 未列出的步骤与 `BLANK` 单元格用基础 DataID；日志标注 `数据驱动替换 TestForm: T001 → T101（FormMatrix[alice]）` |
| DD-03 | 用例单独运行只执行一次 |
| DD-04 | `failure_isolation_suite`：第 2 个实例失败，其余照常通过 |
| DD-05 | `DD_STATE`：实例之间 Return 历史与 set 变量隔离 |
| DD-06 | `DD_TWICE`：同一模型两个基础 DataID 分别替换 |
| DD-07 | `DD_API`：send / verify / DB 按驱动表替换 |
| DD-11 | `--data-id` / `--exclude-data-id` 与 `@plan` 同用 |
| DD-12 | 13 种错误配置（含动态列、挂错用例、调试计划）在执行任何用例前报错 |
| DD-13 | `DD_LOOP`：loop 中 `T00${i}` 不被替换 |
| DD-14 | `create-driver` / `add-row` / `add-field` / `set --remark` / `show` / `list` / `validate`；旧库自动迁移并保留 `.bak` |
| DD-17 | 实例标题取行备注；被引用数据行缺备注只 WARN |

业务模型（DD-08/09）见 `rodski-demo/mock_api/business_model/run_data_driven_acceptance.py`；Web + App 混合用例（DD-10）见 `rodski-demo/mobile/app/scripts/run_data_driven_acceptance.py`。
