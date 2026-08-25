# BLOCK_4 - 食譜和食材管理 集成指南

## 📋 文件清單

區塊 4 包含 4 個核心文件：

1. **BLOCK_4_models.py** - SQLAlchemy ORM 模型（7 個表）
2. **BLOCK_4_schemas.py** - Pydantic 驗證和序列化 schemas
3. **BLOCK_4_services.py** - 業務邏輯層
4. **BLOCK_4_routes.py** - FastAPI 路由（21 個 endpoints）

---

## 🔧 集成步驟

### 1. 將模型加入資料庫初始化

**在區塊 1 的 `database.py` 中**：

```python
from BLOCK_4_models import (
    Recipe, RecipeIngredient, RecipeStep, RecipeNutrition,
    IngredientLibrary, IngredientStock,
    PurchaseLocation, IngredientLocationPreference
)

# 在創建表時
Base.metadata.create_all(bind=engine)
```

### 2. 在主應用中注冊路由

**在 `app_main.py` 或 `main.py` 中**：

```python
from fastapi import FastAPI
from BLOCK_4_routes import router as block4_router

app = FastAPI()

# 註冊區塊 4 路由
app.include_router(block4_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 3. 確保資料庫依賴正確

**修改 routes 中的依賴**（第 29 行附近）：

```python
# 舊版本（佔位符）
db: Session = Depends(lambda: None)

# 改為（來自區塊 2）
from BLOCK_2_database import get_db
db: Session = Depends(get_db)
```

---

## 📊 API 端點總覽

### 食材管理（8 個端點）

| 方法 | 端點 | 功能 |
|------|------|------|
| POST | `/api/ingredients` | 建立食材 |
| GET | `/api/ingredients/{id}` | 取得食材詳情 |
| PUT | `/api/ingredients/{id}` | 更新食材 |
| GET | `/api/ingredients` | 列表食材（分頁） |
| GET | `/api/ingredients/search` | 搜尋食材（按名稱） |
| GET | `/api/ingredients/low-stock` | 取得低庫存食材 |
| GET | `/api/ingredients/{id}/stock` | 取得庫存 |
| PUT | `/api/ingredients/{id}/stock` | 更新庫存 |

### 食譜管理（8 個端點）

| 方法 | 端點 | 功能 |
|------|------|------|
| POST | `/api/recipes` | 建立食譜 |
| GET | `/api/recipes/{id}` | 取得食譜詳情 |
| PUT | `/api/recipes/{id}` | 更新食譜 |
| DELETE | `/api/recipes/{id}` | 軟刪除食譜 |
| GET | `/api/recipes` | 列表食譜（分頁） |
| GET | `/api/recipes/search` | 搜尋食譜 |
| GET | `/api/recipes/{id}/nutrition` | 取得營養素 |
| POST | `/api/recipes/{id}/calculate-nutrition` | 手動計算營養素 |

### 食譜步驟版本控制（3 個端點）

| 方法 | 端點 | 功能 |
|------|------|------|
| GET | `/api/recipes/{id}/steps` | 取得步驟（可指定版本） |
| POST | `/api/recipes/{id}/steps` | 新增步驟新版本 |
| PUT | `/api/recipes/{id}/steps/{version}/set-current` | 設定某版本為當前 |

### 購買地點管理（5 個端點）

| 方法 | 端點 | 功能 |
|------|------|------|
| POST | `/api/purchase-locations` | 建立購買地點 |
| GET | `/api/purchase-locations/{id}` | 取得購買地點 |
| GET | `/api/purchase-locations` | 列表所有購買地點 |
| PUT | `/api/purchase-locations/{id}` | 更新購買地點 |
| DELETE | `/api/purchase-locations/{id}` | 軟刪除購買地點 |

### 健康檢查（1 個端點）

| 方法 | 端點 | 功能 |
|------|------|------|
| GET | `/api/health/block4` | 區塊 4 狀態檢查 |

---

## 🚀 使用範例

### 1. 建立食材（含庫存追蹤）

**請求**：
```bash
curl -X POST http://localhost:8000/api/ingredients \
  -H "Content-Type: application/json" \
  -d '{
    "ingredient_name": "雞胸肉",
    "category": "肉類",
    "unit": "g",
    "calories_per_100g": 165.0,
    "protein_per_100g": 31.0,
    "carbs_per_100g": 0.0,
    "fat_per_100g": 3.6,
    "fiber_per_100g": 0.0,
    "needs_stock_tracking": true
  }'
