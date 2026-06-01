<!-- 自动生成 from rodski/docs/TEST_CASE_WRITING_GUIDE.md  请勿手工编辑 -->

## 10. 测试计划（plan/*.xml）

v6.3.0 起，RodSki 支持通过 `plan/*.xml` 定义测试计划，控制"本次执行跑哪些 case/scenario/step"。

### 10.1 核心概念

| 概念 | 说明 |
|------|------|
| 测试计划 | 一个 `plan/*.xml` 文件，定义本次执行的 case/scenario/step 范围 |
| `<scenario>` | case 内一个可独立选择的测试场景，写在 `<test_case>` 内 |
| 显式 plan 模式 | `rodski run @plan_id`，执行范围来自 plan XML |
| 临时 selector 模式 | `rodski run --tag smoke`，执行范围来自 case XML 元数据 |

### 10.2 在 case 中使用 `<scenario>`

```xml
<cases tags="demo" step_wait="500">
  <case execute="是" id="TC040" title="开票税点判定表" component_type="界面">
    <pre_process>
      <test_step action="navigate" data="GlobalValue.DefaultValue.URL"/>
      <test_step action="type" model="LoginForm" data="L001"/>
    </pre_process>

    <test_case>
      <scenario id="INV-001" group="positive" tag="smoke,p0"
                title="仅开票+普通发票+商品税率13，保存成功">
        <test_step action="type" model="InvoiceConfig" data="D001"/>
        <test_step action="verify" model="InvoiceConfig" data="V001"/>
      </scenario>

      <scenario id="INV-N01" group="negative" tag="p1"
                title="未选开票类型，保存提示错误">
        <test_step action="type" model="InvoiceConfig" data="D002"/>
        <test_step action="verify" model="InvoiceConfig" data="V002"/>
      </scenario>
    </test_case>

    <post_process>
      <test_step action="close" data=""/>
    </post_process>
  </case>
</cases>
```

**scenario 属性**：

| 属性 | 必填 | 说明 |
|------|------|------|
| `id` | 是 | 场景标识，同一 case 内唯一 |
| `title` | 否 | 场景描述 |
| `group` | 否 | 单值分组，如 `positive`、`negative` |
| `tag` | 否 | 多值标签，逗号分隔，如 `smoke,p0` |
| `depends` | 否 | 依赖的 scenario id，逗号分隔 |

**兼容规则**：不含 `<scenario>` 的旧 case 继续按原有步骤执行，无需改造。

### 10.3 创建测试计划

测试计划放在 `plan/` 目录，文件名格式为 `{测试目的}_{测试类型}.xml`：

```bash
# 初始化默认全量计划
rodski plan init

# 创建冒烟计划
rodski plan create invoice_smoke --kind suite --default-execute 否 --title "开票冒烟"

# 向计划添加 case 和 scenario
rodski plan add-case invoice_smoke TC040
rodski plan add-scenario invoice_smoke TC040 INV-001

# 从 tag 选择结果生成计划
rodski plan create invoice_smoke --kind suite --from-tag smoke --title "开票冒烟"
```

**plan XML 示例**（`plan/invoice_smoke.xml`）：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<test_plan id="invoice_smoke"
           title="开票冒烟测试"
           kind="suite"
           execute="是"
           default_execute="否">
  <case id="TC040" execute="是">
    <scenario id="INV-001" execute="是"/>
  </case>
</test_plan>
```

### 10.4 执行测试计划

```bash
# 执行指定计划
rodski run @invoice_smoke

# 执行默认计划（优先 plan/project_full.xml）
rodski run

# 预览计划最终执行范围（不实际执行）
rodski run @invoice_smoke --dry-run

# 查看计划列表
rodski plan list

# 校验计划引用是否有效
rodski plan validate
```

### 10.5 临时 tag/group 选择器

不需要创建 plan 文件，直接按 scenario 元数据临时筛选：

```bash
# 按 tag 执行（OR 匹配）
rodski run --tag smoke
rodski run --tag smoke,p0

# 按 group 执行（精确匹配）
rodski run --group negative

# 排除 tag
rodski run --tag smoke --exclude-tag slow

# 预览临时选择结果
rodski run --tag smoke --dry-run
```

临时 selector 不读取、不修改 `plan/*.xml`。

### 10.6 plan 与 selector 不能同时使用

显式 plan 和临时 selector 是两种独立的执行范围来源，**不能在同一次 `rodski run` 中组合**：

```bash
# ❌ 以下命令全部报错
rodski run @invoice_smoke --tag smoke
rodski run @invoice_smoke --group negative
rodski run @invoice_smoke --exclude-tag slow
rodski run @invoice_smoke --priority P0
```

如果需要把 tag 选择结果长期保存，先生成 plan 再执行：

```bash
rodski plan create invoice_smoke --from-tag smoke
rodski run @invoice_smoke
```

### 10.7 调试计划

```bash
# 创建 scenario 调试计划
rodski plan debug-scenario inv_debug --case TC040 --scenario INV-001 --prepare auto --cleanup 否

# 创建 step 调试计划
rodski plan debug-step inv_step_debug --case TC040 --scenario INV-001 --step 2 --step-mode only --prepare auto --cleanup 否

# 执行调试
rodski run @inv_debug --debug
rodski run @inv_step_debug --debug
```

**prepare 选项**：

| 值 | 行为 |
|----|------|
| `auto` | 执行 `pre_process` + 目标 step 之前的步骤 |
| `case` | 只执行 `pre_process` |
| `none` | 不执行前置，直接执行目标 |

**step_mode 选项**（仅 step_debug）：

| 值 | 行为 |
|----|------|
| `all` | 执行整个 scenario |
| `from` | 从指定 step 执行到 scenario 结束 |
| `only` | 只执行指定 step |

### 10.8 管理计划

```bash
# 禁用某个 case
rodski plan disable-case invoice_smoke TC040

# 启用某个 scenario
rodski plan enable-scenario invoice_smoke TC040 INV-001

# 预览最终执行范围
rodski plan preview invoice_smoke
```

### 10.9 执行优先级

```text
case XML 中 <case execute="否">（最高，硬关闭）
  > test_plan.execute="否"
  > plan case execute="否"
  > plan scenario execute="否"
  > plan step execute="否"
  > test_plan.default_execute（最低）
```

只要上层关闭，下层即使显式开启也不会执行。

---
