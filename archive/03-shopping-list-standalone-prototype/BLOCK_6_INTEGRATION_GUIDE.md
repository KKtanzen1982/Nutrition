# 區塊 6 完整集成指南

**狀態**：✅ 所有代碼已生成，準備集成
**最後更新**：2026-08-11

---

## 📦 生成的文件列表

```
✅ BLOCK_6_models.py               # SQLAlchemy 模型
✅ BLOCK_6_schemas.py              # Pydantic 數據模型
✅ BLOCK_6_shopping_service.py     # 純計算邏輯
✅ BLOCK_6_db_service.py           # 資料庫查詢/持久化
✅ BLOCK_6_shopping_list_api.py    # API endpoints（4 個 router）
✅ BLOCK_6_seed_data.py            # 測試種子資料
✅ BLOCK_6_test_db.py              # 獨立測試用資料庫連線
✅ main.py                         # 測試伺服器
✅ BLOCK_6_TEST_EXAMPLES.py        # 端對端測試腳本
✅ BLOCK_6_INTEGRATION_GUIDE.md    # 本文檔
```

---

## 🔧 集成步驟

### 1️⃣ 環境準備

```bash
pip install -r requirements.txt
```

### 2️⃣ 導入和註冊路由

本區塊有 **4 個獨立的 router**（不是 1 個），全部要註冊：

```python
from fastapi import FastAPI
import BLOCK_6_shopping_list_api as shopping_list_api

app = FastAPI(title="營養管理系統")

app.dependency_overrides[shopping_list_api.get_db] = get_db  # 換成真正的 session

app.include_router(shopping_list_api.router_meal_plans)          # POST /meal-plans/{id}/confirm
app.include_router(shopping_list_api.router_shopping_lists)      # /shopping-lists/*
app.include_router(shopping_list_api.router_purchase_locations)  # /purchase-locations/*
app.include_router(shopping_list_api.router_ingredient_preferences)  # /ingredients/{id}/location-preference
```

### 3️⃣ 資料庫集成 —— 最重要的部分

本區塊在自己的獨立 Base 裡放了 **7 張唯讀參照表**（`User`, `Recipe`, `RecipeIngredient`, `IngredientLibrary`, `IngredientStock`, `WeeklyMealPlan`, `DailyMealDetail`），只是為了讓區塊 6 能夠獨立跑測試，**不是**本區塊擁有的資料表。正式整合時：

#### 步驟 A：把 `BLOCK_6_models.py` 拆成兩半

- **真正屬於區塊 6 的 5 張表**（`PurchaseLocation`, `IngredientLocationPreference`, `ShoppingList`, `ShoppingListItem`, `ShoppingListHistory`）→ 保留，併入你整合後的主 `models.py`
- **7 張唯讀參照表** → 刪除，改成 `from your_project.models import User, Recipe, RecipeIngredient, IngredientLibrary, IngredientStock, WeeklyMealPlan, DailyMealDetail`（分別對應區塊 1 的表 1、區塊 4 的表 5a/5b/5i/5e、區塊 5 的表 5f/5g）

#### 步驟 B：檢查欄位是否對得上

`BLOCK_6_db_service.py` 只用到唯讀參照表的以下欄位，整合時確認這些欄位在正式資料表裡都存在且型別相容：

| 表 | 用到的欄位 |
|---|---|
| `Recipe` | `id`, `base_weight_g`, `cost_level` |
| `RecipeIngredient` | `recipe_id`, `ingredient_id`, `quantity_g` |
| `IngredientLibrary` | `id`, `ingredient_name`, `category`, `unit`, `needs_stock_tracking`, `preferred_purchase_location` |
| `IngredientStock` | `ingredient_id`, `current_quantity_g`, `min_threshold_g` |
| `WeeklyMealPlan` | `id`, `plan_date`, `plan_status` |
| `DailyMealDetail` | `meal_plan_id`, `meal_date`, `recipe_id`, `assigned_user_id`, `serving_weight_g` |

架構文件裡 `ingredient_library` 表（表 5i）沒有 `cost_level` 欄位——本設計刻意改成從「食材出現的食譜」反推成本等級（取最高者），詳見 `BLOCK_6_ARCHITECTURE_DESIGN.md` 的「核心演算法」章節。如果區塊 4 之後幫食材本身加了 `cost_level` 欄位，記得回來調整 `determine_cost_level()` 的邏輯。

#### 步驟 C：處理與區塊 5 的端點衝突

區塊 5 的 `BLOCK_5_meal_plan_api.py` 已經掛了一個 `PUT /meal-plans/{plan_id}/confirm`（stub 版本，`shopping_list_id` 永遠是 `null`）。本區塊實作的是 `POST /meal-plans/{plan_id}/confirm`（跟架構文件的 API 設計章節一致）。

