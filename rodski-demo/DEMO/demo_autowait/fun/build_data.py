#!/usr/bin/env python3
"""生成 demo_autowait / demo_autowait_zero / demo_autowait_long 三个模块的 data/data.sqlite。

data.sqlite 是唯一测试数据文件（CORE §2.1）；本脚本只是可复现的生成器，不是数据源。
- 同一逻辑表所有行字段集合一致（缺字段一律显式 BLANK，CORE §2.4.1）
- 字段顺序按模型元素顺序写入 rs_datatable_field.field_order
- 写完后请用 `rodski data validate <module>` 校验；日常增删改行请用
  `rodski data add-row / set / delete-row`

用法: python3 rodski-demo/DEMO/demo_autowait/fun/build_data.py
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple

HERE = Path(__file__).resolve().parent
DEMO = HERE.parent.parent  # rodski-demo/DEMO

try:
    from rodski.core.sqlite_schema import SQLITE_DDL
except ImportError:  # 源码树直接运行
    import sys
    sys.path.insert(0, str(DEMO.parent.parent / "rodski"))
    from core.sqlite_schema import SQLITE_DDL  # type: ignore

B = "BLANK"
# 表名 -> (字段顺序, {DataID: (备注, {字段: 值})})
Table = Tuple[List[str], Dict[str, Tuple[str, Dict[str, str]]]]


def t(fields: List[str], rows: Dict[str, Tuple[str, Dict[str, str]]]) -> Table:
    for data_id, (_, values) in rows.items():
        assert set(values) == set(fields), f"{data_id} 字段集合与表不一致: {sorted(values)} vs {sorted(fields)}"
    return fields, rows


LATE_INPUT = {
    "LateInput": t(["nameInput", "echoText"], {
        "I001": ("输入延迟出现的输入框", {"nameInput": "自动等待-张三", "echoText": B}),
    }),
    "LateInput_verify": t(["nameInput", "echoText"], {
        "V001": ("回显等于输入值", {"nameInput": B, "echoText": "自动等待-张三"}),
    }),
}
LATE_BUTTON = {
    "LateButton": t(["submitBtn", "clickCount"], {
        "C001": ("点击延迟出现的按钮", {"submitBtn": "click", "clickCount": B}),
    }),
    "LateButton_verify": t(["submitBtn", "clickCount"], {
        "V001": ("恰好点击一次", {"submitBtn": B, "clickCount": "1"}),
    }),
}
READY_FIELDS = [f"field{i}" for i in range(1, 9)] + ["city", "submit", "summary", "submitCount"]
READY = {
    "ReadyForm": t(READY_FIELDS, {
        "R001": ("10 个就绪字段一次 type", {
            **{f"field{i}": f"v{i}" for i in range(1, 9)},
            "city": "select【北京】", "submit": "click", "summary": B, "submitCount": B,
        }),
    }),
    "ReadyForm_verify": t(READY_FIELDS, {
        "V001": ("汇总全部输入", {
            **{f"field{i}": B for i in range(1, 9)}, "city": B, "submit": B,
            "summary": "v1|v2|v3|v4|v5|v6|v7|v8|北京", "submitCount": "1",
        }),
    }),
}

AUTOWAIT: Dict[str, Table] = {
    **LATE_INPUT,
    **LATE_BUTTON,
    "DisabledButton": t(["enableLaterBtn", "disResult", "disCount"], {
        "C001": ("点击先 disabled 后 enabled 的按钮", {"enableLaterBtn": "click", "disResult": B, "disCount": B}),
    }),
    "DisabledButton_verify": t(["enableLaterBtn", "disResult", "disCount"], {
        "V001": ("已提交且只提交一次", {"enableLaterBtn": B, "disResult": "已提交", "disCount": "1"}),
    }),
    "Overlay": t(["coveredBtn", "ovCount", "blockedCount"], {
        "C001": ("点击被遮罩覆盖的按钮", {"coveredBtn": "click", "ovCount": B, "blockedCount": B}),
    }),
    "Overlay_verify": t(["coveredBtn", "ovCount", "blockedCount"], {
        "V001": ("按钮被真实点击一次，遮罩未拦截", {"coveredBtn": B, "ovCount": "1", "blockedCount": "0"}),
    }),
    "HiddenButton": t(["showLaterBtn", "hidCount"], {
        "C001": ("点击先隐藏后显示的按钮", {"showLaterBtn": "click", "hidCount": B}),
    }),
    "HiddenButton_verify": t(["showLaterBtn", "hidCount"], {
        "V001": ("点击一次", {"showLaterBtn": B, "hidCount": "1"}),
    }),
    "AsyncSelect": t(["regionSelect", "selectedText"], {
        "S001": ("选择异步填充的选项", {"regionSelect": "select【华东】", "selectedText": B}),
    }),
    "AsyncSelect_verify": t(["regionSelect", "selectedText"], {
        "V001": ("已选择华东", {"regionSelect": B, "selectedText": "华东"}),
    }),
    "LateHover": t(["menuTrigger", "menuState"], {
        "H001": ("悬停延迟出现的目标", {"menuTrigger": "hover", "menuState": B}),
    }),
    "LateHover_verify": t(["menuTrigger", "menuState"], {
        "V001": ("菜单已展开", {"menuTrigger": B, "menuState": "已展开"}),
    }),
    "LateDblclick": t(["dblBox", "dblCount"], {
        "D001": ("双击延迟出现的目标", {"dblBox": "double_click", "dblCount": B}),
    }),
    "LateDblclick_verify": t(["dblBox", "dblCount"], {
        "V001": ("双击一次", {"dblBox": B, "dblCount": "1"}),
    }),
    "LateContextMenu": t(["ctxBox", "ctxCount"], {
        "R001": ("右键延迟出现的目标", {"ctxBox": "right_click", "ctxCount": B}),
    }),
    "LateContextMenu_verify": t(["ctxBox", "ctxCount"], {
        "V001": ("右键一次", {"ctxBox": B, "ctxCount": "1"}),
    }),
    "LateIframe": t(["frameField", "frameEchoText"], {
        "F001": ("在延迟插入的 iframe 内输入", {"frameField": "iframe内输入-李四", "frameEchoText": B}),
    }),
    "LateIframe_verify": t(["frameField", "frameEchoText"], {
        "V001": ("iframe 内回显", {"frameField": B, "frameEchoText": "iframe内输入-李四"}),
    }),
    "ChainForm": t(["stepA", "stepB", "stepC", "chainResult", "bCount", "cCount"], {
        "A001": ("一行 type 批量 A/B/C", {"stepA": "链式-A", "stepB": "click", "stepC": "click",
                                        "chainResult": B, "bCount": B, "cCount": B}),
    }),
    "ChainForm_verify": t(["stepA", "stepB", "stepC", "chainResult", "bCount", "cCount"], {
        "V001": ("链路完成，B/C 各点一次", {"stepA": B, "stepB": B, "stepC": B,
                                          "chainResult": "链路完成", "bCount": "1", "cCount": "1"}),
    }),
    "MultiLocator": t(["fallbackBtn", "mlCount"], {
        "M001": ("第 2 个定位器命中后点击", {"fallbackBtn": "click", "mlCount": B}),
    }),
    "MultiLocator_verify": t(["fallbackBtn", "mlCount"], {
        "V001": ("点击一次", {"fallbackBtn": B, "mlCount": "1"}),
    }),
    "MultiMiss": t(["ghostBtn"], {
        "M001": ("全部定位器永不命中", {"ghostBtn": "click"}),
    }),
    "LateGet": t(["lateValue"], {
        "G001": ("get 模型模式（读取全部元素，本行值不参与）", {"lateValue": B}),
    }),
    "LateGetRef_verify": t(["refValue"], {
        "V001": ("参考值等于 get 读到的延迟文本", {"refValue": "${Return[-1].lateValue}"}),
    }),
    "LateClear_verify": t(["clearEcho"], {
        "V001": ("输入框已被清空", {"clearEcho": "值:[]"}),
    }),
    "LateUpload_verify": t(["fileNameText"], {
        "V001": ("已选择样例文件", {"fileNameText": "upload_sample.txt"}),
    }),
    **READY,
}

ZERO: Dict[str, Table] = {**LATE_INPUT, **LATE_BUTTON, **READY}
LONG: Dict[str, Table] = {**LATE_INPUT, **LATE_BUTTON}


def write_module(module: Path, tables: Dict[str, Table]) -> None:
    db = module / "data" / "data.sqlite"
    db.parent.mkdir(parents=True, exist_ok=True)
    if db.exists():
        db.unlink()
    conn = sqlite3.connect(str(db))
    conn.executescript(SQLITE_DDL)
    for name, (fields, rows) in tables.items():
        kind = "verify" if name.endswith("_verify") else "data"
        model = name[: -len("_verify")] if kind == "verify" else name
        conn.execute("INSERT INTO rs_datatable (table_name, model_name, table_kind, row_mode, remark) "
                     "VALUES (?,?,?,?,?)", (name, model, kind, "standard", ""))
        for i, f in enumerate(fields):
            conn.execute("INSERT INTO rs_datatable_field VALUES (?,?,?)", (name, f, i))
        for data_id, (remark, values) in rows.items():
            conn.execute("INSERT INTO rs_row VALUES (?,?,?)", (name, data_id, remark))
            for f in fields:
                conn.execute("INSERT INTO rs_field VALUES (?,?,?,?)", (name, data_id, f, values[f]))
    conn.commit()
    conn.close()
    print(f"[OK] {db.relative_to(DEMO.parent.parent)}: {len(tables)} 张表")


if __name__ == "__main__":
    write_module(DEMO / "demo_autowait", AUTOWAIT)
    write_module(DEMO / "demo_autowait_zero", ZERO)
    write_module(DEMO / "demo_autowait_long", LONG)
