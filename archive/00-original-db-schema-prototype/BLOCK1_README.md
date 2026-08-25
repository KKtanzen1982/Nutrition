# 區塊 1：數據庫和初始化

## 📋 概述

**目標**：建立SQLite資料庫，創建所有25+個表並加載種子數據

**輸出物**：
- `nutrition_system.db` - SQLite數據庫文件
- `schema.sql` - 完整數據庫架構定義
- `init_db.py` - 初始化和種子數據加載腳本
- `requirements.txt` - Python依賴

**依賴**：無

**後續依賴**：所有其他區塊（2-7）

---

## 📁 文件清單

### 1. `schema.sql`
完整的SQLite DDL文件，包含：
- **25個數據表**
  - 用戶和目標管理（4個表）
  - 體重追蹤（1個表）
  - 運動追蹤（7個表）
  - 食材管理（2個表）
  - 食譜管理（4個表）
  - 購買地點管理（2個表）
  - 週推薦和購物清單（7個表）
  - 版本控制（1個表）

- **性能索引**（15個索引）
  - 用戶查詢優化
  - 日期範圍查詢優化
  - 分類篩選優化

- **便利視圖**（3個視圖）
  - `user_latest_weight` - 用戶最新體重
  - `recipe_complete_info` - 食譜完整信息
  - `low_stock_ingredients` - 低庫存食材

### 2. `init_db.py`
Python初始化腳本，自動：
- 創建SQLite數據庫
- 加載架構（schema.sql）
- 填充種子數據：
  - **5個購買地點**（全聯、美廉社、好市多等）
  - **100+個常用食材**（含營養信息）
    - 20個肉類/豆類
    - 15個穀物
    - 30個蔬菜
    - 15個水果
    - 10個調味料
    - 10個其他
  - **25個訓練項目**（分類訓練）
  - **20個瑜珈/拉伸項目**
  - 初始化所有食材庫存

### 3. `requirements.txt`
Python環境依賴配置

---

## 🚀 快速開始

### 前置要求
- Python 3.8+
- pip（Python包管理）
- SQLite3（通常已內置）

### 安裝步驟

#### 1. 創建虛擬環境（推薦）
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

#### 2. 安裝依賴
```bash
pip install -r requirements.txt
```

#### 3. 運行初始化腳本
```bash
python init_db.py
```

**預期輸出**：
```
======================================================================
飲食管理系統 - 數據庫初始化
======================================================================
✓ 數據庫連接成功: nutrition_system.db
✓ 數據庫架構加載成功
✓ 記錄架構版本
✓ 加載 5 個購買地點
✓ 加載 100+ 個食材
✓ 加載 25 個訓練項目
✓ 加載 20 個瑜珈/拉伸項目
✓ 初始化 100+ 個食材庫存

======================================================================
✓ 數據庫初始化完成！
  數據庫文件: /current/path/nutrition_system.db
  已加載:
    - 購買地點: 5
    - 食材: 100+
    - 訓練項目: 25
    - 瑜珈/拉伸項目: 20
======================================================================
```

#### 4. 驗證數據庫
```bash
# 使用SQLite CLI查看
sqlite3 nutrition_system.db

# 在SQLite shell中執行
sqlite> SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;
sqlite> SELECT COUNT(*) FROM ingredient_library;
sqlite> SELECT COUNT(*) FROM purchase_locations;
sqlite> .quit
```

或使用Python驗證：
```python
import sqlite3
conn = sqlite3.connect('nutrition_system.db')
cursor = conn.cursor()

# 查看所有表
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
tables = cursor.fetchall()
print(f"總表數: {len(tables)}")
for table in tables:
    print(f"  - {table[0]}")

# 查看食材數量
cursor.execute("SELECT COUNT(*) FROM ingredient_library")
print(f"食材數: {cursor.fetchone()[0]}")

conn.close()
```

---

## 📊 數據庫架構詳解

### 表分組結構

