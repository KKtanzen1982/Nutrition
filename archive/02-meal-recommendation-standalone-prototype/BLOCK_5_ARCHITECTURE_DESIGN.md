# 區塊 5：Claude 推薦引擎 - 完整架構設計

**版本**：1.0  
**日期**：2024-08-06  
**狀態**：✅ 架構確認完成

---

## 📋 目錄

1. [資料模型擴展](#資料模型擴展)
2. [系統架構](#系統架構)
3. [API 設計](#api-設計)
4. [非同步任務流程](#非同步任務流程)
5. [推薦邏輯](#推薦邏輯)
6. [微調邏輯](#微調邏輯)
7. [生理期調整](#生理期調整)
8. [代碼組織](#代碼組織)

---

## 資料模型擴展

### 擴展 users 表 - 新增經期相關字段

```sql
-- 已有字段（保留）
menstrual_cycle_length_days INTEGER,  -- 平均週期天數
last_menstrual_date DATE,  -- 最後月經開始日期
menstrual_cycle_irregular BOOLEAN,  -- 月經不規律

-- 新增字段（用戶可修改）
menstrual_luteal_phase_start_offset_days INTEGER,  -- 黃體期開始的天數偏移
  -- 例：週期 28 天，黃體期第 15 天開始 → offset = 14（0-index）
menstrual_luteal_phase_adjustment_calories INTEGER,  -- 黃體期額外熱量，預設 +150
-- 例："含鐵食材,高蛋白"
menstrual_phase_food_preferences TEXT,

calorie_calculation_method TEXT,  -- 'harris_benedict' / 'mifflin_st_jeor' / 'custom'
  -- 用戶可選的計算公式，預設 'harris_benedict'
```

### 新增表：meal_plan_jobs（非同步任務追蹤）

```sql
CREATE TABLE meal_plan_jobs (
  id INTEGER PRIMARY KEY,
  job_id TEXT NOT NULL UNIQUE,  -- UUID，用於前端輪詢
  user_id_a INTEGER NOT NULL,
  user_id_b INTEGER NOT NULL,
  week_start_date DATE NOT NULL,
  
  status TEXT NOT NULL,  -- 'pending' / 'processing' / 'completed' / 'failed'
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  
  plan_id INTEGER,  -- 完成後存入的 weekly_meal_plan.id
  error_message TEXT,  -- 失敗時的錯誤信息
  
  FOREIGN KEY(user_id_a) REFERENCES users(id),
  FOREIGN KEY(user_id_b) REFERENCES users(id),
  FOREIGN KEY(plan_id) REFERENCES weekly_meal_plan(id)
);
```

### 擴展 weekly_meal_plan 表 - 新增欄位

```sql
-- 已有欄位（保留）
plan_date DATE,
user_id_a INTEGER,
user_id_b INTEGER,
breakfast_recipe_id INTEGER,
...
claude_generated BOOLEAN,

-- 新增欄位
calorie_calculation_method TEXT,  -- 此計畫使用的計算方法
user_a_daily_calories_target INTEGER,
user_b_daily_calories_target INTEGER,
user_a_menstrual_phase TEXT,  -- '月經期' / '黃體期' / '卵泡期' / '排卵期'
user_b_menstrual_phase TEXT,
-- JSON 格式，記錄本週推薦的理由（便於審計和改進）
recommendation_notes TEXT,
```

---

## 系統架構

### 整體流程圖

```
┌─────────────────────────────────────────────────────────┐
│                   用戶操作：啟動推薦                     │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
    ┌─────────────────┐
    │ 1. 收集用戶數據  │  （體重、運動、預選菜色）
    └────────┬────────┘
             │
             ▼
    ┌──────────────────────┐
    │ 2. 篩選候選食譜       │  （根據過敏、偏好、成本）
    │    計算營養目標       │  （TDEE、蛋白質、碳水、脂肪）
    │    準備推薦數據       │
    └────────┬─────────────┘
             │
             ▼
    ┌────────────────────────────────┐
    │ 3. 建立非同步任務（job_id）     │
    │    立即返回 job_id 給前端      │
    └────────┬─────────────────────────┘
             │
             ▼
    ┌──────────────────────────────────────────────────────┐
    │ 4. 背景任務：調用 Claude API（非同步）              │
    │    ├─ 打包 JSON（用戶 A、B、食譜庫）                │
    │    ├─ 發送 Claude prompt                             │
    │    ├─ 解析 Claude 回應                               │
    │    └─ 存入 weekly_meal_plan 和 daily_meal_detail   │
    └────────┬──────────────────────────────────────────────┘
             │
             ▼
    ┌──────────────────────────────────┐
    │ 5. 更新 job 狀態為 'completed'   │
    │    記錄 plan_id                   │
    └──────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                前端輪詢：查詢 job 狀態                  │
│    POST /meal-plans/jobs/{job_id}/status               │
│    回應：{ status, plan_id, error_message }             │
└─────────────────────────────────────────────────────────┘
```

### 微調流程

```
推薦完成 → 用戶修改菜色
  │
  ├─ 方案 A：替換單菜色
  │  └─ 直接替換 + 重新計算營養 + 記錄 meal_adjustments
  │
  ├─ 方案 B：重推整天
  │  └─ 保留其他 6 天 + 新建非同步任務 + Claude 重推該天
  │
  ├─ 方案 C：搜尋替換
  │  └─ 用戶搜尋菜色 + 替換 + 記錄 meal_adjustments
  │
  └─ 方案 D：調整分量
     └─ 修改 serving_weight_g + 自動計算營養
```

---

## API 設計

### 推薦相關 Endpoints

```
POST /meal-plans/generate
  功能: 啟動推薦任務（非同步）
  輸入: {
    week_start_date: "2024-08-05",
    user_a_id: 1,
    user_b_id: 2,
    calorie_calculation_method: "harris_benedict",  -- 用戶選的公式
    user_a_preselected: [
      { day: "Monday", meal_type: "lunch", recipe_id: 10 }
    ],
    user_b_preselected: []
  }
  回應: {
    success: true,
    job_id: "550e8400-e29b-41d4-a716-446655440000",
    message: "推薦任務已啟動，請輪詢查詢狀態"
  }

GET /meal-plans/jobs/{job_id}/status
  功能: 查詢推薦任務的進度
  回應: {
    job_id: "550e8400-...",
    status: "processing",  -- 'pending' / 'processing' / 'completed' / 'failed'
    plan_id: null,  -- 完成後會有值
    error_message: null,
    created_at: "2024-08-06T10:00:00",
    started_at: "2024-08-06T10:01:00",
    completed_at: null
  }

GET /meal-plans/{plan_id}
  功能: 取得週推薦詳情
  回應: {
    plan_id: 1,
    week_start_date: "2024-08-05",
    status: "draft",
    user_a_daily_calories_target: 1400,
    user_b_daily_calories_target: 2300,
    daily_details: [
      {
        meal_date: "2024-08-05",
        meals: [
          {
            meal_type: "breakfast",
            user_id: 1,
            recipe_id: 5,
            recipe_name: "燕麥粥",
            serving_weight_g: 150,
            calories: 250,
            protein_g: 8,
            carbs_g: 45,
            fat_g: 3
          }
        ]
      }
    ],
    nutrition_summary: {
      user_a: {
        total_calories: 9800,  -- 7 天
        avg_protein_g: 110,
        avg_carbs_g: 160,
        avg_fat_g: 35
      },
      user_b: { ... }
    }
  }
```

### 微調相關 Endpoints

```
POST /meal-plans/{plan_id}/adjust/replace-meal
  功能: 方案 A - 替換單菜色
  輸入: {
    meal_date: "2024-08-05",
    meal_type: "lunch",
    user_id: 1,
    new_recipe_id: 15
  }
  回應: {
    success: true,
    updated_meal: { ... },
    adjustment_recorded: true
  }

POST /meal-plans/{plan_id}/adjust/regenrate-day
  功能: 方案 B - 重推整天
  輸入: {
    meal_date: "2024-08-05",
    fixed_meals: [  -- 固定不變的餐次
      { meal_type: "breakfast", user_id: 1, recipe_id: 5 }
    ]
  }
  回應: {
    success: true,
    job_id: "550e8400-...",  -- 返回新任務 ID
    message: "日推薦任務已啟動"
  }

POST /meal-plans/{plan_id}/adjust/search-and-replace
  功能: 方案 C - 搜尋替換
  輸入: {
    meal_date: "2024-08-05",
    meal_type: "lunch",
    user_id: 1,
    search_query: "番茄",  -- 搜尋食譜
    new_recipe_id: 20
  }
  回應: {
    success: true,
    updated_meal: { ... },
    adjustment_recorded: true
  }

PUT /meal-plans/{plan_id}/adjust/serving-weight
  功能: 方案 D - 調整分量
  輸入: {
    meal_date: "2024-08-05",
    meal_type: "lunch",
    user_id: 1,
    new_serving_weight_g: 180  -- 原本 150g，改成 180g
  }
  回應: {
    success: true,
    updated_meal: {
      serving_weight_g: 180,
      calories: 300,  -- 自動重新計算
      protein_g: 9.6,
      carbs_g: 54,
      fat_g: 3.6
    }
  }

PUT /meal-plans/{plan_id}/confirm
  功能: 確認推薦（狀態改為 'confirmed'）
  回應: {
    success: true,
    plan: { ... },
    shopping_list_id: 2  -- 自動生成購物清單
  }
```

---

## 非同步任務流程

### 後台工作流（使用 Python 的 `asyncio` 或 `Celery`）

**選項 1：簡單版本（Asyncio）**

```python
# app.py 中
import asyncio
from fastapi import BackgroundTasks

@app.post("/meal-plans/generate")
async def generate_meal_plan(request: GenerateMealPlanRequest):
    job_id = str(uuid.uuid4())
    
    # 立即建立 job 記錄
    job = MealPlanJob(
        job_id=job_id,
        user_id_a=request.user_a_id,
        user_id_b=request.user_b_id,
        week_start_date=request.week_start_date,
        status="pending"
    )
    db.add(job)
    db.commit()
    
    # 後台啟動推薦任務
    asyncio.create_task(
        run_meal_plan_recommendation(job_id, request)
    )
    
    return {
        "success": True,
        "job_id": job_id
    }

async def run_meal_plan_recommendation(job_id: str, request: GenerateMealPlanRequest):
    try:
        # 更新狀態為 processing
        job = db.query(MealPlanJob).filter(MealPlanJob.job_id == job_id).first()
        job.status = "processing"
        job.started_at = datetime.now()
        db.commit()
        
        # 調用推薦邏輯
        plan = await RecommendationService.generate_meal_plan(request)
        
        # 存入資料庫
        plan_id = save_meal_plan(plan)
        
        # 更新 job 狀態
        job.status = "completed"
        job.plan_id = plan_id
        job.completed_at = datetime.now()
        db.commit()
        
    except Exception as e:
        job.status = "failed"
        job.error_message = str(e)
        job.completed_at = datetime.now()
        db.commit()
        logger.error(f"推薦任務失敗: {job_id}: {e}")
```

**選項 2：生產版本（Celery + Redis）**

```python
# celery_app.py
from celery import Celery

app = Celery('nutrition_system')
app.config_from_object('celeryconfig')

@app.task(bind=True)
def generate_meal_plan_task(self, job_id: str, request_data: dict):
    try:
        job = db.query(MealPlanJob).filter(MealPlanJob.job_id == job_id).first()
        job.status = "processing"
        job.started_at = datetime.now()
        db.commit()
        
        plan = RecommendationService.generate_meal_plan(request_data)
        plan_id = save_meal_plan(plan)
        
        job.status = "completed"
        job.plan_id = plan_id
        job.completed_at = datetime.now()
        db.commit()
        
    except Exception as e:
        job.status = "failed"
        job.error_message = str(e)
        job.completed_at = datetime.now()
        db.commit()
```

我們先用**選項 1（Asyncio）**，簡單快速。後期如需要可升級到 Celery。

---

## 推薦邏輯

### 1. 熱量目標計算

```python
class CalorieCalculator:
    
    HARRIS_BENEDICT_COEFFICIENTS = {
        "久坐": 1.2,
        "輕度": 1.375,
        "中度": 1.55,
        "高度": 1.725
    }
    
    MIFFLIN_ST_JEOR_COEFFICIENTS = {
        "久坐": 1.2,
        "輕度": 1.375,
        "中度": 1.55,
        "高度": 1.725
    }
    
    @staticmethod
    def calculate_bmr(user: User) -> float:
        """計算基礎代謝率"""
        if user.calorie_calculation_method == "harris_benedict":
            if user.gender == "女":
                bmr = 655 + (9.6 * user.weight_kg) + \
                      (1.8 * user.height_cm) - (4.7 * user.age)
            else:  # 男
                bmr = 88 + (13.4 * user.weight_kg) + \
                      (4.8 * user.height_cm) - (5.7 * user.age)
        elif user.calorie_calculation_method == "mifflin_st_jeor":
            if user.gender == "女":
                bmr = (10 * user.weight_kg) + (6.25 * user.height_cm) - \
                      (5 * user.age) - 161
            else:
                bmr = (10 * user.weight_kg) + (6.25 * user.height_cm) - \
                      (5 * user.age) + 5
        return bmr
    
    @staticmethod
    def calculate_tdee(user: User, exercise_data: dict) -> float:
        """計算每日總能量消耗"""
        bmr = CalorieCalculator.calculate_bmr(user)
        
        # 活動等級係數
        activity_coeff = CalorieCalculator.HARRIS_BENEDICT_COEFFICIENTS[
            user.activity_level
        ]
        
        tdee = bmr * activity_coeff
        
        # 根據本週運動調整（±50~100 kcal per session）
        gym_sessions = exercise_data.get("gym_sessions", 0)
        tdee += gym_sessions * 75  # 每次健身房 +75 kcal
        
        return tdee
    
    @staticmethod
    def adjust_for_goal(tdee: float, goal: str, is_weekly_max: bool = False) -> float:
        """根據目標調整熱量"""
        if goal == "減脂":
            adjustment = -350  # 每天減 350 kcal，約一週減 0.5 kg
        elif goal == "增肌":
            adjustment = +250
        else:  # 維持
            adjustment = 0
        
        adjusted = tdee + adjustment
        return max(adjusted, 1200)  # 最低 1200 kcal
    
    @staticmethod
    def adjust_for_menstrual_phase(
        calories: float,
        menstrual_phase: str,
        adjustment_config: dict
    ) -> float:
        """根據生理期調整熱量"""
        if menstrual_phase == "黃體期":
            # 黃體期可增加 150-200 kcal
            adjustment = adjustment_config.get("luteal_phase_adjustment", 150)
            return calories + adjustment
        elif menstrual_phase == "經前期":
            # 經前期可增加 100-150 kcal
            adjustment = adjustment_config.get("premenstrual_adjustment", 120)
            return calories + adjustment
        # 月經期、卵泡期、排卵期：無特殊調整
        return calories
```

### 2. 資料打包和篩選

```python
class RecommendationDataPacker:
    
    @staticmethod
    def pack_for_claude(
        user_a: User,
        user_b: User,
        week_start_date: date,
        exercise_data_a: dict,
        exercise_data_b: dict,
        preselected_meals_a: list,
        preselected_meals_b: list,
        candidate_recipes: list  # 篩選過的食譜
    ) -> dict:
        """
        打包推薦所需的所有數據為 JSON
        
        candidate_recipes 應該是根據過敏、偏好、成本預先篩選過的
        """
        
        # 計算熱量目標
        tdee_a = CalorieCalculator.calculate_tdee(user_a, exercise_data_a)
        daily_calories_a = CalorieCalculator.adjust_for_goal(
            tdee_a, user_a.primary_goal
        )
        
        # 計算生理期和調整
        menstrual_phase_a = calculate_menstrual_phase(user_a, week_start_date)
        daily_calories_a = CalorieCalculator.adjust_for_menstrual_phase(
            daily_calories_a,
            menstrual_phase_a,
            {
                "luteal_phase_adjustment": user_a.menstrual_luteal_phase_adjustment_calories
            }
        )
        
        # 類似計算 user_b 的熱量
        tdee_b = CalorieCalculator.calculate_tdee(user_b, exercise_data_b)
        daily_calories_b = CalorieCalculator.adjust_for_goal(tdee_b, user_b.primary_goal)
        menstrual_phase_b = calculate_menstrual_phase(user_b, week_start_date)
        daily_calories_b = CalorieCalculator.adjust_for_menstrual_phase(
            daily_calories_b, menstrual_phase_b, {}
        )
        
        # 計算營養目標比例
        nutrients_a = calculate_nutrient_targets(user_a, daily_calories_a)
        nutrients_b = calculate_nutrient_targets(user_b, daily_calories_b)
        
        return {
            "analysis_date": date.today().isoformat(),
            "week_start_date": week_start_date.isoformat(),
            
            "user_a": {
                "id": user_a.id,
                "name": user_a.name,
                "gender": user_a.gender,
                "age": user_a.age,
                "height_cm": user_a.height_cm,
                "primary_goal": user_a.primary_goal,
                "activity_level": user_a.activity_level,
                "menstrual_phase": menstrual_phase_a,
                "allergies": user_a.dietary_preferences.allergies or "無",
                "restrictions": user_a.dietary_preferences.restrictions or "無",
                "daily_calories_target": int(daily_calories_a),
                "daily_protein_g": int(nutrients_a["protein_g"]),
                "daily_carbs_g": int(nutrients_a["carbs_g"]),
                "daily_fat_g": int(nutrients_a["fat_g"]),
                "this_week_exercise": exercise_data_a
            },
            
            "user_b": { ... },  # 類似 user_a
            
            "user_a_preselected_meals": preselected_meals_a,
            "user_b_preselected_meals": preselected_meals_b,
            
            "recipe_database": [
                {
                    "id": r.id,
                    "name": r.recipe_name,
                    "category": r.category,
                    "base_weight_g": r.base_weight_g,
                    "cost_level": r.cost_level,
                    "calories": r.nutrition.total_calories_kcal,
                    "protein_g": r.nutrition.protein_g,
                    "carbs_g": r.nutrition.carbs_g,
                    "fat_g": r.nutrition.fat_g,
                    "fiber_g": r.nutrition.fiber_g,
                    "ingredients": [ing.name for ing in r.ingredients],
                    "is_vegetarian": r.is_vegetarian,
                    "contains_allergens": r.allergen_tags
                }
                for r in candidate_recipes
            ]
        }
```

### 3. 食譜篩選

```python
class RecipeFilter:
    
    @staticmethod
    def filter_candidate_recipes(
        user_a: User,
        user_b: User,
        all_recipes: list
    ) -> list:
        """
        根據過敏、偏好、成本篩選候選食譜
        
        返回經過篩選的食譜列表，供 Claude 使用
        """
        
        # 收集過敏和限制
        allergens_a = set(user_a.dietary_preferences.allergies.split(",")) if user_a.dietary_preferences.allergies else set()
        allergens_b = set(user_b.dietary_preferences.allergies.split(",")) if user_b.dietary_preferences.allergies else set()
        all_allergens = allergens_a | allergens_b
        
        # 收集限制（素食等）
        restrictions_a = set(user_a.dietary_preferences.restrictions.split(",")) if user_a.dietary_preferences.restrictions else set()
        restrictions_b = set(user_b.dietary_preferences.restrictions.split(",")) if user_b.dietary_preferences.restrictions else set()
        
        candidates = []
        
        for recipe in all_recipes:
            # 檢查過敏
            if any(allergen in recipe.allergen_tags for allergen in all_allergens):
                continue
            
            # 檢查素食限制
            if "素食" in restrictions_a and recipe.contains_meat:
                continue
            if "素食" in restrictions_b and recipe.contains_meat:
                continue
            
            # 可選：篩選成本（高成本菜色可選擇性推薦）
            candidates.append(recipe)
        
        return candidates
```

---

## 微調邏輯

### 方案 A：替換單菜色

```python
class MealAdjustmentService:
    
    @staticmethod
    def replace_meal(
        plan_id: int,
        meal_date: date,
        meal_type: str,  # 'breakfast', 'lunch', 'dinner', 'afternoon_snack'
        user_id: int,
        new_recipe_id: int
    ) -> dict:
        """直接替換單個菜色"""
        
        plan = db.query(WeeklyMealPlan).filter(WeeklyMealPlan.id == plan_id).first()
        
        # 取得新食譜
        new_recipe = db.query(Recipe).filter(Recipe.id == new_recipe_id).first()
        
        # 更新 daily_meal_detail
        meal = db.query(DailyMealDetail).filter(
            DailyMealDetail.meal_plan_id == plan_id,
            DailyMealDetail.meal_date == meal_date,
            DailyMealDetail.meal_type == meal_type,
            DailyMealDetail.assigned_user_id == user_id
        ).first()
        
        old_recipe_id = meal.recipe_id
        meal.recipe_id = new_recipe_id
        meal.serving_weight_g = new_recipe.base_weight_g
        meal.total_calories = new_recipe.nutrition.total_calories_kcal
        meal.protein_g = new_recipe.nutrition.protein_g
        meal.carbs_g = new_recipe.nutrition.carbs_g
        meal.fat_g = new_recipe.nutrition.fat_g
        
        db.commit()
        
        # 記錄微調
        adjustment = MealAdjustment(
            plan_id=plan_id,
            adjustment_type="替換",
            original_recipe_id=old_recipe_id,
            adjusted_recipe_id=new_recipe_id,
            reason="用戶手動替換",
            adjusted_by="user",
            adjusted_at=datetime.now()
        )
        db.add(adjustment)
        db.commit()
        
        return {
            "success": True,
            "updated_meal": meal.to_dict(),
            "adjustment_recorded": True
        }
```

### 方案 B：重推整天

```python
@staticmethod
async def regenerate_day(
    plan_id: int,
    meal_date: date,
    fixed_meals: list  # [{ meal_type, user_id, recipe_id }]
) -> dict:
    """
    重新推薦某一天，固定某些菜色，其他菜色由 Claude 重推
    
    返回新的 job_id
    """
    
    plan = db.query(WeeklyMealPlan).filter(WeeklyMealPlan.id == plan_id).first()
    
    # 建立新的任務
    job_id = str(uuid.uuid4())
    job = MealPlanJob(
        job_id=job_id,
        user_id_a=plan.user_id_a,
        user_id_b=plan.user_id_b,
        week_start_date=plan.plan_date,
        status="pending",
        plan_id=plan_id  # 關聯到現有的週計畫
    )
    db.add(job)
    db.commit()
    
    # 啟動後台任務
    asyncio.create_task(
        regenerate_day_background(job_id, plan_id, meal_date, fixed_meals)
    )
    
    return {"success": True, "job_id": job_id}

async def regenerate_day_background(
    job_id: str,
    plan_id: int,
    meal_date: date,
    fixed_meals: list
):
    """後台重推某一天"""
    try:
        job = db.query(MealPlanJob).filter(MealPlanJob.job_id == job_id).first()
        job.status = "processing"
        job.started_at = datetime.now()
        db.commit()
        
        plan = db.query(WeeklyMealPlan).filter(WeeklyMealPlan.id == plan_id).first()
        user_a = plan.user_a
        user_b = plan.user_b
        
        # 收集已有的菜色（除了要重推的日期）
        other_days_meals = get_other_days_meals(plan_id, meal_date)
        
        # 打包數據（只包含要重推的一天）
        pack_data = RecommendationDataPacker.pack_for_claude_single_day(
            user_a, user_b,
            meal_date,
            fixed_meals,
            other_days_meals,
            candidate_recipes
        )
        
        # 調用 Claude
        claude_response = await ClaudeRecommendationService.call_claude(pack_data)
        
        # 更新該天的菜色
        update_day_meals(plan_id, meal_date, claude_response["meals"])
        
        # 記錄微調
        for meal in claude_response["meals"]:
            adjustment = MealAdjustment(
                plan_id=plan_id,
                adjustment_type="重推整天",
                original_recipe_id=None,
                adjusted_recipe_id=meal["recipe_id"],
                reason=f"用戶重推 {meal_date}",
                adjusted_by="user"
            )
            db.add(adjustment)
        
        db.commit()
        
        job.status = "completed"
        job.completed_at = datetime.now()
        db.commit()
        
    except Exception as e:
        job.status = "failed"
        job.error_message = str(e)
        job.completed_at = datetime.now()
        db.commit()
        logger.error(f"重推整天失敗: {job_id}: {e}")
```

### 方案 C / D：搜尋替換和分量調整

（類似方案 A 的邏輯，程式碼簡潔，不再贅述）

---

## 生理期調整

### 生理期計算邏輯

```python
def calculate_menstrual_phase(user: User, target_date: date) -> str:
    """
    根據用戶的月經週期計算某一日期是哪個生理期
    
    週期階段劃分（假設 28 天週期）：
    - 第 1-5 天：月經期
    - 第 6-12 天：卵泡期
    - 第 13-14 天：排卵期
    - 第 15-28 天：黃體期
    
    用戶可自訂黃體期開始日期（menstrual_luteal_phase_start_offset_days）
    """
    
    if user.gender != "女" or not user.last_menstrual_date:
        return "無"
    
    cycle_length = user.menstrual_cycle_length_days or 28
    days_since_start = (target_date - user.last_menstrual_date).days % cycle_length
    
    # 月經期：第 1-5 天（0-4）
    if days_since_start < 5:
        return "月經期"
    
    # 黃體期開始的偏移日期（可由用戶修改）
    luteal_start = user.menstrual_luteal_phase_start_offset_days or 14
    premenstrual_start = cycle_length - 3  # 經前 3 天
    
    if days_since_start >= premenstrual_start:
        return "經前期"  # 新增的階段
    elif days_since_start >= luteal_start:
        return "黃體期"
    elif days_since_start >= 12:
        return "排卵期"
    else:
        return "卵泡期"

def get_menstrual_phase_food_recommendations(user: User, phase: str) -> dict:
    """取得該生理期的飲食建議"""
    recommendations = {
        "月經期": {
            "key_nutrients": "鐵、維生素 B12",
            "suggested_ingredients": ["紅肉", "菠菜", "黑木耳", "紅棗"],
            "calorie_adjustment": 0
        },
        "卵泡期": {
            "key_nutrients": "蛋白質、碳水",
            "suggested_ingredients": ["雞胸肉", "糙米", "蛋"],
            "calorie_adjustment": 0
        },
        "排卵期": {
            "key_nutrients": "礦物質、維生素",
            "suggested_ingredients": ["堅果", "綠葉蔬菜"],
            "calorie_adjustment": 0
        },
        "黃體期": {
            "key_nutrients": "蛋白質、鎂",
            "suggested_ingredients": ["牛肉", "黑巧克力", "南瓜子"],
            "calorie_adjustment": user.menstrual_luteal_phase_adjustment_calories or 150
        },
        "經前期": {
            "key_nutrients": "鎂、維生素 B6、鈣",
            "suggested_ingredients": ["香蕉", "黑巧克力", "杏仁"],
            "calorie_adjustment": 120  # 可由用戶自訂
        }
    }
    return recommendations.get(phase, {})
```

---

## 代碼組織

```
BLOCK_5/
├─ BLOCK_5_schemas.py              # Pydantic 數據模型
├─ BLOCK_5_prompts.py              # Claude Prompt 模板
├─ BLOCK_5_recommendation_service.py  # 核心服務類
├─ BLOCK_5_adjustment_service.py    # 微調邏輯
├─ BLOCK_5_meal_plan_api.py         # 推薦相關 API endpoints
├─ BLOCK_5_adjustment_api.py        # 微調相關 API endpoints
└─ BLOCK_5_tests.py                # 單元測試
```

---

## 開發優先級

1. ✅ **資料模型擴展**（表、字段）
2. ✅ **Pydantic Schemas**（數據驗證）
3. ✅ **CalorieCalculator**（熱量計算）
4. ✅ **RecipeFilter** + **RecommendationDataPacker**（篩選和打包）
5. ✅ **Claude Prompt 模板**
6. ✅ **ClaudeRecommendationService**（調用 Claude API）
7. ✅ **MealPlanManager**（儲存和查詢）
8. ✅ **非同步任務框架**（Asyncio）
9. ✅ **MealAdjustmentService**（方案 A/B/C/D）
10. ✅ **API Endpoints**（所有 /meal-plans/* 路由）
11. ✅ **測試和文檔**

---

**準備開始編碼？** 確認無誤後，我會按順序生成所有代碼檔案。
