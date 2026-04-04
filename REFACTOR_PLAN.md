# 项目文档统一重构计划

## 目标
将分散的项目管理文档统一到 `.pb/` (PhoenixBear 缩写) 隐藏目录

## 当前问题
1. **phoenixbear/** - 未隐藏，应该是 `.phoenixbear`
2. **rodski/docs/** - 与 phoenixbear 内容重复
3. **.kiro/** (根) + **rodski/.kiro/** - 分散在两处
4. 文档冗余严重，维护困难

## 统一后结构

```
.pb/                          # PhoenixBear 缩写，隐藏目录
├── design/                   # 设计文档（合并 phoenixbear/design + rodski/docs/design）
├── agent/                    # Agent 指南（合并 phoenixbear/agent + rodski/docs/agent-guides）
├── requirements/             # 需求文档（来自 phoenixbear/requirements）
├── conventions/              # 项目约定（来自 phoenixbear/conventions）
├── iterations/               # 迭代开发记录（来自 rodski/.kiro/iterations）
├── specs/                    # 规格说明（来自 .kiro/specs）
├── archive/                  # 归档文档（来自 rodski/docs/archive）
└── README.md                 # 目录说明
```

## 迁移步骤

### 1. 创建新目录结构
```bash
mkdir -p .pb/{design,agent,requirements,conventions,iterations,specs,archive}
```

### 2. 合并设计文档
```bash
# 从 phoenixbear/design 复制
cp -r phoenixbear/design/* .pb/design/

# 从 rodski/docs/design 合并（去重）
# 需要手动检查冲突文件
```

### 3. 合并 Agent 文档
```bash
cp -r phoenixbear/agent/* .pb/agent/
# rodski/docs/agent-guides 内容合并
```

### 4. 迁移其他目录
```bash
cp -r phoenixbear/requirements/* .pb/requirements/
cp -r phoenixbear/conventions/* .pb/conventions/
cp -r rodski/.kiro/iterations/* .pb/iterations/
cp -r .kiro/specs/* .pb/specs/
cp -r rodski/docs/archive/* .pb/archive/
```

### 5. 删除旧目录
```bash
rm -rf phoenixbear
rm -rf rodski/docs
rm -rf rodski/.kiro
rm -rf .kiro
```

## 自动化配置

### 更新 CLAUDE.md
在项目根目录 CLAUDE.md 中添加：
```markdown
## 项目文档位置

所有项目管理文档统一存放在 `.pb/` 目录：
- 设计文档 → `.pb/design/`
- 需求文档 → `.pb/requirements/`
- 迭代记录 → `.pb/iterations/`
- 规格说明 → `.pb/specs/`
- Agent 指南 → `.pb/agent/`
- 项目约定 → `.pb/conventions/`

**重要：** 创建新的设计、需求、迭代文档时，必须写入 `.pb/` 对应子目录。
```

### 更新 .gitignore
确保不忽略 `.pb/` 目录：
```
# 不要忽略项目文档
!.pb/
```

### 更新 Memory
在 auto-memory 中记录：
```markdown
---
name: Project Documentation Location
description: All project docs unified in .pb/ directory
type: reference
---

项目文档统一位置规则：
- 所有设计、需求、迭代、规格文档必须写入 `.pb/` 目录
- 不再使用 phoenixbear/、docs/、.kiro/ 等旧目录
- 目录结构：design/、requirements/、iterations/、specs/、agent/、conventions/、archive/

**Why:** 消除文档冗余，统一管理项目知识库

**How to apply:** 创建任何项目文档时，自动选择 `.pb/` 下对应子目录
```

## 冲突文件处理策略

对于重复文件（如 ARCHITECTURE.md、VISION_LOCATION.md）：
1. 比较两个版本的差异
2. 保留最新、最完整的版本
3. 将旧版本移到 `.pb/archive/` 并标注日期

## 验证清单

- [ ] 所有设计文档已迁移到 `.pb/design/`
- [ ] 所有迭代记录已迁移到 `.pb/iterations/`
- [ ] 所有规格说明已迁移到 `.pb/specs/`
- [ ] CLAUDE.md 已更新文档位置说明
- [ ] Memory 已记录新的文档位置规则
- [ ] 旧目录已删除
- [ ] Git 提交信息清晰

## 缩写选择

推荐 `.pb` (PhoenixBear)：
- 简短（2字符）
- 语义清晰
- 易于输入

备选：`.phx`、`.pxb`
