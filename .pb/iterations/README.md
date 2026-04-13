# 迭代规划总览

**最近更新**: 2026-04-13

---

## 已完成迭代

| 迭代 | 版本 | 状态 | 主要内容 |
|------|------|------|----------|
| iteration-14 ~ 19 | v4.6.0 ~ v4.11.0 | ✅ 已完成 | P0修复、清理、demosite、关键字、视觉定位、负面测试 |
| iteration-20 | v5.0.0 | ✅ 已完成 | DB 关键字重写 |
| iteration-21 | v5.1.0 | ✅ 已完成 | DB demo 迁移 |
| iteration-22 | v5.2.0 | ✅ 已完成 | 文档更新 |
| iteration-23 | v5.3.1 | ✅ 已完成 | 数据文件组织修正 |
| iteration-24 | v5.3.1 | ✅ 已完成 | verify 空校验修复 |
| iteration-25 | v5.3.1 | ✅ 已完成 | 框架文档修正 |

---

## 架构改进迭代 (iteration-26 ~ 29)

**规划来源**: `.pb/requirements/architecture_improvement_v6.md`  
**总体规划**: `.pb/iterations/iteration-26-29-plan.md`  
**目标**: 将 RodSki 收敛为"面向 AI Agent 的确定性执行引擎 + 活文档协议层"

| 迭代 | 版本 | 工时 | 状态 | 主要内容 |
|------|------|------|------|----------|
| iteration-26 | v5.4.0 | 5h | 📋 待开始 | 契约统一（代码）+ Excel 移除 + Agent 示例归档 |
| iteration-27 | v5.5.0 | 4h | 📋 待开始 | 文档契约统一（定位器 + Excel） |
| iteration-28 | v5.6.0 | 5h | 📋 待开始 | LLM 统一服务层（capabilities + config 合并） |
| iteration-29 | v5.7.0 | 4h | 📋 待开始 | 定位叙事统一（README + AGENT_INTEGRATION 重写） |

**合计**: 18h

### 迭代依赖

```
iteration-26 → iteration-27 → iteration-28 → iteration-29
```

### 下一步

从 iteration-26 开始执行：

```bash
git checkout main && git pull
git checkout -b release/v5.4.0
# 参考 .pb/iterations/iteration-26/tasks.md
```

---

## 关键原则

1. **按顺序执行** — 不要跳过或并行
2. **每个迭代独立交付** — 完成后立即发布版本
3. **任务失败立即停止** — 记录问题，调整计划
4. **文档同步更新** — 每个迭代都要更新 record.md
5. **回归测试必做** — 确保无回归问题

---

## 历史规划

- `.pb/iterations/iteration-14-19-plan.md` — 迭代 14-19 总体规划
- `.pb/iterations/iteration-26-29-plan.md` — 迭代 26-29 架构改进规划
