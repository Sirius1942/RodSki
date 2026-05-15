# Iteration 43 任务清单 — 契约对齐：迁移与文档交付

**版本**: v6.7.6  
**分支**: `feature/iteration-43-migration-docs`  
**依赖**: iteration-42 完成（运行时严格化已生效）  
**设计文档**: `.pb/specs/v6.7.6-contract-alignment-fix.md`  
**目标**: 让 rodski-demo 通过 strict 验收，交付迁移文档，完成 v6.7.6 发布准备  
**范围**: 数据迁移 + 文档 + 发布回归，不再修改框架运行时逻辑

---

## T43-001: rodski-demo 主链路迁移 [2.5h]

### 任务

1. 以 `rodski-demo/DEMO/demo_full` 作为 v6.7.6 主验收 demo。
2. 清理 `demo_full/data/data.sqlite` 中 11 个非 UI `_verify` 的 `${Return[-1]}` 自引用：
   - `QuerySQL_verify.V001.order_no` → 改为字面期望值
   - `QuerySQL_verify.V003.total` → 改为字面期望值
   - `QueryMySQL_verify.V001.order_no` → 改为字面期望值
   - `ReturnTest_verify.V001.result` → 改为字面期望值
   - `SetGetVerify_verify.V001.value` → 改为字面期望值
   - `GetVerify_verify.V001.result` → 改为字面期望值
   - `EvaluateResult_verify.V001.title` → 改为字面期望值
   - `GetModelVerify_verify.V001.formResult` → 改为字面期望值
   - `DemoFormVerify_verify.V001.resultId` → 改为字面期望值
   - `LoginAPICapture_verify.V001.data.token` → 改为字面期望值
   - `KeywordTest_verify.V002.formResult` → 改为字面期望值
3. 确认 `demo_full` 行字段一致性为 0 mismatch（当前已满足）。
4. 处理根 demo（按 T41-001 决策结果）：
   - 若归档：移动到 `rodski-demo/DEMO/_archive/legacy_root_demo/`。
   - 若保留：补齐 20 个缺字段行。
5. 归档旧 XML 数据文件（移动到对应 demo 的 `_archive/` 子目录）：
   - `DEMO/demo_v7_features/data/data.xml`
   - `DEMO/iteration-01-vision/data/data.xml`
   - `DEMO/iteration-01-vision/data/data_verify.xml`
   - `DEMO/vision_desktop/data/NotepadPage.xml`
   - `DEMO/vision_web/data/data.xml`
   - `DEMO/vision_web/data/data_verify.xml`
   - `rodski-demo/data/data.xml`
   - `rodski-demo/data/data_verify.xml`
6. 保留 `vision_desktop` 的 `launch` 和 `run data="fun/..."` 作为回归用例。

### 验证

```bash
rodski data validate rodski-demo/DEMO/demo_full --strict
rodski run rodski-demo/DEMO/demo_full/case/ --dry-run
rodski run rodski-demo/DEMO/vision_desktop/case/desktop_demo.xml --dry-run
```

---

## T43-002: 文档更新与发布前回归 [1.0h]

### 任务

1. 更新 `CORE_DESIGN_CONSTRAINTS.md`：
   - 补充 iteration-41 决策结果（builtin_call、DB 字段路径格式）。
   - 确认版本号标注为 v6.7.6。
2. 更新 `TEST_CASE_WRITING_GUIDE.md`：
   - `launch` 用法示例。
   - 完整 `<location>` 格式强调（旧格式已移除）。
   - SQLite strict 字段规则说明。
   - `_verify` 禁止 `${Return[-1]}` 说明。
   - `run` 路径写法（带/不带 `fun/` 前缀）。
3. 运行完整单元测试 + 安装态检查 + demo dry-run。
4. 整理 release record。

### 验证

```bash
PYTHONPATH=rodski python3 -m pytest rodski/tests -q
python3 -m build
rodski data validate rodski-demo/DEMO/demo_full --strict
rodski run rodski-demo/DEMO/demo_full/case/ --dry-run
```

