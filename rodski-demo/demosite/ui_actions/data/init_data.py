#!/usr/bin/env python3
"""重建 ui_actions 模块的 data/data.sqlite（可重复执行）。

用法：python3 rodski-demo/demosite/ui_actions/data/init_data.py

约束（TEST_CASE_WRITING_GUIDE §5.1 / CORE §2.4.1）：同一逻辑表所有行字段集合一致；
行内不关心的字段由 row() 显式写成 BLANK（存储到 SQLite 的就是字面值 BLANK）。
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple

MODULE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = MODULE_DIR / "data" / "data.sqlite"
SCHEMA_FILE = Path(__file__).resolve().parents[4] / "rodski" / "core" / "sqlite_schema.py"

Rows = List[Tuple[str, Dict[str, str], str]]


def row(data_id: str, fields: List[str], remark: str = "", **values: str) -> Tuple[str, Dict[str, str], str]:
    unknown = set(values) - set(fields)
    if unknown:
        raise ValueError(f"{data_id}: 未知字段 {sorted(unknown)}")
    return data_id, {f: values.get(f, "BLANK") for f in fields}, remark


def add_table(conn: sqlite3.Connection, name: str, kind: str, fields: List[str], rows: Rows, remark: str) -> None:
    conn.execute(
        "INSERT INTO rs_datatable(table_name,model_name,table_kind,row_mode,remark) VALUES(?,?,?,'standard',?)",
        (name, name, kind, remark),
    )
    conn.executemany(
        "INSERT INTO rs_datatable_field(table_name,field_name,field_order) VALUES(?,?,?)",
        [(name, f, i) for i, f in enumerate(fields)],
    )
    for data_id, values, row_remark in rows:
        if set(values) != set(fields):
            raise ValueError(f"{name}.{data_id}: 行字段集合必须与 schema 一致")
        conn.execute("INSERT INTO rs_row(table_name,data_id,remark) VALUES(?,?,?)", (name, data_id, row_remark))
        conn.executemany(
            "INSERT INTO rs_field(table_name,data_id,field_name,field_value) VALUES(?,?,?,?)",
            [(name, data_id, f, values[f]) for f in fields],
        )


def tables():
    """返回 [(表名, kind, 字段, 行, 说明)]。"""
    t = []

    # ---------------- F023 key_press ----------------
    f = ["kpInput", "kpEnter", "kpSelAll", "kpDel", "kpTab", "kpOther"]
    t.append(("KeyPress", "data", f, [
        row("K_ENTER", f, "输入后在同一输入框按 Enter", kpInput="hello", kpEnter="key_press【Enter】"),
        row("K_TAB", f, "GUIDE §5.4 示例：key_press【Tab】切换焦点", kpInput="abc", kpTab="key_press【Tab】"),
        row("K_COMBO", f, "组合键 Control+A 全选后 Backspace 删除（GUIDE §5.4：macOS 上 Control 对应 Command 行为）",
            kpInput="abc", kpSelAll="key_press【Control+A】", kpDel="key_press【Backspace】"),
        row("K_TARGET", f, "焦点在 kpInput 时对 kpOther 字段 key_press：应作用于目标元素",
            kpInput="xyz", kpOther="key_press【Enter】"),
    ], "F023 key_press"))
    f = ["kpEcho", "kpResult", "kpOtherResult", "focusState"]
    t.append(("KeyPressView_verify", "verify", f, [
        row("V_ENTER", f, kpEcho="V:hello", kpResult="ENTER:hello", kpOtherResult="none"),
        row("V_TAB", f, kpEcho="V:abc", kpResult="none", focusState="FOCUS:kpOther"),
        row("V_COMBO", f, kpEcho="V:", kpResult="none"),
        row("V_TARGET", f, kpEcho="V:xyz", kpResult="none", kpOtherResult="OTHER:Enter"),
    ], "F023 断言"))

    # ---------------- F024 drag ----------------
    f = ["username", "password", "loginBtn"]
    t.append(("LoginForm", "data", f, [row("L001", f, "demosite 管理员", username="admin", password="123456", loginBtn="click")],
              "demosite 登录"))
    t.append(("NavMenu", "data", ["testLink"], [row("N001", ["testLink"], testLink="click")], "进入功能测试区"))
    t.append(("DemoDrag", "data", ["dragSource"], [row("D001", ["dragSource"], dragSource="drag【#dropZone】")],
              "F024 demosite 首页拖拽"))
    f = ["dropZone", "actionResult"]
    t.append(("DemoDragView_verify", "verify", f, [row("V001", f, dropZone="拖拽成功", actionResult="拖拽成功")],
              "F024 demosite 拖拽结果"))
    t.append(("DragPage", "data", ["card"], [
        row("D_B", ["card"], "拖到 B 区", card="drag【#dropB】"),
        row("D_A", ["card"], "拖到 A 区", card="drag【#dropA】"),
    ], "F024 目标定位器决定放置区"))
    f = ["dropA", "dropB", "dropLog"]
    t.append(("DragPageView_verify", "verify", f, [
        row("V_B", f, dropA="A:empty", dropB="B:card", dropLog="DROP:dropB"),
        row("V_A", f, dropA="A:card", dropB="B:empty", dropLog="DROP:dropA"),
    ], "F024 断言"))

    # ---------------- F025 scroll ----------------
    t.append(("ScrollPage", "data", ["anchor"], [
        row("S_DEF", ["anchor"], "默认滚动：向下 300px", anchor="scroll"),
        row("S_DOWN500", ["anchor"], anchor="scroll【0,500】"),
        row("S_RIGHT200", ["anchor"], anchor="scroll【200,0】"),
        row("S_UP300", ["anchor"], anchor="scroll【0,-300】"),
    ], "F025 scroll / scroll【x,y】"))
    f = ["pos", "farState"]
    t.append(("ScrollView_verify", "verify", f, [
        row("V_INIT", f, pos="0,0", farState="out-of-view"),
        row("V_300", f, pos="0,300"),
        row("V_500", f, pos="0,500"),
        row("V_800", f, pos="0,800", farState="in-view"),
        row("V_X", f, pos="200,800"),
        row("V_UP", f, pos="200,500"),
    ], "F025 断言：scrollX,scrollY 与远处元素是否进入视口"))

    # ---------------- F026 BLANK / NULL / NONE ----------------
    f = ["fb", "fn", "fo", "fp", "ghost"]
    t.append(("ControlInput", "data", f, [
        row("C_SKIP", f, "BLANK/NULL/NONE 都应跳过，原值保留且不聚焦",
            fb="BLANK", fn="NULL", fo="NONE", fp="typed-ok", ghost="BLANK"),
        row("C_GHOST_NULL", f, "不存在的元素填 NULL：跳过，不查找", fp="g-null", ghost="NULL"),
        row("C_GHOST_NONE", f, "不存在的元素填 NONE：跳过，不查找", fp="g-none", ghost="NONE"),
    ], "F026 type 控制值"))
    f = ["eb", "en", "eo", "ep", "cb", "cn", "co", "noise", "missingEl"]
    t.append(("ControlView_verify", "verify", f, [
        row("V_SKIP", f, "noise/missingEl 填 BLANK：UI verify 跳过",
            eb="B:orig-b", en="N:orig-n", eo="O:orig-o", ep="P:typed-ok", cb="0", cn="0", co="0"),
        row("V_GNULL", f, ep="P:g-null", eb="B:orig-b"),
        row("V_GNONE", f, ep="P:g-none", eb="B:orig-b"),
        row("V_NONE", f, "CORE §4.1：NONE 跳过验证", ep="P:", noise="NONE", missingEl="NONE"),
        row("V_NULL", f, "CORE §4.1：NULL 期望 null；页面文本为 random-noise，应失败（ep 为一致的字面值，失败只能来自 noise）",
            ep="P:", noise="NULL"),
    ], "F026 verify 控制值"))

    # ---------------- F031 class / tag / text ----------------
    t.append(("LocClassInput", "data", ["clsInput"], [row("L001", ["clsInput"], clsInput="abc-class")], "F031 class 单类名 type"))
    t.append(("LocMultiClass", "data", ["multiBtn"], [row("L001", ["multiBtn"], multiBtn="click")], "F031 class 多类名 type"))
    t.append(("LocTagInput", "data", ["tagArea"], [row("L001", ["tagArea"], tagArea="tag-text")], "F031 tag type"))
    t.append(("LocTextBtn", "data", ["textBtn"], [row("L001", ["textBtn"], textBtn="click")], "F031 text type"))
    t.append(("LocTextBtnById", "data", ["textBtnById"], [row("L001", ["textBtnById"], textBtnById="click")],
              "F031 id 点击文本按钮（隔离 text verify）"))
    f = ["clsEcho", "multiResult", "tagEcho", "textResult"]
    t.append(("LocResultView_verify", "verify", f, [
        row("V_CLS", f, clsEcho="CLS:abc-class"),
        row("V_MULTI", f, multiResult="MULTI:clicked"),
        row("V_TAG", f, tagEcho="TAG:tag-text"),
        row("V_TEXT", f, textResult="文本按钮已点击"),
    ], "F031 type 结果"))
    t.append(("LocVerifyClass_verify", "verify", ["noteCls"], [row("V001", ["noteCls"], noteCls="单类名文本")], "F031 class verify"))
    t.append(("LocVerifyMulti_verify", "verify", ["badgeMulti"], [row("V001", ["badgeMulti"], badgeMulti="MULTI-CLASS-TEXT")],
              "F031 多类名 verify"))
    t.append(("LocVerifyTag_verify", "verify", ["h2Tag"], [row("V001", ["h2Tag"], h2Tag="标签定位标题")], "F031 tag verify"))
    t.append(("LocVerifyText_verify", "verify", ["textLoc"], [row("V001", ["textLoc"], textLoc="文本按钮已点击")], "F031 text verify"))

    # ---------------- F040 元素级操作符 ----------------
    f = ["items", "items2", "present", "absent", "shown", "hiddenEl"]
    t.append(("ElemOps_verify", "verify", f, [
        row("V_OK", f, items='{"$count": 5}', items2='{"$count_gte": 3}', present='{"$exists": true}',
            absent='{"$exists": false}', shown='{"$visible": true}', hiddenEl='{"$visible": false}'),
        row("V_BOUND", f, "边界：count_lte=5 / count_gte=5；不存在的元素 $visible:false；隐藏元素 $exists:true",
            items='{"$count_lte": 5}', items2='{"$count_gte": 5}', absent='{"$visible": false}',
            hiddenEl='{"$exists": true}'),
        row("N_COUNT", f, items='{"$count": 6}'),
        row("N_GTE", f, items='{"$count_gte": 6}'),
        row("N_LTE", f, items='{"$count_lte": 4}'),
        row("N_EXISTS", f, absent='{"$exists": true}'),
        row("N_NOTEXISTS", f, present='{"$exists": false}'),
        row("N_VISFALSE", f, shown='{"$visible": false}'),
        row("N_VISTRUE", f, hiddenEl='{"$visible": true}'),
        row("N_VISABSENT", f, absent='{"$visible": true}'),
    ], "F040 $count/$count_gte/$count_lte/$exists/$visible"))

    # ---------------- F041 数值 / 包含操作符 ----------------
    f = ["pGt", "pGte", "pLt", "pLte", "qty", "msg"]
    t.append(("CmpOps_verify", "verify", f, [
        row("V_OK", f, pGt='{"$gt": 100}', pGte='{"$gte": 128.5}', pLt='{"$lt": 200}', pLte='{"$lte": 128.5}',
            qty='{"$lt": 8}', msg='{"$contains": "ORD-2026"}'),
        row("N_GT", f, "128.50 不大于 128.5", pGt='{"$gt": 128.5}'),
        row("N_GTE", f, pGte='{"$gte": 128.51}'),
        row("N_LT", f, "128.50 不小于 128.5", pLt='{"$lt": 128.5}'),
        row("N_LTE", f, pLte='{"$lte": 128.49}'),
        row("N_CONTAINS", f, msg='{"$contains": "ORD-2027"}'),
    ], "F041 $gt/$gte/$lt/$lte/$contains"))

    # ---------------- F017 多浏览器对象 ----------------
    f = ["msg", "sendBtn"]
    t.append(("BuyerForm", "data", f, [row("B001", f, msg="hello-seller", sendBtn="click")], "F017 买家浏览器"))
    t.append(("BuyerView_verify", "verify", ["status"], [row("B001", ["status"], status="SENT:hello-seller")], "F017"))
    f = ["title", "inbox"]
    t.append(("SellerView_verify", "verify", f, [row("S001", f, title="Seller Console", inbox="empty")], "F017"))

    # ---------------- F055 UI _verify 引用 ${Return[-N]} ----------------
    t.append(("OrderCopy", "data", ["copyBtn"], [row("C001", ["copyBtn"], copyBtn="click")], "F055 复制订单号"))
    f = ["copied", "orderNoMirror"]
    t.append(("OrderCopyView_verify", "verify", f, [
        row("V_RET2", f, "get → type → verify：Return[-2] 是 get 的返回", copied="${Return[-2].orderNo}"),
        row("V_RET1", f, "get → verify：Return[-1] 是 get 的返回", orderNoMirror="${Return[-1].orderNo}"),
        row("N_RET2", f, "引用另一个随机单号，必须不一致", copied="${Return[-2].otherNo}"),
    ], "F055 UI verify 跨源比对"))

    # ---------------- F059 random() / date() ----------------
    gen = ["gUser", "gInt", "gDigits", "gStr", "gPhone", "gEmail", "gUuid", "gChoice", "gToday", "gNow", "gOffset", "gTs36"]
    t.append(("GenForm", "data", gen, [
        row("G001", gen, "GUIDE §7.7 数据生成函数",
            gUser="user_${random(int, 4)}", gInt="${random(int, 1000, 9999)}", gDigits="${random(digits, 8)}",
            gStr="${random(str, 6)}", gPhone="${random(phone)}", gEmail="${random(email)}",
            gUuid="${random(uuid)}", gChoice="${random(choice, A, B, C)}", gToday="${date(today)}",
            gNow="${date(now, %Y%m%d_%H%M%S)}", gOffset="${date(offset, -2h, %H:%M)}", gTs36="${timestamp36()}"),
        row("G_UUID", gen, "再取一次 uuid：每次执行重新计算", gUuid="${random(uuid)}"),
        row("G_BAD", gen, "格式不合规的字面值（负向：证明格式断言有效）", gUser="user_abcd"),
    ], "F059 生成值写入页面"))
    gv = [f"ok_{g}" for g in gen] + ["intGte", "intLte", "userEcho", "uuidChanged"]
    t.append(("GenView_verify", "verify", gv, [
        row("V001", gv, **{f"ok_{g}": "OK" for g in gen}, intGte='{"$gte": 1000}', intLte='{"$lte": 9999}',
            userEcho='{"$contains": "user_"}'),
        row("V_UUID", gv, ok_gUuid="OK", uuidChanged="CHANGED"),
        row("V_BAD", gv, ok_gUser="OK"),
    ], "F059 格式断言"))
    return t


def main() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
    schema_module = SCHEMA_FILE.read_text(encoding="utf-8")
    start = schema_module.index('SQLITE_DDL = """') + len('SQLITE_DDL = """')
    ddl = schema_module[start:schema_module.index('"""', start)]
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(ddl)
        for name, kind, fields, rows, remark in tables():
            add_table(conn, name, kind, fields, rows, remark)
    print(f"已生成 {DB_PATH}")


if __name__ == "__main__":
    main()
