# RodSki VSCode Extension

RodSki 的 VSCode 插件提供 SQLite 测试数据表编辑、Case 面板和业务模型图示。

## 业务模型图

在 RodSki 测试模块的 `business/` 目录下打开 `business.xml`，右键选择：

```text
RodSki: Open Business Model Diagram
```

图面板支持：

- 多个 `business_model` 切换；
- 节点、条件边和 flow 路径展示；
- 基本流、备选流、异常流路径高亮；
- 节点步骤和业务条件详情；
- 缩放、复位、拖拽和源文件跳转；
- XML 外部修改自动刷新。

图示是业务模型 XML 的只读投影。它不会编辑 XML，也不会执行业务模型；正式执行仍必须通过 Case 中显式指定 `business_call@flow`。
