# 飲食管理系統

雙人家庭的營養與體態管理 App：體重/運動紀錄、訓練計畫月曆、食譜食材庫、規則式週菜單推薦、購物清單、資料備份。

## 專案結構

```
Nutrition/
├── backend/    # FastAPI + SQLAlchemy + Postgres，依功能領域分資料夾（見 backend/README.md）
├── frontend/   # Vue 3 + TypeScript，依功能領域分資料夾（見 frontend/README.md）
├── archive/    # 整合前的獨立原型與早期草稿，僅供歷史參考，非活動程式碼
└── nutrition.db  # 舊的本機測試資料，未搬遷，正式資料以 Supabase Postgres 為準
```

後端跟前端都採用同一套 7 個功能領域劃分，兩邊資料夾名稱互相對應：

| 領域 | 內容 |
|---|---|
| `users` | 使用者基本資料、生理期欄位、飲食偏好 |
| `fitness` | 體重紀錄、運動紀錄、每日步數 |
| `training` | 動作資料庫、訓練範本、多天訓練計畫、月曆排程、週目標 |
| `recipes` | 食材庫、食材庫存、食譜（含步驟版本控制、營養素計算） |
| `meal_plans` / `meal-plans` | 週推薦引擎、熱量/巨量營養素計算、規則式選餐演算法 |
| `shopping` | 購買地點、食材地點偏好、購物清單 |

前端另外有 `dashboard`（總覽頁）、`settings`（設定頁，跨功能）、`trends`（趨勢圖表）、`shared`（跨功能共用元件/composable/型別）。

## 啟動方式（本機開發用）

正式日常使用是連雲端部署的版本（見下方「雲端部署」），這裡是本機開發、改程式時用的跑法。

**後端**（在 `backend/` 目錄下）：
```bash
pip install -r requirements.txt
python -m uvicorn main:app --port 8000
```
啟動前先複製 `backend/.env.example` 為 `backend/.env`，填入 Supabase 專案的 Postgres 連線字串（`DATABASE_URL`）。

API 文件：http://localhost:8000/docs

**前端**（在 `frontend/` 目錄下）：
```bash
npm install
npm run dev
```
開發伺服器：http://localhost:5173

## 資料庫

共用的雲端 Postgres（Supabase），供兩台電腦連同一份資料。連線字串在 `backend/.env` 的 `DATABASE_URL`，每台電腦各自設定，不進版控。開發階段的慣例是「重啟後端會自動建表 + 灌示範資料，若已有資料則跳過」。正式使用時請透過「設定」頁的「資料備份」功能定期匯出（JSON 快照），避免資料遺失。

專案根目錄的 `nutrition.db` 裡是舊的本機測試資料，確認不需要搬遷，可以封存或刪除，後端已不再讀取這個檔案。目前 Postgres 裡的資料是後端第一次啟動時自動灌的示範資料（`main.py` 的 `seed_demo_data`），之後就是正式使用累積的真實資料。

## 雲端部署（Railway + GitHub Pages）

因為公司網路會擋 Postgres 用的 5432/6543 埠，兩台電腦沒辦法直接連 Supabase，所以正式使用走雲端部署，兩台電腦只要用瀏覽器打開網址：

- **後端**：部署到 Railway，連 GitHub repo 後自動建置（`backend/Procfile`），在 Railway 後台設定環境變數 `DATABASE_URL`（Root Directory 設成 `backend`）
- **前端**：部署到 GitHub Pages，由 `.github/workflows/deploy-pages.yml` 在 push 到 `master` 時自動建置部署，網址是 `https://kktanzen1982.github.io/Nutrition/`
- 前端建置時需要知道後端網址：在 repo 的 Settings → Secrets and variables → Actions → Variables 設定 `VITE_API_BASE_URL`，值是 Railway 後端網址加上 `/api`（例如 `https://xxx.up.railway.app/api`）

設定一次之後，之後改程式碼 push 到 GitHub，前後端都會自動重新部署。

`backend/migrate_to_postgres.py` 是本來要把本機 `nutrition.db` 搬進 Postgres 用的一次性腳本，後來確認本機那份是測試資料不需要搬，所以沒有用到；保留在專案裡以防之後又要用類似的搬遷方式（例如換一份 Postgres）。
