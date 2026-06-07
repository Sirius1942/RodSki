---
name: rodski-test-guide
description: >
  RodSki 用例 / 模型 / 数据 / 关键字编写权威指南。当用户询问如何写 RodSki 用例、
  如何写 model.xml、关键字（type / verify / send / DB / run / navigate / wait / get /
  set / screenshot / assert / clear / upload_file / launch / evaluate / close / check）
  怎么用、data.sqlite 怎么填、Case XML 三阶段（pre_process / test_case / post_process）
  格式、scenario 容器、测试计划 plan/*.xml、GlobalValue 引用、Return 索引、视觉定位器
  vision/ocr/vision_bbox、桌面端 / 移动端自动化时触发。完整内容按章节拆分在 reference/*.md，
  Agent 命中后按需 Read 对应章节。
type: reference
version: 7.2.1
source: rodski/docs/TEST_CASE_WRITING_GUIDE.md
---

# RodSki 用例编写指南 Skill

## 触发时机

当用户的问题命中以下任一意图时调用：

- **写用例**：「帮我写一个 RodSki 用例」「Case XML 怎么写」「pre_process / test_case / post_process 分别放什么」
- **写模型**：「model.xml 怎么写」「定位器格式」「vision 定位怎么用」
- **填数据**：「data.sqlite 怎么填」「数据表字段一致性」「BLANK / NULL / NONE」「Return 引用怎么用」「random / date 函数」
- **关键字使用**：「type / verify / send / DB / run / get / set / wait / navigate / launch / screenshot / assert / clear / upload_file / evaluate / close 怎么用」「click / select / hover 是关键字吗」
- **测试计划**：「plan/*.xml 怎么写」「scenario 容器」「按 tag/group 筛选」
- **平台**：「桌面端怎么测」「移动端怎么测」「Appium 配置」「app:// URI」
- **校验失败**：「XSD 校验报错」「Schema 约束」

## 使用方式

本 Skill 采用**章节切片**结构：

1. SKILL.md（本文件）只提供索引与速查
2. 完整章节内容存放在 `reference/*.md`，按需 Read
3. **不要一次性 Read 全部章节**，根据用户具体问题选取 1~2 个相关章节即可

## 章节索引

| 文件 | 章节 | 适用问题 |
|------|------|---------|
| [`reference/01_concepts.md`](reference/01_concepts.md) | 1. 核心概念：关键字 + 模型 + 数据 | 三要素如何协作、整体心智模型 |
| [`reference/02_directory.md`](reference/02_directory.md) | 2. 目录结构 | `product/项目/模块/{case,model,data,fun,plan,result}` 六文件夹规范、XSD 校验入口 |
| [`reference/03_case_xml.md`](reference/03_case_xml.md) | 3. Case XML — 用例编写 | `<cases>` / `<case>` / `<pre_process>` / `<test_case>` / `<post_process>` / `<test_step>` / `<scenario>` / `<if>` / `<loop>` 属性与执行语义 |
| [`reference/04_model_xml.md`](reference/04_model_xml.md) | 4. model.xml — 模型编写 | `<model>` / `<element>` / `<location type>` 全部 12 种定位器、多定位器优先级 |
| [`reference/05_data_tables.md`](reference/05_data_tables.md) | 5. 数据表 — 测试数据编写 | `data.sqlite` EAV 元表、`rodski data` 命令、字段一致性、UI 动作关键字（click / select / key_press 等）、SQL 数据表 |
| [`reference/06_global_value.md`](reference/06_global_value.md) | 6. GlobalValue XML — 全局变量 | `globalvalue.xml` 格式、`GlobalValue.组名.变量` 引用、WaitTime、数据库连接 |
| [`reference/07_variable_refs.md`](reference/07_variable_refs.md) | 7. 数据引用与变量解析 | `${Return[-1]}` 索引、set/get 命名变量、内置 `random()` / `date()` 函数、verify 自引用禁忌 |
| [`reference/08_keywords.md`](reference/08_keywords.md) | 8. 关键字手册 | 17 个 SUPPORTED 关键字详解、type/send/verify 三大核心、接口模型 `_method` / `_url` / `_header_*` |
| [`reference/09_examples.md`](reference/09_examples.md) | 9. 完整示例 | model.xml / globalvalue.xml / data.sqlite / case.xml 端到端样例、`rodski run` CLI 选项 |
| [`reference/10_test_plan.md`](reference/10_test_plan.md) | 10. 测试计划 plan/*.xml | `rodski plan` 命令族、显式 plan 与临时 selector 互斥、scenario 调试 |
| [`reference/11_dynamic_steps.md`](reference/11_dynamic_steps.md) | 11. 固定与动态测试步骤（规划） | 运行时插入步骤、暂停 / 终止 / 强制终止语义 |
| [`reference/12_vision_locator.md`](reference/12_vision_locator.md) | 12. 视觉定位器 vision / vision_bbox | OmniParser + LLM 语义定位、坐标定位、配置 vision_config.yaml |
| [`reference/13_desktop.md`](reference/13_desktop.md) | 13. 桌面端自动化 | `driver_type=windows/macos`、`launch` 启动、屏幕绝对坐标、桌面操作脚本约定 |
| [`reference/14_mobile.md`](reference/14_mobile.md) | 14. 移动端自动化 | `driver_type=android/ios`、`app://` URI、Appium 配置、视觉降级策略 |
| [`reference/90_faq.md`](reference/90_faq.md) | 附录 常见问题 | execute=是 / type 失败 / verify 报错 / DB 连接 / Return 不生效 等排查 |
| [`reference/91_keyword_cheatsheet.md`](reference/91_keyword_cheatsheet.md) | 附录 关键字速查清单 | 16 个 ActionType 枚举值（含 `check` 兼容项）一句话说明 |
| [`reference/92_result_xml.md`](reference/92_result_xml.md) | 附录 测试结果 XML result.xsd | 框架生成的 `result/*.xml` 结构 |

## 不可违反的核心约束（速查）

> 完整列表见 `rodski/docs/CORE_DESIGN_CONSTRAINTS.md`。

### 17 个 SUPPORTED 关键字

```
close, type, verify, wait, navigate, launch,
assert, evaluate, screenshot,
upload_file, clear, get_text, get,
send, set, DB, run
```

兼容关键字：`check` ≡ `verify`。

**禁止当作独立关键字**：`click / double_click / right_click / hover / select / key_press / drag / scroll` —— 这些只能写在数据表 field 值中，由 `type` 批量模式识别。

**不存在**：`http_get / http_post / assert_json / assert_status` —— 接口测试用 `send` + `verify`。

### 数据文件

- `data/data.sqlite` 是**唯一**测试数据文件（v6.0.0+）
- `data.xml` / `data_verify.xml` 已废弃
- `globalvalue.xml` 独立维护
- 同一逻辑表所有行字段集合必须完全一致（v6.7.6+），缺字段必须显式写 `BLANK` / `NULL` / `NONE`

### 模型定位器（v5.4.0+）

唯一支持格式：`<location type="类型">值</location>`。简化属性格式 `type="..." value="..."` 已移除。

### 目录结构（强制）

```
product/{项目}/{模块}/{case,model,data,fun,plan,result}/
```

6 个固定文件夹名不可改；`model.xml` 是唯一模型文件名。

### Return 引用规则

- `${Return[-1]}` 只写在**数据表 field 值**中，不能写在 Case XML 的 `data` 属性
- 接口 / DB 模型的 `_verify` 表中**禁止**使用 `${Return[-1]}`（自引用恒真）
- UI 模型的 `_verify` 表中允许引用 `${Return[-N]}`（跨源比对）

### 测试计划

- `@plan_id` 与 `--tag / --group / --priority` **固定互斥**
- 一个计划一个 XML，文件名 stem = 计划 ID
- 计划 XML 不进 `data.sqlite`

## 维护说明

- **本文件 + reference/ 均由 `rodski/docs/TEST_CASE_WRITING_GUIDE.md` 生成**
- 修改请编辑源文档，然后运行：

  ```bash
  bash rodski-skills/scripts/sync_test_guide.sh
  ```

- 版本号由发布流程 `bump_all_versions()` 自动同步，无需手工改 frontmatter
