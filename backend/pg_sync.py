"""
Postgres 資料搬遷/備份共用工具
================================================

被 backup_router.py（線上匯出/匯入）跟 migrate_to_postgres.py（一次性搬遷）共用：
- 表格的匯出/匯入依外鍵相依順序排序
- JSON 匯出用的型別序列化／還原（date、datetime）
- 匯入完資料後同步 Postgres 的 auto-increment 序列，避免撞主鍵
"""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, MetaData, text
from sqlalchemy.engine import Connection


def tables_in_insert_order(metadata: MetaData):
    """依外鍵相依性排序：被依賴的表在前，適合匯入/搬遷時的寫入順序。"""
    return metadata.sorted_tables


def tables_in_delete_order(metadata: MetaData):
    """插入順序反過來：依賴別人的表先刪，避免外鍵擋刪除。"""
    return list(reversed(metadata.sorted_tables))


def serialize_value(value):
    """把 date/datetime 轉成 ISO 字串，其餘型別（int/float/bool/str/None）原樣返回，JSON 可直接編碼。"""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def deserialize_row(table, row: dict) -> dict:
    """把 JSON 讀回來的字串依 column 型別還原成 date/datetime 物件，其餘欄位原樣使用。"""
    result = {}
    for col in table.columns:
        if col.name not in row:
            continue
        value = row[col.name]
        if value is not None:
            if isinstance(col.type, DateTime):
                value = datetime.fromisoformat(value)
            elif isinstance(col.type, Date):
                value = date.fromisoformat(value)
        result[col.name] = value
    return result


def sync_sequences(conn: Connection, metadata: MetaData) -> None:
    """插入完帶著原始 id 的資料後，把每張表的 auto-increment 序列調到目前最大 id，避免之後新增資料撞主鍵。"""
    for table in metadata.sorted_tables:
        for col in table.primary_key.columns:
            if col.type.python_type is not int:
                continue
            seq_name = conn.execute(
                text("SELECT pg_get_serial_sequence(:t, :c)"),
                {"t": table.name, "c": col.name},
            ).scalar()
            if not seq_name:
                continue
            max_id = conn.execute(text(f'SELECT MAX("{col.name}") FROM "{table.name}"')).scalar()
            if max_id is not None:
                conn.execute(text("SELECT setval(:seq, :val)"), {"seq": seq_name, "val": max_id})
