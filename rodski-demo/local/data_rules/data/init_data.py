#!/usr/bin/env python3
"""重建 data_rules 模块的 data.sqlite（使用 RodSki 公共 SQLite schema）。

用法：python3 rodski-demo/local/data_rules/data/init_data.py

约束（TEST_CASE_WRITING_GUIDE §5.1）：逻辑表名 = 模型名；同一逻辑表所有行字段集合一致，
不用的字段显式填 BLANK / NULL / NONE。
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = MODULE_DIR / "data" / "data.sqlite"
SCHEMA_FILE = Path(__file__).resolve().parents[4] / "rodski" / "core" / "sqlite_schema.py"

PASSWORD = "Zq7SecretPw"          # F027 明文；产物中不得出现（run_acceptance.py 断言）
PASSWORD_SUM = sum(map(ord, PASSWORD))
ECHO = "http://127.0.0.1:18121"

GEN_FIELDS = {
    "r_int_range": "${random(int, 1000, 9999)}",
    "r_int_len": "${random(int, 4)}",
    "r_float": "${random(float, 10.00, 999.99)}",
    "r_str": "${random(str, 6)}",
    "r_digits": "${random(digits, 8)}",
    "r_phone": "${random(phone)}",
    "r_email": "${random(email)}",
    "r_choice": "${random(choice, A, B, C)}",
    "r_uuid": "${random(uuid)}",
    "d_now": "${date(now)}",
    "d_now_fmt": "${date(now, %Y%m%d_%H%M%S)}",
    "d_today": "${date(today)}",
    "d_today_fmt": "${date(today, %Y%m%d)}",
    "d_time": "${date(time)}",
    "d_ts": "${date(timestamp)}",
    "d_ts_ms": "${date(timestamp_ms)}",
    "d_off_p30": "${date(offset, 30)}",
    "d_off_m7": "${date(offset, -7)}",
    "d_off_m2h": "${date(offset, -2h)}",
    "d_off_m2h_fmt": "${date(offset, -2h, %H:%M)}",
    "ts": "${timestamp()}",
    "ts_ms": "${timestamp_ms()}",
    "ts36": "${timestamp36()}",
    "order_no": "ORD_${date(today, %Y%m%d)}_${random(digits, 4)}",
    "escaped": "$${random(int, 1, 9)}",
}

TABLES = [
    # ── F027 .Password ──────────────────────────────────────────
    ("PwdForm", "data", ["username", "password", "loginBtn"],
     [("P001", {"username": "alice", "password": f"{PASSWORD}.Password", "loginBtn": "click"})],
     "F027 password 字段带 .Password 后缀"),
    ("PwdResult_verify", "verify", ["result"],
     [("V001", {"result": f"user=alice;len={len(PASSWORD)};sum={PASSWORD_SUM}"})],
     "F027 输入值去掉后缀：长度与字符码和与明文一致"),
    # ── F026 BLANK / NULL / NONE ────────────────────────────────
    ("SpecForm", "data", ["f1", "f2", "f3", "f4", "f5", "dumpBtn"],
     [("S001", {"f1": "BLANK", "f2": "NULL", "f3": "NONE", "f4": "new4", "f5": "BLANK", "dumpBtn": "click"}),
      ("S002", {"f1": "BLANK", "f2": "BLANK", "f3": "BLANK", "f4": "BLANK", "f5": "", "dumpBtn": "click"})],
     "F026 UI type：S001 BLANK/NULL/NONE 跳过；S002 f5 空值跳过"),
    ("SpecDump_verify", "verify", ["dump"],
     [("V001", {"dump": "f1=keep1|f2=keep2|f3=keep3|f4=new4|f5=keep5"}),
      ("V002", {"dump": "f1=keep1|f2=keep2|f3=keep3|f4=keep4|f5=keep5"})],
     "F026 跳过的输入框保持预填值"),
    ("SpecText_verify", "verify", ["t1", "t2", "t3"],
     [("V_SKIP", {"t1": "BLANK", "t2": "NONE", "t3": "CCC"})],
     "F026 UI verify：BLANK/NONE 跳过（实际 AAA/BBB）"),
    ("EchoSpecial", "data", ["f_blank", "f_null", "f_none", "f_text"],
     [("D001", {"f_blank": "BLANK", "f_null": "NULL", "f_none": "NONE", "f_text": "hello"})],
     "F026 send：BLANK→空串 NULL→null NONE→不发送"),
    ("EchoSpecialResult_verify", "verify", ["keys", "types", "f_blank", "f_null", "f_text"],
     [("V001", {"keys": "f_blank,f_null,f_text", "types": "f_blank:str,f_null:null,f_text:str",
                "f_blank": "BLANK", "f_null": "NULL", "f_text": "hello"})],
     "F026 mock 收到的请求体字段与类型"),
    ("FixedAPI", "data", ["_url"],
     [("D001", {"_url": f"{ECHO}/fixed/specials"})],
     "F026 固定响应接口"),
    ("FixedResult_verify", "verify", ["v_empty", "v_null", "v_other", "v_text"],
     [("V_BLANK_NULL", {"v_empty": "BLANK", "v_null": "NULL", "v_other": "xyz", "v_text": "hello"}),
      ("V_NONE", {"v_empty": "BLANK", "v_null": "NULL", "v_other": "NONE", "v_text": "hello"}),
      ("V_BLANK_MISMATCH", {"v_empty": "BLANK", "v_null": "NULL", "v_other": "xyz", "v_text": "BLANK"})],
     "F026 接口 verify：BLANK=期望空串 NULL=期望 null NONE=跳过"),
    ("BizDB", "data", ["query", "sql", "operation"],
     [("Q_CREATE", {"query": "BLANK", "operation": "execute",
                    "sql": "CREATE TABLE IF NOT EXISTS t_spec (c_id INTEGER PRIMARY KEY, c_text TEXT, c_null TEXT, c_other TEXT)"}),
      ("Q_UPSERT", {"query": "BLANK", "operation": "execute",
                    "sql": "INSERT OR REPLACE INTO t_spec (c_id, c_text, c_null, c_other) VALUES (1, 'aaa', NULL, 'zzz')"}),
      ("Q_ROW", {"query": "BLANK", "operation": "query",
                 "sql": "SELECT c_id, c_text, c_null, c_other FROM t_spec WHERE c_id = 1"})],
     "F026/F056 本地 SQLite（.runtime/biz.db）"),
    ("BizDB_verify", "verify", ["c_id", "c_text", "c_null", "c_other"],
     [("V_BLANK_NULL", {"c_id": "1", "c_text": "BLANK", "c_null": "NULL", "c_other": "zzz"}),
      ("V_NONE", {"c_id": "1", "c_text": "BLANK", "c_null": "NULL", "c_other": "NONE"})],
     "F026 DB verify 控制值"),
    # ── F055 Return / 表名.DataID.字段名 ───────────────────────
    ("EchoRef", "data", ["r_m2", "r_m1", "ref", "ref_mixed"],
     [("D001", {"r_m2": "${Return[-2].tag}", "r_m1": "${Return[-1].tag}",
                "ref": "PwdForm.P001.username", "ref_mixed": "pre-SpecForm.S001.f4-post"})],
     "F055 引用写在数据表字段值中"),
    ("EchoRefResult_verify", "verify", ["r_m2", "r_m1", "ref", "ref_mixed"],
     [("V001", {"r_m2": "second", "r_m1": "third", "ref": "alice", "ref_mixed": "pre-new4-post"})],
     "F055 解析结果（字面期望值）"),
    ("EchoRef0", "data", ["r_0"],
     [("D001", {"r_0": "${Return[0].tag}"})],
     "F055 ${Return[0]}：本用例第一步的返回值"),
    ("EchoRef0Result_verify", "verify", ["r_0"],
     [("V001", {"r_0": "step-one"})],
     "F055 Return[0] 期望为本用例第一步 {\"tag\": \"step-one\"}"),
    ("RetForm", "data", ["inp", "showBtn"],
     [("R001", {"inp": "${Return[-1].tag}", "showBtn": "click"})],
     "F055 UI type 字段值引用上一步 run 的返回值"),
    ("RetOut_verify", "verify", ["out"],
     [("V001", {"out": "${Return[-2].tag}"})],
     "F055 UI verify 期望值跨源引用 ${Return[-2]}（允许）"),
    # ── F059 数据生成类函数 ─────────────────────────────────────
    ("GenAPI", "data", ["_url"] + list(GEN_FIELDS),
     [("G001", {"_url": f"{ECHO}/echo/gen1", **GEN_FIELDS}),
      ("G002", {"_url": f"{ECHO}/echo/gen2", **GEN_FIELDS})],
     "F059 生成函数写在数据表字段值中（两行用于验证每次重新求值）"),
    # ── F060 set 中纯函数 / 转义 ────────────────────────────────
    ("EchoUp", "data", ["up"],
     [("D001", {"up": "${up}"})],
     "F060 读取 set 中纯函数的结果"),
    ("EchoUpResult_verify", "verify", ["up"],
     [("V001", {"up": "ABC"})],
     "F060 toUpperCase(abc) = ABC"),
    ("EchoLit", "data", ["lit"],
     [("D001", {"lit": "${lit}"})],
     "F060 读取 set 中 $${ 转义的值"),
    ("EchoLitResult_verify", "verify", ["lit"],
     [("V001", {"lit": "$${random(int, 1, 9)}"})],
     "F060 $${ 转义应得到字面量 ${random(int, 1, 9)}"),
]

# F056 负向数据：接口 / DB _verify 表中自引用 ${Return[-1]}。
# 不进入模块自身的 data.sqlite（运行前合规检查会拦截整个模块），由 run_acceptance.py 写入临时副本。
NEGATIVE_F056 = [
    ("EchoSelfRef_verify", "verify", ["tag"],
     [("V001", {"tag": "${Return[-1].tag}"})],
     "F056 负向：接口 _verify 中自引用"),
    ("BizDBSelf_verify", "verify", ["c_id", "c_text", "c_null", "c_other"],
     [("V_SELFREF", {"c_id": "${Return[-1].c_id}", "c_text": "BLANK", "c_null": "NULL", "c_other": "zzz"})],
     "F056 负向：DB _verify 中自引用"),
]


def add_table(conn, name, kind, fields, rows, remark):
    conn.execute("INSERT INTO rs_datatable(table_name,model_name,table_kind,row_mode,remark) "
                 "VALUES(?,?,?,'standard',?)", (name, name, kind, remark))
    conn.executemany("INSERT INTO rs_datatable_field(table_name,field_name,field_order) VALUES(?,?,?)",
                     [(name, f, i) for i, f in enumerate(fields)])
    for data_id, values in rows:
        if set(values) != set(fields):
            raise ValueError(f"{name}.{data_id}: 行字段集合必须与 schema 一致")
        conn.execute("INSERT INTO rs_row(table_name,data_id,remark) VALUES(?,?,?)", (name, data_id, ""))
        conn.executemany("INSERT INTO rs_field(table_name,data_id,field_name,field_value) VALUES(?,?,?,?)",
                         [(name, data_id, f, values[f]) for f in fields])


def build(db_path: Path = DB_PATH, extra_tables=()) -> None:
    if db_path.exists():
        db_path.unlink()
    with sqlite3.connect(db_path) as conn:
        src = SCHEMA_FILE.read_text(encoding="utf-8")
        start = src.index('SQLITE_DDL = """') + len('SQLITE_DDL = """')
        conn.executescript(src[start:src.index('"""', start)])
        for name, kind, fields, rows, remark in list(TABLES) + list(extra_tables):
            add_table(conn, name, kind, fields, rows, remark)


def main() -> None:
    build()
    print(f"Created {DB_PATH}")


if __name__ == "__main__":
    main()
