# 區塊 6：購物清單管理 - 完整代碼索引

**生成日期**：2026-08-11
**版本**：1.0 - 完整版
**總文件數**：14 份

---

## 📑 快速導航

### 📘 先讀這些（文檔）

| 序號 | 文件 | 用途 | 優先級 |
|------|------|------|--------|
| 1️⃣ | **BLOCK_6_COMPLETION_SUMMARY.md** | 區塊 6 完成總結 | ⭐⭐⭐ |
| 2️⃣ | **BLOCK_6_ARCHITECTURE_DESIGN.md** | 完整架構設計 | ⭐⭐⭐ |
| 3️⃣ | **BLOCK_6_INTEGRATION_GUIDE.md** | 集成指南 + 使用範例 | ⭐⭐⭐ |

### 💻 然後看這些（代碼）

| 序號 | 文件 | 關鍵內容 | 優先級 |
|------|------|---------|--------|
| 1️⃣ | **BLOCK_6_models.py** | ORM 模型（5 張本區塊擁有的表 + 7 張唯讀參照） | ⭐⭐⭐ |
| 2️⃣ | **BLOCK_6_schemas.py** | Pydantic 請求/回應模型 | ⭐⭐⭐ |
| 3️⃣ | **BLOCK_6_shopping_service.py** | 純計算邏輯（加總/成本/地點/補貨） | ⭐⭐⭐ |
| 4️⃣ | **BLOCK_6_db_service.py** | 資料庫查詢與持久化 | ⭐⭐⭐ |
| 5️⃣ | **BLOCK_6_shopping_list_api.py** | 4 個 router、13 個端點 | ⭐⭐⭐ |
| 6️⃣ | **BLOCK_6_seed_data.py** | 測試種子資料 | ⭐⭐☆ |
| 7️⃣ | **BLOCK_6_test_db.py** | 獨立測試用資料庫連線 | ⭐☆☆ |
| 8️⃣ | **main.py** | 真實資料庫版測試伺服器 | ⭐⭐☆ |
| 9️⃣ | **BLOCK_6_TEST_EXAMPLES.py** | 端對端測試腳本 | ⭐⭐☆ |

---

## 📂 文件詳細說明

### 1️⃣ BLOCK_6_models.py
**🗄️ SQLAlchemy ORM 模型**

- 本區塊擁有：`PurchaseLocation`（6a）、`IngredientLocationPreference`（6b）、`ShoppingList`（6c）、`ShoppingListItem`（6d）、`ShoppingListHistory`（6e）
- 唯讀參照（獨立測試用，正式整合要換掉）：`User`、`Recipe`、`RecipeIngredient`、`IngredientLibrary`、`IngredientStock`、`WeeklyMealPlan`、`DailyMealDetail`

**何時讀**：需要知道資料表欄位/關聯時

---

### 2️⃣ BLOCK_6_schemas.py
**📋 Pydantic 數據模型**

- 列舉：`ShoppingListStatus`、`CostLevel`、`MealPlanStatus`
- 請求模型：`ShoppingListItemCreate`、`ShoppingListItemUpdate`、`PurchaseLocationCreate`、`IngredientLocationPreferenceSet` 等
- 回應模型：`ShoppingListResponse`（含 `items_by_location` 分組結構）、`ConfirmMealPlanResponse` 等

**何時用**：定義 API 請求/回應時

---

### 3️⃣ BLOCK_6_shopping_service.py
**🧮 購物清單純計算邏輯**

不 import SQLAlchemy，只吃/吐 plain dict，方便單元測試：

```python
aggregate_ingredient_quantities()  # 跨 7 天 x 2 人的食材加總（依食譜基準份量比例換算）
determine_assigned_user()          # 單人專屬 vs 兩人共用
determine_cost_level()             # 多食譜取最高成本等級
determine_purchase_location()      # 結構化偏好 -> 文字備援 -> None
determine_needs_restocking()       # 庫存 - 所需量 < 閾值
build_shopping_list_items()        # 組裝成可寫入 DB 的 dict 列表
```

**何時用**：要改「怎麼合併食材/怎麼判斷成本/怎麼分配地點」這些規則時，只需要改這個檔案

---

