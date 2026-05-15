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

- 最新发布：**v6.7.6**
- 对应路线图：契约对齐修复

## 6. 版本历史摘要

| 发布版本 | 路线图 | 主要变更 |
|---------|--------|---------|
| 5.0.0 | v5 | Excel → XML 迁移（Breaking Change → MAJOR） |
| 5.1.0 ~ 5.3.2 | v5 | 契约统一、DB 支持、Bug 修复 |
| 5.4.0 ~ 5.7.1 | v6 | 视觉定位、桌面自动化、Agent 架构 |
| 5.8.0 ~ 5.8.1 | v7 | 报告系统、可观测性、KPI、tags、elif、网络拦截 |
| 6.0.0 | v8 | 废弃 data.xml，统一 SQLite 数据层 |
| 6.1.0 | v8 | VSCode 数据表管理插件 rodski-vscode |
| **6.7.6** | **v8** | 契约对齐：XSD/运行时/数据严格化、打包统一 |

## 7. 发布流程规范

### 7.1 发布脚本（必须使用）

所有版本级别的发布**必须**通过 `scripts/release_check.sh` 完成：

```bash
# 完整流程：构建 + 验收 + 发布到 releases/
scripts/release_check.sh <version> --build --publish

# 示例
scripts/release_check.sh 6.7.6 --build --publish
```

脚本自动完成以下步骤：
1. 构建 wheel + sdist（`--build`）
2. 检查构建产物存在性
3. 验证 wheel 内容完整性（18 个关键文件）
4. 干净 venv 安装态验证（模块导入、schemas、依赖）
5. CLI 版本验证
6. 复制到 `releases/rodski/v<version>/` 并生成 SHA256SUMS + README.md（`--publish`）

**发布目录结构**：
```
releases/rodski/v<version>/
├── README.md                          # 安装说明
├── rodski-<version>-py3-none-any.whl  # wheel 包（推荐）
├── rodski-<version>.tar.gz            # 源码包
└── SHA256SUMS                         # 校验和
```

### 7.2 发布前检查清单

```bash
# 1. 确认版本号已更新（三处必须一致）
grep version pyproject.toml          # 根 pyproject.toml
grep __version__ rodski/__init__.py  # 源码版本

# 2. 运行全量单元测试
PYTHONPATH=rodski python3 -m pytest rodski/tests -q

# 3. 运行发布脚本
scripts/release_check.sh <version> --build --publish

# 4. 本地安装验证
pip install releases/rodski/v<version>/rodski-<version>-py3-none-any.whl
python3 -c "import rodski; print(rodski.__version__)"
```

### 7.3 提交与打 tag

```bash
# 提交代码（包含 releases/ 目录）
git add rodski/ pyproject.toml releases/rodski/v<version>/ scripts/
git commit -m "release(v<version>): <简要说明>"
git tag v<version>

# 推送
git push origin main --tags
```

### 7.4 禁止事项

- ❌ 手动复制 wheel 到 releases/ 目录（必须通过脚本）
- ❌ 跳过安装态验证直接发布
- ❌ 版本号不一致时发布（pyproject.toml 与 __init__.py 必须同步）
- ❌ 在 releases/ 中修改已发布版本的文件（已发布即不可变）

## 8. 分支与版本对应

| 类型 | 分支命名 | 版本示例 |
|-----|---------|---------|
| 功能迭代 | `feature/xxx` → merge to `main` | v6.1.0 |
| Bug 修复 | `fix/xxx` → merge to `main` | v6.1.1 |
| 大版本 | `release/v7.0.0` | v7.0.0 |
