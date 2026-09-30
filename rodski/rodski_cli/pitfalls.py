"""AI 编写契约速查（v11.6.0，spec §6 C6）。

``rodski capabilities`` 输出的 ``pitfalls`` 字段与 rodski-skills 中
case-writer / test-guide 的「契约速查」一节同源：两边都以本列表为准，
改动这里时同步更新 skill（单测 ``test_v116_capabilities_pitfalls`` 会校验
每条 ``id`` 都出现在 case-writer SKILL.md 中）。

每条字段：
- ``id``：稳定标识，供 Agent / skill / lint 交叉引用
- ``title``：一句话描述坑
- ``wrong``：常见错误写法
- ``right``：正确写法
- ``lint``：``rodski case lint`` 中对应的规则级别与说明（无对应规则时为 None）
"""
from typing import Dict, List, Optional

PITFALLS: List[Dict[str, Optional[str]]] = [
    {
        "id": "verify_strict_subset",
        "title": "verify 默认 strict：_verify 行必须包含模型全部字段",
        "wrong": "_verify 行只写部分字段，运行报「字段缺失」后反复试错",
        "right": '只校验部分字段时在步骤上写 match_mode="subset"；或在不校验的字段填 BLANK',
        "lint": "INFO：strict 模式下 _verify 行 BLANK 字段占比 > 50%，建议 match_mode=\"subset\"",
    },
    {
        "id": "xml_attr_escape",
        "title": "XML 属性里不能直接写 && 和 <",
        "wrong": 'evaluate data="a && b"，XML 解析失败只给行列号',
        "right": "属性中写成 &amp;&amp; / &lt;；或把脚本放到模块内 fun/js/*.js，用 data=\"file:fun/js/x.js\" 引用",
        "lint": None,
    },
    {
        "id": "sql_placeholder",
        "title": "SQL 命名参数 :name 必须以字母或下划线开头",
        "wrong": "认为 '2026-01-01 00:00:00' 里的 :00 需要传参（v11.5.2 前会报「未提供参数 :00」）",
        "right": "参数写 :user_id 这类名字；引号内的冒号与 ::int 类型转换不会被当作参数",
        "lint": None,
    },
    {
        "id": "sql_blank_fallback",
        "title": "同表混用 sql / query：BLANK/NULL/NONE/空 视为未提供",
        "wrong": "某行 sql 与 query 都填 BLANK，运行时才报错",
        "right": "每行带齐 sql / query / operation，不用的填 BLANK；先取有效 sql，没有再回落 query；两者至少一个有效",
        "lint": "ERROR：数据行 sql 为 BLANK 且没有有效 query",
    },
    {
        "id": "dialog",
        "title": "原生 alert/confirm/prompt 用 dialog 策略处理，不要写垫片",
        "wrong": "evaluate 里写 window.confirm = () => true 之类垫片",
        "right": "globalvalue DefaultValue.DialogPolicy=accept|dismiss|fail（默认 fail）；一次性处理在模型里声明 "
                 "<location type=\"page\">dialog</location> 元素，type 数据表字段填 accept / dismiss / accept:文本，"
                 "verify 该字段读取最近一次弹窗文本",
        "lint": "WARNING：evaluate 中出现 window.confirm/alert/prompt 垫片",
    },
    {
        "id": "db_assertion",
        "title": "DB 断言走 DB + verify，不用 evaluate / if 判断查询结果",
        "wrong": "查询后用 evaluate 或 <if> 判断结果；DB 的 _verify 期望值写 ${Return[-1]}",
        "right": "数据库模型用 <location type=\"field\">列名</location> 声明列，DB 步骤后接 verify 模型名 行ID"
                 "（与第一行结果比较）；_verify 期望值写字面值或 GlobalValue",
        "lint": None,
    },
    {
        "id": "waittime_ms",
        "title": "DefaultValue.WaitTime 与 <cases step_wait> 单位统一为毫秒，作用于每一步",
        "wrong": "WaitTime=1 以为是 1 秒；用例里到处写 wait 1/2 等异步表格",
        "right": "新模块 WaitTime=0，交互等待交给自动等待（DefaultValue.AutoWait，单位毫秒，须显式设置如 5000，不设置 = 不自动等待；作用于 type 每个字段 / verify / get 等所有查找测试对象的步骤）；"
                 "旧值 ≤30 暂按秒兼容并打印弃用告警",
        "lint": "WARNING：DefaultValue.WaitTime > 0；用例中出现数字字面量 wait（附估算耗时）",
    },
    {
        "id": "autowait_all_lookups",
        "title": "自动等待（AutoWait）作用于所有查找测试对象的步骤，不只 verify（v11.7.0）",
        "wrong": "元素晚出现就在 type 前插 wait 2；以为自动等待只管 verify；globalvalue 不写 AutoWait 却指望自动等待；页面慢就改 config.json 的 smart_wait_*",
        "right": "type 每个字段（输入 / click / select / hover）、verify、get、clear、upload_file 都会等元素出现，"
                 "上限 globalvalue DefaultValue.AutoWait（毫秒，须显式设置如 5000；不设置 = 不自动等待）；超时报 SKI326 元素 X 在 AutoWait=Nms 内未找到。"
                 "慢页面调大 AutoWait，不要写 wait；smart_wait_* 从未生效且已删除",
        "lint": "WARNING：用例中出现数字字面量 wait（附估算耗时）",
    },
    {
        "id": "native_assert_over_evaluate",
        "title": "元素数量/存在/可见/URL/标题断言用 verify 原生操作符，不用 evaluate",
        "wrong": "evaluate 里 querySelectorAll(...).length / location.pathname 断言，选择器失效时静默通过",
        "right": '_verify 字段填 {"$count": 10} / {"$count_gte": 1} / {"$exists": true} / {"$visible": true}；'
                 'URL/标题用 <location type="page">url|title|path</location> 元素 + 普通 verify；0 匹配按实际 0 判定',
        "lint": "WARNING：evaluate 脚本中出现 querySelectorAll(...).length / querySelector / location.pathname 等断言模式",
    },
    {
        "id": "ui_atomic_in_data",
        "title": "click/hover/select 等是 type 数据表字段值，不是关键字",
        "wrong": '<test_step action="click" .../>',
        "right": "模型声明元素，数据表该字段填 click / hover / select【选项】 等，用 type 步骤批量执行",
        "lint": None,
    },
]


def get_pitfalls() -> List[Dict[str, Optional[str]]]:
    """返回契约速查列表的副本。"""
    return [dict(p) for p in PITFALLS]
