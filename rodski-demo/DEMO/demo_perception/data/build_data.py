#!/usr/bin/env python3
"""为 demo_perception 生成 data.sqlite。
逻辑表（每个模型对应一对 input + verify）：
- PerceptionLogin / PerceptionLogin_verify       (vision 单目标)
- PerceptionForm  / PerceptionForm_verify        (vision 批量)
- TemplateLogin   / TemplateLogin_verify         (vision_image 模板匹配)
- HybridLogin     / HybridLogin_verify           (vision_image + vision 混合)
- MissingTemplate / MissingTemplate_verify       (vision_image 参考图缺失，错误处理)
"""
import sqlite3
from pathlib import Path

DB = Path(__file__).parent / "data.sqlite"
if DB.exists():
    DB.unlink()

con = sqlite3.connect(DB)
cur = con.cursor()

cur.executescript("""
CREATE TABLE rs_datatable (
    table_name TEXT PRIMARY KEY,
    model_name TEXT NOT NULL,
    table_kind TEXT NOT NULL,
    row_mode TEXT NOT NULL,
    remark TEXT DEFAULT '',
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE rs_datatable_field (
    table_name TEXT NOT NULL,
    field_name TEXT NOT NULL,
    field_order INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (table_name, field_name)
);
CREATE TABLE rs_row (
    table_name TEXT NOT NULL,
    data_id TEXT NOT NULL,
    remark TEXT DEFAULT '',
    PRIMARY KEY (table_name, data_id)
);
CREATE TABLE rs_field (
    table_name TEXT NOT NULL,
    data_id TEXT NOT NULL,
    field_name TEXT NOT NULL,
    field_value TEXT NOT NULL,
    PRIMARY KEY (table_name, data_id, field_name)
);
""")


def add_table(table, model, kind, fields, rows):
    cur.execute(
        "INSERT INTO rs_datatable(table_name, model_name, table_kind, row_mode, remark) VALUES (?,?,?,?,?)",
        (table, model, kind, "standard", ""),
    )
    for i, f in enumerate(fields):
        cur.execute(
            "INSERT INTO rs_datatable_field(table_name, field_name, field_order) VALUES (?,?,?)",
            (table, f, i),
        )
    for data_id, values in rows:
        cur.execute("INSERT INTO rs_row(table_name, data_id) VALUES (?,?)", (table, data_id))
        for f in fields:
            v = values.get(f, "BLANK")
            cur.execute(
                "INSERT INTO rs_field(table_name, data_id, field_name, field_value) VALUES (?,?,?,?)",
                (table, data_id, f, str(v)),
            )


# === 共用：4 字段登录表 ===
LOGIN_FIELDS = ["username", "password", "loginBtn", "welcomeMsg"]
LOGIN_INPUT = ("L001", {"username": "admin", "password": "123456",
                        "loginBtn": "click", "welcomeMsg": "BLANK"})
LOGIN_VERIFY = ("V001", {"username": "BLANK", "password": "BLANK",
                         "loginBtn": "BLANK", "welcomeMsg": "欢迎"})

# === PerceptionLogin (vision VLM) ===
add_table("PerceptionLogin", "PerceptionLogin", "data", LOGIN_FIELDS, [LOGIN_INPUT])
add_table("PerceptionLogin_verify", "PerceptionLogin", "verify", LOGIN_FIELDS, [LOGIN_VERIFY])

# === PerceptionForm (vision VLM 批量) ===
FORM_FIELDS = ["usernameField", "roleSelect", "submitBtn", "formResult"]
add_table("PerceptionForm", "PerceptionForm", "data", FORM_FIELDS, [
    ("F001", {"usernameField": "perception_user", "roleSelect": "admin",
              "submitBtn": "click", "formResult": "BLANK"}),
])
add_table("PerceptionForm_verify", "PerceptionForm", "verify", FORM_FIELDS, [
    ("V001", {"usernameField": "BLANK", "roleSelect": "BLANK",
              "submitBtn": "BLANK", "formResult": "提交成功"}),
])

# === TemplateLogin (vision_image 模板匹配) ===
add_table("TemplateLogin", "TemplateLogin", "data", LOGIN_FIELDS, [LOGIN_INPUT])
add_table("TemplateLogin_verify", "TemplateLogin", "verify", LOGIN_FIELDS, [LOGIN_VERIFY])

# === HybridLogin (vision_image 主, vision 兜底) ===
add_table("HybridLogin", "HybridLogin", "data", LOGIN_FIELDS, [LOGIN_INPUT])
add_table("HybridLogin_verify", "HybridLogin", "verify", LOGIN_FIELDS, [LOGIN_VERIFY])

# === FusionLogin (vision_image + ocr + vision 融合裁决) ===
add_table("FusionLogin", "FusionLogin", "data", LOGIN_FIELDS, [LOGIN_INPUT])
add_table("FusionLogin_verify", "FusionLogin", "verify", LOGIN_FIELDS, [LOGIN_VERIFY])

# === MissingTemplate (vision_image 参考图缺失，错误处理) ===
MT_FIELDS = ["username"]
add_table("MissingTemplate", "MissingTemplate", "data", MT_FIELDS, [
    ("L001", {"username": "admin"}),
])
add_table("MissingTemplate_verify", "MissingTemplate", "verify", MT_FIELDS, [
    ("V001", {"username": "BLANK"}),
])

con.commit()
con.close()
print(f"✓ data.sqlite created at {DB}")
