"""
BLOCK_6 測試伺服器（真實資料庫版本）
======================================

依照 BLOCK_5/BLOCK_5_test_app.py 的做法：建立所有 BLOCK_6 資料表、
灌入種子資料，並把 BLOCK_6_shopping_list_api 的三個 router 掛到一個
真正連接 SQLite（block6_test.db）的 FastAPI app 上。

啟動：
    uvicorn main:app --reload --port 8126
或透過 .claude/launch.json 的 block6-test-server 設定啟動，然後打開 /docs 手動測試。

建議測試流程：
    1. GET  /shopping-lists/1                       -> 404（種子資料只建了週計畫，還沒生成清單）
    2. POST /meal-plans/1/confirm                    -> 確認種子週計畫、生成購物清單，回傳 shopping_list_id
    3. GET  /shopping-lists/{shopping_list_id}        -> 看到依購買地點分組的完整清單
    4. PUT  /shopping-lists/{id}/items/{item_id}/purchased -> 勾選已購
    5. PUT  /shopping-lists/{id}/status（status=歸檔） -> 歸檔，寫入採購歷史
    6. GET  /shopping-lists/history                  -> 看到剛剛的歸檔快照
"""

import logging

from fastapi import FastAPI

from BLOCK_6_models import Base
from BLOCK_6_test_db import engine, get_db, new_session
from BLOCK_6_seed_data import seed_if_empty

import BLOCK_6_shopping_list_api as shopping_list_api

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)

_seed_db = new_session()
try:
    if seed_if_empty(_seed_db):
        logger.info("種子資料已灌入 block6_test.db")
    else:
        logger.info("block6_test.db 已有資料，略過種子資料")
finally:
    _seed_db.close()

app = FastAPI(title="BLOCK_6 測試伺服器（真實資料庫）", description="購物清單管理 - 本地測試")

app.dependency_overrides[shopping_list_api.get_db] = get_db

app.include_router(shopping_list_api.router_meal_plans)
app.include_router(shopping_list_api.router_shopping_lists)
app.include_router(shopping_list_api.router_purchase_locations)
app.include_router(shopping_list_api.router_ingredient_preferences)


@app.get("/")
async def root():
    return {"message": "BLOCK_6 測試伺服器運行中（真實資料庫），請前往 /docs 測試 API"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8126)
