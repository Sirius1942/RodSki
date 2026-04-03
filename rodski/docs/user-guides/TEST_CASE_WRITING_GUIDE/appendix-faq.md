# 附录：常见问题

> **来源**: RodSki 测试用例编写指南 v3.4  
> 本文档为独立章节，完整指南请见 [TEST_CASE_WRITING_GUIDE.md](../TEST_CASE_WRITING_GUIDE.md)

---


### Q1: 用例没有执行？

1. 检查 Case XML 的 `execute` 属性是否为 `是`（不是 `Y`、`true`；XSD 仅允许 `是` / `否`）
2. 检查 XML 文件编码是否为 UTF-8
3. 检查 XML 格式是否合法（可用浏览器打开验证）
4. 可选：用 `xmllint` 对照 `rodski/schemas/case.xsd` 校验（见上文 **§2.2 Schema 约束**）

### Q2: type 批量输入失败？

1. 检查 model.xml 元素 `name` 是否与数据表 field `name` **完全一致**（区分大小写）
2. 检查定位方式是否正确（用浏览器 F12 验证）
3. 数据表中未定义的字段会被跳过

### Q3: verify 报错"缺少验证目标"？

verify 必须同时填写 **model 和 data** 属性，走批量验证模式。不支持只传 locator 的简单模式。

### Q4: DB 连接失败？

1. 检查 globalvalue.xml 中是否有对应组名的连接配置
2. SQLite：确认 `database` 路径正确且文件存在
3. MySQL/PostgreSQL：确认已安装对应驱动（pymysql / psycopg2）

### Q5: Return 引用没有生效？

Return 引用只应写在**数据表 XML 的 field 值中**，不要直接写在 Case XML。如果 Return 引用的索引不存在，原文保持不变。

### Q6: 数据引用不生效？

1. 检查数据文件名是否正确（必须与 datatable name 一致）
2. 检查 DataID（row id）是否存在
3. 引用格式：`表名.DataID`（整行）或 `表名.DataID.字段名`（单字段）

### Q7: XSD 校验报错「元素 test_step 缺失」？

`case.xsd` 要求每个 `<case>` **必须**包含恰好一个 `<test_step>`。仅写 `<pre_process>` 等而不写 `<test_step>` 不会通过校验。

---

