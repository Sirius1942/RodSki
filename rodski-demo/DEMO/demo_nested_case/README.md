# demo_nested_case — 用例目录多级嵌套验收（v11.5.0）

设计：`.pb/specs/v11.5.0-nested-case-directory-design.md`
验收方案：`.pb/iterations/iteration-63/ACCEPTANCE.md`

## 目录

```
case/
├── smoke_root.xml                          TC001        根目录文件
├── .draft/not_a_case.xml                   —            以 . 开头的目录被忽略（故意不合 case.xsd）
├── order/
│   ├── order_basic.xml                     TC001 TC002  第 1 层
│   └── refund/
│       ├── refund_apply.xml                TC001        第 2 层，与其他文件同 ID（合法）
│       └── approve/
│           └── refund_approve_flow.xml     TC001(S01)   第 3 层，含 scenario
└── user/login/
    ├── login_basic.xml                     TC001 TC002  TC002 execute=否
    └── README.md                           —            非 xml 文件被忽略
plan/
├── project_full.xml         全量
├── refund_regression.xml    case@file + id 精确选择
├── mixed_selection.xml      case_dir（可选）+ case 混合
├── stale_reference.xml      stale 引用不崩溃
└── legacy_missing_file.xml  负向：多文件模块省略 file 报错
```

配套模块：

- `../demo_nested_case_single/`：模块只有一个用例文件（位于子目录），plan 省略 `file` 兼容执行；
- `../demo_nested_case_dup_id/`：同一文件内用例 ID 重复，执行前报错（负向）。

所有页面都是 `GlobalValue.Page.*` 中的内嵌 `data:` URL，不依赖任何外部服务。

## 运行

```bash
source .venv/bin/activate
python3 rodski-demo/DEMO/demo_nested_case/run_acceptance.py        # 全部 18 项
python3 rodski-demo/DEMO/demo_nested_case/run_acceptance.py A02    # 单项

# 手工
cd rodski-demo/DEMO/demo_nested_case
rodski run case/ --headless                                        # 递归全树
rodski run case/order/refund/ --headless                           # 子目录
rodski run case/order/order_basic.xml --case-id TC002 --headless   # 文件 + 用例
rodski run @refund_regression --headless                           # plan
```

结果目录镜像 case 目录：`result/rodski_{ts}/case/order/refund/refund_apply/screenshots/...`
