"""
BLOCK_4 獨立測試伺服器
======================

依照 BLOCK_4_INTEGRATION_GUIDE.md 的步驟，將 BLOCK_4 路由掛載到一個
最小的 FastAPI app 上，並用 SQLAlchemy 建立所有 BLOCK_4 資料表，
以便執行 BLOCK_4_TEST_EXAMPLES.py 進行端對端測試。
"""

from fastapi import FastAPI

from BLOCK_4_models import Base
from test_db import engine
from BLOCK_4_routes import router as block4_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="BLOCK_4 測試伺服器")
app.include_router(block4_router)


@app.get("/")
def root():
    return {"message": "BLOCK_4 test server running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
