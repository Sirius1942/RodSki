# Iteration 32: data CLI 与可观测性

**版本**: v5.10.0  
**分支**: feature/iteration-32-data-cli  
**预计工时**: 4h  
**优先级**: P0  
**状态**: ✅ 已完成  
**依赖**: iteration-31 完成

---

## 目标

1. 新增 `rodski data` 命令族：`list` / `schema` / `show` / `query` / `validate`
2. CLI 直接复用统一数据 facade 与 schema validator，避免重复实现第二套解析逻辑
3. 提供 XML + SQLite 共存场景下的数据查询、校验与问题定位能力

## 包含工作项

| WI | 名称 | 大小 | 来源 |
|----|------|------|------|
| WI-35 | data CLI 子命令实现 | L | sqlite testdata coexistence design |
| WI-36 | CLI 注册与帮助文案 | S | sqlite testdata coexistence design |
| WI-37 | data CLI 单元测试 | M | sqlite testdata coexistence design |

## 设计约束

- `rodski data` 只做查询 / 校验，不改变 DSL 语义
- `validate` 必须覆盖跨源冲突、SQLite schema、一致性与命名规则
- `--strict` 需要额外识别 XML 列漂移
- 两个 CLI 装配入口都必须注册：`rodski/cli_main.py` 与 `rodski/rodski_cli/__init__.py`
