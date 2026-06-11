# 版本号管理规范

**创建日期**: 2026-04-13  
**更新日期**: 2026-06-08  
**适用版本**: v8.0.0+

---

## 1. 版本号格式

```
MAJOR . MINOR . PATCH
  X   .   Y   .   Z
大版本  特性版本  修复版本
```

**当前最新版本**: `8.0.1`（截至本文档更新）

---

## 2. 三位版本号规则（核心）

### Z — 修复版本（Patch）

**触发条件**：每修复一个 Bug，Z+1。

| 触发场景 | 示例 |
|---------|------|
| Bug 修复 | endpoint name 显示为 `POST` 而非 `POST /api/login` |
| 行为修正 | MagicMock 误判导致测试失败 |
| 文档纠错 | 指南中命令写错 |
| 测试修复 | 测试期望值与新逻辑不符 |
| 兼容性补丁 | gevent monkey-patch 干扰 argparse |

**规则**：
- 修复了 N 个 Bug → Z+N（每个 Bug 对应一次 Z 递增，可合并成一次提交）
- 或：一次发布批量修复多个 Bug → Z+1（批量修复算一次）
- **推荐实践**：攒够一批修复后统一发布，而非每个 Bug 一个版本

**示例**：`8.0.0` → 修复 3 个 Bug → `8.0.1`（或依次 `.1` `.2` `.3`，取决于修复节奏）

---

### Y — 特性版本（Minor）

**触发条件**：每添加一个新功能，Y+1，Z 归零。

| 触发场景 | 示例 |
|---------|------|
| 新增能力 | 性能压测（v8.0.0 相对 v7.x.x）|
| 新增关键字 | switch 关键字 |
| 新增驱动 | PlaywrightLoadEngine |
| 新增 CLI 参数 | --load-ui |
| Schema 扩展（向后兼容）| plan.xsd 新增 kind=load |
| 新增 optional extras | rodski[load] |

**规则**：
- 向后兼容的新功能 → Y+1，Z 归 0
- **不能因为功能大就直接 X+1**（大版本由 owner 决定）

**示例**：`8.0.1` → 新增 browser 压测模式 → `8.1.0`

---

### X — 大版本（Major）

**触发条件**：由 **owner（项目负责人）手动决定**，不自动递增。

通常对应以下场景（但最终判断权在 owner）：

| 场景 | 说明 |
|------|------|
| 重大架构方向转变 | 如引入性能压测体系（7.x → 8.0） |
| 核心 Breaking Change | 删除已发布关键字、不兼容 XML 格式变更 |
| 重大路线图里程碑 | 如 RPA 能力完整落地 |

**规则**：
- X 递增时，Y 和 Z 均归零（X.0.0）
- **任何人不得在未经 owner 确认时递增 X**
- AI Agent 在开发中遇到需要递增 X 的变更，应暂停并请 owner 确认

---

## 3. 版本号决策流程图

```
变更类型判断
      │
      ├── 修复了已有功能的问题？
      │     └── YES → Z+1
      │
      ├── 添加了新功能/新能力？
      │     └── YES → Y+1，Z 归 0
      │
      └── 需要 X 递增？
            └── → 必须 owner 确认后才能操作
```

**判断时的常见陷阱**：

| 容易误判的场景 | 正确处理 |
|--------------|---------|
| 修复了很多 Bug | Z+1（不管 Bug 数量，批量修复一次 Z+1）|
| 加了很大的功能 | Y+1（大不等于 Major）|
| 重构了内部代码 | Z+1（内部重构，不影响用户接口）|
| 更新了文档 | Z+1 或不递增（视是否发布而定）|

---

## 4. 版本号文件清单

每次版本发布，以下文件必须保持一致：

| 文件 | 位置 | 更新方式 |
|------|------|---------|
| `pyproject.toml` | 根目录 | `version = "X.Y.Z"` |
| `rodski/pyproject.toml` | rodski/ 子目录（dev-only）| 同上 |
| `rodski/__init__.py` | 源码入口 | `__version__ = "X.Y.Z"` |
| `rodski-skills/VERSION` | skills 目录 | 纯文本 `X.Y.Z` |
| `CLAUDE.md` | 根目录 | 文档说明中的版本号 |

**验证命令**：

```bash
# 一次性检查所有版本号
rodski --version                            # 应输出 RodSki X.Y.Z
python3 -c "import rodski; print(rodski.__version__)"
grep '^version' pyproject.toml rodski/pyproject.toml
cat rodski-skills/VERSION
grep '当前版本' CLAUDE.md
git describe --tags HEAD                    # 应输出 vX.Y.Z
```

---

## 5. 发布操作步骤

### 5.1 Patch 发布（修复版本）