```

**回應**：
```json
{
  "id": 1,
  "ingredient_name": "雞胸肉",
  "category": "肉類",
  "unit": "g",
  "calories_per_100g": 165.0,
  "protein_per_100g": 31.0,
  "carbs_per_100g": 0.0,
  "fat_per_100g": 3.6,
  "fiber_per_100g": 0.0,
  "needs_stock_tracking": true,
  "created_at": "2024-08-06T10:00:00",
  "stock": {
    "id": 1,
    "ingredient_id": 1,
    "current_quantity_g": 0.0,
    "min_threshold_g": null,
    "unit": "g",
    "last_purchased_at": null,
    "notes": null
  }
}
```

### 2. 建立食譜（含食材和步驟）

**請求**：
```bash
curl -X POST http://localhost:8000/api/recipes \
  -H "Content-Type: application/json" \
  -d '{
    "recipe_name": "番茄雞肉義大利麵",
    "category": "主食",
    "base_weight_g": 400,
    "cost_level": "低",
    "ingredients": [
      {
        "ingredient_id": 1,
        "quantity_g": 150,
        "unit": "g",
        "notes": "切成小塊"
      },
      {
        "ingredient_id": 2,
        "quantity_g": 200,
        "unit": "g",
        "notes": "新鮮番茄"
      },
      {
        "ingredient_id": 3,
        "quantity_g": 80,
        "unit": "g",
        "notes": "未煮"
      }
    ],
    "steps": [
      {
        "step_number": 1,
        "step_description": "將義大利麵煮至 al dente（約 8-10 分鐘）"
      },
      {
        "step_number": 2,
        "step_description": "雞胸肉切塊，用橄欖油快炒至半熟"
      },
      {
        "step_number": 3,
        "step_description": "加入新鮮番茄塊，炒 2-3 分鐘"
      },
      {
        "step_number": 4,
        "step_description": "將煮好的麵加入，混合均勻即可盛盤"
      }
    ]
  }'
```

**回應**：
```json
{
  "id": 1,
  "recipe_name": "番茄雞肉義大利麵",
  "category": "主食",
  "base_weight_g": 400,
  "cost_level": "低",
  "is_active": true,
  "created_at": "2024-08-06T10:05:00",
  "last_updated_at": "2024-08-06T10:05:00",
  "ingredients": [...],
  "steps": [...],
  "nutrition": {
    "id": 1,
    "recipe_id": 1,
    "total_calories_kcal": 520.5,
    "protein_g": 42.3,
    "carbs_g": 48.0,
    "fat_g": 12.8,
    "fiber_g": 2.4,
    "calculated_at": "2024-08-06T10:05:00"
  }
}
```

### 3. 搜尋食譜（按食材）

**請求**：
```bash
curl "http://localhost:8000/api/recipes/search?query=番茄&search_by=ingredient"
```

**回應**：
```json
[
  {
    "id": 1,
    "recipe_name": "番茄雞肉義大利麵",
    "category": "主食",
    "base_weight_g": 400,
    "cost_level": "低",
    "total_calories_kcal": 520.5,
    "protein_g": 42.3,
    "carbs_g": 48.0,
    "fat_g": 12.8
  }
]
```

### 4. 更新食材營養素（自動觸發食譜重新計算）

**請求**：
```bash
curl -X PUT http://localhost:8000/api/ingredients/1 \
  -H "Content-Type: application/json" \
  -d '{
    "protein_per_100g": 32.0
  }'
