# 数据文件组织与 verify 规则修正设计

> 状态: 待审核
> 日期: 2026-04-11
> 分支: fix/v5.3.1-validation

---

## 1. 问题背景

当前存在两类问题：

1. **文件组织矛盾**: 文档 vs 代码 vs 实际数据三方不一致，导致死文件
2. **verify 空校验**: `_verify` 数据表中大量使用 `${Return[-1]}` 导致"自己跟自己比"，断言永远通过，失去验证价值

---

## 第一部分：数据文件组织修正

## 2. 三方矛盾详情

### 2.1 文档 A — TEST_CASE_WRITING_GUIDE.md（每个模型独立文件）

描述了一套从未被实现的架构：

```
data/
├── Login.xml            ← 数据表（与模型同名）
├── Login_verify.xml     ← 验证数据表
└── QuerySQL.xml         ← SQL 数据表
```

关键描述（均与代码实现矛盾）：
- 第 70 行: `Login_verify.xml ← 验证数据表`
- 第 83 行: `验证数据表 Sheet → {模型名}_verify.xml`
- 第 95 行: `datatable@name 必须与文件名一致（不含 .xml）`
- 第 480 行: `verify Login V001 → data/Login_verify.xml`
- 第 769 行: 数据文件列 `{模型名}_verify.xml`
- 第 821 行: 示例路径 `data/LoginAPI_verify.xml`
- 第 922 行: 目录树列出 `Login_verify.xml`

**问题**: 文档描述的独立文件模式**代码从未实现**，按此文档创建的文件框架不会加载。

### 2.2 文档 B — DATA_FILE_ORGANIZATION.md（单一 data.xml，遗漏 verify）

- 明确写道: "所有数据表必须合并到一个 data.xml 文件中"
- **完全没有提到 `_verify` 和 `data_verify.xml`**

### 2.3 代码实现（data.xml + data_verify.xml 两文件）

**data_table_parser.py** — 唯一的数据加载入口：
```python
self.data_file = self.data_dir / "data.xml"          # 主数据
self.verify_file = self.data_dir / "data_verify.xml"  # verify 数据

def parse_all_tables(self):
    self._parse_file(self.data_file)       # 加载 data.xml
    self._parse_file(self.verify_file)     # 加载 data_verify.xml（可选）
```

**ski_executor.py** — 模型加载入口：
```python
self.model_file = self.model_dir / "model.xml"    # 只读这一个文件
```

**关键事实**: 
- `DataTableParser` 只读 `data.xml` + `data_verify.xml`，**无目录扫描逻辑**
- `ModelParser` 只读 `model.xml`，**无多文件加载逻辑**

### 2.4 死文件来源追溯

通过 git 历史追溯，这些死文件的产生经过了三个阶段：

| 时间 | 提交 | 事件 |
|------|------|------|
| 04-07 | `1566dcc` v4.4.0 | AI Agent 按文档 A 创建了独立的 `{Model}.xml` / `{Model}_verify.xml` 文件 |
| 04-09 | `078bcd7` expect_fail | 另一次开发将同样的数据合并进了 `data.xml`（正确做法） |
| 04-10 | `ffdb940` v4.7.0 | 清理了 44 个独立文件，但**漏删了 7 个** |

漏删的 7 个文件从 v4.7.0 一直存活到现在，与 `data.xml` 内容重复。

### 2.5 矛盾汇总

| 维度 | 文档 A (GUIDE) | 文档 B (ORGANIZATION) | 代码实现 | 实际数据 |
|------|---------------|----------------------|---------|---------|
| 输入数据 | `{Model}.xml` 独立文件 | `data.xml` 合并 | **只读 `data.xml`** | data.xml + 死文件 |
| verify 数据 | `{Model}_verify.xml` 独立 | 未提及 | **只读 `data_verify.xml`** | 混在 data.xml |
| 模型文件 | 未涉及 | 未涉及 | **只读 `model.xml`** | model.xml + 死文件 |
| 目录扫描 | 隐含支持 | 不涉及 | **不支持** | N/A |

