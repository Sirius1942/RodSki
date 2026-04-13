# RodSki 项目 - Claude 协作指南

> RodSki 是面向 AI Agent 的跨平台确定性测试执行引擎。

## 项目文档位置 ⚠️ 重要

**框架文档（AI Agent 必读）统一存放在 `rodski/docs/`：**

- `rodski/docs/ARCHITECTURE.md` — 框架架构
- `rodski/docs/CORE_DESIGN_CONSTRAINTS.md` — 核心设计约束（不可违反）
- `rodski/docs/API_REFERENCE.md` — API 参考
- `rodski/docs/TEST_CASE_WRITING_GUIDE.md` — 测试用例编写指南
- `rodski/docs/SKILL_REFERENCE.md` — 关键字语法参考
- `rodski/docs/AGENT_INTEGRATION.md` — Agent 集成指南
- `rodski/docs/DATA_FILE_ORGANIZATION.md` — 数据文件组织
- `rodski/docs/DB_DRIVER_SUPPORT.md` — 数据库支持
- `rodski/docs/json_support_design.md` — JSON 支持
- `rodski/docs/VISION_LOCATION.md` — 视觉定位

**项目管理文档存放在 `.pb/` 目录：**

- **需求文档** → `.pb/requirements/`
- **迭代记录** → `.pb/iterations/`
- **规格说明** → `.pb/specs/`
- **项目约定** → `.pb/conventions/`
- **归档文档** → `.pb/archive/`

### 文档创建规则

1. **框架使用文档**（架构、API、指南）→ `rodski/docs/`
2. **项目管理文档**（需求、迭代、规格）→ `.pb/` 对应子目录
3. **迭代开发记录**（iteration-XX）→ `.pb/iterations/iteration-XX/`

### 禁止使用的旧目录

❌ 不再使用以下目录：
- `phoenixbear/`
- `.kiro/`
- `rodski/.kiro/`
- `rodski/examples/` — 已废弃，示例统一放在 `rodski-demo/`

## 项目结构

```
RodSki/
├── .pb/                    # 项目管理文档（需求、迭代、规格）
├── rodski/
│   ├── docs/               # 框架文档（AI Agent 必读）
│   └── ...                 # 核心框架代码
├── rodski-demo/            # 框架官方示例（基于 TEST_CASE_WRITING_GUIDE.md）
├── cassmall/               # 业务测试用例
└── CLAUDE.md               # 本文件
```

### 示例目录规则

- **`rodski-demo/`** 是 RodSki 唯一的示例目录，需纳入版本管理
- `rodski-demo/` 中的用例和结构严格遵循 `rodski/docs/TEST_CASE_WRITING_GUIDE.md`
- ❌ `rodski/examples/` 已废弃，不再使用

## 开发约定

详见 `.pb/conventions/` 目录下的文档。
