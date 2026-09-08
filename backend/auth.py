"""簡易 API Key 驗證 - 保護 /api 和 /mcp
================================================

給 Claude.ai 的 MCP connector 用。只保護 /mcp 這個掛載點本身（開啟 MCP session、列工具、呼叫工具），
不動 /api 底下原本給前端用的端點——前端目前完全沒有登入機制，若連 /api 一起擋，現有網頁會直接打不通。
這代表 /api 本身的資料仍然是誰都能讀寫，這是既有風險，不在這次「保護 MCP 對外窗口」的範圍內。

本機開發沒設 MCP_API_KEY 環境變數時直接放行；正式環境（Railway）要暴露給 Claude.ai 前務必設定，
不設等於 /mcp 完全不驗證。

Claude.ai 端連線設定裡帶 `Authorization: Bearer <MCP_API_KEY>`，fastapi-mcp 收到工具呼叫時會把
這個 header 轉發進它打回 /api 的內部請求，但 /api 本身不檢查，所以轉不轉發其實不影響驗證結果，
真正把關的只有這支 middleware。
"""

import os

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

PROTECTED_PREFIXES = ("/mcp",)


class ApiKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        api_key = os.getenv("MCP_API_KEY")
        if api_key and request.url.path.startswith(PROTECTED_PREFIXES):
            if request.headers.get("authorization") != f"Bearer {api_key}":
                return JSONResponse(status_code=401, content={"detail": "未授權：缺少或錯誤的 API key"})
        return await call_next(request)