```

**效果**：
- 雞胸肉的蛋白質更新為 32g/100g
- **自動**觸發所有使用雞胸肉的食譜的營養素重新計算
- 例如「番茄雞肉義大利麵」的蛋白質會自動更新

### 5. 新增食譜步驟新版本

**請求**：
```bash
curl -X POST http://localhost:8000/api/recipes/1/steps \
  -H "Content-Type: application/json" \
  -d '[
    {
      "step_number": 1,
      "step_description": "將義大利麵煮至 al dente（約 9-11 分鐘）"
    },
    {
      "step_number": 2,
      "step_description": "雞胸肉切塊，用橄欖油快炒至全熟"
    },
    {
      "step_number": 3,
      "step_description": "加入新鮮番茄塊和蒜末，炒 3 分鐘"
    },
    {
      "step_number": 4,
      "step_description": "將煮好的麵加入，混合均勻，加鹽調味"
    }
  ]'
```

**回應**：
```json
{
  "success": true,
  "recipe_id": 1,
  "new_version": 2
}
```

### 6. 取得低庫存食材

**請求**：
```bash
curl http://localhost:8000/api/ingredients/low-stock
```

**回應**：
```json
[
  {
    "ingredient_id": 1,
    "ingredient_name": "雞胸肉",
    "category": "肉類",
    "current_quantity_g": 50.0,
    "min_threshold_g": 200.0,
    "unit": "g",
    "last_purchased_at": "2024-08-01",
    "deficit_g": 150.0
  }
]
```

---

## 🔄 業務流程集成

### 場景 1：新增食材和庫存

```
1. 使用者輸入食材資訊
   ↓
2. API: POST /api/ingredients
   ↓
3. IngredientService.create_ingredient()
   - 建立食材記錄
   - 如果 needs_stock_tracking=true，建立庫存記錄
   ↓
4. 返回食材詳情（含庫存）
```

### 場景 2：建立食譜並自動計算營養素

```
1. 使用者輸入食譜資訊（食材、步驟）
   ↓
2. API: POST /api/recipes
   ↓
3. RecipeService.create_recipe()
   - 建立食譜記錄
   - 新增食材清單
   - 新增步驟（版本 1）
   - 調用 RecipeService.calculate_nutrition()
   ↓
4. 返回食譜詳情（含自動計算的營養素）
```

### 場景 3：更新食材營養素並級聯重新計算

```
1. 使用者更新食材營養素（如蛋白質）
   ↓
2. API: PUT /api/ingredients/{id}
   ↓
3. IngredientService.update_ingredient()
   - 更新食材資訊
   - 檢測到營養素有改變
   ↓
4. RecipeService.recalculate_recipes_using_ingredient()
   - 查詢所有使用該食材的食譜
   - 逐一調用 calculate_nutrition()
   ↓
5. 所有相關食譜營養素自動更新
```

### 場景 4：搜尋食譜（含過敏原篩選）

```
1. 使用者搜尋 "番茄"，排除過敏原 ID=5,6
   ↓
2. API: GET /api/recipes/search?query=番茄&exclude_allergen_ids=5,6
   ↓
3. RecipeService.search_recipes()
   - 按食材名稱搜尋
   - 排除包含 ID=5,6 食材的食譜
   ↓
