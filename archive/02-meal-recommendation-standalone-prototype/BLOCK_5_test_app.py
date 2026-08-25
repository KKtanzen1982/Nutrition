"""
BLOCK_5 測試伺服器（真實資料庫版本）
======================================

依照 BLOCK_4/extracted/test_app.py 的做法：建立所有 BLOCK_5 資料表、
灌入種子資料，並把 BLOCK_5_meal_plan_api / BLOCK_5_adjustment_api 的路由
掛到一個真正連接 SQLite（block5_test.db）的 FastAPI app 上。

沒有設定 ANTHROPIC_API_KEY 時，Claude 呼叫會自動使用
BLOCK_5_claude_client.MockClaudeService，整條「生成推薦 → 微調 → 確認」
流程不需要真的打 Anthropic API 也能端對端測試。

啟動：
    uvicorn BLOCK_5_test_app:app --reload --port 8123
或透過 .claude/launch.json 的 block5-test-server 設定啟動。
"""

import logging

from fastapi import FastAPI

from BLOCK_5_models import Base
from BLOCK_5_test_db import engine, get_db, new_session
from BLOCK_5_seed_data import seed_if_empty

import BLOCK_5_meal_plan_api as meal_plan_api
import BLOCK_5_adjustment_api as adjustment_api

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)

_seed_db = new_session()
try:
    if seed_if_empty(_seed_db):
        logger.info("種子資料已灌入 block5_test.db")
    else:
        logger.info("block5_test.db 已有資料，略過種子資料")
finally:
    _seed_db.close()

app = FastAPI(title="BLOCK_5 測試伺服器（真實資料庫）", description="Claude 推薦引擎 - 本地測試")

app.dependency_overrides[meal_plan_api.get_db] = get_db
app.dependency_overrides[meal_plan_api.get_session_factory] = lambda: new_session
app.dependency_overrides[adjustment_api.get_db] = get_db
app.dependency_overrides[adjustment_api.get_session_factory] = lambda: new_session

app.include_router(meal_plan_api.router)
app.include_router(adjustment_api.router)


@app.get("/")
async def root():
    return {"message": "BLOCK_5 測試伺服器運行中（真實資料庫），請前往 /docs 測試 API"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8123)
