"""簡易 API Key 驗證 - 保護 /api 和 /mcp
================================================

兩把獨立的鑰匙，各自保護不同的對外窗口，互不影響：

- `/mcp`：給 Claude.ai 的 MCP connector 用，鑰匙是 MCP_API_KEY，驗證 `Authorization: Bearer <key>`。
- `/api`：給前端網頁用，鑰匙是 APP_ACCESS_KEY，驗證 `X-App-Key: <key>` 這個自訂 header。
  前端（frontend/src/shared/AccessGate.vue + http.ts）第一次進站會跳密碼輸入畫面，輸入正確後
  存進 localStorage，之後每次 API 請求都帶上這個 header。

本機開發兩個環境變數都不設時直接放行（方便本機開發/mock db 不用先設密碼）；正式環境
（Render/Railway）要暴露在公開網址上，務必至少設定 APP_ACCESS_KEY，不設等於 /api 完全不驗證、
誰都能讀寫所有資料。

CORS 前置的 OPTIONS 預檢請求一律放行不檢查——瀏覽器送 preflight 時不會帶自訂 header，
如果在這裡連 OPTIONS 都擋，會導致所有跨網域請求（GitHub Pages 前端 → Render 後端）直接失敗，
連帶把整個網站打不通。
"""

import os

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

PROTECTED = (
    ("/mcp", "MCP_API_KEY", "authorization", lambda key: f"Bearer {key}"),
    ("/api", "APP_ACCESS_KEY", "x-app-key", lambda key: key),
)


class ApiKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path
        for prefix, env_name, header_name, expected in PROTECTED:
            if not path.startswith(prefix):
                continue
            api_key = os.getenv(env_name)
            if api_key and request.headers.get(header_name) != expected(api_key):
                return JSONResponse(status_code=401, content={"detail": "未授權：缺少或錯誤的存取密碼"})
            break
        return await call_next(request)
