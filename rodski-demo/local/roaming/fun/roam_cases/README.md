# fun/roam_cases — F109/F110 补充用例源文件

这些用例**不放在** `case/` 下：`run_demo.py` 断言 `rodski run <模块> --roam` 只产生 1 个用例结果，
且 `api_roam.xml`（接口用例声明 `roam="是"`）在解析阶段就抛 `SKI803`，会让整个模块无法执行。

`run_acceptance_extra.py` 把模块复制到临时目录，再按每个检查项的需要把这里的文件复制进临时模块的
`case/negative/` 后执行，不修改本模块任何已有文件。
