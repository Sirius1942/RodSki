#!/usr/bin/env python3
"""初始化订单管理系统数据库"""
import sqlite3
from pathlib import Path

def init_database():
    db_path = Path(__file__).parent / "demo.db"
    sql_path = Path(__file__).parent / "init_db.sql"

    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    with open(sql_path, 'r', encoding='utf-8') as f:
        sql_script = f.read()
        cursor.executescript(sql_script)

    conn.commit()
    conn.close()

    print(f"✅ 数据库初始化完成: {db_path}")
    print(f"📊 已创建表：users, orders, products")
    print(f"👤 用户数据：3条")
    print(f"📦 订单数据：3条")
    print(f"🛍️  商品数据：3条")

if __name__ == "__main__":
    init_database()
