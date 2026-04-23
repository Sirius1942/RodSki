# 版本号管理规范

**创建日期**: 2026-04-13
**更新日期**: 2026-04-16

---

## 1. 语义化版本格式

```
MAJOR.MINOR.PATCH
  X  .  Y  .  Z
```

## 2. 递增规则

| 位 | 含义 | 何时递增 | Z/Y 归零 |
|----|------|---------|---------|
| **Z（PATCH）** | Bug 修复、文档纠错、小补丁 | 不改功能行为，只修问题 | — |
| **Y（MINOR）** | 新功能、功能增强、重构 | **向后兼容**的功能变更 | Z 归零 |
| **X（MAJOR）** | 架构级 Breaking Change | 旧用法/数据格式不兼容 | Y 和 Z 归零 |

## 3. 判断标准（重要）

### 递增 PATCH (Z+1)
- Bug 修复、热修补
- 文档小修、注释更新
- 测试补充（不改功能）

### 递增 MINOR (Y+1)
- 新增关键字、新增模块（如 report/、observability/）
- 新增 CLI 参数（如 --tags、--report）
- Schema 新增可选属性（向后兼容）
- 新增内建函数（如 mock_route）
- if/elif 语法扩展（原有 if/else 仍可用）

### 递增 MAJOR (X+1) — 仅以下情况
- XML Schema 不兼容变更（删除必需属性、修改元素结构）
- 删除或重命名已发布关键字
- 核心引擎架构重写（如 Excel → XML 迁移）
- Python API 公共接口不兼容变更

### 绝对不递增 MAJOR 的场景
- 新增功能（不管多大） — 用 MINOR
- 内部重构（不影响用户接口） — 用 MINOR 或 PATCH
- 路线图阶段推进（如 v7 路线图的功能） — 用 MINOR

## 4. 路线图版本 vs 发布版本

**路线图版本**（如 v7、v8）是内部规划标识，标注功能方向和阶段。

**发布版本**（如 5.8.0）是面向用户的语义化版本号，写入 `pyproject.toml`。

两者独立：

| 路线图 | 发布版本 | 说明 |
|--------|---------|------|
| v6 Phase 0-3 | 5.1.0 ~ 5.7.1 | 视觉定位、桌面自动化等 |
| v7 Phase 4-6 | **5.8.0** | 报告系统、可观测性、tags、elif 等 |
| v8（待定） | 5.9.0 或 5.10.0 | RPA 相关功能 |

只有真正不兼容的架构变更才推进到 **6.0.0**。

## 5. 当前版本

- 最新发布：**v6.1.0**
- 对应路线图：VSCode 数据表管理插件

## 6. 版本历史摘要

| 发布版本 | 路线图 | 主要变更 |
|---------|--------|---------|
| 5.0.0 | v5 | Excel → XML 迁移（Breaking Change → MAJOR） |
| 5.1.0 ~ 5.3.2 | v5 | 契约统一、DB 支持、Bug 修复 |
| 5.4.0 ~ 5.7.1 | v6 | 视觉定位、桌面自动化、Agent 架构 |
| 5.8.0 ~ 5.8.1 | v7 | 报告系统、可观测性、KPI、tags、elif、网络拦截 |
| 6.0.0 | v8 | 废弃 data.xml，统一 SQLite 数据层 |
| **6.1.0** | **v8** | VSCode 数据表管理插件 rodski-vscode |

## 7. 发布流程规范

每次发布需完成以下步骤：

```bash
# 1. 更新版本号
# pyproject.toml → version = "X.Y.Z"
# rodski-vscode/package.json → version = "X.Y.Z"（如有 VSCode 插件变更）

# 2. 运行全量测试（确认无新增失败）
PYTHONPATH=rodski python3 -m rodski.ski_run rodski-demo/DEMO/demo_full/case/demo_case.xml

# 3. 提交代码
git add <files>
git commit -m "release(vX.Y.Z): ..."
git tag vX.Y.Z

# 4. 推送到 GitHub
git push origin main --tags

# 5. 发布到 PyPI
python3 -m build
python3 -m twine upload dist/rodski-X.Y.Z*

# 6. 创建 GitHub Release（附 .vsix 文件如有）
gh release create vX.Y.Z [附件] --title "..." --notes "..."
```

## 8. 分支与版本对应

| 类型 | 分支命名 | 版本示例 |
|-----|---------|---------|
| 功能迭代 | `feature/xxx` → merge to `main` | v6.1.0 |
| Bug 修复 | `fix/xxx` → merge to `main` | v6.1.1 |
| 大版本 | `release/v7.0.0` | v7.0.0 |
