# RodSki 项目 - Claude 协作指南

## 项目文档位置 ⚠️ 重要

**所有项目管理文档统一存放在 `.pb/` 目录（PhoenixBear 缩写）：**

- **设计文档** → `.pb/design/`
- **需求文档** → `.pb/requirements/`
- **迭代记录** → `.pb/iterations/`
- **规格说明** → `.pb/specs/`
- **Agent 指南** → `.pb/agent/`
- **项目约定** → `.pb/conventions/`
- **归档文档** → `.pb/archive/`

### 文档创建规则

创建任何项目文档时，必须遵循以下规则：

1. **设计文档**（架构、技术方案）→ `.pb/design/`
2. **需求文档**（功能需求、用户故事）→ `.pb/requirements/`
3. **迭代开发记录**（iteration-XX）→ `.pb/iterations/iteration-XX/`
4. **规格说明**（specs、mockups）→ `.pb/specs/`
5. **Agent 相关文档**（工作流、技能）→ `.pb/agent/`

### 禁止使用的旧目录

❌ 不再使用以下目录：
- `phoenixbear/`
- `rodski/docs/`
- `.kiro/`
- `rodski/.kiro/`

## 项目结构

```
RodSki/
├── .pb/                    # 项目文档（隐藏目录）
├── rodski/                 # 核心框架代码
├── cassmall/               # 业务测试用例
└── CLAUDE.md               # 本文件
```

## 开发约定

详见 `.pb/conventions/` 目录下的文档。