---

## T43-003: 老用例失败排查与修改指南 [1.0h]

### 任务

1. 新增 `rodski/docs/6.7.6_OLD_CASE_FAILURE_GUIDE.md`。
2. 文档标题：**"v6.7.6 老用例失败排查与修改指南"**。
3. 面向用户和 AI Agent，按"症状 → 原因 → 检查命令 → 修改方式 → 修改前后示例"组织。
4. 覆盖以下 9 类失败：

| # | 失败类型 |
|---|----------|
| 1 | 旧 model 简化定位器格式被拒绝 |
| 2 | `data.xml` / `data_verify.xml` 不再作为运行时数据源 |
| 3 | SQLite 同表行缺字段失败 |
| 4 | `type` / `verify` 缺字段不再静默跳过 |
| 5 | 接口/DB `_verify` 使用 `${Return[-1]}` 被拒绝 |
| 6 | DB `verify` 不能空校验通过 |
| 7 | Case XML `data` 中 `${random(...)}` / `${date(...)}` 被拒绝 |
| 8 | `run` 路径规范化导致老脚本路径需确认 |
| 9 | wheel/sdist 安装态缺依赖或缺 `schemas/*.xsd` |

5. 给 AI Agent 提供固定检查顺序：
   ```
   1. rodski run <case> --dry-run
   2. 检查 model/model.xml 定位器格式
   3. 检查 data/ 下是否有废弃 XML 数据文件
   4. rodski data validate <module> --strict
   5. 检查 _verify 表是否包含 ${Return[-1]}
   6. 检查安装态 schemas/*.xsd 和依赖
   ```
6. 每类问题明确标注"修改老用例"还是"升级/重装 RodSki 包"。
7. 在 release record 中链接该指南。

### 验证

```bash
test -f rodski/docs/6.7.6_OLD_CASE_FAILURE_GUIDE.md
# 检查文档覆盖所有关键词
rg -c "症状|原因|检查命令|修改前|修改后|AI Agent|Return\[-1\]|data.sqlite|location" rodski/docs/6.7.6_OLD_CASE_FAILURE_GUIDE.md
```

---

## 执行顺序

```text
T43-001 (demo 迁移) ← 最耗时，先做
    ↓
T43-002 (文档 + 回归)
    ↓
T43-003 (老用例失败指南)
```

## 工时估算

| 任务 | 预估 |
|------|------|
| T43-001 rodski-demo 主链路迁移 | 2.5h |
| T43-002 文档更新与发布前回归 | 1.0h |
| T43-003 老用例失败排查与修改指南 | 1.0h |
| **合计** | **4.5h** |

---

## 完成定义

1. `rodski-demo/DEMO/demo_full` 通过 `--strict` 数据校验和 dry-run。
2. `vision_desktop` dry-run 不再因 `launch` 或 `run data="fun/..."` 失败。
3. 旧 XML 数据文件已归档，不在验收路径中。
4. `CORE_DESIGN_CONSTRAINTS.md` 和 `TEST_CASE_WRITING_GUIDE.md` 与 v6.7.6 实现一致。
5. `6.7.6_OLD_CASE_FAILURE_GUIDE.md` 已交付，覆盖 9 类失败场景。
6. release record 完整，可发布。

---

## v6.7.6 发布检查清单

iteration-43 完成后，v6.7.6 可发布。最终检查：

- [ ] `python3 -m pytest rodski/tests` 全绿
- [ ] 干净 venv 安装 wheel 成功
- [ ] `rodski data validate rodski-demo/DEMO/demo_full --strict` 通过
- [ ] `rodski run rodski-demo/DEMO/demo_full/case/ --dry-run` 通过
- [ ] `6.7.6_OLD_CASE_FAILURE_GUIDE.md` 存在且内容完整
- [ ] git tag `v6.7.6`
