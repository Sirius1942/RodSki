"""初始化 mobile_app demo 数据库 — Iteration 48"""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / "data" / "data.sqlite"
db_path.parent.mkdir(parents=True, exist_ok=True)

conn = sqlite3.connect(str(db_path))
c = conn.cursor()

c.executescript("""
CREATE TABLE IF NOT EXISTS rs_datatable (
    table_name TEXT PRIMARY KEY,
    display_name TEXT,
    table_kind TEXT,
    table_type TEXT,
    description TEXT,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS rs_datatable_field (
    table_name TEXT,
    field_name TEXT,
    field_order INTEGER,
    PRIMARY KEY (table_name, field_name)
);
CREATE TABLE IF NOT EXISTS rs_row (
    table_name TEXT,
    row_id TEXT,
    remark TEXT,
    PRIMARY KEY (table_name, row_id)
);
CREATE TABLE IF NOT EXISTS rs_field (
    table_name TEXT,
    row_id TEXT,
    field_name TEXT,
    field_value TEXT,
    PRIMARY KEY (table_name, row_id, field_name)
);
""")

# LoginScreen 输入表
c.execute("INSERT OR REPLACE INTO rs_datatable VALUES ('LoginScreen','LoginScreen','data','standard','','2026-05-19')")
for i, f in enumerate(['username', 'password', 'loginBtn']):
    c.execute("INSERT OR REPLACE INTO rs_datatable_field VALUES ('LoginScreen',?,?)", (f, i))
c.execute("INSERT OR REPLACE INTO rs_row VALUES ('LoginScreen','L001','正常登录')")
for f, v in [('username', 'admin'), ('password', '123456'), ('loginBtn', 'click')]:
    c.execute("INSERT OR REPLACE INTO rs_field VALUES ('LoginScreen','L001',?,?)", (f, v))
c.execute("INSERT OR REPLACE INTO rs_row VALUES ('LoginScreen','L002','错误密码')")
for f, v in [('username', 'admin'), ('password', 'wrong'), ('loginBtn', 'click')]:
    c.execute("INSERT OR REPLACE INTO rs_field VALUES ('LoginScreen','L002',?,?)", (f, v))

# LoginScreen_verify 验证表
c.execute("INSERT OR REPLACE INTO rs_datatable VALUES ('LoginScreen_verify','LoginScreen_verify','verify','standard','','2026-05-19')")
for i, f in enumerate(['welcomeText', 'errorMsg']):
    c.execute("INSERT OR REPLACE INTO rs_datatable_field VALUES ('LoginScreen_verify',?,?)", (f, i))
c.execute("INSERT OR REPLACE INTO rs_row VALUES ('LoginScreen_verify','V001','登录成功验证')")
for f, v in [('welcomeText', '欢迎，admin'), ('errorMsg', 'NONE')]:
    c.execute("INSERT OR REPLACE INTO rs_field VALUES ('LoginScreen_verify','V001',?,?)", (f, v))
c.execute("INSERT OR REPLACE INTO rs_row VALUES ('LoginScreen_verify','V002','登录失败验证')")
for f, v in [('welcomeText', 'NONE'), ('errorMsg', '用户名或密码错误')]:
    c.execute("INSERT OR REPLACE INTO rs_field VALUES ('LoginScreen_verify','V002',?,?)", (f, v))

conn.commit()
conn.close()
print(f"data.sqlite 创建完成: {db_path}")
