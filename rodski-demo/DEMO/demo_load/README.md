# demo_load — 接口压测示例

本示例演示 RodSki 负载测试（kind=load）能力，使用 LoginAPI 和 OrderAPI 两个接口。

## 目录结构

```
demo_load/
├── case/
│   ├── api_login.xml        # TC-LOAD-001 登录接口压测
│   └── api_order_query.xml  # TC-LOAD-002 查询订单接口压测
├── model/
│   └── model.xml            # LoginAPI / OrderAPI 接口模型
├── data/
│   ├── globalvalue.xml      # 全局变量（URL、WaitTime）
│   └── data.sqlite          # EAV 测试数据
├── plan/
│   └── api_load_basic.xml   # 负载计划：并发 5，持续 30 秒
└── perf/                    # 压测结果输出目录（框架自动写入）
```

## 运行方式

```bash
# 执行压测计划
rodski run rodski-demo/DEMO/demo_load/case/ @plan_id=api_load_basic

# 生成 HTML 报告
rodski run rodski-demo/DEMO/demo_load/case/ @plan_id=api_load_basic --report html
```

## 压测参数

| 参数 | 值 |
|------|----|
| 模式 | api |
| 并发数 | 5 |
| 持续时间 | 30 秒 |
| 爬坡时间 | 5 秒 |
| 思考时间 | 100~500 ms |
| TC-LOAD-001 权重 | 2 |
| TC-LOAD-002 权重 | 1 |
