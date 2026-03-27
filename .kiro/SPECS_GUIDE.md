# Kiro Specs 使用指南

## 什么是 Specs

Specs 是 Kiro 提供的结构化需求和任务管理机制，位于 `.kiro/specs/` 目录下。它允许你：

- 以文档形式定义功能需求和设计
- 将需求分解为可执行的任务列表
- 与 AI Agent 协作完成复杂的多步骤开发

## 目录结构

```
.kiro/
├── specs/
│   ├── feature-name/           # 功能模块目录
│   │   ├── requirements.md     # 需求文档
│   │   ├── design.md          # 设计文档
│   │   ├── tasks.md           # 任务列表
│   │   └── notes.md           # 开发笔记
│   └── SPECS_GUIDE.md         # 本指南
```

## 使用流程

### 1. 创建 Spec 目录

为新功能创建独立目录：

```bash
mkdir -p .kiro/specs/your-feature-name
```

### 2. 编写需求文档 (requirements.md)

描述功能的目标、背景和约束：

```markdown
# 功能名称

## 目标
- 实现什么功能
- 解决什么问题

## 背景
- 为什么需要这个功能
- 当前存在的问题

## 约束
- 必须遵守的设计原则
- 技术限制
```

### 3. 编写设计文档 (design.md)

详细的技术设计方案：

```markdown
# 技术设计

## 架构
- 模块划分
- 接口设计

## 实现方案
- 关键技术点
- 数据结构
- API 设计

## 示例
- 代码示例
- 使用示例
```

### 4. 分解任务 (tasks.md)

将设计拆分为可执行的任务：

```markdown
# 任务列表

## Wave 1 - 基础设施 (3任务, 2h)

### Task 1.1: 创建核心模块
- 文件: `rodski/module/core.py`
- 工作量: 30min
- 依赖: 无

### Task 1.2: 添加配置支持
- 文件: `rodski/config/settings.yaml`
- 工作量: 30min
- 依赖: Task 1.1

## Wave 2 - 功能实现 (5任务, 4h)
...
```

### 5. 与 AI 协作开发

在 Kiro 中引用 spec 文件：

```
请按照 #[[file:.kiro/specs/your-feature/tasks.md]]
中的任务列表开始开发
```

## 最佳实践

### 任务分解原则

1. **按波次组织**: 将相关任务分组为 Wave，便于并行开发
2. **明确依赖**: 标注任务间的依赖关系
3. **估算工作量**: 每个任务 15-60 分钟为宜
4. **指定文件**: 明确每个任务涉及的文件路径

### 文档引用

在 spec 文档中可以引用其他文件：

```markdown
参考 API 设计: #[[file:../design/API_REFERENCE.md]]
遵循约束: #[[file:../design/核心设计约束.md]]
```

### 版本管理

- 重大修改时创建新版本: `tasks-v2.md`, `tasks-v3.md`
- 保留历史版本用于回溯
- 在文件头部注明版本和修改原因

## 完成后的清理

功能开发完成后：

1. **归档有价值的文档**: 将设计文档移至 `rodski/docs/design/`
2. **删除临时文件**: 删除任务列表、开发笔记等临时文件
3. **保留参考价值**: 如果设计过程有参考价值，可移至 `docs/archive/`

```bash
# 归档设计文档
mv .kiro/specs/feature-name/design.md rodski/docs/design/FEATURE_NAME.md

# 删除临时文件
rm -rf .kiro/specs/feature-name/
```

## 示例：视觉定位功能

参考已完成的视觉定位功能开发过程：

- 需求分析: `.kiro/specs/rodski-doc-code-audit/vision-location-design-v2.md`
- 任务分解: `.kiro/specs/rodski-doc-code-audit/vision-location-tasks-v4.md`
- 最终文档: `rodski/docs/design/VISION_LOCATION.md`

## 注意事项

⚠️ **不要提交敏感信息**
- Spec 文件可能包含内部设计细节
- 考虑将 `.kiro/specs/` 加入 `.gitignore`（如果包含敏感信息）

⚠️ **及时清理**
- Spec 是开发过程的临时产物
- 完成后及时归档或删除，避免项目膨胀

---

**最后更新**: 2026-03-27