整合時二選一：
- **建議**：把區塊 5 router 裡的 `confirm_meal_plan` endpoint **刪掉**，只保留本區塊的 `POST` 版本（本區塊的版本才有真正生成購物清單）
- 或者：如果要保留 `PUT` 語意，把本區塊 `BLOCK_6_shopping_list_api.py` 裡 `router_meal_plans` 的 `@router_meal_plans.post(...)` 改成 `@router_meal_plans.put(...)`，並確認不會跟區塊 5 的路由同時註冊到同一個 app（否則後註冊的會覆蓋前者，行為變成不可預期）

### 4️⃣ 資料庫遷移

把以下 5 張表的 DDL 併入你的主 schema（架構文件已有完整定義，見 `nutrition_system_architecture_1.md` 表 6a~6e）：

```sql
CREATE TABLE purchase_locations (...);
CREATE TABLE ingredient_location_preference (...);
CREATE TABLE shopping_list (...);
CREATE TABLE shopping_list_items (...);
CREATE TABLE shopping_list_history (...);
```

---

## 📖 使用範例（curl）

```bash
# 1. 確認推薦，生成購物清單
curl -X POST http://localhost:8000/meal-plans/1/confirm

# 2. 取得購物清單
curl http://localhost:8000/shopping-lists/1

# 3. 新增臨時食材
curl -X POST http://localhost:8000/shopping-lists/1/items \
  -H "Content-Type: application/json" \
  -d '{"ingredient_id": 3, "quantity_needed_g": 300, "notes": "臨時想加購"}'

# 4. 標記已購
curl -X PUT http://localhost:8000/shopping-lists/1/items/12/purchased \
  -H "Content-Type: application/json" \
  -d '{"is_purchased": true}'

# 5. 歸檔（自動寫入採購歷史）
curl -X PUT http://localhost:8000/shopping-lists/1/status \
  -H "Content-Type: application/json" \
  -d '{"status": "歸檔"}'

# 6. 設定食材地點偏好
curl -X PUT http://localhost:8000/ingredients/5/location-preference \
  -H "Content-Type: application/json" \
  -d '{"preferences": [{"preferred_location_id": 2, "priority": 1, "notes": "傳統市場比較新鮮"}]}'
```

---

## 🐛 常見集成問題和解決方案

### Q1:「ImportError: cannot import name 'XXX'」
**解決**：確認所有 `BLOCK_6_*.py` 檔案都在同一目錄；本區塊全部用絕對 import（`from BLOCK_6_xxx import ...`），不是套件相對 import。

### Q2:「兩個 router 都掛了 /meal-plans/{plan_id}/confirm，行為怪怪的」
**解決**：見上方「步驟 C」，同時掛區塊 5 和區塊 6 的 confirm 端點會衝突，要移除其中一個。

### Q3:「購物清單生成後，某個食材的地點是 null」
**解決**：正常情況——代表這個食材既沒有在 `ingredient_location_preference` 設定過偏好，`ingredient_library.preferred_purchase_location` 文字欄位也對不上任何 `purchase_locations.location_name`。UI 應該讓用戶手動指定，或者去補上偏好設定。

### Q4:「needs_restocking 一直是 true，但我明明有進貨」
**解決**：檢查 `ingredient_stock` 是否有該食材的紀錄。沒有紀錄時本設計會視同「目前庫存 = 0」（保守預設），詳見架構文件。

### Q5:「重複呼叫 confirm，購物清單內容沒有更新」
**解決**：這是設計行為（冪等）——`confirm_plan_and_generate_list()` 偵測到該 `plan_id` 已有購物清單就直接回傳既有 ID，不會重新計算。如果週計畫在確認後又被微調（區塊 5 的方案 A/B/C/D），需要重新生成清單，目前沒有對外的「強制重新生成」端點，可以直接呼叫 `BLOCK_6_db_service.generate_shopping_list_for_plan()` 並自行處理舊清單。

---

## ✅ 集成檢查清單

- [ ] 5 張本區塊擁有的表已併入主 schema 並執行 migration
- [ ] 7 張唯讀參照表已換成區塊 1/4/5 的正式模型（`import` 路徑已更新）
- [ ] 唯讀參照表的欄位名稱/型別跟正式資料表對得上（見「步驟 B」表格）
- [ ] 區塊 5 與區塊 6 的 `confirm` 端點衝突已處理（保留其中一個）
- [ ] 4 個 router 都已 `include_router`
- [ ] `get_db` 依賴已換成連到正式資料庫的 session
- [ ] 用 `BLOCK_6_TEST_EXAMPLES.py`（改指向正式伺服器的 URL）重跑一次端對端測試
