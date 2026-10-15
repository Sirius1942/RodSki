# demosite/ui_actions — UI 原子动作、控制值、定位器与 verify 操作符验收

按 `rodski/docs/TEST_CASE_WRITING_GUIDE.md` / `CORE_DESIGN_CONSTRAINTS.md` 描述的行为编写的验收用例。
框架与文档不符时保留用例、不改框架，由 `run_acceptance.py` 判为 **KNOWN** 并给出文档条款与怀疑的代码位置。

## 入口

```bash
# 仓库根目录；退出码 0 = 无 FAIL；最后一行「汇总: PASS=x FAIL=y KNOWN=z」
/usr/local/bin/python3 rodski-demo/demosite/ui_actions/run_acceptance.py
/usr/local/bin/python3 rodski-demo/demosite/ui_actions/run_acceptance.py F040 F041   # 按功能编号
/usr/local/bin/python3 rodski-demo/demosite/ui_actions/run_acceptance.py KP_TARGET   # 按用例 ID
```

脚本自动完成：重建 `data/data.sqlite`（`data/init_data.py`）、重建 assert 参考图（`fun/make_assert_refs.py`）、
在 `127.0.0.1:18140` 启动 `fun/site/` 静态页面、`:8000` 未运行时启动共享站点（只停自己启动的进程）、
逐个 `rodski run <文件> --case-id <ID> --headless`（包入口 `rodski.rodski_cli`）并读取本次 `result/<run>/`。
负向用例（`expect_fail="是"`）除了要求判 PASS，还要求失败原因包含指定关键字，防止因无关错误「假通过」。

单独跑某个用例文件（需先手动起 18140 静态服务：`cd fun/site && python3 -m http.server 18140 --bind 127.0.0.1`）：

```bash
/usr/local/bin/python3 -c "import sys; from rodski.rodski_cli import main; sys.argv=['rodski']+sys.argv[1:]; sys.exit(main())" \
  run rodski-demo/demosite/ui_actions/case/element_ops.xml --headless
```

## 覆盖

| 功能 | 用例文件 | 文档 | 内容 |
|------|----------|------|------|
| F023 key_press | `case/key_press.xml` | GUIDE §5.4 | Enter / Tab / Control+A 组合键 / 目标元素非焦点 |
| F024 drag | `case/drag.xml` | GUIDE §5.4 | demosite 首页 `drag【#dropZone】`；双放置区按目标定位器落点 |
| F025 scroll | `case/scroll.xml` | GUIDE §5.4 | 默认 300px、`scroll【0,500】`、水平、负值、远处元素进入视口 |
| F026 BLANK/NULL/NONE | `case/control_values.xml` | GUIDE §5.4 / §5.7.3，CORE §4.1 | type 跳过（原值保留、未聚焦、不存在元素不查找）；verify BLANK/NONE 跳过、NULL 期望 null |
| F031 class/tag/text | `case/locators.xml` | GUIDE §4.3.1，CORE §2.5.1 | type 与 verify 各 4 项，含 class 多类名（带干扰元素） |
| F040 元素级操作符 | `case/element_ops.xml` | GUIDE §5.7.1，CORE §4.6.1 | `$count` / `$count_gte` / `$count_lte` / `$exists` / `$visible`（含 false、不存在元素）及 8 个负向 |
| F041 数值/包含操作符 | `case/compare_ops.xml` | GUIDE §5.7.1 | UI 侧 `$gt/$gte/$lt/$lte/$contains`，含等值边界负向 |
| F017 launch | `case/launch.xml`、`case/launch_multi.xml` | CORE §1.3，SKILL_REFERENCE §2.1；SPEC-012 §1.2 | 非法应用 / ftp:// / 空目标应报错；`launch id=` + `target=` 多浏览器对象 |
| F011 assert 图片 | `case/assert_image.xml` | GUIDE 附录 A、§7.5 | 正向（相似度 1.0）/ 负向（约 0.83 < 0.95） |
| F055 Return 跨源比对 | `case/return_ref.xml` | GUIDE §7.3 / §7.4，CORE §4.3 | 页面随机订单号，UI `_verify` 引用 `${Return[-2]}` / `${Return[-1]}`，负向引用另一单号 |
| F059 生成值 | `case/generated_values.xml` | GUIDE §7.7，CORE §4.4 | random/date/timestamp36 写入页面后格式断言；两次求值不同；不合规值负向 |

## 目录

```
ui_actions/
├── case/                 # 11 个用例文件
├── model/model.xml
├── data/
│   ├── globalvalue.xml   # AutoWait=2000、Site.URL=:18140、Demo.URL=:8000
│   ├── init_data.py      # 生成 data.sqlite（可重复执行，行字段集合一致，未用字段显式 BLANK）
│   └── data.sqlite
├── fun/
│   ├── site/             # 本模块专用静态页面（keys / drag / scroll / control / locators / ops / return / gen / assert / buyer / seller）
│   └── make_assert_refs.py
├── images/assert/        # assert 参考图（pattern_ref.png / pattern_other.png）；failures/ 为运行产物，脚本结束时清理
└── run_acceptance.py
```

## 环境前置

- `opencv-python`、`numpy`（F011 assert 图片比对与参考图生成）。
- Playwright Chromium。F023 `KP_COMBO` 的结论与平台有关：macOS 上 `Control+A` 不全选（文档声明应等同 Command）。

KNOWN 清单以 `run_acceptance.py` 中的 `KNOWN` 表为准，每项含现象、文档条款、怀疑的框架代码位置与建议。