## 3. 文件组织修正方案

### 3.1 原则：以代码实现为准，文档和数据向代码对齐

### 3.2 目标目录结构

```
project/
├── model/
│   └── model.xml             ← 所有模型定义（唯一模型文件）
├── data/
│   ├── data.xml              ← 所有输入数据表（type/send/DB 用）
│   ├── data_verify.xml       ← 所有验证数据表（verify 用）
│   └── globalvalue.xml       ← 全局变量
└── ...
```

### 3.3 修改清单

#### A. 数据文件整理 — rodski-demo/DEMO/demo_full/

| 操作 | 文件 | 说明 |
|------|------|------|
| **拆分** | `data/data.xml` | 将 33 个 `_verify` datatable 移出 |
| **新建** | `data/data_verify.xml` | 用 `<datatables>` 根元素承接所有 `_verify` 表 |
| **删除** | `data/DemoForm.xml` | 死文件 |
| **删除** | `data/DemoFormVerify_verify.xml` | 死文件 |
| **删除** | `data/EvaluateResult_verify.xml` | 死文件 |
| **删除** | `data/GetVerify_verify.xml` | 死文件 |
| **删除** | `data/LoginAPICapture.xml` | 死文件 |
| **删除** | `data/LoginAPICapture_verify.xml` | 死文件 |
| **删除** | `data/SetGetVerify_verify.xml` | 死文件 |

#### B. 数据文件整理 — rodski-demo/ (根)

| 操作 | 文件 | 说明 |
|------|------|------|
| **拆分** | `data/data.xml` | 将 `_verify` datatable 移出 |
| **新建** | `data/data_verify.xml` | 承接 `_verify` 表 |

#### C. 模型文件整理 — rodski-demo/ (根)

| 操作 | 文件 | 说明 |
|------|------|------|
| **合并** | `model/model_db.xml` | 内容合并到 `model/model.xml`，然后删除 |
| **合并** | `model/model_e.xml` | 内容合并到 `model/model.xml`，然后删除 |
| **合并** | `model/model_f.xml` | 内容合并到 `model/model.xml`，然后删除 |

#### D. 其他 DEMO 子目录

| 目录 | 文件 | 操作 |
|------|------|------|
| `DEMO/vision_web/data/` | `data_verify.xml` | **保留** |
| `DEMO/vision_web/data/` | `SearchPage_verify.xml` | **删除**（死文件） |
| `DEMO/iteration-01-vision/data/` | `LoginPage_verify.xml` | **合并**到 data_verify.xml 后删除 |

#### E. 框架文档修正

**DATA_FILE_ORGANIZATION.md** — 补全 verify + 明确加载规则，修改后完整目标：

```markdown
## 数据目录结构

data/
├── data.xml             # 所有输入数据表（必须）
├── data_verify.xml      # 所有验证数据表（verify 关键字使用，可选）
└── globalvalue.xml      # 全局变量（独立）

## 加载规则

框架只加载以上三个固定文件名，不扫描目录下其他 XML 文件。

1. 输入数据（type/send/DB 关键字使用）→ 全部放入 data.xml
2. 验证数据（verify 关键字使用）→ 全部放入 data_verify.xml
3. 全局变量 → globalvalue.xml
4. data/ 目录下的其他 XML 文件不会被框架读取
```

**TEST_CASE_WRITING_GUIDE.md** — 需修正的段落（文件组织部分）：

