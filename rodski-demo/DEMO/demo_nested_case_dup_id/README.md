# demo_nested_case_dup_id — 文件内用例 ID 重复（负向验收）

`case/dup/dup_in_file.xml` 中 `TC001` 出现两次（第二个 `execute="否"`），执行前必须报错、指出文件与 ID、不启动浏览器。
`case/dup/other.xml` 与之跨文件同 ID，属于合法情况。

由 `../demo_nested_case/run_acceptance.py A14 A17` 驱动验收。
