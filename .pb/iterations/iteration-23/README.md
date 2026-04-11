# Iteration 23: 数据文件组织修正

> 版本: v5.3.1
> 分支: fix/v5.3.1-validation
> 日期: 2026-04-11
> 工时: 3h
> 优先级: P0
> 前置依赖: 无
> 设计文档: `.pb/specs/verify-data-organization-fix.md` 第一部分

---

## 需求

### 业务需求

- 数据文件组织与代码实现不一致：`_verify` 数据表混在 `data.xml` 中，未拆分到 `data_verify.xml`
- 存在多个死文件（框架不加载但占据目录）：7 个独立 XML 数据文件 + 3 个独立模型文件
- 其他 DEMO 子目录也有遗留的独立 `_verify.xml` 死文件

### 技术需求

- 将 `data.xml` 中的 `_verify` datatable 拆分到 `data_verify.xml`（两处：`demo_full/data/` 和 `rodski-demo/data/`）
- 删除不被框架加载的死文件
- 合并独立模型文件到 `model.xml` 后删除

---

## 开发任务

### T23-001: demo_full 数据拆分 (预计 45min)

**文件**: `rodski-demo/DEMO/demo_full/data/data.xml` → 拆出到 `data_verify.xml`

**任务**:
1. 读取 `data.xml`，识别所有 `name` 以 `_verify` 结尾的 `<datatable>` 元素
2. 将这些 `_verify` datatable 移到新建的 `data_verify.xml`，根元素为 `<datatables>`
3. 从 `data.xml` 中删除已移出的 `_verify` datatable
4. 确保 XML 格式正确，缩进一致

**验收**:
- [ ] `data_verify.xml` 存在且包含所有 `_verify` 表
- [ ] `data.xml` 不再包含任何 `_verify` 表
- [ ] 两个文件 XML 格式正确

### T23-002: rodski-demo 根目录数据拆分 (预计 30min)

**文件**: `rodski-demo/data/data.xml` → 拆出到 `data_verify.xml`

**任务**:
1. 同 T23-001 操作，对 `rodski-demo/data/data.xml` 执行相同拆分
2. 创建 `rodski-demo/data/data_verify.xml`

**验收**:
- [ ] `data_verify.xml` 存在且包含所有 `_verify` 表
- [ ] `data.xml` 不再包含任何 `_verify` 表

### T23-003: demo_full 死文件清理 (预计 15min)

**文件**: `rodski-demo/DEMO/demo_full/data/` 下 7 个死文件

**任务**:
删除以下文件（框架只读 `data.xml` + `data_verify.xml`，这些独立文件不会被加载）：
1. `DemoForm.xml`
2. `DemoFormVerify_verify.xml`
3. `EvaluateResult_verify.xml`
4. `GetVerify_verify.xml`
5. `LoginAPICapture.xml`
6. `LoginAPICapture_verify.xml`
7. `SetGetVerify_verify.xml`

**验收**:
- [ ] 7 个文件已删除
- [ ] `data/` 目录仅剩 `data.xml`、`data_verify.xml`、`globalvalue.xml`、`DB_USAGE.md`、`README.md`

### T23-004: 模型文件合并 (预计 45min)

**文件**: `rodski-demo/model/` 下 3 个独立模型文件 → 合并到 `model.xml`

**任务**:
1. 读取 `model_db.xml`，提取其中的 `<model>` 元素
2. 读取 `model_e.xml`，提取其中的 `<model>` 元素
3. 读取 `model_f.xml`，提取其中的 `<model>` 元素
4. 检查 `model.xml` 中是否已有同名模型，**避免重复合并**
5. 将不重复的模型追加到 `model.xml` 的 `<models>` 根元素内
6. 删除 `model_db.xml`、`model_e.xml`、`model_f.xml`

**验收**:
- [ ] 3 个独立模型文件已删除
- [ ] `model.xml` 包含原来所有模型定义
- [ ] `model/` 目录仅剩 `model.xml`
- [ ] XML 格式正确

### T23-005: 其他 DEMO 子目录死文件清理 (预计 15min)

**文件**:
- `DEMO/vision_web/data/SearchPage_verify.xml` — 删除
- `DEMO/vision_web/data/SearchPage.xml` — 检查是否在 data.xml 中，若是则删除
- `DEMO/iteration-01-vision/data/LoginPage_verify.xml` — 内容合并到 data_verify.xml（若不存在则创建）后删除
- `DEMO/iteration-01-vision/data/` 下其他独立 XML — 检查是否在 data.xml 中，若是则删除

**验收**:
- [ ] `vision_web/data/` 仅剩 `data.xml`、`data_verify.xml`、`globalvalue.xml`
- [ ] `iteration-01-vision/data/` 无独立的 `_verify.xml` 死文件

### T23-006: 验证测试 (预计 30min)

**任务**:
1. 初始化 DB: `python3 rodski-demo/run_demo.py --init-db`
2. 运行 demo_full 主用例: `python3 rodski/ski_run.py rodski-demo/DEMO/demo_full/case/demo_case.xml`
3. 运行独立 DB 用例: `python3 rodski/ski_run.py rodski-demo/case/tc_database.xml`
4. 运行独立数据引用: `python3 rodski/ski_run.py rodski-demo/case/tc_data_ref.xml`
5. 运行独立脚本用例: `python3 rodski/ski_run.py rodski-demo/case/tc_script.xml`

**验收**:
- [ ] 通过率与修改前一致（不引入新失败）
- [ ] 结果记录到 `record.md`

---

## 验收标准

1. **文件组织**: `data/` 目录下仅有 `data.xml` + `data_verify.xml` + `globalvalue.xml`（+ 文档）
2. **模型组织**: `model/` 目录下仅有 `model.xml`
3. **无回归**: 测试通过率与修改前一致
4. **XML 格式**: 所有文件格式正确，可被框架正常解析

---

## 风险与注意事项

1. 拆分 `data.xml` 时需确保 `_verify` 表完整移出，不遗漏也不多删
2. 模型合并时需检查重复，避免同名模型出现两次
3. 运行测试前必须初始化 DB（`--init-db`）
