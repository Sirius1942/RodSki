---
name: phoenixbear_integration
description: PhoenixBear 项目管理体系已建立，整合了所有文档
type: reference
---

**PhoenixBear 已建立**，以 `phoenixbear/` 为唯一真实源。

**目录结构**：
```
phoenixbear/
├── README.md                      # 顶层入口
├── design/                        # 含⭐核心约束
│   ├── CORE_DESIGN_CONSTRAINTS.md  # ⭐ 不可违反
│   ├── TEST_CASE_WRITING_GUIDE.md # ⭐ 不可违反
│   ├── ARCHITECTURE.md
│   ├── VISION_LOCATION.md
│   ├── AGENT_AUTOMATION_DESIGN.md
│   ├── DATA_FILE_ORGANIZATION.md
│   ├── DB_DRIVER_SUPPORT.md
│   ├── json_support_design.md
│   └── archive/                   # 历史归档文档
├── conventions/                   # 项目规范
│   ├── PROJECT_CONSTRAINTS.md     # 含§8核心文档不可违反约束
│   ├── GIT_WORKFLOW.md
│   └── CI_CD_GUIDE.md
├── requirements/
├── agent/                        # Agent 开发规范
│   ├── AGENT_INTEGRATION.md
│   ├── AGENT_SKILL_GUIDE.md
│   ├── SKILL_REFERENCE.md
│   ├── LIVING_DOCUMENTATION.md
│   └── ERROR_HANDLING.md
└── iterations/                   # iteration-03~07
```

**文档整合**：
- 删除了重复文档（SPECS_GUIDE.md、API_REFERENCE.md）
- 归档了历史文档（RPA_ROADMAP、RPA_GAP_ANALYSIS 等）
- 修复了所有路径引用和旧命令
