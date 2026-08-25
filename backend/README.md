# 後端（FastAPI + SQLAlchemy + Postgres）

依功能領域分資料夾，每個領域自己有 `models.py` / `schemas.py` / `services.py` / `router.py`（部分領域另有 `seed_data.py` 或純函式模組）。想改哪個功能，打開對應資料夾就好，不用在一個巨大檔案裡找。

```
backend/
├── main.py           # 進入點：建立 app、掛 CORS、include 各領域 router、啟動時建表+灌示範資料
├── database.py        # 共用：Base / engine / SessionLocal / get_db()，連線字串讀 .env 的 DATABASE_URL
├── backup_router.py    # 資料備份匯出/匯入（JSON 快照），跟功能領域無關的獨立小工具
├── pg_sync.py          # backup_router / migrate_to_postgres 共用的序列化與序列同步工具
├── migrate_to_postgres.py  # 一次性搬遷腳本：把本機 nutrition.db 搬進 Postgres
├── users/              # 使用者基本資料、生理期欄位、飲食偏好
├── fitness/             # 體重、運動、步數
├── training/             # 動作資料庫、訓練範本、多天計畫、月曆排程、週目標
├── recipes/              # 食材庫、食譜（含步驟版本控制、營養素計算）
├── meal_plans/            # 週推薦引擎、熱量計算、規則式選餐演算法
└── shopping/               # 購買地點、食材地點偏好、購物清單
```

## 跨領域依賴

各領域彼此獨立，但少數地方需要讀別的領域的資料（正常現象，不是要消除的東西）：

- `training` 的排程調整邏輯會讀寫 `fitness` 的運動紀錄。
- `meal_plans` 的推薦引擎會讀 `users`（使用者資料）、`fitness`（體重/運動）、`recipes`（食譜）。
- `shopping` 的購物清單彙總會讀 `recipes`（食譜食材）、`meal_plans`（週計畫菜單）。

每個領域的 `models.py` 都 `from database import Base`（共用同一個 registry），`main.py` 在 `Base.metadata.create_all()` 之前會 import 全部 6 個領域的 `models.py`，確保跨領域的外鍵能正確解析。

## 啟動

先複製 `.env.example` 為 `.env`，填入 Supabase 專案的 Postgres 連線字串（`DATABASE_URL`）。

```bash
pip install -r requirements.txt
python -m uvicorn main:app --port 8000
```

API 文件：http://localhost:8000/docs — 所有路由都掛在 `/api` 前綴下（`main.py` 統一加，各 router 內部路徑不含 `/api`）。

## 路由順序注意事項

`recipes/router.py` 的 `/recipes/search` 必須註冊在 `/recipes/{recipe_id}` 之前，`/ingredients/search`、`/ingredients/low-stock` 同理必須在 `/ingredients/{ingredient_id}` 之前；`shopping/router.py` 的 `/shopping-lists/history` 必須在 `/shopping-lists/{list_id}` 之前。這是 FastAPI/Starlette 路徑匹配的硬性規則（字面路徑段優先於變數路徑段要靠註冊順序），改動這些檔案時保留原本的順序。
