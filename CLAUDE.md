# RodSki 项目 - Claude 协作指南

> RodSki 是面向 AI Agent 的跨平台确定性测试执行引擎。当前版本：v8.0.0

## 核心文档（每次开发前必读）

| 文档 | 路径 | 说明 |
|------|------|------|
| **核心设计约束** | `rodski/docs/CORE_DESIGN_CONSTRAINTS.md` | **不可违反**，每次迭代必须对照检查 |
| **用例编写指南** | `rodski/docs/TEST_CASE_WRITING_GUIDE.md` | 用例/模型/数据编写规范 |
| 框架架构 | `rodski/docs/ARCHITECTURE.md` | 整体架构 |
| API 参考 | `rodski/docs/API_REFERENCE.md` | 公开 API |
| 关键字语法 | `rodski/docs/SKILL_REFERENCE.md` | 关键字详细参数 |
| Agent 集成 | `rodski/docs/AGENT_INTEGRATION.md` | Agent 集成指南 |
| 数据文件组织 | `rodski/docs/DATA_FILE_ORGANIZATION.md` | 数据文件规范 |
| 数据库支持 | `rodski/docs/DB_DRIVER_SUPPORT.md` | DB 驱动 |
| **性能压测指南** | `rodski/docs/LOAD_TESTING_GUIDE.md` | v8.0 压测能力（plan/perf/Web UI）|

**项目管理文档存放在 `.pb/` 目录：**

- **需求文档** → `.pb/requirements/`
- **迭代记录** → `.pb/iterations/`
- **规格说明** → `.pb/specs/`
- **项目约定** → `.pb/conventions/`
- **归档文档** → `.pb/archive/`

---

## 不可违反的核心约束（摘自 CORE_DESIGN_CONSTRAINTS.md）

### 关键字清单（17 个，不可随意新增）

```python
SUPPORTED = [
    "close", "type", "verify", "wait", "navigate", "launch",
    "assert", "evaluate", "screenshot",
    "upload_file", "clear", "get_text", "get",
    "send", "set", "DB", "run",
]
# 兼容关键字：check（等同 verify）
```

- `click / double_click / right_click / hover / select / key_press / drag / scroll` **不是独立关键字**，只能写在数据表 field 值中，由 `type` 批量模式识别
- 不存在 `http_get / http_post / assert_json / assert_status` 等独立 HTTP 关键字
- 新增关键字必须同时更新 `rodski/schemas/case.xsd` 和 `CORE_DESIGN_CONSTRAINTS.md`

### 数据文件约束

- `data/data.sqlite` 是**唯一**测试数据文件（v6.0.0 起）
- `data.xml` / `data_verify.xml` 已废弃，若存在则运行时报错
- `globalvalue.xml` 独立维护，不进入 SQLite
- v6.7.6 起：同一逻辑表所有行字段集合必须完全一致，缺字段必须显式填 BLANK/NULL/NONE

### 模型定位器约束（v5.4.0 起）

唯一支持的格式：`<location type="类型">值</location>`

```xml
<!-- 正确 -->
<element name="loginBtn" type="web">
    <location type="id">loginBtn</location>
</element>

<!-- 错误（已废弃） -->
<!-- <element name="loginBtn" type="id" value="loginBtn"/> -->
```

### 目录结构（强制）

```
product/                    ← 顶层，固定名称
└── {项目名}/
    └── {模块名}/
        ├── case/           ← 用例 XML
        ├── model/          ← model.xml（唯一文件名）
        ├── fun/            ← run 关键字脚本
        ├── data/           ← data.sqlite + globalvalue.xml
        ├── plan/           ← 测试计划 XML
        └── result/         ← 框架自动生成
```

- `product/` 必须是最顶层，不可省略
- 6 个固定文件夹名称不可更改
- `model.xml` 是唯一的模型文件名

### Return 引用规则

