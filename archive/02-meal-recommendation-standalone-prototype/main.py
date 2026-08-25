"""
BLOCK_5 測試用啟動檔

這個檔案不是原始交付內容的一部分，是為了讓 BLOCK_5 的 API
可以在沒有真實資料庫、沒有真實 Claude API 金鑰的情況下啟動，
讓你可以用 Swagger UI (/docs) 實際點擊測試每個 endpoint。

- get_db() 的 NotImplementedError 被 override 成回傳 None，
  讓需要它的 endpoint 能執行到底（回應的是程式碼裡寫死的模擬資料）。
- /generate 和 /adjust/regenerate-day 兩個端點會啟動背景任務並嘗試呼叫
  Claude API；因為沒有設定 ANTHROPIC_API_KEY，該背景任務會失敗，
  但可以透過 /meal-plans/jobs/{job_id}/status 觀察到完整的
  pending → processing → failed 流程。
"""

from fastapi import FastAPI

import BLOCK_5_meal_plan_api as meal_plan_api
import BLOCK_5_adjustment_api as adjustment_api

app = FastAPI(title="BLOCK_5 測試伺服器", description="Claude 推薦引擎 - 本地測試")


def _mock_db():
    return None


app.dependency_overrides[meal_plan_api.get_db] = _mock_db
app.dependency_overrides[adjustment_api.get_db] = _mock_db

app.include_router(meal_plan_api.router)
app.include_router(adjustment_api.router)


@app.get("/")
async def root():
    return {"message": "BLOCK_5 測試伺服器運行中，請前往 /docs 測試 API"}