| 位置 | 当前（错误） | 修正为 |
|------|-------------|--------|
| 第 68-73 行 目录结构 | `Login.xml` / `Login_verify.xml` 独立文件 | `data.xml` / `data_verify.xml` |
| 第 82-83 行 映射表 | `{模型名}.xml` → `data/` 目录 | 合并到 `data/data.xml` 中的 datatable |
| | `{模型名}_verify.xml` → `data/` 目录 | 合并到 `data/data_verify.xml` 中的 datatable |
| 第 95 行 XSD 约束 | `datatable@name 必须与文件名一致` | `datatable@name 必须与模型名一致` |
| 第 480 行 | `data/Login_verify.xml` | `data_verify.xml 中的 Login_verify 表` |
| 第 709 行 示例 | `${Return[-1]}` 用于 verify 数据 | 改为字面期望值 + 追加 7.4 节禁止说明 |
| 第 769 行 | `{模型名}_verify.xml` | `data_verify.xml 中的 {模型名}_verify 表` |
| 第 821 行 | `data/LoginAPI_verify.xml` | `data_verify.xml 中的 LoginAPI_verify 表` |
| 第 922 行 目录树 | `Login_verify.xml` | 替换为 `data_verify.xml` |

---

## 第二部分：verify 空校验修正

## 4. 问题分析

### 4.1 verify 的实际值获取机制

`_batch_verify` 对非 UI 模型（接口/DB）的处理（keyword_engine.py:1405-1411）：

```python
# 非 UI 模型：实际值自动从 Return[-1] 取
last_return = self.get_return(-1)
if isinstance(last_return, dict):
    actual_val = self._get_nested_return(last_return, locator_value or element_name)
```

verify **已经自动从 `Return[-1]` 中按模型元素的 locator 提取实际值**。

### 4.2 数据表中 `${Return[-1]}` 的解析时机

期望值在比较前会经过 `data_resolver.resolve_with_return()` 解析（keyword_engine.py:1362-1363）：

```python
expected = str(data_row[element_name])
if self.data_resolver:
    expected = self.data_resolver.resolve_with_return(expected)  # ← 先解析引用
```

当 `_verify` 数据表写了 `${Return[-1].title}` 时：

1. `resolve_with_return` 将 `${Return[-1].title}` 解析为实际值 → 比如 `"DemoSite"`
2. `_batch_verify` 再从 `Return[-1]` 取 `title` 字段 → 也得到 `"DemoSite"`
3. 比较 `"DemoSite" == "DemoSite"` → **永远 PASS**

**这是"自己跟自己比"的空校验，不可能失败，没有任何断言价值。**

### 4.3 受影响用例清单

| 数据表 | 字段 | 当前值 | 问题 |
|--------|------|--------|------|
| `EvaluateResult_verify` V001 | title | `${Return[-1].title}` | 自己比自己 |
| `ReturnTest_verify` V001 | result | `${Return[-1]}` | 自己比自己 |
| `SetGetVerify_verify` V001 | value | `${Return[-1]}` | 自己比自己 |
| `GetVerify_verify` V001 | result | `${Return[-1]}` | 自己比自己 |
| `GetModelVerify_verify` V001 | formResult | `${Return[-1].formResult}` | 自己比自己 |
| `DemoFormVerify_verify` V001 | resultId | `${Return[-1].resultId}` | 自己比自己 |
| `KeywordTest_verify` V002 | formResult | `${Return[-1]}` | 自己比自己 |
| `QuerySQL_verify` V001 | order_no | `${Return[-1][0].order_no}` | 自己比自己 |
| `QuerySQL_verify` V003 | total | `${Return[-1][0].total}` | 自己比自己 |
| `QueryMySQL_verify` V001 | order_no | `${Return[-1][0].order_no}` | 自己比自己 |

### 4.4 `${Return[-1]}` 在 verify 数据表中的合法用途

`${Return[-1]}` 在 verify 数据表中**并非全部错误**，有一种合法场景：

**跨步骤传值验证**：verify 的模型是 UI 模型时，实际值从页面元素读取（不从 Return 取），而期望值引用前序步骤的 Return 做比对。此时两侧数据来源不同，是真正的断言。

```xml
<!-- 合法：UI 模型 verify，实际值从页面读取，期望值从前序步骤 Return 取 -->
<!-- 步骤1: send LoginAPI D001 → Return[-1] = {token: "abc"} -->
<!-- 步骤2: verify PageDisplay V001 → 从页面读实际值，与 Return[-1] 的 token 比较 -->
<datatable name="PageDisplay_verify">
  <row id="V001">
    <field name="tokenDisplay">${Return[-2].token}</field>  <!-- 合法：跨源比对 -->
  </row>
</datatable>
```

