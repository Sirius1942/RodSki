# 附录：测试结果 XML（result.xsd）

> **来源**: RodSki 测试用例编写指南 v3.4  
> 本文档为独立章节，完整指南请见 [TEST_CASE_WRITING_GUIDE.md](../TEST_CASE_WRITING_GUIDE.md)

---


`rodski/schemas/result.xsd` 描述框架写入的 **`result/*.xml`**，手工一般**不需要**编写，了解结构即可排查报告问题。

| 约束 | 说明 |
|------|------|
| 根元素 | `<testresult>` |
| 子元素顺序 | 先 `<summary>`（1 个），再 `<results>`（1 个） |
| `<summary>` | `total` / `passed` / `failed` 必填；`skipped`、`errors` 等有默认值 |
| `<results>` 下 `<result>` | `case_id`、`status` 必填；`status` 只能是 `PASS` \| `FAIL` \| `SKIP` \| `ERROR` |

---

**文档版本**: v3.4
**最后更新**: 2026-04-02
