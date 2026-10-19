#!/usr/bin/env python3
"""Build RodSki website acceptance test data.

The module uses data/data.sqlite as the only test data file. This script is
idempotent and rebuilds the SQLite EAV tables from the definitions below.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent / "data.sqlite"

SCHEMA = """
CREATE TABLE rs_datatable (
    table_name TEXT PRIMARY KEY,
    model_name TEXT NOT NULL,
    table_kind TEXT NOT NULL CHECK (table_kind IN ('data', 'verify')),
    row_mode TEXT NOT NULL CHECK (row_mode IN ('standard', 'db_query', 'db_sql')),
    remark TEXT DEFAULT '',
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE rs_datatable_field (
    table_name TEXT NOT NULL,
    field_name TEXT NOT NULL,
    field_order INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (table_name, field_name),
    FOREIGN KEY (table_name) REFERENCES rs_datatable(table_name)
);
CREATE TABLE rs_row (
    table_name TEXT NOT NULL,
    data_id TEXT NOT NULL,
    remark TEXT DEFAULT '',
    PRIMARY KEY (table_name, data_id),
    FOREIGN KEY (table_name) REFERENCES rs_datatable(table_name)
);
CREATE TABLE rs_field (
    table_name TEXT NOT NULL,
    data_id TEXT NOT NULL,
    field_name TEXT NOT NULL,
    field_value TEXT NOT NULL,
    PRIMARY KEY (table_name, data_id, field_name),
    FOREIGN KEY (table_name, data_id) REFERENCES rs_row(table_name, data_id),
    FOREIGN KEY (table_name, field_name) REFERENCES rs_datatable_field(table_name, field_name)
);
"""


def add_table(
    conn: sqlite3.Connection,
    table_name: str,
    model_name: str,
    table_kind: str,
    fields: list[str],
    rows: list[tuple[str, str, dict[str, str]]],
    remark: str = "",
) -> None:
    conn.execute(
        """
        INSERT INTO rs_datatable(table_name, model_name, table_kind, row_mode, remark)
        VALUES (?, ?, ?, 'standard', ?)
        """,
        (table_name, model_name, table_kind, remark),
    )
    for order, field_name in enumerate(fields):
        conn.execute(
            "INSERT INTO rs_datatable_field(table_name, field_name, field_order) VALUES (?, ?, ?)",
            (table_name, field_name, order),
        )

    expected = set(fields)
    for data_id, row_remark, values in rows:
        missing = expected - set(values)
        extra = set(values) - expected
        if missing or extra:
            raise ValueError(
                f"{table_name}.{data_id} field mismatch: "
                f"missing={sorted(missing)}, extra={sorted(extra)}"
            )
        conn.execute(
            "INSERT INTO rs_row(table_name, data_id, remark) VALUES (?, ?, ?)",
            (table_name, data_id, row_remark),
        )
        for field_name in fields:
            conn.execute(
                "INSERT INTO rs_field(table_name, data_id, field_name, field_value) VALUES (?, ?, ?, ?)",
                (table_name, data_id, field_name, values[field_name]),
            )


def main() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()

    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(SCHEMA)

        add_table(
            conn,
            "WebsiteLanding_verify",
            "WebsiteLanding",
            "verify",
            ["headline", "docsLink", "changelogLink", "quickstartLink"],
            [
                (
                    "V001",
                    "landing page core content and navigation",
                    {
                        "headline": "面向 AI Agent 的确定性测试执行引擎",
                        "docsLink": "文档",
                        "changelogLink": "Changelog",
                        "quickstartLink": "快速开始 →",
                    },
                )
            ],
            "Landing page expected content",
        )

        add_table(
            conn,
            "V8DocsHome_verify",
            "V8DocsHome",
            "verify",
            ["title", "quickstartLink", "keywordsLink", "guideLink", "changelogLink"],
            [
                (
                    "V001",
                    "v8 docs home links use current route shape",
                    {
                        "title": "RodSki v8.0 文档",
                        "quickstartLink": "快速开始",
                        "keywordsLink": "关键字手册",
                        "guideLink": "用例编写指南",
                        "changelogLink": "更新日志",
                    },
                )
            ],
            "v8 docs home expected content",
        )

        add_table(
            conn,
            "DocsPageTitle_verify",
            "DocsPageTitle",
            "verify",
            ["title"],
            [
                ("V_QUICKSTART", "quickstart page title", {"title": "快速开始"}),
                ("V_KEYWORDS", "keywords page title", {"title": "关键字手册"}),
                ("V_GUIDE", "test case guide page title", {"title": "用例编写指南（v8.0）"}),
                ("V_API", "api reference page title", {"title": "API 参考"}),
                ("V_ARCH", "architecture page title", {"title": "架构说明"}),
                ("V_CHANGELOG", "changelog page title", {"title": "更新日志"}),
                ("V_V7_GUIDE", "v7 guide page title", {"title": "用例编写指南（v7.3.0）"}),
            ],
            "Shared docs page title expectations",
        )

        add_table(
            conn,
            "V7DocsHome_verify",
            "V7DocsHome",
            "verify",
            ["title", "latestLink", "guideLink"],
            [
                (
                    "V001",
                    "v7 docs historical page links to current docs and v7 guide",
                    {
                        "title": "RodSki v7.x 文档",
                        "latestLink": "v8.0 文档",
                        "guideLink": "用例编写指南",
                    },
                )
            ],
            "v7 docs expected content",
        )

        add_table(
            conn,
            "WebsiteRouteState_verify",
            "WebsiteRouteState",
            "verify",
            ["pathname"],
            [
                ("V_LANDING", "root redirects to landing", {"pathname": "/landing"}),
            ],
            "Route state returned from evaluate",
        )

        add_table(
            conn,
            "WebsiteResourceState_verify",
            "WebsiteResourceState",
            "verify",
            ["status", "contains"],
            [
                ("V_LLMS", "llms route serves v8 mdx text", {"status": "200", "contains": "true"}),
                ("V_404", "missing docs route returns 404", {"status": "404", "contains": "true"}),
            ],
            "Fetch state returned from evaluate",
        )

    print(f"data.sqlite created: {DB_PATH}")


if __name__ == "__main__":
    main()