**非法场景总结**：当 verify 的模型类型为接口/DB 时，实际值本身就从 `Return[-1]` 取，此时期望值再写 `${Return[-1]}` 就是自引用。

## 5. verify 空校验修正方案

### 5.1 数据修正：将空校验替换为字面期望值

示例：

```xml
<!-- 修正前：空校验 -->
<field name="title">${Return[-1].title}</field>

<!-- 修正后：写明具体期望值 -->
<field name="title">DemoSite</field>
```

完整修正表见第 4.3 节，每个字段需根据业务逻辑确定具体的期望字面值。

### 5.2 代码防护：在 `_batch_verify` 中增加自引用检测

在 `keyword_engine.py` 的 `_batch_verify` 方法中，对非 UI 模型增加警告：

```python
# keyword_engine.py _batch_verify 方法，在 resolve_with_return 之前
raw_expected = str(data_row[element_name])

# 自引用检测：非 UI 模型的 verify 数据中不应使用 ${Return[-1]}
if model_type != MODEL_TYPE_UI and '${Return[-1]}' in raw_expected:
    logger.warning(
        f"[空校验警告] {element_name}: 期望值 '{raw_expected}' "
        f"引用了 Return[-1]，但 verify 在接口/DB 模式下实际值也取自 "
        f"Return[-1]，这会导致自己跟自己比较，断言永远通过。"
        f"请改为具体的期望字面值。"
    )
```

### 5.3 文档约束：在三处文档中增加禁止规则

#### A. CORE_DESIGN_CONSTRAINTS.md — 第 4.2 节 "Return 引用" 后追加

追加内容：

```markdown
### 4.3 verify 数据表中 ${Return} 的使用限制

**禁止：接口/DB 模型的 _verify 表中使用 ${Return[-1]}**

verify 对接口和数据库模型的实际值**自动从 Return[-1] 提取**（按模型元素的 locator 字段匹配）。
如果期望值也写 ${Return[-1]}，则期望值和实际值取自同一数据源，比较结果永远相等，
断言失去验证价值（"空校验"）。

```xml
<!-- 禁止：接口/DB verify 的期望值引用 Return[-1]（自己比自己） -->
<datatable name="LoginAPI_verify">
  <row id="V001">
    <field name="token">${Return[-1].token}</field>    <!-- ✗ 空校验 -->
  </row>
</datatable>

<!-- 正确：写明具体的期望字面值 -->
<datatable name="LoginAPI_verify">
  <row id="V001">
    <field name="token">demo_token_123</field>         <!-- ✓ 真正断言 -->
  </row>
</datatable>
```

**允许：UI 模型的 _verify 表中引用 ${Return[-N]}（N >= 2 或跨模型）**

UI verify 的实际值从页面元素读取（不从 Return 取），期望值引用前序步骤的
Return 做跨源比对，这是合法的断言。

```xml
<!-- 允许：UI verify 的期望值引用前序步骤结果做跨源比对 -->
<datatable name="PageDisplay_verify">
  <row id="V001">
    <field name="displayToken">${Return[-2].token}</field>  <!-- ✓ 页面值 vs 接口值 -->
  </row>
</datatable>
```

**判断规则**：
- verify 模型的 `__model_type__` 为 `interface` 或 `database` → 禁止 `${Return[-1]}`
- verify 模型的 `__model_type__` 为 `ui` → 允许（实际值来源不同）
```

#### B. TEST_CASE_WRITING_GUIDE.md — 第 7.3 节 "Return 引用的正确用法" 后追加

追加内容：

