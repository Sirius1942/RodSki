"""RodSki SQLite 元表 DDL — 供 init 和 data import 共用"""

SQLITE_DDL = """
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
"""
