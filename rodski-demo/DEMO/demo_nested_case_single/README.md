# demo_nested_case_single — plan 省略 file 的兼容验收

模块 `case/` 下（递归）只有一个用例文件 `case/only/only_case.xml`，此时 `plan/legacy_plan.xml` 中的 `<case id="TC002"/>` 可省略 `file`，自动指向唯一文件。

由 `../demo_nested_case/run_acceptance.py A13` 驱动验收。
