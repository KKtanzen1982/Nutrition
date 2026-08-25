"""
一次性搬遷腳本：把本機 nutrition.db（SQLite）的資料搬進 DATABASE_URL 指向的 Postgres。
================================================

使用方式（在 backend/ 目錄下）：
    python migrate_to_postgres.py

前置條件：
- backend/.env 的 DATABASE_URL 已經指向目標 Postgres（database.py 會讀這個值）
- 專案根目錄的 nutrition.db 是要搬過去的那份資料

這支腳本只負責「搬資料」，不負責決定要不要搬。目標 Postgres 的表如果已經有資料，
腳本會印警告並中止，避免重複執行造成資料重複。
"""

import os
import sys

from sqlalchemy import create_engine

# 確保所有 ORM class 註冊到 Base.metadata（跟 main.py 開頭那段一樣）
from database import Base, engine as target_engine
import users.models  # noqa: F401
import fitness.models  # noqa: F401
import training.models  # noqa: F401
import recipes.models  # noqa: F401
import meal_plans.models  # noqa: F401
import shopping.models  # noqa: F401

from pg_sync import sync_sequences, tables_in_insert_order

SQLITE_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "nutrition.db")


def main():
    if not os.path.exists(SQLITE_DB_PATH):
        print(f"找不到來源 SQLite 檔案：{SQLITE_DB_PATH}")
        sys.exit(1)

    source_engine = create_engine(f"sqlite:///{SQLITE_DB_PATH}")

    print(f"來源：{SQLITE_DB_PATH}")
    print(f"目標：{target_engine.url.render_as_string(hide_password=True)}")

    Base.metadata.create_all(bind=target_engine)

    tables = tables_in_insert_order(Base.metadata)

    with target_engine.connect() as target_conn:
        for table in tables:
            existing = target_conn.execute(table.select().limit(1)).first()
            if existing is not None:
                print(f"目標表 {table.name} 已經有資料，為避免重複搬遷已中止。"
                      f"如果確定要重跑，請先清空目標 Postgres 的資料。")
                sys.exit(1)

    with source_engine.connect() as source_conn, target_engine.begin() as target_conn:
        for table in tables:
            rows = source_conn.execute(table.select()).mappings().all()
            if not rows:
                print(f"{table.name}: 0 筆（略過）")
                continue
            target_conn.execute(table.insert(), [dict(row) for row in rows])
            print(f"{table.name}: {len(rows)} 筆")

        sync_sequences(target_conn, Base.metadata)

    print("搬遷完成。建議去 Postgres 對照每張表筆數，確認跟上面印出的一致。")


if __name__ == "__main__":
    main()