#### A. 用戶和目標管理（4個表）
```
users                      用戶基本信息
├── user_goal_history      目標變化歷史
├── dietary_preferences    飲食偏好
└── user_sport_preferences 運動偏好
```

#### B. 體重追蹤（1個表）
```
weight_records             體重、體脂、腰圍記錄
```

#### C. 運動追蹤（7個表）
```
exercise_sessions          運動會話主記錄
├── exercise_details       訓練項目明細
├── exercise_item_library  訓練項目庫
├── workout_templates      訓練模板
├── template_details       模板詳細項目
├── daily_steps            每日步數
└── yoga_stretch_items     瑜珈/拉伸項目
```

#### D. 食材管理（2個表）
```
ingredient_library         食材庫（營養信息）
└── ingredient_stock       食材庫存
```

#### E. 食譜管理（4個表）
```
recipes                    食譜庫
├── recipe_ingredients     食譜食材明細
├── recipe_steps          製作步驟（版本控制）
└── recipe_nutrition      營養素自動計算
```

#### F. 購買管理（2個表）
```
purchase_locations         購買地點庫
└── ingredient_location_preference 食材偏好地點
```

#### G. 週推薦和購物（7個表）
```
weekly_meal_plan          週菜單主記錄
├── daily_meal_detail     日菜單詳情
├── meal_adjustments      推薦微調記錄
├── shopping_list         購物清單主表
├── shopping_list_items   購物項目明細
└── shopping_list_history 採購歷史
```

#### H. 系統（1個表）
```
schema_version            數據庫版本控制
```

---

## 🗂️ 種子數據概況

### 購買地點（5個）
| 地點 | 優先級 | 說明 |
|------|------|------|
| 全聯超市 | 1 | 常用超市，商品齊全 |
| 美廉社 | 2 | 便利，步行可達 |
| 好市多 | 3 | 大宗採購，較便宜 |
| 傳統菜市場 | 4 | 蔬菜水果新鮮 |
| 網購平台 | 5 | 方便送達，部分食材 |

### 食材分類（100+個）
- **肉類/豆類**（20個）：雞肉、豬肉、牛肉、魚、蝦、蛋、豆腐、豆漿、牛奶、起司、豆類
- **穀物**（15個）：白米、糙米、燕麥、麵粉、義大利麵、麵包、玉米、地瓜
- **蔬菜**（30個）：西蘭花、番茄、菠菜、胡蘿蔔、洋蔥、青椒、蘑菇等
- **水果**（15個）：蘋果、香蕉、橙、葡萄、草莓、芒果等
- **調味料**（10個）：油、鹽、醬油、醋、味噌、蜂蜜等
- **其他**（10個）：花生醬、咖啡、茶、海帶等

### 訓練項目（25個）
分類：
- 胸部訓練（4個）：俯臥撑、臥推、上斜臥推、蝴蝶機
- 背部訓練（4個）：拉力下拉、槓鈴划船、引體向上等
- 下肢訓練（7個）：蹲舉、腿舉、硬舉、提踵等
- 手臂訓練（4個）：彎舉、三頭肌訓練等
- 核心訓練（4個）：平板支撐、仰臥起坐、俄羅斯轉體等
- 有氧運動（3個）：跑步機、橢圓機、划船機

### 瑜珈/拉伸項目（20個）
瑜珈（10個）：太陽式敬禮、樹式、下犬式、戰士式等
拉伸（10個）：頸部、肩部、腰部、腿部等伸展

---

## 🔍 驗證檢查清單

初始化完成後，建議進行以下檢查：

### 1. 表創建檢查
```sql
SELECT COUNT(*) as table_count FROM sqlite_master WHERE type='table';
-- 預期結果: 25
```

### 2. 索引檢查
```sql
SELECT COUNT(*) as index_count FROM sqlite_master WHERE type='index';
-- 預期結果: 15+
```

### 3. 視圖檢查
```sql
SELECT COUNT(*) as view_count FROM sqlite_master WHERE type='view';
-- 預期結果: 3
```

