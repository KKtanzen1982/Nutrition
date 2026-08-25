# 區塊 5 完整集成指南

**狀態**：✅ 所有代碼已生成，準備集成  
**最後更新**：2024-08-06

---

## 📦 生成的文件列表

```
✅ BLOCK_5_schemas.py                  # Pydantic 數據模型
✅ BLOCK_5_prompts.py                  # Claude Prompt 模板
✅ BLOCK_5_recommendation_service.py   # 熱量計算、篩選、Claude 調用
✅ BLOCK_5_adjustment_service.py       # 微調邏輯（A/B/C/D）
✅ BLOCK_5_meal_plan_api.py            # 推薦 API endpoints
✅ BLOCK_5_adjustment_api.py           # 微調 API endpoints
✅ BLOCK_5_INTEGRATION_GUIDE.md        # 本文檔
```

---

## 🔧 集成步驟

### 1️⃣ 環境準備

```bash
# 1. 確保所有依賴已安裝
pip install anthropic fastapi sqlalchemy pydantic python-dotenv

# 2. 設置 Claude API 金鑰
export ANTHROPIC_API_KEY="sk-ant-..."
```

### 2️⃣ 導入和註冊路由

在你的 **main.py** 或 **app.py** 中：

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 導入區塊 5 的 routers
from BLOCK_5_meal_plan_api import router as meal_plan_router
from BLOCK_5_adjustment_api import router as adjustment_router

# 初始化 FastAPI 應用
app = FastAPI(
    title="營養管理系統",
    version="1.0.0",
    description="2 人飲食管理和 AI 推薦系統"
)

# 添加 CORS 中間件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 註冊路由
app.include_router(meal_plan_router)
app.include_router(adjustment_router)

# 健康檢查
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 3️⃣ 數據庫集成

區塊 5 代碼中有多個 `TODO: 從數據庫取得` 的地方。你需要根據 **BLOCK_1** 的數據庫結構來填充：

#### 在 `BLOCK_5_meal_plan_api.py` 中

```python
# 找到以下部分，填入真實的數據庫查詢

# ========== 第 1 步：取得用戶數據 ==========
# 替換為：
from sqlalchemy.orm import Session
from block_1_models import User, WeightRecord

user_a = db.query(User).filter(User.id == request.user_a_id).first()
if not user_a:
    raise HTTPException(status_code=404, detail="用戶 A 不存在")

# 取得最新體重
latest_weight_a = db.query(WeightRecord).filter(
    WeightRecord.user_id == request.user_a_id
).order_by(WeightRecord.date.desc()).first()

user_a_data = {
    "id": user_a.id,
    "name": user_a.name,
    "gender": user_a.gender,
    "age": user_a.age,
    "height_cm": user_a.height_cm,
    "weight_kg": latest_weight_a.weight_kg if latest_weight_a else 60,
    # ... 其他字段
}
```

#### 在 `BLOCK_5_meal_plan_api.py` 中

```python
# ========== 第 2 步：取得本週運動數據 ==========
# 替換為：
from block_1_models import ExerciseSession
from datetime import timedelta

week_end = request.week_start_date + timedelta(days=6)

# 查詢本週的運動
exercises_a = db.query(ExerciseSession).filter(
    ExerciseSession.user_id == request.user_a_id,
    ExerciseSession.date >= request.week_start_date,
    ExerciseSession.date <= week_end
).all()

exercise_data_a = {
    "gym_sessions": len([e for e in exercises_a if e.exercise_type == "健身房"]),
    "walking_steps_total": sum([
        ws.steps for ws in db.query(DailySteps).filter(
            DailySteps.user_id == request.user_a_id,
            DailySteps.date >= request.week_start_date,
            DailySteps.date <= week_end
        ).all()
    ]) or 0,
    "yoga_sessions": len([e for e in exercises_a if e.exercise_type == "瑜珈"])
}
```

#### 在 `BLOCK_5_meal_plan_api.py` 中

```python
# ========== 第 3 步：取得所有食譜 ==========
# 替換為：
from block_4_models import Recipe, RecipeNutrition

all_recipes = []
recipes = db.query(Recipe).filter(Recipe.is_active == True).all()

for recipe in recipes:
    nutrition = db.query(RecipeNutrition).filter(
        RecipeNutrition.recipe_id == recipe.id
    ).first()
    
    all_recipes.append({
        "id": recipe.id,
        "name": recipe.recipe_name,
        "category": recipe.category,
        "base_weight_g": recipe.base_weight_g,
        "cost_level": recipe.cost_level,
        "calories": nutrition.total_calories_kcal if nutrition else 0,
        "protein_g": nutrition.protein_g if nutrition else 0,
        # ... 其他字段
    })
```

#### 在 `BLOCK_5_meal_plan_api.py` 中（第 8 步）

