# 开发和测试工程相关的核心约束

**版本**: v3.7
**日期**: 2026-03-27

## 1. 项目结构说明

### 1.1 核心框架代码

**位置**：`rodski/`

**说明**：RodSki 测试框架的核心代码，包括：
- `core/` - 核心引擎（解析器、执行器、关键字引擎）
- `drivers/` - 驱动层（浏览器、接口、数据库）
- `data/` - 数据处理模块
- `schemas/` - XML Schema 定义

**开发约束**：
- 所有核心功能修改必须保持向后兼容
- 新增关键字需要同步更新 `schemas/case.xsd`
- 修改数据格式需要更新相关文档

### 1.2 Demo 演示项目

**位置**：`rodski-demo/DEMO/`

**目的**：通过简单的示例项目演示 RodSki 的各种用法和功能

**包含项目**：
- `demo_full/` - 完整功能演示（UI、接口、数据库、Return引用等）
- `demo_runtime_control/` - 运行时控制演示（暂停、插入、终止）

**约束**：
- Demo 项目必须简单易懂，代码量最小化
- 每个 Demo 必须有独立的 README.md 说明
- Demo 用例必须能够独立运行
- 不依赖外部真实业务系统

### 1.3 业务测试项目

**位置**：项目根目录下的独立目录（如 `cassmall/`）

**目的**：真实业务场景的自动化测试

**特点**：
- 独立于 Demo 项目
- 包含真实业务逻辑
- 可能依赖外部系统
- 测试数据来自真实业务

**当前项目**：
- `cassmall/thdh/` - Cassmall 同行调货业务测试

## 2. 功能发布测试流程

### 2.1 核心功能测试

**步骤**：

1. **单元测试**（如果有）
   ```bash
   python3 rodski/selftest.py
   ```

2. **Demo 项目验证**
   ```bash
   # 运行完整功能 Demo
   python3 rodski/ski_run.py rodski-demo/DEMO/demo_full/case/demo_case.xml

   # 运行运行时控制 Demo
   python3 rodski/ski_run.py rodski-demo/DEMO/demo_runtime_control/case/runtime_case.xml
   ```

3. **验收标准**
   - 所有 Demo 用例通过
   - 无异常错误
   - 结果文件正常生成

### 2.2 新功能测试

**添加新关键字时**：

1. 在 `schemas/case.xsd` 中添加关键字定义
2. 在 `demo_full/` 中添加演示用例
3. 更新相关文档（API_TESTING_GUIDE.md 等）
4. 运行完整测试验证

**添加新数据格式时**：

1. 更新相关 Schema 文件
2. 在 Demo 中添加示例
3. 更新 TEST_CASE_WRITING_GUIDE.md
4. 验证向后兼容性

### 2.3 回归测试

**每次发布前必须执行**：

```bash
# 1. 运行所有 Demo 项目
python3 rodski/ski_run.py rodski-demo/DEMO/demo_full/case/demo_case.xml
python3 rodski/ski_run.py rodski-demo/DEMO/demo_runtime_control/case/runtime_case.xml

# 2. 检查结果
ls -la rodski-demo/DEMO/*/result/

# 3. 验证关键功能
# - 登录流程
# - 接口测试
# - 数据库操作
# - Return 引用
# - 步骤等待时间
```

## 3. 测试数据管理

### 3.1 Demo 项目数据

**原则**：
- 使用本地数据（SQLite、本地服务）
- 数据可重复初始化
- 不依赖外部网络

**示例**：
```bash
# demo_full 初始化数据库
cd rodski-demo/DEMO/demo_full
python3 init_db.py
```

### 3.2 业务项目数据

**原则**：
- 使用测试环境账号
- 在 `data/globalvalue.xml` 中配置
- 敏感信息不提交到代码库

**示例**：
```xml
<group name="test_account">
    <var name="username" value="test_user"/>
    <var name="password" value="test_pass"/>
</group>
```

