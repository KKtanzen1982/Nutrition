# 前端（Vue 3 + TypeScript + Vite）

依功能領域分資料夾，每個領域資料夾裡直接放該功能的 view + component + api 封裝檔，不再像以前分散在 `views/`、`components/`、`api/` 三個平鋪資料夾裡。想改哪個功能，打開對應資料夾就好。

```
frontend/src/
├── App.vue / main.ts / router/router.ts   # 應用進入點
├── shared/         # 跨功能共用：Modal、ConfirmDialog、UserSwitcher、http.ts、date_utils.ts、types.ts 等
├── dashboard/      # 總覽頁 + 卡片自訂
├── users/          # 個人資料頁
├── fitness/        # 體重、運動頁
├── training/       # 動作資料庫、訓練計畫月曆
├── recipes/        # 食譜、食材頁
├── meal-plans/     # 週推薦頁
├── shopping/       # 購物清單、採購歷史頁
├── settings/       # 設定頁（使用者/購買地點/資料備份，本來就跨功能）
└── trends/         # 趨勢圖表頁
```

## 啟動

```bash
npm install
npm run dev
```

開發伺服器：http://localhost:5173，預期後端跑在 http://localhost:8000（見 `shared/http.ts` 的 `VITE_API_BASE_URL` / 預設值）。

## 命名慣例

Vue 元件用 PascalCase（`WeightView.vue`），TypeScript 檔案用 snake_case（`weight_api.ts`）。資料夾路徑本身就是功能分類，檔名不再需要加專案代號前綴。
