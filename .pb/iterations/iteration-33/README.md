# Iteration 33: init CLI 与 demo 验收收口

**版本**: v5.10.0  
**分支**: feature/iteration-33-init-cli  
**预计工时**: 4h  
**优先级**: P0  
**状态**: ✅ 已完成  
**依赖**: iteration-32 完成

---

## 目标

1. 新增 `rodski init`，创建符合 RodSki 约束的标准测试模块骨架
2. 支持可选创建 `data_verify.xml` 与 `testdata.sqlite`
3. 补齐 `rodski-demo` 验收场景与最终回归
4. 完成从分支开发到 main 发布的版本收口说明

## 包含工作项

| WI | 名称 | 大小 | 来源 |
|----|------|------|------|
| WI-38 | init CLI 子命令实现 | M | sqlite testdata coexistence design |
| WI-39 | SQLite 元表初始化 | M | sqlite testdata coexistence design |
| WI-40 | demo acceptance 补齐 | M | sqlite testdata coexistence design |
| WI-41 | 发布前收口与文档校对 | S | sqlite testdata coexistence design |

## 设计约束

- `init` 只创建骨架和模板文件，不生成业务测试内容
- 默认不覆盖已有文件；仅 `--force` 允许覆盖模板文件
- `--with-sqlite` 时必须直接创建设计约束要求的 SQLite 元表结构
- 发布流程遵循“分支开发，main 发布”