```python
# ========== 第 8 步：存入數據庫 ==========
# 替換為：
from block_5_models import WeeklyMealPlan, DailyMealDetail

# 存入週計畫主表
plan_record = WeeklyMealPlan(
    plan_date=request.week_start_date,
    user_id_a=request.user_a_id,
    user_id_b=request.user_b_id,
    calorie_calculation_method=request.calorie_calculation_method.value,
    user_a_daily_calories_target=int(recommendation_data["user_a"]["daily_calories_target"]),
    user_b_daily_calories_target=int(recommendation_data["user_b"]["daily_calories_target"]),
    user_a_menstrual_phase=calculate_menstrual_phase(user_a, request.week_start_date),
    user_b_menstrual_phase=calculate_menstrual_phase(user_b, request.week_start_date),
    status="draft",
    claude_generated=True,
    recommendation_notes=recommendation.get("analysis_notes", "")
)
db.add(plan_record)
db.flush()  # 取得 ID
plan_id = plan_record.id

# 存入每日菜色詳情
for meal in meal_plan["meals"]:
    meal_detail = DailyMealDetail(
        meal_plan_id=plan_id,
        meal_date=meal.get("meal_date"),
        meal_type=meal.get("meal_type"),
        recipe_id=meal.get("recipe_id"),
        assigned_user_id=meal.get("user_id"),
        serving_weight_g=meal.get("serving_weight_g"),
        total_calories=meal.get("calories"),
        protein_g=meal.get("protein_g"),
        carbs_g=meal.get("carbs_g"),
        fat_g=meal.get("fat_g")
    )
    db.add(meal_detail)

db.commit()
```

---

## 📝 使用範例

### 示例 1：生成週推薦

```bash
curl -X POST http://localhost:8000/meal-plans/generate \
  -H "Content-Type: application/json" \
  -d '{
    "week_start_date": "2024-08-12",
    "user_a_id": 1,
    "user_b_id": 2,
    "calorie_calculation_method": "harris_benedict",
    "user_a_preselected": [
      {
        "day": "Monday",
        "meal_type": "lunch",
        "recipe_id": 10
      }
    ],
    "user_b_preselected": []
  }'

# 回應
{
  "success": true,
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "推薦任務已啟動，請輪詢查詢狀態"
}
```

### 示例 2：輪詢任務狀態

```bash
curl http://localhost:8000/meal-plans/jobs/550e8400-e29b-41d4-a716-446655440000/status

# 回應（處理中）
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "plan_id": null,
  "error_message": null,
  "created_at": "2024-08-06T10:00:00",
  "started_at": "2024-08-06T10:01:00",
  "completed_at": null
}

# 回應（完成）
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "plan_id": 1,
  "error_message": null,
  "created_at": "2024-08-06T10:00:00",
  "started_at": "2024-08-06T10:01:00",
  "completed_at": "2024-08-06T10:05:30"
}
```

### 示例 3：取得週推薦詳情

```bash
curl http://localhost:8000/meal-plans/1

# 回應：完整的週菜單 + 營養統計
```

### 示例 4：方案 A - 替換單菜色

```bash
curl -X POST http://localhost:8000/meal-plans/1/adjust/replace-meal \
  -H "Content-Type: application/json" \
  -d '{
    "meal_date": "2024-08-12",
    "meal_type": "lunch",
    "user_id": 1,
    "new_recipe_id": 15,
    "reason": "用戶想吃不同的菜"
  }'

# 回應
{
  "success": true,
  "updated_meal": {
    "meal_date": "2024-08-12",
    "meal_type": "lunch",
    "user_id": 1,
    "recipe_id": 15,
    "recipe_name": "番茄雞肉義大利麵",
    "serving_weight_g": 300,
    "calories": 450,
    "protein_g": 35,
    "carbs_g": 45,
    "fat_g": 12
  },
  "adjustment_recorded": true,
  "message": "菜色替換成功"
}
```

### 示例 5：方案 B - 重推整天

```bash
curl -X POST http://localhost:8000/meal-plans/1/adjust/regenerate-day \
  -H "Content-Type: application/json" \
  -d '{
    "meal_date": "2024-08-12",
    "fixed_meals": [
      {
        "meal_type": "breakfast",
        "user_id": 1,
        "recipe_id": 5
      }
    ]
  }'

# 回應
{
  "success": true,
  "job_id": "a7c9d8e2-1f42-4b89-8c5d-6e3a2b1f9d04",
  "message": "整天重推任務已啟動，請使用 job_id a7c9d8e2-1f42-4b89-8c5d-6e3a2b1f9d04 輪詢狀態"
}
```

### 示例 6：方案 C - 搜尋替換

```bash
curl -X POST http://localhost:8000/meal-plans/1/adjust/search-replace \
  -H "Content-Type: application/json" \
  -d '{
    "meal_date": "2024-08-12",
    "meal_type": "dinner",
    "user_id": 1,
    "search_query": "番茄",
    "new_recipe_id": 20
  }'
```

