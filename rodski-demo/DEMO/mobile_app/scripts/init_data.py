"""初始化 mobile_app demo 数据库"""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / "data" / "data.sqlite"
db_path.parent.mkdir(parents=True, exist_ok=True)

if db_path.exists():
    db_path.unlink()

conn = sqlite3.connect(str(db_path))
c = conn.cursor()

c.executescript("""
CREATE TABLE IF NOT EXISTS rs_datatable (
    table_name TEXT PRIMARY KEY,
    model_name TEXT NOT NULL,
    table_kind TEXT NOT NULL CHECK (table_kind IN ('data', 'verify')),
    row_mode TEXT NOT NULL CHECK (row_mode IN ('standard', 'db_query', 'db_sql')),
    remark TEXT DEFAULT '',
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS rs_datatable_field (
    table_name TEXT NOT NULL,
    field_name TEXT NOT NULL,
    field_order INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (table_name, field_name),
    FOREIGN KEY (table_name) REFERENCES rs_datatable(table_name)
);
CREATE TABLE IF NOT EXISTS rs_row (
    table_name TEXT NOT NULL,
    data_id TEXT NOT NULL,
    remark TEXT DEFAULT '',
    PRIMARY KEY (table_name, data_id),
    FOREIGN KEY (table_name) REFERENCES rs_datatable(table_name)
);
CREATE TABLE IF NOT EXISTS rs_field (
    table_name TEXT NOT NULL,
    data_id TEXT NOT NULL,
    field_name TEXT NOT NULL,
    field_value TEXT NOT NULL,
    PRIMARY KEY (table_name, data_id, field_name),
    FOREIGN KEY (table_name, data_id) REFERENCES rs_row(table_name, data_id),
    FOREIGN KEY (table_name, field_name) REFERENCES rs_datatable_field(table_name, field_name)
);
""")

# LoginScreen 输入表
c.execute("INSERT INTO rs_datatable VALUES ('LoginScreen','LoginScreen','data','standard','','2026-05-19')")
for i, f in enumerate(['username', 'password', 'loginBtn', 'welcomeText', 'errorMsg']):
    c.execute("INSERT INTO rs_datatable_field VALUES ('LoginScreen',?,?)", (f, i))
c.execute("INSERT INTO rs_row VALUES ('LoginScreen','L001','正常登录')")
for f, v in [('username', 'admin'), ('password', '123456'), ('loginBtn', 'click'), ('welcomeText', 'NONE'), ('errorMsg', 'NONE')]:
    c.execute("INSERT INTO rs_field VALUES ('LoginScreen','L001',?,?)", (f, v))
c.execute("INSERT INTO rs_row VALUES ('LoginScreen','L002','错误密码')")
for f, v in [('username', 'admin'), ('password', 'wrong'), ('loginBtn', 'click'), ('welcomeText', 'NONE'), ('errorMsg', 'NONE')]:
    c.execute("INSERT INTO rs_field VALUES ('LoginScreen','L002',?,?)", (f, v))

# LoginScreen_verify 验证表
c.execute("INSERT INTO rs_datatable VALUES ('LoginScreen_verify','LoginScreen','verify','standard','','2026-05-19')")
for i, f in enumerate(['welcomeText', 'errorMsg']):
    c.execute("INSERT INTO rs_datatable_field VALUES ('LoginScreen_verify',?,?)", (f, i))
c.execute("INSERT INTO rs_row VALUES ('LoginScreen_verify','V001','登录成功验证')")
for f, v in [('welcomeText', '欢迎，admin'), ('errorMsg', 'NONE')]:
    c.execute("INSERT INTO rs_field VALUES ('LoginScreen_verify','V001',?,?)", (f, v))
c.execute("INSERT INTO rs_row VALUES ('LoginScreen_verify','V002','登录失败验证')")
for f, v in [('welcomeText', 'NONE'), ('errorMsg', '用户名或密码错误')]:
    c.execute("INSERT INTO rs_field VALUES ('LoginScreen_verify','V002',?,?)", (f, v))

# HomeScreen 输入表
c.execute("INSERT INTO rs_datatable VALUES ('HomeScreen','HomeScreen','data','standard','','2026-05-19')")
for i, f in enumerate(['welcomeText', 'orderListBtn']):
    c.execute("INSERT INTO rs_datatable_field VALUES ('HomeScreen',?,?)", (f, i))
c.execute("INSERT INTO rs_row VALUES ('HomeScreen','H001','点击订单列表按钮')")
for f, v in [('welcomeText', 'NONE'), ('orderListBtn', 'click')]:
    c.execute("INSERT INTO rs_field VALUES ('HomeScreen','H001',?,?)", (f, v))

# HomeScreen_verify 验证表
c.execute("INSERT INTO rs_datatable VALUES ('HomeScreen_verify','HomeScreen','verify','standard','','2026-05-19')")
for i, f in enumerate(['welcomeText', 'orderListBtn']):
    c.execute("INSERT INTO rs_datatable_field VALUES ('HomeScreen_verify',?,?)", (f, i))
c.execute("INSERT INTO rs_row VALUES ('HomeScreen_verify','VH001','主页验证')")
for f, v in [('welcomeText', '欢迎，admin'), ('orderListBtn', 'NONE')]:
    c.execute("INSERT INTO rs_field VALUES ('HomeScreen_verify','VH001',?,?)", (f, v))

conn.commit()
conn.close()
print(f"data.sqlite 创建完成: {db_path}")