```markdown
### 7.4 verify 数据表中禁止自引用

接口和数据库模型的 `_verify` 数据表中**禁止**使用 `${Return[-1]}`。

原因：verify 对接口/DB 模型自动从 `Return[-1]` 读取实际值。如果期望值也引用 `Return[-1]`，
等于自己跟自己比较，断言永远通过，无法发现问题。

| 场景 | 期望值 | 结论 |
|------|--------|------|
| 接口/DB verify + `${Return[-1]}` | 自引用 | **禁止** |
| 接口/DB verify + 字面值 `"demo_token"` | 真正断言 | **正确** |
| UI verify + `${Return[-2].token}` | 跨源比对 | **允许** |
```

#### C. SKILL_REFERENCE.md — verify 关键字条目追加备注

在 verify 关键字说明中追加：

```markdown
> 注意：接口/DB 模型的 _verify 数据表禁止使用 ${Return[-1]}，详见 CORE_DESIGN_CONSTRAINTS 4.3 节。
```

---

## 第三部分：代码层面无需修改的部分

### 6.1 assert 与 verify 的关系

| | **verify** | **assert** |
|--|--|--|
| **用途** | 数据验证（文本/字段值比较） | 视觉断言（图片/视频像素比对） |
| **实际值来源** | UI: 页面元素文本；接口/DB: `Return[-1]` | 截图像素 / 录屏帧 |
| **期望值来源** | `_verify` 数据表中的字符串 | 参考图片文件 |
| **比较方式** | 字符串包含或相等 | OpenCV 图像相似度 |

**结论**: verify（数据断言）和 assert（视觉断言）职责完全不同，两者都需要保留。

### 6.2 代码无需修改的模块

| 文件 | 说明 |
|------|------|
| `rodski/core/data_table_parser.py` | 已实现 data.xml + data_verify.xml 两文件加载 |
| `rodski/core/ski_executor.py` | 已使用固定路径 model.xml / data/ |
| `rodski/core/model_parser.py` | 已实现单文件 model.xml 加载 |
| `rodski/schemas/data.xsd` | 已支持 `<datatables>` 合并根元素 |

### 6.3 需要修改的代码

| 文件 | 修改 | 说明 |
|------|------|------|
| `rodski/core/keyword_engine.py` | `_batch_verify` 增加自引用检测 warning | 见 5.2 节 |

---

## 7. 验证计划

修改完成后重新运行全量测试确认无回归：

```bash
# 1. 初始化 DB
python3 rodski-demo/run_demo.py --init-db

# 2. demo_full 主用例
python3 rodski/ski_run.py rodski-demo/DEMO/demo_full/case/demo_case.xml

# 3. 独立 DB 用例
python3 rodski/ski_run.py rodski-demo/case/tc_database.xml

# 4. 独立数据引用用例
python3 rodski/ski_run.py rodski-demo/case/tc_data_ref.xml

# 5. 独立脚本用例
python3 rodski/ski_run.py rodski-demo/case/tc_script.xml
```

通过标准: 与修改前通过率一致（不引入新失败）。

## 8. 修改总览

| 类别 | 文件 | 操作 |
|------|------|------|
| **数据拆分** | demo_full/data/data.xml | 拆出 _verify 表到 data_verify.xml |
| **数据拆分** | rodski-demo/data/data.xml | 同上 |
| **死文件清理** | demo_full/data/ 下 7 个独立 XML | 删除 |
| **死文件清理** | model/ 下 model_db/e/f.xml | 合并后删除 |
| **死文件清理** | 其他 DEMO 子目录独立 _verify.xml | 合并后删除 |
| **空校验修复** | data_verify.xml 中 10 处 ${Return[-1]} | 替换为字面期望值 |
| **代码防护** | keyword_engine.py `_batch_verify` | 增加自引用检测 warning |
| **文档修正** | CORE_DESIGN_CONSTRAINTS.md | 新增 4.3 节禁止规则 |
| **文档修正** | TEST_CASE_WRITING_GUIDE.md | 新增 7.4 节 + 修正文件组织描述 |
| **文档修正** | DATA_FILE_ORGANIZATION.md | 补全 data_verify.xml + 加载规则 |
| **文档修正** | SKILL_REFERENCE.md | verify 条目追加备注 |
