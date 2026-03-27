# Git 工作流规范

## 分支策略

采用**分支开发、主干发布**模式（Trunk-Based Development）

### 主干分支

- `main` - 主干分支，始终保持可发布状态
- 所有发布从 main 分支打 tag

### 开发流程

**每轮迭代必须从主干创建新分支**：

```bash
# 1. 确保主干最新
git checkout main
git pull origin main

# 2. 创建功能分支（命名规范见下文）
git checkout -b feature/your-feature-name

# 3. 开发和提交
git add .
git commit -m "feat: 功能描述"

# 4. 合并回主干
git checkout main
git merge feature/your-feature-name

# 5. 删除功能分支
git branch -d feature/your-feature-name
```

## 分支命名规范

```
feature/功能名称    - 新功能开发
fix/问题描述        - Bug修复
refactor/重构内容   - 代码重构
docs/文档更新       - 文档修改
test/测试内容       - 测试相关
chore/杂项任务      - 构建、工具等
```

**示例**：
- `feature/vision-location`
- `fix/excel-parser-crash`
- `refactor/keyword-engine`
- `docs/update-api-reference`
- `chore/cleanup-deprecated-code`

## 提交信息规范

遵循 Conventional Commits：

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type 类型**：
- `feat` - 新功能
- `fix` - Bug修复
- `refactor` - 重构
- `docs` - 文档
- `test` - 测试
- `chore` - 构建、工具、依赖等
- `perf` - 性能优化
- `style` - 代码格式（不影响功能）

**示例**：
```
feat(vision): 添加视觉定位支持

- 实现 OmniParser 客户端
- 集成多模态 LLM 分析
- 支持 vision: 和 vision_bbox: 定位器

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
```

## 合并策略

- **小功能**：直接合并到 main
- **大功能**：可以先合并到 develop 分支测试，稳定后再合并到 main
- **紧急修复**：从 main 创建 hotfix 分支，修复后立即合并回 main

## 发布流程

```bash
# 1. 确保 main 分支测试通过
pytest rodski/tests/

# 2. 更新版本号（setup.py, __init__.py）
# 3. 创建发布标签
git tag -a v2.1.0 -m "release: v2.1.0 - 功能描述"
git push origin v2.1.0

# 4. 生成 CHANGELOG
```

## 注意事项

⚠️ **禁止直接在 main 分支开发**
⚠️ **每个功能必须从最新的 main 创建分支**
⚠️ **合并前确保测试通过**
⚠️ **保持提交历史清晰，避免无意义的提交**

---

**最后更新**: 2026-03-27