- `${Return[-1]}` 只能写在**数据表 field 值**中，不能写在 Case XML 的 `data` 属性
- 接口/DB 模型的 `_verify` 表中**禁止**使用 `${Return[-1]}`（v6.7.6 起硬性约束）
- UI 模型的 `_verify` 表中允许引用 `${Return[-N]}`（跨源比对）

### 测试计划约束（v6.3.0）

- `@plan_id` 与 `--tag / --group / --priority` 等 selector **固定互斥**，不能同时使用
- 一个计划一个 XML 文件，文件名 stem = 计划 ID
- 计划 XML 不得写入 `data.sqlite`

### 测试分层约束

- 单元测试：`rodski/tests/`，允许 pytest
- 验收测试：必须在 `rodski-demo/` 中落地为可执行用例
- 只有单元测试通过而无 `rodski-demo` 验收用例，**不能判定为验收完成**

### 合规检查清单（每次提交前）

- [ ] SUPPORTED 关键字列表与文档一致
- [ ] UI 原子动作不在 SUPPORTED 中
- [ ] 目录结构符合 `product/项目/模块` 规范
- [ ] 测试计划只存放在 `plan/*.xml`，不进入 `data.sqlite`
- [ ] `@plan_id` 与 selector 固定互斥
- [ ] 数据表格式符合规范（字段集合一致）
- [ ] 视觉定位器使用 `<location>` 子节点格式

---

## 项目结构

```
RodSki/
├── .pb/                    # 项目管理文档（需求、迭代、规格）
├── .claude/                # Claude 项目配置
├── rodski/                 # 核心框架代码
│   ├── docs/               # 框架文档（AI Agent 必读）
│   ├── core/               # 核心引擎
│   ├── drivers/            # 驱动层
│   ├── schemas/            # XSD Schema
│   └── tests/              # 单元测试
├── rodski-demo/            # 框架官方示例（唯一示例目录）
├── cassmall/               # 业务测试用例
└── CLAUDE.md               # 本文件
```

### 示例目录规则

- **`rodski-demo/`** 是 RodSki 唯一的示例目录，需纳入版本管理
- `rodski-demo/` 中的用例和结构严格遵循 `rodski/docs/TEST_CASE_WRITING_GUIDE.md`
- ❌ `rodski/examples/` 已废弃，不再使用

### 禁止使用的旧目录

❌ 不再使用：`phoenixbear/`、`.kiro/`、`rodski/.kiro/`、`rodski/examples/`

---

## 文档创建规则

1. **框架使用文档**（架构、API、指南）→ `rodski/docs/`
2. **项目管理文档**（需求、迭代、规格）→ `.pb/` 对应子目录
3. **迭代开发记录** → `.pb/iterations/iteration-XX/`

## 开发约定

详见 `.pb/conventions/` 目录下的文档。

## 常用命令

```bash
# 运行测试
python3 rodski/selftest.py

# 运行 Demo 验收
rodski run rodski-demo/DEMO/demo_full/case/

# 可观测性：导出 trace.json（run/case/keyword 三层 span + 耗时/重试指标）
rodski run <case/> --trace
# --report html 也会顺带采集指标，报告含"性能概览"区块

# run 调内置函数（如网络拦截 mock_route/wait_for_response/clear_routes）
# 注意：内置函数 model 必须为空，否则被当作 fun/ 外部脚本工程名
#   正确: <test_step action="run" model="" data="mock_route(...)"/>
#   内置函数实现在 rodski/builtin_ops/（非 builtins/）

# 数据迁移
rodski data import <module>

# 校验 XML
xmllint --noout --schema rodski/schemas/case.xsd <case.xml>

# 查看数据
rodski data list <module>
rodski data show <module> <table> <data_id>

# 性能压测（v8.0，需要 pip install rodski[load]）
rodski run @api_load_basic                        # 执行 kind=load 压测计划
rodski run @api_load_basic --load-ui              # 压测 + Locust Web UI 实时监控
rodski run @api_load_basic --load-ui-port 9090    # 指定监控端口
rodski run @api_load_basic --no-compile           # 跳过预编译（调试用）
```
