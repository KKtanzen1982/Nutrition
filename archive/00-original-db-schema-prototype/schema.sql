-- ============================================================================
-- 飲食管理系統 - SQLite 數據庫架構
-- 版本: 1.0
-- 創建日期: 2024-08-06
-- ============================================================================

-- ============================================================================
-- 第1部分：用戶和目標管理
-- ============================================================================

-- 表1: 用戶基本資料
CREATE TABLE users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  gender TEXT NOT NULL CHECK(gender IN ('男', '女', '其他')),
  age INTEGER NOT NULL,
  height_cm INTEGER NOT NULL,
  primary_goal TEXT NOT NULL CHECK(primary_goal IN ('減脂', '增肌', '維持')),
  activity_level TEXT NOT NULL CHECK(activity_level IN ('久坐', '輕度', '中度', '高度')),
  menstrual_cycle_length_days INTEGER,
  last_menstrual_date DATE,
  menstrual_cycle_irregular BOOLEAN DEFAULT FALSE,
  medical_conditions TEXT,
  sport_limitations TEXT,
  notes TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 表1a: 用戶目標變化歷史
CREATE TABLE user_goal_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  goal_type TEXT NOT NULL CHECK(goal_type IN ('weight', 'body_fat', 'waist_circumference')),
  target_value REAL NOT NULL,
  previous_value REAL,
  set_date DATE NOT NULL,
  achieved BOOLEAN DEFAULT FALSE,
  achievement_date DATE,
  notes TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 表4: 飲食偏好