## 4. 持续集成建议

### 4.1 CI 流程

```yaml
# 示例 CI 配置
test:
  script:
    - python3 rodski/selftest.py
    - python3 rodski/ski_run.py rodski-demo/DEMO/demo_full/case/demo_case.xml
  artifacts:
    paths:
      - rodski-demo/DEMO/*/result/
```

### 4.2 测试报告

**位置**：`{project}/result/`

**格式**：XML 格式结果文件

**内容**：
- 用例执行状态
- 执行时间
- 错误信息
- 截图路径（失败时）

## 5. 开发规范

### 5.1 代码提交前检查

- [ ] 运行 Demo 项目验证
- [ ] 更新相关文档
- [ ] 检查向后兼容性
- [ ] 添加必要的注释

### 5.2 文档更新

**必须同步更新的文档**：
- `phoenixbear/design/CORE_DESIGN_CONSTRAINTS.md`（核心设计约束）
- `phoenixbear/design/TEST_CASE_WRITING_GUIDE.md`（用例编写指南）
- API_TESTING_GUIDE.md（接口相关）
- QUICKSTART.md（入门相关）

### 5.3 版本发布

**发布清单**：
1. 所有 Demo 测试通过
2. 文档已更新
3. CHANGELOG 已记录
4. 版本号已更新

## 6. 故障排查

### 6.1 Demo 失败排查

**常见问题**：
- 数据库未初始化 → 运行 `init_db.py`
- 端口被占用 → 检查 8000 端口
- 浏览器驱动问题 → 检查 Playwright 安装

### 6.2 业务测试失败排查

**常见问题**：
- 账号密码错误 → 检查 `globalvalue.xml`
- 网络连接问题 → 检查测试环境可访问性
- 页面元素变化 → 更新 `model.xml`

## 7. 最佳实践

### 7.1 Demo 项目开发

- 保持简单，一个 Demo 演示一个功能点
- 提供完整的运行脚本
- 包含详细的 README
- 数据可重复初始化

### 7.2 业务项目开发

- 独立目录，不混入 Demo
- 使用有意义的项目名称
- 配置文件与代码分离
- 定期维护测试数据

### 7.3 测试用例编写

- 用例 ID 有规律（TC001、TC002...）
- 标题清晰描述测试内容
- 添加 post_process 清理资源
- 合理使用全局等待时间

---

## 8. 核心文档不可违反约束

以下两份文档是每个迭代的实现**绝对不能违反**的约束基准：

| 文档 | 路径 | 说明 |
|------|------|------|
| **核心设计约束** | `../design/CORE_DESIGN_CONSTRAINTS.md` | 框架核心设计决策与约束规则 |
| **用例编写指南** | `../design/TEST_CASE_WRITING_GUIDE.md` | 用例编写规范 |

### 8.1 约束条款

1. **每次迭代的代码改动在上线前，必须逐一对照上述两份文档检查合规性**
2. **若发现文档描述与代码实现不一致，以文档为准**（文档是规范，代码必须服从）
3. **不允许在代码中实现与上述文档描述相矛盾的功能**
4. **新增关键字或变更关键字行为，必须同时更新** `CORE_DESIGN_CONSTRAINTS.md`
5. **新增或变更 XML Schema、XSD 约束，必须同时更新** `TEST_CASE_WRITING_GUIDE.md`

### 8.2 合规检查清单

每次代码提交前，对照核心设计约束检查：

- [ ] SUPPORTED 关键字列表与文档一致（§5）
- [ ] UI 原子动作（click/hover 等）不在 SUPPORTED 中（§1.2）
- [ ] 目录结构符合 `product/项目/模块` 规范（§6）
- [ ] 自检不使用 pytest（§9）
- [ ] 数据表格式符合规范（§7.3）
- [ ] 视觉定位器类型符合规范（§10）

---

**最后更新**: 2026-04-02
