#!/usr/bin/env python3
"""生成 dialog_accept / dialog_dismiss / dialog_default 三个模块的 data/data.sqlite（F072 DialogPolicy）。

data.sqlite 是唯一测试数据文件（CORE §2.1）；本脚本只是可复现的生成器，不是数据源。
- 同一逻辑表所有行字段集合一致（缺字段一律显式 BLANK，CORE §2.4.1）
- 字段顺序按模型元素顺序写入 rs_datatable_field.field_order（dialog 必须排在按钮之前）
- 三个模块使用同一份表：差别只在 globalvalue.xml 的 DefaultValue.DialogPolicy

用法: python3 rodski-demo/local/dialog_accept/fun/build_data.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Tuple

HERE = Path(__file__).resolve().parent
LOCAL = HERE.parent.parent  # 项目层 rodski-demo/local
REPO = LOCAL.parent.parent

try:
    from rodski.core.sqlite_schema import SQLITE_DDL
except ImportError:  # 源码树直接运行
    sys.path.insert(0, str(REPO / "rodski"))
    from core.sqlite_schema import SQLITE_DDL  # type: ignore

B = "BLANK"
FIELDS = ["dialog", "alertBtn", "confirmBtn", "promptBtn",
          "alertResult", "confirmResult", "confirmLog", "promptResult"]
Table = Tuple[List[str], Dict[str, Tuple[str, Dict[str, str]]]]


def row(remark: str, **values: str) -> Tuple[str, Dict[str, str]]:
    unknown = set(values) - set(FIELDS)
    assert not unknown, f"未知字段: {unknown}"
    return remark, {f: values.get(f, B) for f in FIELDS}


TABLES: Dict[str, Table] = {
    "DialogPolicyPage": (FIELDS, {
        # 不注册一次性处理器（dialog=BLANK）→ 按 DefaultValue.DialogPolicy 处理
        "D_ALERT": row("点 alert，不注册处理器", alertBtn="click"),
        "D_CONFIRM": row("点 confirm，不注册处理器", confirmBtn="click"),
        "D_PROMPT": row("点 prompt，不注册处理器", promptBtn="click"),
        # 一次性处理器（page=dialog 字段取值，CORE §2.5.6 第 4 条）
        "D_ONCE_DISMISS_CONFIRM": row("一次性 dismiss 后点 confirm", dialog="dismiss", confirmBtn="click"),
        "D_ONCE_ACCEPT_CONFIRM": row("一次性 accept 后点 confirm", dialog="accept", confirmBtn="click"),
        "D_ONCE_TEXT_PROMPT": row("一次性 accept:加急 后点 prompt", dialog="accept:加急", promptBtn="click"),
        "D_REGISTER_ONLY": row("只注册一次性 accept，不触发弹窗", dialog="accept"),
    }),
    "DialogPolicyPage_verify": (FIELDS, {
        "V_ALERT": row("alert 已关闭，弹窗文本可读", dialog="保存成功", alertResult="alert-closed"),
        "V_CONFIRM_TRUE": row("confirm 被确认", dialog="确认删除订单 ORD9?", confirmResult="confirm=true"),
        "V_CONFIRM_FALSE": row("confirm 被取消", dialog="确认删除订单 ORD9?", confirmResult="confirm=false"),
        "V_PROMPT_DEFAULT": row("prompt 按默认值确认", dialog="请输入备注", promptResult="prompt=默认备注"),
        "V_PROMPT_NULL": row("prompt 被取消", dialog="请输入备注", promptResult="prompt=null"),
        "V_PROMPT_TEXT": row("prompt 输入加急后确认", dialog="请输入备注", promptResult="prompt=加急"),
        "V_LOG_FALSE_TRUE": row("一次性 dismiss 只生效一次，第二次回到全局 accept", confirmLog="false,true"),
        "V_LOG_TRUE_FALSE": row("一次性 accept 只生效一次，第二次回到全局 dismiss", confirmLog="true,false"),
    }),
}

MODULES = ("dialog_accept", "dialog_dismiss", "dialog_default")


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


def build_all(quiet: bool = False) -> None:
    for m in MODULES:
        write_module(LOCAL / m, TABLES)
        if not quiet:
            print(f"[OK] rodski-demo/local/{m}/data/data.sqlite: {len(TABLES)} 张表")


if __name__ == "__main__":
    build_all()
