# 區塊 6：購物清單管理 - 完成總結

**完成日期**：2026-08-11
**狀態**：✅ 架構確認 + 代碼全部生成 + 端對端測試通過

---

## 📋 生成的文件清單

| 文件名 | 用途 | 狀態 |
|------|------|------|
| **BLOCK_6_ARCHITECTURE_DESIGN.md** | 完整架構設計文檔 | ✅ |
| **BLOCK_6_models.py** | SQLAlchemy ORM 模型 | ✅ |
| **BLOCK_6_schemas.py** | Pydantic 數據模型 | ✅ |
| **BLOCK_6_shopping_service.py** | 純計算邏輯（加總/成本/地點/補貨判斷） | ✅ |
| **BLOCK_6_db_service.py** | 資料庫查詢與持久化 | ✅ |
| **BLOCK_6_shopping_list_api.py** | 購物清單相關 API endpoints | ✅ |
| **BLOCK_6_seed_data.py** | 測試種子資料 | ✅ |
| **BLOCK_6_test_db.py** | 獨立測試用資料庫連線 | ✅ |
| **main.py** | 真實資料庫版測試伺服器 | ✅ |
| **BLOCK_6_TEST_EXAMPLES.py** | 端對端測試腳本 | ✅ |
| **requirements.txt** | 相依套件 | ✅ |
| **BLOCK_6_INTEGRATION_GUIDE.md** | 集成指南 | ✅ |
| **BLOCK_6_INDEX.md** | 代碼索引 | ✅ |
| **BLOCK_6_COMPLETION_SUMMARY.md** | 本文檔 | ✅ |

---

## 🏗️ 架構概覽

### 核心流程

```
週計畫已由區塊 5 生成（daily_meal_detail 已有完整 7 天 x 2 人的餐次）
    ↓
用戶點「確認推薦」
    ↓
POST /meal-plans/{plan_id}/confirm
    ↓
① plan_status 改為「已確認」
    ↓
② 展開該週所有餐次 → 依食譜食材明細換算實際用量
    ↓
③ 跨 7 天、跨 A/B 兩人合併加總（同一食材只出現一次）
    ↓
④ 判定成本等級（取最高）/ 使用者標記 / 購買地點 / 補貨警告
    ↓
⑤ 寫入 shopping_list + shopping_list_items
    ↓
回傳 shopping_list_id（重複確認會沿用既有清單，冪等）
```

### 核心模組

| 模組 | 職責 | 主要函式 |
|------|------|--------|
| **BLOCK_6_shopping_service** | 純計算（不碰 DB） | `aggregate_ingredient_quantities()`, `determine_cost_level()`, `determine_purchase_location()`, `determine_needs_restocking()`, `build_shopping_list_items()` |
| **BLOCK_6_db_service** | 查詢 + 持久化 | `generate_shopping_list_for_plan()`, `confirm_plan_and_generate_list()`, `get_shopping_list_detail()`, `update_shopping_list_status()` |

---

## 🔌 API 端點速查表

```bash
# 確認推薦 → 生成購物清單
POST   /meal-plans/{plan_id}/confirm
       → { success, plan_id, shopping_list_id, message }

# 購物清單
GET    /shopping-lists/{list_id}
       → 按「購買地點 -> 食材分類」分組的完整清單
POST   /shopping-lists/{list_id}/items
PUT    /shopping-lists/{list_id}/items/{item_id}
DELETE /shopping-lists/{list_id}/items/{item_id}
PUT    /shopping-lists/{list_id}/items/{item_id}/purchased
PUT    /shopping-lists/{list_id}/status
GET    /shopping-lists/history

# 購買地點 / 食材地點偏好
GET    /purchase-locations
POST   /purchase-locations
PUT    /purchase-locations/{location_id}
DELETE /purchase-locations/{location_id}
GET    /ingredients/{ingredient_id}/location-preference
PUT    /ingredients/{ingredient_id}/location-preference
```

---

## 🎯 關鍵設計決策

這些是架構文件沒寫死細節、由本區塊實作時補上的規則（詳細理由見 `BLOCK_6_ARCHITECTURE_DESIGN.md`）：

1. **成本等級衝突**：食材出現在多道成本等級不同的食譜 → 取最高者（保守估算）
2. **補貨警告的預設值**：食材沒有庫存紀錄 → 視同「目前庫存 = 0」，等於預設需要補購
3. **購買地點分配優先序**：結構化偏好（表 6b, priority=1）> 食材庫的文字備援欄位 > 留空
4. **確認推薦端點的歸屬**：架構文件把 `POST /meal-plans/:id/confirm` 列在「週推薦 API」章節，但按區塊劃分邏輯應屬於區塊 6；本區塊實作了完整版本（真正生成購物清單），取代區塊 5 目前掛的 stub（`shopping_list_id` 回 `null`）
5. **recipe_ingredients / ingredient_library 的所有權**：本區塊不宣稱擁有這兩張表的 DDL，只在自己的獨立測試資料庫放唯讀簡化版（做法比照區塊 5 對 `User`/`Recipe` 的處理），正式整合時要換成區塊 4 的正式資料表

---

## ✅ 測試驗證

已用 `main.py`（真實 SQLite 資料庫）+ `BLOCK_6_TEST_EXAMPLES.py` 跑過完整端對端流程並全部通過：

- [x] 確認推薦 → 生成購物清單（含正確的跨用戶/跨天食材加總，人工核算過一筆食材的計算結果）
- [x] 重複確認同一個週計畫 → 冪等，不會產生第二份清單
- [x] 依購買地點分組、依食材分類分組
- [x] 新增 / 編輯 / 刪除購物項目
- [x] 標記已購
- [x] 狀態轉換 草稿 → 已確認 → 採購中 → 已採購 → 歸檔
- [x] 歸檔時自動寫入採購歷史快照
- [x] 採購歷史查詢
- [x] 購買地點 CRUD
- [x] 食材地點偏好整批覆蓋
- [x] 查無資料回傳 404

---

## 🚀 下一步

### 短期
- [ ] 依 `BLOCK_6_INTEGRATION_GUIDE.md` 把 7 張唯讀參照表換成區塊 1/4/5 的正式資料表
- [ ] 把區塊 5 的 `PUT /meal-plans/{id}/confirm` stub 換成本區塊的 `POST` 版本

### 中期
- [ ] 開發區塊 7（Web UI 前端），串接本區塊所有 API
- [ ] 完整系統端對端測試（區塊 1～7 全部整合後）
