"""資料備份（匯出／匯入整個資料庫的 JSON 快照），跟任何一個功能領域都無關，獨立成一個檔案"""

import json
from datetime import date, datetime

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import Response

from database import Base, engine
from pg_sync import (
    deserialize_row,
    serialize_value,
    sync_sequences,
    tables_in_delete_order,
    tables_in_insert_order,
)

router = APIRouter(tags=["backup"])


@router.get("/backup/export")
def export_backup():
    """把目前資料庫所有表匯出成一份 JSON 檔下載下來，之後可以用 /api/backup/import 還原。"""
    backup = {"exported_at": datetime.utcnow().isoformat(), "tables": {}}

    with engine.connect() as conn:
        for table in tables_in_insert_order(Base.metadata):
            rows = conn.execute(table.select()).mappings().all()
            backup["tables"][table.name] = [
                {k: serialize_value(v) for k, v in row.items()} for row in rows
            ]

    filename = f"nutrition-backup-{date.today().isoformat()}.json"
    content = json.dumps(backup, ensure_ascii=False, indent=2)
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/backup/import")
async def import_backup(file: UploadFile = File(...)):
    """
    用上傳的 JSON 備份檔整個覆蓋現有資料庫。危險操作，前端要在呼叫前先跟使用者二次確認。
    先驗證檔案結構（有 tables 欄位、且包含 users 表），避免誤匯入不相關的檔案把現有資料庫弄壞。
    """
    content = await file.read()
    try:
        backup = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="不是合法的 JSON 備份檔")

    tables_data = backup.get("tables")
    if not isinstance(tables_data, dict) or "users" not in tables_data:
        raise HTTPException(status_code=400, detail="這個檔案看起來不是本系統的備份（缺少 users 表）")

    with engine.begin() as conn:
        for table in tables_in_delete_order(Base.metadata):
            conn.execute(table.delete())

        for table in tables_in_insert_order(Base.metadata):
            rows = tables_data.get(table.name, [])
            if rows:
                conn.execute(table.insert(), [deserialize_row(table, row) for row in rows])

        sync_sequences(conn, Base.metadata)

    return {"success": True, "message": "匯入完成，資料已還原，請重新整理頁面"}