4. 返回符合條件的食譜列表
```

---

## 🧪 測試檢查清單

### 食材管理測試

- [ ] 建立食材（無庫存追蹤）
- [ ] 建立食材（啟用庫存追蹤）
- [ ] 更新食材基本資訊
- [ ] 更新食材營養素（驗證級聯重新計算）
- [ ] 搜尋食材（按名稱）
- [ ] 列表食材（按分類篩選）
- [ ] 更新庫存數量
- [ ] 取得低庫存食材列表

### 食譜管理測試

- [ ] 建立食譜（含食材和步驟）
- [ ] 驗證營養素自動計算
- [ ] 更新食譜基本資訊
- [ ] 軟刪除食譜（驗證 is_active 標記）
- [ ] 搜尋食譜（按名稱、食材、分類）
- [ ] 搜尋食譜（過敏原篩選）
- [ ] 取得營養素資訊
- [ ] 列表食譜（按成本篩選）

### 步驟版本控制測試

- [ ] 取得最新版本步驟（version=None）
- [ ] 取得特定版本步驟
- [ ] 新增步驟新版本（驗證版本號遞增）
- [ ] 驗證新版本自動標記為當前版本
- [ ] 設定舊版本為當前版本

### 購買地點管理測試

- [ ] 建立購買地點
- [ ] 列表所有購買地點（按優先順序排序）
- [ ] 更新購買地點
- [ ] 軟刪除購買地點

---

## ⚠️ 重要設計決策回顧

### 1. 軟刪除（is_active=false）

**為什麼**：
- 保留歷史數據完整性（週推薦和購物清單的外鍵不會斷裂）
- 用戶可復原誤刪的食譜
- 審計和數據追蹤

**影響**：
- 所有 GET / LIST 查詢需過濾 `is_active=true`（除非明確要求）
- DELETE 端點實現為軟刪除而非物理刪除

### 2. 營養素即時計算

**為什麼**：
- 新增食材或編輯食材營養素時立即計算
- 保證推薦引擎始終使用最新營養素數據
- 級聯更新所有受影響的食譜

**影響**：
- 食材更新可能較慢（需遍歷所有相關食譜）
- 計算邏輯需處理 NULL 值（部分食材可能缺少營養素）

### 3. 用戶自訂庫存追蹤

**為什麼**：
- 調味料等不需要追蹤
- 靈活適應不同用戶需求
- 減少無謂的數據記錄

**影響**：
- `ingredient_stock` 表可能有稀疏記錄
- 低庫存查詢需 LEFT JOIN 並檢查 NULL

### 4. 食譜版本控制

**為什麼**：
- 允許多個步驟版本共存
- 只標記一個版本為「當前」

**影響**：
- 取得步驟時需指定版本或預設取當前版本
- 舊版本保留供歷史查閱

---

## 📝 後續開發（區塊 5、6、7）

### 區塊 5（推薦引擎）依賴
- ✅ 食譜搜尋、篩選、營養素
- ✅ 食材過敏原篩選
- ✅ 庫存和低庫存查詢

### 區塊 6（購物清單）依賴
- ✅ 購買地點管理
- ✅ 食材庫存追蹤
- ✅ 食譜和食材關聯

### 區塊 7（前端）UI 組件
- 食材搜尋和編輯
- 食譜瀏覽、搜尋、建立
- 庫存管理儀表板
- 營養素可視化

---

## 📞 常見問題

**Q: 如何在編輯食材營養素後不觸發級聯重新計算？**  
A: 目前每次營養素更新都會自動級聯。如需控制，可在 `IngredientService.update_ingredient()` 中添加 `cascade_recalculate` 參數。

**Q: 刪除的食譜是否可恢復？**  
A: 是的，軟刪除只是標記 `is_active=false`，可通過 `UPDATE` 恢復。

**Q: 能否批量導入食譜和食材？**  
A: 本區塊未實現批量 API，建議在區塊 7 (設定頁) 或區塊 1 (初始化腳本) 中添加。

**Q: 營養素計算支援自訂單位轉換嗎？**  
A: 目前假設 `quantity_g` 為克，如需支援其他單位，需擴展 `calculate_nutrition()` 邏輯。

---

**版本**: 1.0  
**更新**: 2024-08-06  
**狀態**: ✅ 準備集成
