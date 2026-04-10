# Iteration 21 实施记录

**版本**: v5.1.0  
**分支**: release/v5.1.0  
**日期**: 2026-04-10  
**状态**: ✅ 已完成

---

## 完成内容

### ✅ T21-001: 创建 `model_db.xml`

- 已创建 `rodski-demo/model/model_db.xml`
- 已定义 `QuerySQL` 与 `QueryMySQL` 两个 `type="database"` 模型
- 两个模型均包含 `connection` 属性
- 查询模板采用 `:param` 占位符

### ✅ T21-002: 迁移 `tc_database.xml`

- 已更新 `rodski-demo/case/tc_database.xml`
- DB 步骤已迁移为新语法：
  - `model="QuerySQL"` / `model="QueryMySQL"`
  - `data="Q001"` 等 DataID 形式
- 原始旧版用例已备份到 `rodski-demo/archive/v4.x/tc_database.xml`

### ✅ T21-003: 更新数据库数据表

- 已更新 `rodski-demo/DEMO/demo_full/data/data.xml` 中 `QuerySQL`/`QueryMySQL` 数据段
- 使用 `query` 字段引用模板，参数与 `:param` 对齐
- `verify` 数据支持 `${Return[-1]}` 引用

### ✅ T21-004: 清理旧模型并保留归档

- 旧模型定义已归档到 `rodski-demo/archive/v4.x/model_e.xml`
- 运行库主路径不再使用旧版 `tc_database` 语法

---

## 验证结果

### 1) 核心单元测试（iteration-20 依赖能力）

执行：

```bash
python3 -m pytest rodski/tests/unit/test_db_keyword_v5.py -q
```

结果：

- ✅ 19 passed
- ⚠️ 仅存在环境告警：`urllib3` 的 `NotOpenSSLWarning`（不影响功能）

### 2) 迁移用例可执行性检查（iteration-21）

执行：

```bash
PYTHONPATH=rodski python3 rodski/cli_main.py run rodski-demo/case/tc_database.xml --model rodski-demo/model/model_db.xml --dry-run
```

结果：

- ✅ 识别 3 个用例（TC020/TC021/TC022）
- ✅ 全部通过可执行校验（Dry Run）

---

## 验收结论

### 功能验收

- ✅ `model_db.xml` 创建并生效
- ✅ `tc_database.xml` 已迁移到新 DB 语法
- ✅ 数据表使用查询模板驱动
- ✅ 查询结果可通过 `Return` 进行引用

### 文件验收

- ✅ `rodski-demo/model/model_db.xml`
- ✅ `rodski-demo/case/tc_database.xml`
- ✅ `rodski-demo/DEMO/demo_full/data/data.xml`
- ✅ `rodski-demo/archive/v4.x/*` 备份文件存在

### 测试验收

- ✅ 关键能力单测通过
- ✅ 迁移用例可执行结构校验通过

---

## 备注

- 本记录基于当前仓库状态和实际命令验证补录。
- 如需补齐“真实数据库执行结果”证据，可在目标环境执行 TC020~TC022 的非 dry-run 运行并追加日志。
