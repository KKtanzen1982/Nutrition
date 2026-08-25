# 飲食管理系統 - 完整架構設計文檔

**系統概述**：2人飲食管理系統，整合體重追蹤、運動記錄、AI 食譜推薦、購物清單管理

**開發時間**：2024-08-06  
**技術棧**：React/Vue.js (前端) + Python FastAPI (後端) + SQLite (本地數據庫) + Claude API (推薦引擎)

---

## 📋 目錄

1. [數據模型架構](#數據模型架構)
2. [API 設計](#api-設計)
3. [Claude 推薦邏輯](#claude-推薦邏輯)
4. [系統流程](#系統流程)
5. [區塊劃分](#區塊劃分)

---

## 數據模型架構

### 用戶和目標管理

#### 表 1: users（用戶基本資料）
```sql
CREATE TABLE users (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  gender TEXT NOT NULL,  -- '男' / '女' / '其他'
  age INTEGER NOT NULL,
  height_cm INTEGER NOT NULL,
  primary_goal TEXT NOT NULL,  -- '減脂' / '增肌' / '維持'
  activity_level TEXT NOT NULL,  -- '久坐' / '輕度' / '中度' / '高度'
  menstrual_cycle_length_days INTEGER,  -- 平均週期天數（女性用）
  last_menstrual_date DATE,  -- 最後月經開始日期
  menstrual_cycle_irregular BOOLEAN,  -- 月經不規律
  medical_conditions TEXT,  -- 已知疾病/健康狀況
  sport_limitations TEXT,  -- 運動限制
  notes TEXT,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

#### 表 1a: user_goal_history（目標變化歷史）
```sql
CREATE TABLE user_goal_history (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL,
  goal_type TEXT NOT NULL,  -- 'weight' / 'body_fat' / 'waist_circumference'
  target_value REAL NOT NULL,
  previous_value REAL,
  set_date DATE NOT NULL,
  achieved BOOLEAN,
  achievement_date DATE,
  notes TEXT,
  created_at TIMESTAMP,
  FOREIGN KEY(user_id) REFERENCES users(id)
);
```

#### 表 4: dietary_preferences（飲食偏好）
```sql
CREATE TABLE dietary_preferences (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL,
  allergies TEXT,  -- 逗號分隔，例："堅果, 海鮮"
  restrictions TEXT,  -- 例："素食, 不吃辣"
  preferences TEXT,  -- 例："喜歡亞洲料理, 清淡"
  notes TEXT,
  updated_at TIMESTAMP,
  FOREIGN KEY(user_id) REFERENCES users(id)
);
```

#### 表 5x: user_sport_preferences（運動偏好設定）
```sql
CREATE TABLE user_sport_preferences (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL,
  sport_type TEXT NOT NULL,  -- '健身房' / '走路' / '瑜珈' / '拉伸'
  target_frequency_per_week INTEGER,
  experience_level TEXT,  -- '初級' / '中級' / '進階'
  sport_limitations TEXT,
  notes TEXT,
  created_at TIMESTAMP,
  FOREIGN KEY(user_id) REFERENCES users(id)
);
```

---

### 體重追蹤

#### 表 2: weight_records（體重日誌）
```sql
CREATE TABLE weight_records (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL,
  date DATE NOT NULL,
  weight_kg REAL NOT NULL,
  body_fat_percent REAL,  -- 每週輸入
  waist_cm REAL,  -- 每週輸入
  note TEXT,
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  FOREIGN KEY(user_id) REFERENCES users(id),
  UNIQUE(user_id, date)
);
```

---

### 運動追蹤

#### 表 3a: exercise_sessions（運動日期紀錄）
```sql
CREATE TABLE exercise_sessions (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL,
  date DATE NOT NULL,
  exercise_type TEXT NOT NULL,  -- '健身房' / '走路' / '瑜珈' / '拉伸'
  duration_min INTEGER,
  intensity TEXT,  -- '低' / '中' / '高'
  notes TEXT,
  synced_from TEXT,  -- '手動輸入' / 'Apple Health' / 'Google Fit'
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  FOREIGN KEY(user_id) REFERENCES users(id)
);
```

#### 表 3b: exercise_details（訓練項目明細）
```sql
CREATE TABLE exercise_details (
  id INTEGER PRIMARY KEY,
  exercise_session_id INTEGER NOT NULL,
  exercise_item TEXT NOT NULL,
  sets INTEGER,
  reps_or_duration TEXT,  -- '10' 或 '10 mins'
  weight_kg REAL,
  notes TEXT,
  FOREIGN KEY(exercise_session_id) REFERENCES exercise_sessions(id)
);
```

#### 表 3c: exercise_item_library（訓練項目庫）
```sql
CREATE TABLE exercise_item_library (
  id INTEGER PRIMARY KEY,
  item_name TEXT NOT NULL UNIQUE,
  category TEXT,  -- '胸部' / '背部' / '下肢' / '核心' 等
  description TEXT,
  default_sets INTEGER,
  default_reps INTEGER,
  muscle_group TEXT,
  created_at TIMESTAMP
);
```

#### 表 3d: workout_templates（訓練組合模板）
```sql
CREATE TABLE workout_templates (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL,
  template_name TEXT NOT NULL,
  description TEXT,
  notes TEXT,
  created_at TIMESTAMP,
  FOREIGN KEY(user_id) REFERENCES users(id),
  UNIQUE(user_id, template_name)
);
```

#### 表 3e: template_details（模板詳細項目）
```sql
CREATE TABLE template_details (
  id INTEGER PRIMARY KEY,
  template_id INTEGER NOT NULL,
  exercise_item TEXT NOT NULL,
  order_number INTEGER,
  sets INTEGER,
  reps_or_duration TEXT,
  weight_kg REAL,
  notes TEXT,
  FOREIGN KEY(template_id) REFERENCES workout_templates(id)
);
```

#### 表 3f: daily_steps（每日步數紀錄）
```sql
CREATE TABLE daily_steps (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL,
  date DATE NOT NULL,
  steps INTEGER,
  source TEXT,  -- '手動輸入' / 'Apple Health' / 'Google Fit'
  synced_at TIMESTAMP,
  notes TEXT,
  FOREIGN KEY(user_id) REFERENCES users(id),
  UNIQUE(user_id, date)
);
```

#### 表 3g: yoga_stretch_items（瑜珈拉伸項目庫）
```sql
CREATE TABLE yoga_stretch_items (
  id INTEGER PRIMARY KEY,
  type TEXT NOT NULL,  -- '瑜珈' / '拉伸'
  item_name TEXT NOT NULL UNIQUE,
  duration_min INTEGER,
  description TEXT,
  difficulty TEXT,  -- '初級' / '中級' / '進階'
  created_at TIMESTAMP
);
```

---

### 食譜管理

#### 表 5a: recipes（食譜庫）
```sql
CREATE TABLE recipes (
  id INTEGER PRIMARY KEY,
  recipe_name TEXT NOT NULL UNIQUE,
  category TEXT NOT NULL,  -- '早餐' / '主食' / '肉' / '菜' / '飲料' / '點心'
  base_weight_g INTEGER,  -- 基礎重量
  cost_level TEXT,  -- '低' / '中' / '高'
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP,
  last_updated_at TIMESTAMP
);
```

#### 表 5b: recipe_ingredients（食譜食材明細）
```sql
CREATE TABLE recipe_ingredients (
  id INTEGER PRIMARY KEY,
  recipe_id INTEGER NOT NULL,
  ingredient_id INTEGER NOT NULL,
  quantity_g REAL NOT NULL,
  unit TEXT,  -- 'g' / 'ml' / '顆' / '把' 等
  notes TEXT,
  FOREIGN KEY(recipe_id) REFERENCES recipes(id),
  FOREIGN KEY(ingredient_id) REFERENCES ingredient_library(id)
);
```

#### 表 5c: recipe_steps（製作步驟 - 版本控制）
```sql
CREATE TABLE recipe_steps (
  id INTEGER PRIMARY KEY,
  recipe_id INTEGER NOT NULL,
  version INTEGER NOT NULL,
  step_number INTEGER NOT NULL,
  step_description TEXT NOT NULL,
  created_at TIMESTAMP,
  is_current BOOLEAN,  -- 標記最新版本
  FOREIGN KEY(recipe_id) REFERENCES recipes(id)
);
```

#### 表 5d: recipe_nutrition（營養素資訊 - 自動計算）
```sql
CREATE TABLE recipe_nutrition (
  id INTEGER PRIMARY KEY,
  recipe_id INTEGER NOT NULL,
  total_calories_kcal REAL,
  protein_g REAL,
  carbs_g REAL,
  fat_g REAL,
  fiber_g REAL,
  calculated_at TIMESTAMP,
  FOREIGN KEY(recipe_id) REFERENCES recipes(id)
);
```

---

### 食材管理

#### 表 5i: ingredient_library（食材庫）
```sql
CREATE TABLE ingredient_library (
  id INTEGER PRIMARY KEY,
  ingredient_name TEXT NOT NULL UNIQUE,
  category TEXT NOT NULL,  -- '蔬菜' / '肉類' / '穀物' / '乳製品' / '調味料' / '其他'
  unit TEXT,  -- '克' / 'ml' / '顆' 等
  calories_per_100g REAL,
  protein_per_100g REAL,
  carbs_per_100g REAL,
  fat_per_100g REAL,
  fiber_per_100g REAL,
  preferred_purchase_location TEXT,
  needs_stock_tracking BOOLEAN,
  created_at TIMESTAMP
);
```

#### 表 5e: ingredient_stock（食材庫存）
```sql
CREATE TABLE ingredient_stock (
  id INTEGER PRIMARY KEY,
  ingredient_id INTEGER NOT NULL,
  current_quantity_g REAL,
  min_threshold_g REAL,  -- 警告閾值
  unit TEXT,
  last_purchased_at DATE,
  notes TEXT,
  FOREIGN KEY(ingredient_id) REFERENCES ingredient_library(id)
);
```

---

### 週推薦和購物清單

#### 表 5f: weekly_meal_plan（週菜單安排）
```sql
CREATE TABLE weekly_meal_plan (
  id INTEGER PRIMARY KEY,
  plan_date DATE NOT NULL,  -- 週一的日期
  user_id_a INTEGER NOT NULL,
  user_id_b INTEGER NOT NULL,
  breakfast_recipe_id INTEGER,
  lunch_recipe_id INTEGER,
  afternoon_snack_recipe_id INTEGER,
  dinner_recipe_id INTEGER,
  plan_status TEXT,  -- '草稿' / '待微調' / '已確認'
  claude_generated BOOLEAN,
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  FOREIGN KEY(user_id_a) REFERENCES users(id),
  FOREIGN KEY(user_id_b) REFERENCES users(id)
);
```

#### 表 5g: daily_meal_detail（日菜單詳情）
```sql
CREATE TABLE daily_meal_detail (
  id INTEGER PRIMARY KEY,
  meal_plan_id INTEGER NOT NULL,
  meal_date DATE NOT NULL,
  meal_type TEXT NOT NULL,  -- '早餐' / '主食' / '肉' / '菜' / '下午茶'
  recipe_id INTEGER NOT NULL,
  assigned_user_id INTEGER NOT NULL,  -- A 或 B
  serving_weight_g REAL,
  total_calories REAL,
  protein_g REAL,
  carbs_g REAL,
  fat_g REAL,
  notes TEXT,
  FOREIGN KEY(meal_plan_id) REFERENCES weekly_meal_plan(id),
  FOREIGN KEY(recipe_id) REFERENCES recipes(id),
  FOREIGN KEY(assigned_user_id) REFERENCES users(id)
);
```

#### 表 5h: meal_adjustments（推薦微調紀錄）
```sql
CREATE TABLE meal_adjustments (
  id INTEGER PRIMARY KEY,
  plan_id INTEGER NOT NULL,
  adjustment_type TEXT,  -- '替換' / '刪除' / '新增'
  original_recipe_id INTEGER,
  adjusted_recipe_id INTEGER,
  reason TEXT,
  adjusted_by TEXT,  -- 'A' / 'B' / 'System'
  adjusted_at TIMESTAMP,
  FOREIGN KEY(plan_id) REFERENCES weekly_meal_plan(id)
);
```

#### 表 6a: purchase_locations（購買地點庫）
```sql
CREATE TABLE purchase_locations (
  id INTEGER PRIMARY KEY,
  location_name TEXT NOT NULL UNIQUE,
  description TEXT,
  priority_order INTEGER,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP
);
```

#### 表 6b: ingredient_location_preference（食材地點偏好）
```sql
CREATE TABLE ingredient_location_preference (
  id INTEGER PRIMARY KEY,
  ingredient_id INTEGER NOT NULL,
  preferred_location_id INTEGER NOT NULL,
  priority INTEGER,  -- 1=最優先, 2=次優先, 3=備選
  notes TEXT,
  FOREIGN KEY(ingredient_id) REFERENCES ingredient_library(id),
  FOREIGN KEY(preferred_location_id) REFERENCES purchase_locations(id)
);
```

#### 表 6c: shopping_list（購物清單主表）
```sql
CREATE TABLE shopping_list (
  id INTEGER PRIMARY KEY,
  list_date DATE NOT NULL,
  week_start_date DATE NOT NULL,
  created_from_plan_id INTEGER,
  status TEXT,  -- '草稿' / '已確認' / '採購中' / '已採購' / '歸檔'
  total_items INTEGER,
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  notes TEXT,
  FOREIGN KEY(created_from_plan_id) REFERENCES weekly_meal_plan(id)
);
```

#### 表 6d: shopping_list_items（購物項目明細）
```sql
CREATE TABLE shopping_list_items (
  id INTEGER PRIMARY KEY,
  shopping_list_id INTEGER NOT NULL,
  ingredient_id INTEGER NOT NULL,
  quantity_needed_g REAL NOT NULL,
  unit TEXT,
  purchase_location_id INTEGER,
  cost_level TEXT,  -- '低' / '中' / '高'
  needs_restocking BOOLEAN,  -- 庫存警告
  assigned_user_id INTEGER,  -- A / B / NULL(兩人共用)
  notes TEXT,
  is_purchased BOOLEAN DEFAULT FALSE,
  purchased_at TIMESTAMP,
  FOREIGN KEY(shopping_list_id) REFERENCES shopping_list(id),
  FOREIGN KEY(ingredient_id) REFERENCES ingredient_library(id),
  FOREIGN KEY(purchase_location_id) REFERENCES purchase_locations(id),
  FOREIGN KEY(assigned_user_id) REFERENCES users(id)
);
```

#### 表 6e: shopping_list_history（採購歷史）
```sql
CREATE TABLE shopping_list_history (
  id INTEGER PRIMARY KEY,
  shopping_list_id INTEGER NOT NULL,
  original_item_id INTEGER,
  item_changes TEXT,  -- JSON 格式
  status_log TEXT,  -- JSON 格式
  archived_at TIMESTAMP,
  notes TEXT,
  FOREIGN KEY(shopping_list_id) REFERENCES shopping_list(id)
);
```

---

## API 設計

### 基礎信息

- **Base URL**: `http://localhost:8000/api`
- **認證**: 暫時不需要（2人私密系統）
- **回應格式**: JSON
- **錯誤處理**: HTTP 狀態碼 + 錯誤訊息

### API Endpoints

#### 👤 用戶 API

```
GET /users/:id
  功能: 取得用戶資料
  回應: { id, name, gender, age, height_cm, ... }

PUT /users/:id
  功能: 更新用戶資料（自動記錄目標歷史）
  輸入: { name, age, primary_goal, target_weight_kg, ... }
  回應: { success, user_data, goal_history_recorded }

GET /users/:id/history
  功能: 取得用戶的目標變化歷史
  回應: [{ goal_type, target_value, previous_value, set_date, ... }]

GET /users/:id/profile-complete
  功能: 檢查用戶資料是否完整
  回應: { complete, missing_fields: [...] }
```

#### ⚖️ 體重 API

```
POST /weight-records
  功能: 新增體重記錄
  輸入: { user_id, date, weight_kg, body_fat_percent?, waist_cm? }
  回應: { success, record_id }

GET /weight-records
  功能: 取得體重記錄（帶篩選）
  參數: ?user_id=1&date_start=2024-08-01&date_end=2024-08-07
  回應: [{ id, date, weight_kg, body_fat_percent, waist_cm, ... }]

PUT /weight-records/:id
  功能: 編輯體重記錄
  輸入: { weight_kg?, body_fat_percent?, waist_cm? }
  回應: { success, record }

DELETE /weight-records/:id
  功能: 刪除體重記錄
  回應: { success }
```

#### 🏃 運動 API

```
POST /exercise-sessions
  功能: 新增運動記錄
  輸入: { user_id, date, exercise_type, duration_min, intensity }
  回應: { success, session_id }

GET /exercise-sessions
  功能: 取得運動記錄
  參數: ?user_id=1&date_start=...&date_end=...&type=健身房
  回應: [{ id, date, exercise_type, duration_min, intensity, details: [...] }]

POST /exercise-sessions/:id/details
  功能: 新增訓練項目明細
  輸入: { exercise_item, sets, reps_or_duration, weight_kg? }
  回應: { success, detail_id }

GET /exercise-templates
  功能: 取得用戶的訓練模板列表
  參數: ?user_id=1
  回應: [{ id, template_name, description, details: [...] }]

POST /exercise-templates
  功能: 建立訓練模板
  輸入: { user_id, template_name, description, details: [...] }
  回應: { success, template_id }

PUT /exercise-templates/:id
  功能: 編輯訓練模板
  輸入: { template_name?, description?, details? }
  回應: { success, template }

DELETE /exercise-templates/:id
  功能: 刪除訓練模板
  回應: { success }

POST /daily-steps
  功能: 新增步數記錄
  輸入: { user_id, date, steps, source }
  回應: { success, record_id }

GET /daily-steps
  功能: 取得步數記錄
  參數: ?user_id=1&date_start=...&date_end=...
  回應: [{ date, steps, source }]
```

#### 🍽️ 食譜 API

```
GET /recipes
  功能: 瀏覽食譜庫
  參數: ?category=肉&cost_level=低&page=1&limit=20
  回應: { recipes: [...], total, page }

GET /recipes/search
  功能: 搜尋食譜
  參數: ?query=番茄&by=name|ingredient|category
  回應: [{ id, recipe_name, category, cost_level, base_weight_g, ... }]

POST /recipes
  功能: 新增食譜
  輸入: { 
    recipe_name, category, base_weight_g, cost_level,
    ingredients: [{ ingredient_id, quantity_g, unit }],
    steps: [{ step_number, step_description }]
  }
  回應: { success, recipe_id }

PUT /recipes/:id
  功能: 編輯食譜
  輸入: { recipe_name?, category?, cost_level?, is_active? }
  回應: { success, recipe }

GET /recipes/:id/steps
  功能: 取得食譜當前製作步驟
  回應: { recipe_id, steps: [{ step_number, description }], version }

POST /recipes/:id/steps
  功能: 新增製作步驟版本
  輸入: { steps: [{ step_number, step_description }] }
  回應: { success, new_version }

PUT /recipes/:id/steps/:version
  功能: 設定為當前版本
  回應: { success }

GET /recipes/:id/nutrition
  功能: 取得食譜營養資訊（自動計算）
  回應: { calories, protein_g, carbs_g, fat_g, fiber_g }
```

#### 🥘 食材 API

```
GET /ingredients
  功能: 瀏覽食材庫
  參數: ?category=蔬菜&page=1&limit=20
  回應: { ingredients: [...], total }

GET /ingredients/search
  功能: 搜尋食材
  參數: ?query=番茄&category=蔬菜
  回應: [{ id, ingredient_name, category, calories_per_100g, ... }]

POST /ingredients
  功能: 新增食材
  輸入: { 
    ingredient_name, category, unit,
    calories_per_100g, protein_per_100g, carbs_per_100g, fat_per_100g, fiber_per_100g,
    preferred_purchase_location?, needs_stock_tracking?
  }
  回應: { success, ingredient_id }

PUT /ingredients/:id
  功能: 編輯食材
  輸入: { 營養資訊... }
  回應: { success, ingredient }

GET /ingredients/:id/stock
  功能: 取得食材庫存
  回應: { current_quantity_g, min_threshold_g, last_purchased_at }

PUT /ingredients/:id/stock
  功能: 更新庫存
  輸入: { current_quantity_g?, min_threshold_g? }
  回應: { success, stock }

GET /ingredients/low-stock
  功能: 取得需要補購的食材
  回應: [{ ingredient_id, ingredient_name, current_qty, threshold, ... }]
```

#### 📋 週推薦 API

```
POST /meal-plans/generate
  功能: 觸發 Claude 生成週推薦
  輸入: { 
    week_start_date, 
    user_a_id, user_b_id,
    user_a_preselected?: [{ day, meal_type, recipe_id }],
    user_b_preselected?: [{ day, meal_type, recipe_id }]
  }
  回應: { 
    success, 
    plan_id, 
    meals: {
      Monday: { breakfast, lunch, afternoon_snack, dinner },
      ...
    },
    nutrition_summary: { calories, protein, carbs, fat }
  }

GET /meal-plans/:id
  功能: 取得週推薦詳情
  回應: {
    plan_id, plan_date, status,
    daily_details: [
      {
        meal_date, 
        meals: [{ meal_type, recipe_id, recipe_name, serving_weight_g, calories, protein, carbs, fat, steps }]
      }
    ]
  }

PUT /meal-plans/:id/adjust
  功能: 微調推薦
  輸入: {
    adjustment_type: 'replace' | 'reselect_day' | 'adjust_weight',
    target_day, meal_type,
    original_recipe_id?, adjusted_recipe_id?, new_weight_g?
  }
  回應: { success, updated_meal }

POST /meal-plans/:id/confirm
  功能: 確認週推薦（生成購物清單）
  回應: { success, shopping_list_id }
```

#### 🛒 購物清單 API

```
GET /shopping-lists/:id
  功能: 取得購物清單
  回應: {
    list_id, status, list_date, week_start_date,
    items_by_location: {
      "超市A": {
        category: "蔬菜",
        items: [{ ingredient_name, quantity_needed_g, cost_level, is_purchased }]
      },
      ...
    }
  }

POST /shopping-lists/:id/items
  功能: 新增購物項目
  輸入: { ingredient_id, quantity_needed_g, purchase_location_id?, assigned_user_id? }
  回應: { success, item_id }

PUT /shopping-lists/:id/items/:item_id
  功能: 編輯購物項目
  輸入: { quantity_needed_g?, purchase_location_id?, notes? }
  回應: { success, item }

DELETE /shopping-lists/:id/items/:item_id
  功能: 刪除購物項目
  回應: { success }

PUT /shopping-lists/:id/items/:item_id/purchased
  功能: 標記為已購
  輸入: { is_purchased: true }
  回應: { success }

PUT /shopping-lists/:id/status
  功能: 改變清單狀態
  輸入: { status: 'confirmed' | 'purchasing' | 'completed' | 'archived' }
  回應: { success, shopping_list }

GET /shopping-lists/history
  功能: 取得採購歷史
  參數: ?page=1&limit=10
  回應: { history: [...], total }
```

#### ⚙️ 設定 API

```
GET /purchase-locations
  功能: 取得購買地點列表
  回應: [{ id, location_name, description, priority_order }]

POST /purchase-locations
  功能: 新增購買地點
  輸入: { location_name, description?, priority_order? }
  回應: { success, location_id }

PUT /purchase-locations/:id
  功能: 編輯購買地點
  輸入: { location_name?, description?, priority_order?, is_active? }
  回應: { success, location }

DELETE /purchase-locations/:id
  功能: 刪除購買地點
  回應: { success }

GET /settings/export
  功能: 匯出全部數據（JSON 格式）
  回應: { users, weight_records, exercises, recipes, ingredients, meal_plans, shopping_lists }

POST /settings/import
  功能: 匯入數據
  輸入: multipart/form-data (JSON 檔案)
  回應: { success, imported_counts: { users: 2, recipes: 100, ... } }
```

---

## Claude 推薦邏輯

### 輸入數據結構（JSON）

```json
{
  "analysis_date": "2024-08-06",
  "week_start_date": "2024-08-05",
  
  "user_a": {
    "id": 1,
    "name": "小美",
    "gender": "女",
    "age": 25,
    "height_cm": 160,
    "current_weight_kg": 55,
    "target_weight_kg": 50,
    "primary_goal": "減脂",
    "activity_level": "中度",
    "current_menstrual_phase": "黃體期",
    "allergies": "堅果, 海鮮",
    "restrictions": "素食",
    "medical_conditions": "無",
    "sport_limitations": "無",
    "this_week_exercise": {
      "gym_sessions": 3,
      "walking_steps_total": 45000,
      "yoga_sessions": 2
    }
  },
  
  "user_b": {
    "id": 2,
    "name": "小明",
    "gender": "男",
    "age": 28,
    "height_cm": 175,
    "current_weight_kg": 75,
    "target_weight_kg": 80,
    "primary_goal": "增肌",
    "activity_level": "高度",
    "allergies": "無",
    "restrictions": "無",
    "this_week_exercise": {
      "gym_sessions": 4,
      "walking_steps_total": 60000,
      "yoga_sessions": 1
    }
  },
  
  "user_a_preselected_meals": [
    {"day": "Monday", "meal_type": "lunch", "recipe_id": 10}
  ],
  
  "user_b_preselected_meals": [],
  
  "recipe_database": [
    {
      "id": 10,
      "name": "番茄雞肉義大利麵",
      "category": "主食",
      "base_weight_g": 300,
      "cost_level": "低",
      "calories": 450,
      "protein_g": 35,
      "carbs_g": 45,
      "fat_g": 12,
      "fiber_g": 3,
      "ingredients": ["義大利麵", "番茄", "雞胸肉"],
      "is_vegetarian": false,
      "contains_allergens": []
    }
  ]
}
```

### 推薦邏輯步驟

1. **計算每人的熱量目標**
   - 使用 Harris-Benedict 公式計算 BMR
   - 根據 activity_level 計算 TDEE
   - 根據 primary_goal 調整（減脂-300~500, 增肌+200~300）
   - 根據本週運動量調整
   - 根據生理期調整（黃體期+150~200 kcal）

2. **設定營養目標比例**
   - 減脂：蛋白質 1.6-2.0g/kg，脂肪 25-30%，碳水剩餘
   - 增肌：蛋白質 2.0-2.2g/kg，脂肪 25-30%，碳水剩餘
   - 維持：蛋白質 1.4-1.6g/kg，脂肪 25-30%，碳水剩餘

3. **食譜篩選和推薦**
   - 檢查飲食限制和過敏
   - 計算午餐/晚餐的組合（主食+青菜+肉+可選副食）
   - 符合營養目標
   - 符合成本比例（高+中 < 低）
   - 考慮生理期（月經期推薦含鐵食譜）
   - 優先推薦重複食材（週一二四做飯）
   - 避免 7 天內重複菜色超過 2 次

4. **生成推薦結果**
   - 7 天完整菜單
   - 每餐的營養詳情
   - 製作步驟
   - 購物清單食材清單

### Claude Prompt 模板

```
你是一個專業的營養師和飲食規劃師。根據以下用戶數據和食譜資料庫，為 2 人生成最優化的一週飲食推薦。

【用戶 A 的目標】
- 目標：{primary_goal}
- 推薦熱量：{user_a_daily_calories} kcal/day
- 蛋白質：{user_a_protein_g}g/day
- 碳水：{user_a_carbs_g}g/day
- 脂肪：{user_a_fat_g}g/day
- 生理期：{user_a_menstrual_phase}
- 飲食限制：{user_a_restrictions}
- 過敏：{user_a_allergies}

【用戶 B 的目標】
...

【推薦規則】
1. 午餐/晚餐必須包含：1 主食 + 1 青菜 + 1 肉類 + 可選副食（飲料/點心）
2. 早餐：可選（推薦但不強制），只需選擇「早餐」分類食譜
3. 下午茶：每週要排，內容自由
4. 成本原則：本週推薦的「高」和「中」成本食譜合計 < 「低」成本食譜數量
5. 食材效率：優先推薦已在其他餐出現的食材（2 人做飯集中在週一、二、四）
6. 多樣性：同一食譜 7 天內最多出現 2 次
7. 生理期：
   - 月經期：推薦含鐵食譜（紅肉、菠菜、黑木耳）
   - 黃體期：推薦高蛋白食譜
   - 其他時期：自由推薦

【食譜資料庫】
[已預先提供的食譜 JSON]

【用戶 A 已預選菜色】
{user_a_preselected_meals}

【用戶 B 已預選菜色】
{user_b_preselected_meals}

【輸出格式】
請只返回有效的 JSON（不含任何 Markdown 或額外文本），結構如下：

{
  "success": true,
  "recommendation": {
    "week_start_date": "2024-08-05",
    "user_a_daily_calories": 1400,
    "user_b_daily_calories": 2300,
    "days": [
      {
        "day": "Monday",
        "meals": [
          {
            "meal_type": "早餐",
            "user": "A",
            "recipe_id": 5,
            "recipe_name": "燕麥粥",
            "serving_weight_g": 150,
            "calories": 250,
            "protein_g": 8,
            "carbs_g": 45,
            "fat_g": 3
          },
          ...
        ],
        "day_total_calories_a": 1400,
        "day_total_calories_b": 2300
      },
      ...
    ],
    "shopping_ingredients": [
      {
        "ingredient_id": 1,
        "ingredient_name": "雞胸肉",
        "total_quantity_g": 530,
        "cost_level": "中"
      },
      ...
    ],
    "notes": "推薦說明..."
  }
}
```

---

## 系統流程

### 週推薦完整流程

```
1️⃣ 用戶準備階段
   ├─ 輸入本週體重、體脂肪、腰圍
   ├─ 確認運動記錄（健身房、走路、瑜珈）
   └─ 可選：預選部分菜色

2️⃣ 搜尋和手選菜色
   ├─ 搜尋食譜（按名稱、食材、分類、成本）
   ├─ 決定某些天的菜色（例：週一午餐要吃 XX）
   └─ 記錄用戶預選

3️⃣ Claude 推薦補足
   ├─ 後端打包用戶數據、運動、預選、食譜庫
   ├─ 調用 Claude API
   ├─ Claude 返回推薦結果（JSON）
   └─ 後端解析並存入資料庫

4️⃣ 預覽推薦結果
   ├─ 展示簡表（週一～週日的菜色概覽）
   ├─ 用戶可點擊展開「日詳情」
   └─ 展示營養總結

5️⃣ 微調推薦
   ├─ 微調方式 A：替換單菜色
   │   └─ 推薦類似營養的替代菜色
   ├─ 微調方式 B：重新推薦整天
   │   └─ Claude 根據其他 6 天已確認重新推薦
   ├─ 微調方式 C：搜尋替換
   │   └─ 用戶搜尋想要的菜色 → 替換某一餐
   └─ 微調方式 D：調整分量
       └─ 修改 serving_weight_g → 自動重新計算營養

6️⃣ 確認推薦
   ├─ 用戶點「確認推薦」
   ├─ 推薦狀態改為「已確認」
   └─ 自動觸發購物清單生成

7️⃣ 購物清單生成
   ├─ 計算 2 人所需食材總量
   ├─ 根據偏好分配購買地點
   ├─ 檢查庫存，標記需補購
   ├─ 按「購買地點 → 食材分類」組織
   └─ 輸出購物清單（草稿狀態）

8️⃣ 購物清單微調
   ├─ 新增臨時食材
   ├─ 刪除不需要的項目
   ├─ 調整用量
   ├─ 改變購買地點
   └─ 添加備註

9️⃣ 確認採購
   ├─ 點「確認清單」
   ├─ 狀態改為「已確認」
   └─ 記錄確認時間

🔟 採購跟蹤
   ├─ 邊採購邊勾選完成
   ├─ 系統記錄已購項目和時間
   └─ 全部採購完後標記「已採購」
```

---

## 區塊劃分

根據系統的模組化設計，建議分為以下 **7 個開發區塊**：

### 📦 區塊 1：數據庫和初始化
**目標**：建立 SQLite 資料庫，創建所有 25+ 個表  
**輸出**：`database.db` + `schema.sql` + 初始化腳本  
**依賴**：無  
**後續依賴**：所有其他區塊

**包含內容**：
- SQLite 資料庫創建
- 所有表的 DDL 語句
- 預設食材庫初始化（100+ 常用食材）
- 預設食譜庫初始化（50+ 常用食譜）
- 預設訓練項目庫
- 預設瑜珈/拉伸項目庫
- 預設購買地點

---

### 🔧 區塊 2：Backend 核心框架和用戶管理
**目標**：FastAPI 框架搭建、用戶 CRUD、個人資料管理  
**輸出**：FastAPI 服務器 + 用戶 API endpoints  
**依賴**：區塊 1  
**後續依賴**：區塊 3、4、5、6、7

**包含內容**：
- FastAPI 基礎設置
- SQLAlchemy ORM 配置
- 用戶表 CRUD（表 1、1a、4、5x）
- 用戶管理 API endpoints
- 目標歷史自動記錄邏輯
- 生理期計算邏輯

---

### ⚖️ 區塊 3：體重和運動追蹤
**目標**：體重、運動、步數、訓練模板管理  
**輸出**：體重和運動相關 API endpoints  
**依賴**：區塊 1、2  
**後續依賴**：區塊 6（推薦邏輯需要運動數據）

**包含內容**：
- 體重記錄 CRUD（表 2）
- 運動紀錄管理（表 3a、3b、3c、3d、3e、3f、3g）
- 訓練模板建立、編輯、套用邏輯
- 步數記錄管理
- 本週運動統計計算

---

### 🍽️ 區塊 4：食譜和食材管理
**目標**：食譜庫、食材庫、食譜搜尋、版本控制  
**輸出**：食譜和食材相關 API endpoints  
**依賴**：區塊 1、2  
**後續依賴**：區塊 6（推薦引擎需要）

**包含內容**：
- 食譜 CRUD（表 5a）
- 食譜食材明細管理（表 5b）
- 製作步驟版本控制（表 5c）
- 營養素自動計算邏輯（表 5d）
- 食材庫管理（表 5i）
- 食材庫存追蹤（表 5e）
- 搜尋和篩選功能（名稱、食材、分類、成本、過敏）
- 低庫存警告邏輯

---

### 🧠 區塊 5：Claude 推薦引擎
**目標**：整合 Claude API，實現週推薦邏輯  
**輸出**：推薦服務 + /meal-plans/generate endpoint  
**依賴**：區塊 1、2、3、4  
**後續依賴**：區塊 6、7

**包含內容**：
- TDEE 和熱量目標計算
- 營養素目標分配邏輯
- 數據打包成 Claude 需要的 JSON 格式
- Claude API 調用和結果解析
- 推薦結果存入資料庫（表 5f、5g、5h）
- 微調邏輯（替換、重推、搜尋替換、調整分量）
- 生理期影響調整

---

### 🛒 區塊 6：購物清單管理
**目標**：購物清單生成、編輯、採購跟蹤  
**輸出**：購物清單相關 API endpoints  
**依賴**：區塊 1、2、4、5  
**後續依賴**：無（但與區塊 7 前端共同使用）

**包含內容**：
- 購買地點庫管理（表 6a）
- 食材偏好設定（表 6b）
- 購物清單自動生成（表 6c）
- 購物項目管理（表 6d）
- 按購買地點分類邏輯
- 需補購標記邏輯
- 成本等級標記
- 2 人食材合併計算
- 採購歷史記錄（表 6e）
- 購物清單微調功能

---

### 🎨 區塊 7：Web UI 前端
**目標**：React/Vue 前端應用，實現所有用戶介面  
**輸出**：Web 應用 + PWA 支援  
**依賴**：區塊 2、3、4、5、6（所有後端 API）  
**後續依賴**：無

**包含內容**：
- React/Vue 專案初始化
- PWA 配置（manifest.json、service worker）
- 路由設置（Dashboard、Profile、Weight、Exercise、Meals、Shopping、Recipes、Ingredients、Settings）
- 儀表板模組（可自訂卡片）
- 個人資料編輯表單
- 體重輸入（Smart 表單）
- 運動記錄頁面
- 食譜搜尋和管理
- 週推薦 UI（簡表 + 日詳情 + 微調界面）
- 購物清單 UI（按地點分類）
- 設定頁面
- 趨勢圖表（Chart.js 或 Recharts）
- API 調用層（Axios 或 Fetch）
- 狀態管理（Redux、Vuex 或 Context API）

---

## 開發順序建議

```
1. 區塊 1（數據庫）- 基礎，必須先做
   ↓
2. 區塊 2（Backend 框架 + 用戶管理）- 基礎服務
   ↓
3. 區塊 3（體重和運動）+ 區塊 4（食譜和食材）- 並行可做
   ↓
4. 區塊 5（Claude 推薦引擎）- 依賴 3 和 4
   ↓
5. 區塊 6（購物清單）- 依賴 4 和 5
   ↓
6. 區塊 7（Web 前端）- 最後做，依賴所有後端
```

---

## 文件版本控制

- **版本**：1.0
- **最後更新**：2024-08-06
- **架構確認狀態**：✅ 所有 6 個架構已確認
- **準備開始編碼**：是

---
