# Iteration 25: 框架文档修正

> 版本: v5.3.1
> 分支: fix/v5.3.1-validation
> 日期: 2026-04-11
> 工时: 2h
> 优先级: P1
> 前置依赖: 无（文档修改独立于数据/代码修改）
> 设计文档: `.pb/specs/verify-data-organization-fix.md` 第一部分 3.3E + 第二部分 5.3

---

## 需求

### 业务需求

- 框架文档与代码实现存在三方矛盾，需统一以代码为准
- verify 数据中 `${Return[-1]}` 的使用限制需要在文档中明确约束
- 防止后续 AI Agent 或开发者按错误文档创建无效文件

### 技术需求

修正 4 份文档：
1. `DATA_FILE_ORGANIZATION.md` — 补全 `data_verify.xml` + 加载规则
2. `TEST_CASE_WRITING_GUIDE.md` — 新增 7.4 节 + 修正文件组织描述（9 处）
3. `CORE_DESIGN_CONSTRAINTS.md` — 新增 4.3 节禁止规则
4. `SKILL_REFERENCE.md` — verify 条目追加备注

---

## 开发任务

### T25-001: DATA_FILE_ORGANIZATION.md 修正 (预计 30min)

**文件**: `rodski/docs/DATA_FILE_ORGANIZATION.md`

**任务**:
1. 在数据目录结构说明中增加 `data_verify.xml` 条目
2. 增加"加载规则"段落，明确框架只读三个固定文件名
3. 修正后目标内容：

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

**验收**:
- [ ] `data_verify.xml` 已在目录结构中标注
- [ ] 加载规则段落已添加
- [ ] 与代码实现一致（`DataTableParser` 只读这两个文件）

### T25-002: TEST_CASE_WRITING_GUIDE.md 文件组织修正 (预计 45min)

**文件**: `rodski/docs/TEST_CASE_WRITING_GUIDE.md`

**任务**: 修正 9 处文件组织描述 + 新增 7.4 节

**修正清单**:

| 位置 | 当前（错误） | 修正为 |
|------|-------------|--------|
| ~第 68-73 行 目录结构 | `Login.xml` / `Login_verify.xml` 独立文件 | `data.xml` / `data_verify.xml` |
| ~第 82-83 行 映射表 | `{模型名}.xml` → `data/` | 合并到 `data/data.xml` 中的 datatable |
| | `{模型名}_verify.xml` → `data/` | 合并到 `data/data_verify.xml` 中的 datatable |
| ~第 95 行 XSD 约束 | `datatable@name 必须与文件名一致` | `datatable@name 必须与模型名一致` |
| ~第 480 行 | `data/Login_verify.xml` | `data_verify.xml 中的 Login_verify 表` |
| ~第 709 行 示例 | `${Return[-1]}` 用于 verify 数据 | 改为字面期望值 + 追加 7.4 节禁止说明 |
| ~第 769 行 | `{模型名}_verify.xml` | `data_verify.xml 中的 {模型名}_verify 表` |
| ~第 821 行 | `data/LoginAPI_verify.xml` | `data_verify.xml 中的 LoginAPI_verify 表` |
| ~第 922 行 目录树 | `Login_verify.xml` | 替换为 `data_verify.xml` |

**新增 7.4 节**（在第 7.3 节 "Return 引用的正确用法" 后追加）:

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

**验收**:
- [ ] 9 处文件组织描述已修正
- [ ] 7.4 节已添加，位置正确
- [ ] 无遗漏

### T25-003: CORE_DESIGN_CONSTRAINTS.md 新增 4.3 节 (预计 30min)

**文件**: `rodski/docs/CORE_DESIGN_CONSTRAINTS.md`

**任务**: 在第 4.2 节 "Return 引用" 后追加 4.3 节

**新增内容**:

```markdown
### 4.3 verify 数据表中 ${Return} 的使用限制

**禁止：接口/DB 模型的 _verify 表中使用 ${Return[-1]}**

verify 对接口和数据库模型的实际值**自动从 Return[-1] 提取**（按模型元素的 locator 字段匹配）。
如果期望值也写 ${Return[-1]}，则期望值和实际值取自同一数据源，比较结果永远相等，
断言失去验证价值（"空校验"）。

<!-- 禁止与正确用法的 XML 示例 -->

**判断规则**：
- verify 模型的 `__model_type__` 为 `interface` 或 `database` → 禁止 `${Return[-1]}`
- verify 模型的 `__model_type__` 为 `ui` → 允许（实际值来源不同）
```

（完整内容见设计文档 5.3A 节）

**验收**:
- [ ] 4.3 节已添加，位于 4.2 节之后
- [ ] 包含禁止规则 + 代码示例 + 判断规则

### T25-004: SKILL_REFERENCE.md verify 备注 (预计 15min)

**文件**: `rodski/docs/SKILL_REFERENCE.md`

**任务**: 在 verify 关键字条目中追加备注

**新增内容**:
```markdown
> 注意：接口/DB 模型的 _verify 数据表禁止使用 ${Return[-1]}，详见 CORE_DESIGN_CONSTRAINTS 4.3 节。
```

**验收**:
- [ ] 备注已添加在 verify 关键字说明中
- [ ] 引用路径正确

### T25-005: 文档交叉验证 (预计 15min)

**任务**:
1. 检查 4 份文档修正后的一致性
2. 确认无矛盾描述
3. 确认所有文件路径引用正确

**验收**:
- [ ] 4 份文档关于数据文件组织的描述一致
- [ ] verify 自引用禁止规则在 3 份文档中出现且一致

---

## 验收标准

1. **一致性**: 4 份文档关于数据文件组织的描述与代码实现一致
2. **完整性**: verify 自引用禁止规则在 CORE_DESIGN_CONSTRAINTS、TEST_CASE_WRITING_GUIDE、SKILL_REFERENCE 中均有体现
3. **准确性**: 所有文件路径、加载规则描述与 `DataTableParser` / `ModelParser` 代码一致