### 4. 食材數據檢查
```sql
SELECT category, COUNT(*) as count 
FROM ingredient_library 
GROUP BY category;
```

### 5. 訓練項目檢查
```sql
SELECT COUNT(*) FROM exercise_item_library;
-- 預期結果: 25
```

### 6. 種子數據統計
```sql
SELECT 
  (SELECT COUNT(*) FROM ingredient_library) as 食材總數,
  (SELECT COUNT(*) FROM exercise_item_library) as 訓練項目,
  (SELECT COUNT(*) FROM yoga_stretch_items) as 瑜珈拉伸,
  (SELECT COUNT(*) FROM purchase_locations) as 購買地點,
  (SELECT COUNT(*) FROM ingredient_stock) as 庫存記錄;
```

---

## 🔐 數據完整性約束

### 外鍵關係
- `user_goal_history` → `users`
- `dietary_preferences` → `users`
- `user_sport_preferences` → `users`
- `weight_records` → `users`
- `exercise_sessions` → `users`
- `exercise_details` → `exercise_sessions`
- `daily_steps` → `users`
- `workout_templates` → `users`
- `template_details` → `workout_templates`
- `ingredient_stock` → `ingredient_library`
- `recipe_ingredients` → `recipes` 和 `ingredient_library`
- `recipe_steps` → `recipes`
- `recipe_nutrition` → `recipes`
- `ingredient_location_preference` → `ingredient_library` 和 `purchase_locations`

### 唯一性約束
- `users` - 主鍵
- `dietary_preferences.user_id` - 一對一
- `user_sport_preferences` - (user_id, sport_type)
- `weight_records` - (user_id, date)
- `ingredient_library.ingredient_name`
- `recipes.recipe_name`
- `workout_templates` - (user_id, template_name)
- `daily_steps` - (user_id, date)
- `purchase_locations.location_name`
- `ingredient_location_preference` - (ingredient_id, preferred_location_id)

---

## 🛠️ 故障排除

### 問題1：數據庫文件已存在
**症狀**：運行 `init_db.py` 時提示要求確認

**解決**：
```bash
# 方式1：手動刪除
rm nutrition_system.db
python init_db.py

# 方式2：按提示選擇 'y' 重建
python init_db.py
# 按 'y' 確認刪除
```

### 問題2：找不到 schema.sql
**症狀**：`FileNotFoundError: schema.sql`

**解決**：確保 `schema.sql` 和 `init_db.py` 在同一目錄
```bash
ls -la
# 應該看到：
# schema.sql
# init_db.py
# requirements.txt
```

### 問題3：SQLite導入錯誤
**症狀**：`ModuleNotFoundError: No module named 'sqlite3'`

**解決**：SQLite3通常內置於Python。如果缺失，安裝：
```bash
# Windows
python -m pip install db-sqlite3

# macOS / Linux
# 通常無需操作
```

### 問題4：權限拒絕
**症狀**：`PermissionError: [Errno 13]`

**解決**：
```bash
# 確保腳本可執行
chmod +x init_db.py

# 或直接用Python運行
python init_db.py
```

---

## 📈 後續步驟

區塊1完成後，進行下一步開發：

### 區塊2：Backend 核心框架和用戶管理
- FastAPI服務器設置
- SQLAlchemy ORM配置
- 用戶CRUD API

### 推薦順序
1. ✅ **區塊1** - 數據庫（已完成）
2. ⬜ **區塊2** - Backend框架
3. ⬜ **區塊3** - 體重和運動追蹤
4. ⬜ **區塊4** - 食譜和食材管理
5. ⬜ **區塊5** - Claude推薦引擎
6. ⬜ **區塊6** - 購物清單管理
7. ⬜ **區塊7** - Web UI前端

---

## 📞 支持和反饋

如有問題或改進建議，請參考主文檔：`nutrition_system_architecture.md`

---

## 📄 版本信息

- **版本**：1.0
- **最後更新**：2024-08-06
- **狀態**：✅ 完成並測試

---