```bash
# 1. 确认所有 Bug 都已修复并测试通过
python3 -m pytest rodski/tests/unit -q

# 2. 更新版本号（Z+1）
#    修改以下文件中的版本号：
#    - pyproject.toml
#    - rodski/pyproject.toml
#    - rodski/__init__.py
#    - rodski-skills/VERSION
#    - CLAUDE.md

# 3. 提交
git add pyproject.toml rodski/pyproject.toml rodski/__init__.py \
        rodski-skills/VERSION CLAUDE.md
git commit -m "chore(vX.Y.Z): 版本号更新到 X.Y.Z"

# 4. 打 tag
git tag -a vX.Y.Z -m "vX.Y.Z — 修复摘要"

# 5. （可选）构建发布包
scripts/release_check.sh X.Y.Z --build --publish
```

### 5.2 Minor 发布（特性版本）

同 Patch 流程，但：
- 更新版本号时 Y+1，Z 归零
- commit message 用 `chore(vX.Y.0): 版本号更新到 X.Y.0`
- tag message 说明新增的功能

### 5.3 Major 发布（大版本）

- **需要 owner 明确指示**后才能操作
- 版本号更新时 X+1，Y 和 Z 归零（X.0.0）
- 通常对应一次正式的迭代里程碑完成

---

## 6. 版本历史摘要

| 版本 | 日期 | 类型 | 主要变更 |
|------|------|------|---------|
| 5.0.0 | — | Major | Excel → XML 迁移（Breaking Change）|
| 5.8.0 | — | Minor | 报告系统、可观测性、tags、elif |
| 6.0.0 | — | Major | 废弃 data.xml，统一 SQLite 数据层 |
| 6.7.6 | 2026-04 | Patch | 契约对齐：XSD/运行时/数据严格化 |
| 7.0.0 | 2026-04 | Major | Agent 优化、移动端能力增强 |
| 7.2.1 | 2026-06 | Patch | observability 接线、WI-62 修正 |
| **8.0.0** | **2026-06-07** | **Major** | **性能压测能力（api 模式，Locust 后端）** |
| **8.0.1** | **2026-06-08** | **Patch** | **修复 endpoint name、result 数据、MagicMock 误判** |

---

## 7. 与迭代文档的对应关系

| 版本类型 | 对应迭代文档 |
|---------|------------|
| Patch | 通常不单独开迭代，附在当前迭代的"修复"部分 |
| Minor | `.pb/iterations/iteration-NN/` 独立迭代 |
| Major | `.pb/iterations/iteration-NN/` + `.pb/requirements/roadmap_vX.md` |

---

## 8. 约束与禁止事项

- ✅ AI Agent 可以自主递增 Z（Patch）
- ✅ AI Agent 在完成新功能迭代后可以递增 Y（Minor）
- ❌ AI Agent **不得**在未经 owner 确认时递增 X（Major）
- ❌ 版本号递增后，各文件必须同步更新，不允许只改部分文件
- ❌ 已发布的版本号不可回退或重用

---

## 9. 独立子项目版本管理

`rodski-web` 和 `rodski-agent` 是独立代码库，各自维护版本号，与主仓库（`rodski`）完全解耦。

### 9.1 版本号文件

| 项目 | 版本文件 | 当前版本 | 备注 |
|------|---------|---------|------|
| **rodski**（主仓库）| `pyproject.toml` / `rodski/__init__.py` / `rodski-skills/VERSION` | 8.1.0 | 同步 5 处 |
| **rodski-web** | `rodski-web/VERSION` | 1.0.0 | 纯文本 |
| **rodski-agent** | `rodski-agent/pyproject.toml` + `src/rodski_agent/__init__.py` | 2.3.0 | Python 包 |

### 9.2 独立子项目版本规则

三者均遵循 `MAJOR.MINOR.PATCH` 规范，触发条件与主仓库相同（见第 2 节）。区别如下：

- **rodski-web** 发布时只需更新 `rodski-web/VERSION`，打 tag 格式：`web-vX.Y.Z`
- **rodski-agent** 发布时更新 `pyproject.toml` 和 `__init__.py`，打 tag 格式：`agent-vX.Y.Z`
- 主仓库的 `CLAUDE.md` 中"当前版本"只反映主仓库版本，不随子项目变动

### 9.3 AI Agent 操作范围

| 操作 | 主仓库会话 | rodski-web 会话 | rodski-agent 会话 |
|------|-----------|----------------|------------------|
| 修改主仓库版本 | ✅ | ❌ | ❌ |
| 修改 rodski-web 版本 | ❌ | ✅ | ❌ |
| 修改 rodski-agent 版本 | ❌ | ❌ | ✅ |
| 读取子项目代码 | ✅（只读参考）| ✅ | ✅ |

---

*文档版本: v3.0 | 最后更新: 2026-06-11*