### 示例 7：方案 D - 調整分量

```bash
curl -X PUT http://localhost:8000/meal-plans/1/adjust/serving-weight \
  -H "Content-Type: application/json" \
  -d '{
    "meal_date": "2024-08-12",
    "meal_type": "lunch",
    "user_id": 1,
    "new_serving_weight_g": 400
  }'

# 回應（營養素自動重新計算）
{
  "success": true,
  "updated_meal": {
    "meal_date": "2024-08-12",
    "meal_type": "lunch",
    "user_id": 1,
    "recipe_id": 15,
    "recipe_name": "番茄雞肉義大利麵",
    "serving_weight_g": 400,
    "calories": 600,  # 自動重新計算
    "protein_g": 46.67,
    "carbs_g": 60,
    "fat_g": 16
  }
}
```

### 示例 8：確認推薦

```bash
curl -X PUT http://localhost:8000/meal-plans/1/confirm

# 回應
{
  "success": true,
  "plan_id": 1,
  "status": "confirmed",
  "shopping_list_id": 5,
  "message": "推薦已確認，購物清單已生成"
}
```

---

## 🐛 常見問題和調試

### Q1: Claude API 超時

**症狀**：推薦任務長時間卡在 "processing" 狀態

**解決**：
1. 檢查 Claude API 金鑰是否正確
2. 檢查食譜資料庫大小（太大會導致 token 超出限制）
3. 可考慮縮小食譜候選集（只保留 50-100 個）

### Q2: 食譜篩選後為空

**症狀**：沒有符合的候選食譜

**解決**：
1. 檢查用戶的過敏和限制設置是否太嚴格
2. 檢查食譜數據庫中是否有足夠的食譜
3. 暫時放寬篩選條件進行測試

### Q3: 微調後營養素計算錯誤

**症狀**：分量調整後的營養素不符合預期

**解決**：
1. 檢查食譜的 base_weight_g 和營養素是否正確
2. 檢查 `NutrientCalculator.calculate_meal_nutrition()` 的計算邏輯
3. 驗證食譜數據庫中是否有 NULL 值

---

## 🚀 性能優化建議

### 1. 食譜緩存

```python
# 在 recommendation_service.py 中添加
from functools import lru_cache

@lru_cache(maxsize=1)
def get_all_recipes_cached(db):
    """緩存所有食譜，避免重複查詢"""
    return db.query(Recipe).filter(Recipe.is_active == True).all()
```

### 2. 異步數據庫查詢

```python
# 如果使用 async SQLAlchemy
from sqlalchemy.ext.asyncio import AsyncSession

async def get_user_data_async(session: AsyncSession, user_id: int):
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    return result.scalar_one_or_none()
```

### 3. 分頁查詢

```python
# 避免一次加載所有食譜
def get_recipes_paginated(db, page: int = 1, page_size: int = 50):
    return db.query(Recipe).limit(page_size).offset((page - 1) * page_size).all()
```

---

## 📊 監控和日誌

### 啟用詳細日誌

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('nutrition_system.log'),
        logging.StreamHandler()
    ]
)
```

### 關鍵日誌點

- ✅ 推薦任務啟動：`logger.info(f"推薦任務已啟動：{job_id}")`
- ⚠️ 食譜篩選：`logger.info(f"食譜篩選完成：{len(all)} → {len(candidates)}")`
- 🔴 Claude 調用失敗：`logger.error(f"Claude API 調用失敗：{error}")`
- ✅ 微調成功：`logger.info(f"微調成功：{adjustment_type}")`

---

## ✅ 測試清單

在部署前，確認以下測試全部通過：

- [ ] 熱量計算器：測試各個公式和目標
- [ ] 生理期計算：測試各個階段的判定
- [ ] 食譜篩選：測試過敏和限制的邏輯
- [ ] Claude API：測試調用和回應解析
- [ ] API 端點：測試所有 8 個 endpoint
- [ ] 微調邏輯：測試方案 A/B/C/D
- [ ] 數據庫操作：測試儲存和查詢
- [ ] 非同步任務：測試後台任務的狀態轉換

---

## 📚 下一步

區塊 5 完成後，下一步是：

1. **區塊 6（購物清單管理）**：
   - 自動生成購物清單
   - 按購買地點分類
   - 成本估算

2. **區塊 7（前端應用）**：
   - React/Vue UI
   - 週推薦可視化
   - 微調界面

---

## 🔗 相關文檔

- 📄 [區塊 5 架構設計](./BLOCK_5_ARCHITECTURE_DESIGN.md)
- 📄 [系統總架構](./nutrition_system_architecture.md)
- 📄 [區塊 4 API](./BLOCK_4_DOCUMENTATION.md)（食譜管理）

---

**準備好集成區塊 5 了嗎？** ✨

如有任何問題或需要調整，請隨時聯繫！