### 4️⃣ BLOCK_6_db_service.py
**🔌 資料庫查詢與持久化**

```python
generate_shopping_list_for_plan()   # 從 plan_id 生成購物清單
confirm_plan_and_generate_list()    # 確認 + 生成（冪等）
get_shopping_list_detail()          # 按地點/分類分組讀取
add/update/delete_shopping_list_item()
mark_item_purchased()
update_shopping_list_status()       # 含歸檔快照寫入
list/create/update/delete_purchase_location()
get/set_ingredient_location_preferences()
```

**何時用**：實作/除錯 API endpoint 背後的 DB 邏輯時

---

### 5️⃣ BLOCK_6_shopping_list_api.py
**🎯 API Endpoints（4 個 router，13 個端點）**

```
router_meal_plans              POST /meal-plans/{plan_id}/confirm
router_shopping_lists          GET/POST/PUT/DELETE /shopping-lists/...（7 個端點）
router_purchase_locations      GET/POST/PUT/DELETE /purchase-locations/...
router_ingredient_preferences  GET/PUT /ingredients/{id}/location-preference
```

**何時用**：部署購物清單相關 API 時

---

### 6️⃣ BLOCK_6_seed_data.py
**🌱 測試種子資料**

灌入：2 位使用者、4 個購買地點、11 種食材（含 1 筆低庫存示範補貨警告）、2 筆結構化地點偏好、4 道食譜、1 個涵蓋 7 天 x 2 人（早/午/晚）的週計畫。`seed_if_empty()` 只在 `users` 表空的時候灌，可重複執行。

---

### 7️⃣～9️⃣ BLOCK_6_test_db.py / main.py / BLOCK_6_TEST_EXAMPLES.py
**🧪 獨立測試三件套**（比照區塊 5 的做法）

```bash
uvicorn main:app --reload --port 8126   # 啟動（建表+灌種子+掛路由）
python BLOCK_6_TEST_EXAMPLES.py          # 跑完整流程，斷言關鍵結果
```

---

## 🔀 模組依賴關係

```
BLOCK_6_shopping_service.py（純函式，最底層，無其他依賴）
    ↑
BLOCK_6_db_service.py（呼叫 shopping_service，做 DB 查詢/寫入）
    ↑
BLOCK_6_shopping_list_api.py（呼叫 db_service，回應 HTTP）
    ↑
main.py（掛載 4 個 router + 建表 + 灌種子）
```

---

## 🔍 按用途查找代碼

### 「我需要改食材合併/成本/地點分配的規則」
→ **BLOCK_6_shopping_service.py**

### 「我需要實作確認推薦 → 生成購物清單」
→ **BLOCK_6_shopping_list_api.py** - `confirm_meal_plan()`
→ **BLOCK_6_db_service.py** - `confirm_plan_and_generate_list()`

### 「我需要處理採購歷史歸檔」
→ **BLOCK_6_db_service.py** - `update_shopping_list_status()`

### 「我需要接上區塊 1/4/5 的正式資料表」
→ **BLOCK_6_INTEGRATION_GUIDE.md** - 「資料庫集成」章節

---

## ✅ 完成度檢查

- [x] 架構設計
- [x] 資料模型
- [x] 購物清單生成邏輯（含 2 人合併、成本、地點、補貨規則）
- [x] 購物清單 CRUD + 狀態機 + 採購歷史
- [x] 購買地點 / 食材地點偏好管理
- [x] API 設計
- [x] 端對端測試（真實 SQLite，全部通過）
- [x] 完整文檔

---

## 📞 文檔快速查閱

| 問題 | 查閱文檔 |
|------|--------|
| 「購物清單怎麼生成的？」 | ARCHITECTURE_DESIGN.md「核心演算法」 |
| 「怎麼接上正式資料庫？」 | INTEGRATION_GUIDE.md「資料庫集成」 |
| 「跟區塊 5 的 confirm 端點衝突怎麼辦？」 | INTEGRATION_GUIDE.md「步驟 C」 |
| 「API 怎麼用？」 | INTEGRATION_GUIDE.md「使用範例」 |

---

**區塊 6 生成完成！** 所有 14 份文件已準備好，端對端測試全部通過。