CREATE TABLE dietary_preferences (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL UNIQUE,
  allergies TEXT,
  restrictions TEXT,
  preferences TEXT,
  notes TEXT,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 表5x: 用戶運動偏好設定
CREATE TABLE user_sport_preferences (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  sport_type TEXT NOT NULL CHECK(sport_type IN ('健身房', '走路', '瑜珈', '拉伸')),
  target_frequency_per_week INTEGER,
  experience_level TEXT CHECK(experience_level IN ('初級', '中級', '進階')),
  sport_limitations TEXT,
  notes TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
  UNIQUE(user_id, sport_type)
);

-- ============================================================================
-- 第2部分：體重追蹤
-- ============================================================================

-- 表2: 體重日誌
CREATE TABLE weight_records (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  date DATE NOT NULL,
  weight_kg REAL NOT NULL,
  body_fat_percent REAL,
  waist_cm REAL,
  note TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
  UNIQUE(user_id, date)
);

-- ============================================================================
-- 第3部分：運動追蹤
-- ============================================================================

-- 表3a: 運動日期紀錄
CREATE TABLE exercise_sessions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  date DATE NOT NULL,
  exercise_type TEXT NOT NULL CHECK(exercise_type IN ('健身房', '走路', '瑜珈', '拉伸')),
  duration_min INTEGER,
  intensity TEXT CHECK(intensity IN ('低', '中', '高')),
  notes TEXT,
  synced_from TEXT CHECK(synced_from IN ('手動輸入', 'Apple Health', 'Google Fit')),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 表3b: 訓練項目明細
CREATE TABLE exercise_details (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  exercise_session_id INTEGER NOT NULL,
  exercise_item TEXT NOT NULL,
  sets INTEGER,
  reps_or_duration TEXT,
  weight_kg REAL,
  notes TEXT,
  FOREIGN KEY(exercise_session_id) REFERENCES exercise_sessions(id) ON DELETE CASCADE
);

-- 表3c: 訓練項目庫
CREATE TABLE exercise_item_library (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  item_name TEXT NOT NULL UNIQUE,
  category TEXT,
  description TEXT,
  default_sets INTEGER,
  default_reps INTEGER,
  muscle_group TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 表3d: 訓練組合模板
CREATE TABLE workout_templates (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  template_name TEXT NOT NULL,
  description TEXT,
  notes TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
  UNIQUE(user_id, template_name)
);

-- 表3e: 模板詳細項目
CREATE TABLE template_details (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  template_id INTEGER NOT NULL,
  exercise_item TEXT NOT NULL,
  order_number INTEGER,
  sets INTEGER,
  reps_or_duration TEXT,
  weight_kg REAL,
  notes TEXT,
  FOREIGN KEY(template_id) REFERENCES workout_templates(id) ON DELETE CASCADE
);

-- 表3f: 每日步數紀錄
CREATE TABLE daily_steps (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  date DATE NOT NULL,
  steps INTEGER,
  source TEXT CHECK(source IN ('手動輸入', 'Apple Health', 'Google Fit')),
  synced_at TIMESTAMP,
  notes TEXT,
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
  UNIQUE(user_id, date)
);

-- 表3g: 瑜珈拉伸項目庫
CREATE TABLE yoga_stretch_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  type TEXT NOT NULL CHECK(type IN ('瑜珈', '拉伸')),
  item_name TEXT NOT NULL UNIQUE,
  duration_min INTEGER,
  description TEXT,
  difficulty TEXT CHECK(difficulty IN ('初級', '中級', '進階')),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 第4部分：食材管理
-- ============================================================================

-- 表5i: 食材庫
CREATE TABLE ingredient_library (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ingredient_name TEXT NOT NULL UNIQUE,
  category TEXT NOT NULL CHECK(category IN ('蔬菜', '肉類', '穀物', '乳製品', '調味料', '其他')),
  unit TEXT,
  calories_per_100g REAL,
  protein_per_100g REAL,
  carbs_per_100g REAL,
  fat_per_100g REAL,
  fiber_per_100g REAL,
  preferred_purchase_location TEXT,
  needs_stock_tracking BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 表5e: 食材庫存
CREATE TABLE ingredient_stock (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ingredient_id INTEGER NOT NULL UNIQUE,
  current_quantity_g REAL,
  min_threshold_g REAL,
  unit TEXT,
  last_purchased_at DATE,
  notes TEXT,
  FOREIGN KEY(ingredient_id) REFERENCES ingredient_library(id) ON DELETE CASCADE
);

-- ============================================================================
-- 第5部分：食譜管理
-- ============================================================================

-- 表5a: 食譜庫
CREATE TABLE recipes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  recipe_name TEXT NOT NULL UNIQUE,
  category TEXT NOT NULL CHECK(category IN ('早餐', '主食', '肉', '菜', '飲料', '點心')),
  base_weight_g INTEGER,
  cost_level TEXT CHECK(cost_level IN ('低', '中', '高')),
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 表5b: 食譜食材明細
CREATE TABLE recipe_ingredients (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  recipe_id INTEGER NOT NULL,
  ingredient_id INTEGER NOT NULL,
  quantity_g REAL NOT NULL,
  unit TEXT,
  notes TEXT,
  FOREIGN KEY(recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
  FOREIGN KEY(ingredient_id) REFERENCES ingredient_library(id) ON DELETE CASCADE
);

-- 表5c: 製作步驟 - 版本控制
CREATE TABLE recipe_steps (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  recipe_id INTEGER NOT NULL,
  version INTEGER NOT NULL,
  step_number INTEGER NOT NULL,
  step_description TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  is_current BOOLEAN DEFAULT FALSE,
  FOREIGN KEY(recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);

-- 表5d: 食譜營養素資訊 - 自動計算
CREATE TABLE recipe_nutrition (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  recipe_id INTEGER NOT NULL UNIQUE,
  total_calories_kcal REAL,
  protein_g REAL,
  carbs_g REAL,
  fat_g REAL,
  fiber_g REAL,
  calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);

-- ============================================================================
-- 第6部分：購買地點管理
-- ============================================================================

-- 表6a: 購買地點庫
CREATE TABLE purchase_locations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  location_name TEXT NOT NULL UNIQUE,
  description TEXT,
  priority_order INTEGER,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 表6b: 食材地點偏好
CREATE TABLE ingredient_location_preference (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ingredient_id INTEGER NOT NULL,
  preferred_location_id INTEGER NOT NULL,
  priority INTEGER CHECK(priority IN (1, 2, 3)),
  notes TEXT,
  FOREIGN KEY(ingredient_id) REFERENCES ingredient_library(id) ON DELETE CASCADE,
  FOREIGN KEY(preferred_location_id) REFERENCES purchase_locations(id) ON DELETE CASCADE,
  UNIQUE(ingredient_id, preferred_location_id)
);

-- ============================================================================
-- 第7部分：週推薦和購物清單
-- ============================================================================

-- 表5f: 週菜單安排
CREATE TABLE weekly_meal_plan (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  plan_date DATE NOT NULL,
  user_id_a INTEGER NOT NULL,
  user_id_b INTEGER NOT NULL,
  breakfast_recipe_id INTEGER,
  lunch_recipe_id INTEGER,
  afternoon_snack_recipe_id INTEGER,
  dinner_recipe_id INTEGER,
  plan_status TEXT CHECK(plan_status IN ('草稿', '待微調', '已確認')),
  claude_generated BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(user_id_a) REFERENCES users(id),
  FOREIGN KEY(user_id_b) REFERENCES users(id),
  UNIQUE(plan_date, user_id_a, user_id_b)
);

-- 表5g: 日菜單詳情
CREATE TABLE daily_meal_detail (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  meal_plan_id INTEGER NOT NULL,
  meal_date DATE NOT NULL,
  meal_type TEXT NOT NULL CHECK(meal_type IN ('早餐', '主食', '肉', '菜', '下午茶')),
  recipe_id INTEGER NOT NULL,
  assigned_user_id INTEGER NOT NULL,
  serving_weight_g REAL,
  total_calories REAL,
  protein_g REAL,
  carbs_g REAL,
  fat_g REAL,
  notes TEXT,
  FOREIGN KEY(meal_plan_id) REFERENCES weekly_meal_plan(id) ON DELETE CASCADE,
  FOREIGN KEY(recipe_id) REFERENCES recipes(id),
  FOREIGN KEY(assigned_user_id) REFERENCES users(id)
);

-- 表5h: 推薦微調紀錄
CREATE TABLE meal_adjustments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  plan_id INTEGER NOT NULL,
  adjustment_type TEXT CHECK(adjustment_type IN ('替換', '刪除', '新增')),
  original_recipe_id INTEGER,
  adjusted_recipe_id INTEGER,
  reason TEXT,
  adjusted_by TEXT CHECK(adjusted_by IN ('A', 'B', 'System')),
  adjusted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(plan_id) REFERENCES weekly_meal_plan(id) ON DELETE CASCADE
);

-- 表6c: 購物清單主表
CREATE TABLE shopping_list (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  list_date DATE NOT NULL,
  week_start_date DATE NOT NULL,
  created_from_plan_id INTEGER,
  status TEXT CHECK(status IN ('草稿', '已確認', '採購中', '已採購', '歸檔')),
  total_items INTEGER,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  notes TEXT,
  FOREIGN KEY(created_from_plan_id) REFERENCES weekly_meal_plan(id)
);

-- 表6d: 購物項目明細
CREATE TABLE shopping_list_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  shopping_list_id INTEGER NOT NULL,
  ingredient_id INTEGER NOT NULL,
  quantity_needed_g REAL NOT NULL,
  unit TEXT,
  purchase_location_id INTEGER,
  cost_level TEXT CHECK(cost_level IN ('低', '中', '高')),
  needs_restocking BOOLEAN DEFAULT FALSE,
  assigned_user_id INTEGER,
  notes TEXT,
  is_purchased BOOLEAN DEFAULT FALSE,
  purchased_at TIMESTAMP,
  FOREIGN KEY(shopping_list_id) REFERENCES shopping_list(id) ON DELETE CASCADE,
  FOREIGN KEY(ingredient_id) REFERENCES ingredient_library(id),
  FOREIGN KEY(purchase_location_id) REFERENCES purchase_locations(id),
  FOREIGN KEY(assigned_user_id) REFERENCES users(id)
);

-- 表6e: 購物清單歷史
CREATE TABLE shopping_list_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  shopping_list_id INTEGER NOT NULL,
  original_item_id INTEGER,
  item_changes TEXT,
  status_log TEXT,
  archived_at TIMESTAMP,
  notes TEXT,
  FOREIGN KEY(shopping_list_id) REFERENCES shopping_list(id) ON DELETE CASCADE
);

-- ============================================================================
-- 索引 - 性能優化
-- ============================================================================

-- 用戶相關索引
CREATE INDEX idx_users_gender ON users(gender);
CREATE INDEX idx_users_primary_goal ON users(primary_goal);

-- 體重相關索引
CREATE INDEX idx_weight_records_user_date ON weight_records(user_id, date);

-- 運動相關索引
CREATE INDEX idx_exercise_sessions_user_date ON exercise_sessions(user_id, date);
CREATE INDEX idx_exercise_sessions_type ON exercise_sessions(exercise_type);
CREATE INDEX idx_daily_steps_user_date ON daily_steps(user_id, date);

-- 食譜相關索引
CREATE INDEX idx_recipes_category ON recipes(category);
CREATE INDEX idx_recipes_cost_level ON recipes(cost_level);
CREATE INDEX idx_recipe_ingredients_recipe ON recipe_ingredients(recipe_id);
CREATE INDEX idx_recipe_ingredients_ingredient ON recipe_ingredients(ingredient_id);

-- 食材相關索引
CREATE INDEX idx_ingredient_library_category ON ingredient_library(category);
CREATE INDEX idx_ingredient_stock_ingredient ON ingredient_stock(ingredient_id);

-- 購物清單相關索引
CREATE INDEX idx_shopping_list_date ON shopping_list(list_date);
CREATE INDEX idx_shopping_list_status ON shopping_list(status);
CREATE INDEX idx_shopping_list_items_list ON shopping_list_items(shopping_list_id);
CREATE INDEX idx_shopping_list_items_ingredient ON shopping_list_items(ingredient_id);

-- 週菜單相關索引
CREATE INDEX idx_weekly_meal_plan_date ON weekly_meal_plan(plan_date);
CREATE INDEX idx_weekly_meal_plan_users ON weekly_meal_plan(user_id_a, user_id_b);
CREATE INDEX idx_daily_meal_detail_plan ON daily_meal_detail(meal_plan_id);
CREATE INDEX idx_daily_meal_detail_date ON daily_meal_detail(meal_date);

-- ============================================================================
-- 視圖 - 數據查詢便利
-- ============================================================================

-- 用戶的最新體重記錄視圖
CREATE VIEW user_latest_weight AS
SELECT 
  user_id,
  date,
  weight_kg,
  body_fat_percent,
  waist_cm
FROM weight_records
WHERE (user_id, date) IN (
  SELECT user_id, MAX(date)
  FROM weight_records
  GROUP BY user_id
);

-- 食譜完整信息視圖
CREATE VIEW recipe_complete_info AS
SELECT 
  r.id,
  r.recipe_name,
  r.category,
  r.base_weight_g,
  r.cost_level,
  r.is_active,
  COUNT(DISTINCT ri.ingredient_id) as ingredient_count,
  rn.total_calories_kcal,
  rn.protein_g,
  rn.carbs_g,
  rn.fat_g,
  rn.fiber_g
FROM recipes r
LEFT JOIN recipe_ingredients ri ON r.id = ri.recipe_id
LEFT JOIN recipe_nutrition rn ON r.id = rn.recipe_id
GROUP BY r.id;

-- 低庫存食材視圖
CREATE VIEW low_stock_ingredients AS
SELECT 
  il.id,
  il.ingredient_name,
  il.category,
  igs.current_quantity_g,
  igs.min_threshold_g,
  igs.last_purchased_at
FROM ingredient_library il
JOIN ingredient_stock igs ON il.id = igs.ingredient_id
WHERE igs.current_quantity_g < igs.min_threshold_g;

-- ============================================================================
-- 數據庫架構版本控制表
-- ============================================================================

CREATE TABLE schema_version (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  version_number TEXT NOT NULL UNIQUE,
  description TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  applied_at TIMESTAMP
);
