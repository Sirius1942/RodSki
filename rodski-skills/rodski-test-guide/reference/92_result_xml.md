<!-- 自动生成 from rodski/docs/TEST_CASE_WRITING_GUIDE.md  请勿手工编辑 -->

## 附录：测试结果 XML（result.xsd）

`rodski/schemas/result.xsd` 描述框架写入的 **`result/*.xml`**，手工一般**不需要**编写，了解结构即可排查报告问题。

| 约束 | 说明 |
|------|------|
| 根元素 | `<testresult>` |
| 子元素顺序 | 先 `<summary>`（1 个），再 `<results>`（1 个） |
| `<summary>` | `total` / `passed` / `failed` 必填；`skipped`、`errors` 等有默认值 |
| `<results>` 下 `<result>` | `case_id`、`status` 必填；`status` 只能是 `PASS` \| `FAIL` \| `SKIP` \| `ERROR`；`case_file`（v11.5.0 新增，可选）记录该用例所属文件相对 `case/` 的 POSIX 路径，跨文件同 `case_id` 时用于消歧，见 [§3.2.1](#321-用例-id-唯一性v11500)、[§9.8](#98-结果目录说明v11500) |

---

**文档版本**: v11.5.0
**最后更新**: 2026-09-28
