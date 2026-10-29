# demosite/plan_suites：测试计划测试套（v11.11.0）

在计划里明确划分测试套：**套内用例顺序执行，套与套之间可以并发分配**。规则见 `rodski/docs/CORE_DESIGN_CONSTRAINTS.md` §7.9，需求见 `.pb/requirements/REQ-016-plan-suites-dispatch.md`。

## 写法

```xml
<test_plan id="shop_full" kind="suite" title="商城全量（测试套）" max_parallel="2">
    <suite id="order" title="下单流程">
        <case_dir path="order"/>
        <case file="order/create.xml" id="PS_ORDER_1" data_driven="OrderMatrix"/>
    </suite>
    <suite id="special" title="特殊订单">
        <case file="order/special.xml" id="PS_SPECIAL"/>
    </suite>
    <suite id="archive" title="归档（停用）" execute="否">
        <case file="common/extra.xml" id="PS_EXTRA"/>
    </suite>
</test_plan>
```

- 计划顶层要么全是 `<suite>`，要么全是 `<case>` / `<case_dir>`。不写 `<suite>` 时整个计划是一个隐式套 `default`，行为与 v11.10 一致（`shop_legacy.xml`）。
- 用例归属：显式 `<case>` 优先于 `<case_dir>`，较长的 `case_dir` 优先于较短的。多个套之间同级冲突时报错。
- 能力 `requires` 按整条用例的全部步骤聚合（web / android / ios / desktop）。混合用例需要能同时提供这些能力的执行器，不拆分。
- 数据驱动实例跟随模板用例所在的套，按行顺序执行，不拆到不同套。
- `max_parallel` 限制同一计划同时执行的套数。

## 运行

```bash
python3 rodski-demo/_sites/demosite/app.py &                      # 共享站点 :8000（验收脚本未检测到时会自行启动）
python3 rodski-demo/demosite/plan_suites/run_acceptance.py        # 全部验收（PS-01~21）
cd rodski-demo/demosite/plan_suites
rodski plan compile @shop_full                                    # 文本摘要；--json 输出分发清单（rodski.plan-manifest/1）
rodski run @shop_full --headless                                  # 顺序执行全部启用套
rodski run @shop_full --workers 3 --headless                      # 按套并发（受 max_parallel 限制）
rodski run @shop_full --suite order --headless                    # 只执行一个套
```

数据由 `data/init_data.py` 生成（每次验收前重建，同时生成模块根目录的只读被测订单库 `orders.db`）。`case/mixed/` 下的 Android / iOS / Windows 用例只用于编译检查能力聚合，不执行。

Android 设备上按套分发的真实验收在 `rodski-demo/mobile/app/scripts/run_plan_suites_acceptance.py`（PM-01~03）。

## 验收项

| 编号 | 内容 |
|------|------|
| PS-01 | 编译清单：schema / plan_id / max_parallel / 套顺序 / execute / requires / tags / weight |
| PS-02 | 套内按发现顺序执行，数据驱动实例相邻且按行顺序 |
| PS-03 | 归属裁决：显式 `<case>` 优先于 `<case_dir>` |
| PS-04 | 停用套的用例记为 SKIP（reason=suite_execute_false） |
| PS-05 | 同一用例文件拆到多个套 → `[WARN]` |
| PS-06 | digest 稳定、与模块位置无关；改用例会变化，改 data.sqlite 不变 |
| PS-07 | 混合能力：Web+App+DB、iOS、desktop+os、business_call / if 内步骤计入 |
| PS-08 | 跨平台套报错，`--allow-cross-platform-plan` 放行 |
| PS-09 | driver_type=mobile 且无 Mobile.Platform → 报错 |
| PS-10 | 结构错误：compile / run 非 0 退出，run 不产生结果 |
| PS-11 / 12 | 隐式套编译与执行行为不变 |
| PS-13 | 顺序执行带套：结果带 suite_id，summary 带 plan_id / suites / digest |
| PS-14 / 15 | `--suite` 只执行指定套；无 @plan / 未知套 / 停用套在副作用前报错 |
| PS-16 | `--expect-digest` 不一致报错且无副作用 |
| PS-17 / 18 | `--workers` 按套并发、套内顺序保持；`max_parallel` 限制同时执行的套数 |
| PS-19 | 数据驱动不拆分 |
| PS-20 | 计划模式下 `--workers` 只看选中用例 |
| PS-21 | 文本摘要列出套 / 能力 / 标签 / 并发上限 |
