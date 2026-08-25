# 區塊 6：購物清單管理 - 完整架構設計文檔

**設計日期**：2026-08-11
**依賴**：區塊 1（資料庫）、區塊 2（用戶）、區塊 4（食譜/食材）、區塊 5（Claude 推薦引擎）
**後續依賴**：無（區塊 7 前端會呼叫本區塊的 API）
**對應資料表**：表 6a（purchase_locations）、6b（ingredient_location_preference）、6c（shopping_list）、6d（shopping_list_items）、6e（shopping_list_history）

---

## 📋 目錄

1. [模組定位](#模組定位)
2. [資料模型](#資料模型)
3. [核心演算法：購物清單生成](#核心演算法購物清單生成)
4. [API 設計](#api-設計)
5. [狀態機](#狀態機)
6. [程式碼組織](#程式碼組織)

---

## 模組定位

架構總文件（`nutrition_system_architecture_1.md`）把「確認推薦 → 生成購物清單」畫在週推薦流程的第 6～8 步。實際切分成兩個區塊：

- **區塊 5** 負責「推薦」與「微調」，其 `PUT /meal-plans/{id}/confirm` 端點目前只把 `plan_status` 改成「已確認」，`shopping_list_id` 回傳 `null`，並在程式碼註解寫明購物清單生成留給區塊 6。
- **區塊 6（本區塊）** 接手「確認 → 生成購物清單」這一段，並把整個購物清單的 CRUD、狀態轉換、採購歷史都做完。

依使用者確認的方向，本區塊：
1. 自己實作 `POST /meal-plans/{plan_id}/confirm`（取代區塊 5 的 stub 版本，見 [BLOCK_6_INTEGRATION_GUIDE.md](BLOCK_6_INTEGRATION_GUIDE.md)）。
2. 對「食譜食材明細」(recipe_ingredients) 和「食材庫」(ingredient_library) 只寫查詢邏輯，不宣稱擁有這兩張表——它們的正式定義屬於區塊 1/4。本區塊為了能獨立測試，在自己的 Base 裡放了這兩張表的唯讀簡化版（做法比照區塊 5 對 `User`/`Recipe` 的處理）。

---

## 資料模型

`BLOCK_6_models.py` 用自己的 `declarative_base()`，分成兩類：

### 本區塊真正擁有（DDL 所有權）

| 表 | 對應架構表號 | 說明 |
|---|---|---|
| `PurchaseLocation` | 6a | 購買地點庫 |
| `IngredientLocationPreference` | 6b | 食材地點偏好（`priority` 1~3） |
| `ShoppingList` | 6c | 購物清單主表 |
| `ShoppingListItem` | 6d | 購物項目明細 |
| `ShoppingListHistory` | 6e | 採購歷史（歸檔快照） |

### 唯讀參照（借用其他區塊的表結構簡化版，僅供獨立測試查詢）

| 表 | 對應架構表號 | 借用自 |
|---|---|---|
| `User` | 表 1 | 區塊 2 |
| `Recipe` | 表 5a | 區塊 4 |
| `RecipeIngredient` | 表 5b | 區塊 4 |
| `IngredientLibrary` | 表 5i | 區塊 4 |
| `IngredientStock` | 表 5e | 區塊 4 |
| `WeeklyMealPlan` | 表 5f | 區塊 5 |
| `DailyMealDetail` | 表 5g | 區塊 5 |

正式整合時，這 7 張唯讀參照表要換成區塊 1/4/5 實際建立的資料表（詳見整合指南）。

---

## 核心演算法：購物清單生成

架構文件只列了要點（「2 人食材合併計算」「按購買地點分類」「需補購標記」），沒有寫死規則細節。以下是本區塊補的實作決策，全部實作在 `BLOCK_6_shopping_service.py`（純函式、不碰 DB，方便單元測試），由 `BLOCK_6_db_service.py` 負責把 ORM 查詢結果轉成純函式要的格式：

### 1. 食材加總（`aggregate_ingredient_quantities`）

```
for 每一筆 daily_meal_detail（該週計畫的所有餐次，跨 7 天、跨 A/B 兩人）:
    scale = serving_weight_g / recipe.base_weight_g
    for 該食譜的每個食材:
        該食材總量 += 食譜食材明細.quantity_g * scale
```

即：以食譜的「基準份量」(`base_weight_g`) 為基準，依實際供餐重量 (`serving_weight_g`) 等比例縮放，跨兩人、跨 7 天加總。

### 2. 成本等級（`determine_cost_level`）

同一個食材可能出現在多道成本等級不同的食譜裡。規則：**取最高者**（低 < 中 < 高），理由是購物預算抓保守值比抓樂觀值安全，避免低估總成本。

### 3. 使用者標記（`determine_assigned_user`）

- 食材只出現在單一使用者（A 或 B）的餐點 → `assigned_user_id` 標記該人
- 食材同時出現在兩人餐點（或查無使用者）→ `assigned_user_id = null`（兩人共用）

### 4. 購買地點分配（`determine_purchase_location`）

優先序：
1. `ingredient_location_preference` 表中 `priority` 最小（=最優先）的那筆
2. 查無結構化偏好 → 退回 `ingredient_library.preferred_purchase_location` 文字欄位，去 `purchase_locations.location_name` 做字串比對
3. 都沒有 → `purchase_location_id = null`（未指定地點，UI 應提示用戶手動指定）

### 5. 補貨警告（`determine_needs_restocking`）

```
if not ingredient.needs_stock_tracking:
    return False
剩餘庫存 = 目前庫存 - 本週所需量
return 剩餘庫存 < 最低閾值
```

食材沒有庫存紀錄時，`目前庫存` 視為 0——也就是「沒登記庫存 = 視同缺貨」，是刻意的保守預設，而不是遺漏。

---

## API 設計

### 確認推薦（取代區塊 5 的 stub）

```
POST /meal-plans/{plan_id}/confirm
  功能：週計畫狀態改為「已確認」，並生成購物清單
  回應：{ success, plan_id, shopping_list_id, message }
  冪等：同一個 plan_id 重複確認，回傳既有的 shopping_list_id，不會重複生成
```

### 購物清單

```
GET    /shopping-lists/{list_id}
  回應：{ list_id, status, ..., items_by_location: { 地點名: [ { category, items: [...] } ] } }

POST   /shopping-lists/{list_id}/items         新增項目（臨時食材）
PUT    /shopping-lists/{list_id}/items/{id}    編輯項目（用量/地點/備註）
DELETE /shopping-lists/{list_id}/items/{id}    刪除項目
PUT    /shopping-lists/{list_id}/items/{id}/purchased   標記已購
PUT    /shopping-lists/{list_id}/status                 變更清單狀態

GET    /shopping-lists/history   採購歷史（分頁）
```

### 購買地點 / 食材地點偏好

```
GET/POST    /purchase-locations
PUT/DELETE  /purchase-locations/{id}

GET/PUT     /ingredients/{ingredient_id}/location-preference   整批覆蓋該食材的地點偏好
```

完整請求/回應欄位見 `BLOCK_6_schemas.py`；路由實作見 `BLOCK_6_shopping_list_api.py`。

---

## 狀態機

`shopping_list.status` 的合法值與轉換：

```
草稿 → 已確認 → 採購中 → 已採購 → 歸檔
```

目前實作不強制檢查轉換順序（例如允許從「草稿」直接跳到「歸檔」），只驗證目標狀態是合法值。轉成「歸檔」時，`update_shopping_list_status()` 會自動：
1. 把清單當下所有項目的快照（食材、用量、是否已購）序列化成 JSON，寫入 `shopping_list_history.item_changes`
2. 把這次的狀態轉換記錄（from/to/時間）寫入 `status_log`

---

## 程式碼組織

```
BLOCK_6_models.py              # SQLAlchemy 模型（本區塊擁有 5 張表 + 7 張唯讀參照）
BLOCK_6_schemas.py              # Pydantic 請求/回應模型
BLOCK_6_shopping_service.py     # 純計算邏輯（加總/成本/地點/補貨判斷），不碰 DB
BLOCK_6_db_service.py           # SQLAlchemy 查詢與持久化，呼叫 shopping_service 的純函式
BLOCK_6_shopping_list_api.py    # FastAPI router（4 個 router：confirm / shopping-lists / purchase-locations / ingredient-preferences）
BLOCK_6_seed_data.py            # 測試種子資料（含一組可端到端測試的週計畫）
BLOCK_6_test_db.py              # 獨立測試用 SQLite 連線
main.py                         # 真實資料庫版測試伺服器（建表 + 灌種子 + 掛路由）
BLOCK_6_TEST_EXAMPLES.py        # 端對端測試腳本
```

依賴方向：`shopping_list_api` → `db_service` → `shopping_service`（純函式，最底層，無其他依賴）。
