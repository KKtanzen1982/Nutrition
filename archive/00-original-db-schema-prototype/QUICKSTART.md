# 🚀 快速開始指南 - 區塊1

## 5分鐘初始化飲食管理系統數據庫

### 📋 檢查清單

- [ ] Python 3.8+ 已安裝
- [ ] 當前目錄包含以下文件：
  - [ ] `schema.sql`
  - [ ] `init_db.py`
  - [ ] `requirements.txt`
  - [ ] `verify_db.py`

### ⚡ 快速步驟

#### 第1步：創建虛擬環境（1分鐘）

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

#### 第2步：安裝依賴（2分鐘）

```bash
pip install -r requirements.txt
```

#### 第3步：初始化數據庫（1分鐘）

```bash
python init_db.py
```

**預期看到：**
```
✓ 數據庫連接成功
✓ 數據庫架構加載成功
✓ 記錄架構版本
✓ 加載 5 個購買地點
✓ 加載 100+ 個食材
✓ 加載 25 個訓練項目
✓ 加載 20 個瑜珈/拉伸項目
✓ 初始化食材庫存

✓ 數據庫初始化完成！
```

#### 第4步：驗證（1分鐘）

```bash
python verify_db.py
```

**應該全部通過✓**

---

## ✅ 成功標誌

如果看到以下信息，說明初始化成功：

1. ✓ 生成了 `nutrition_system.db` 文件
2. ✓ 所有驗證檢查通過
3. ✓ 統計信息顯示：
   - 食材：100+
   - 訓練項目：25
   - 瑜珈/拉伸項目：20
   - 購買地點：5

---

## 🔍 快速驗證

用SQL查看數據：

```bash
sqlite3 nutrition_system.db

# 在SQLite shell中執行：
sqlite> SELECT COUNT(*) as 表數 FROM sqlite_master WHERE type='table';
25

sqlite> SELECT category, COUNT(*) FROM ingredient_library GROUP BY category;
肉類|20
穀物|15
蔬菜|30
...

sqlite> .quit
```

---

## 📦 後續步驟

數據庫已準備就緒！現在可以：

1. **開始區塊2開發**
   - FastAPI後端設置
   - 用戶管理API

2. **備份數據庫**
   ```bash
   cp nutrition_system.db nutrition_system.db.backup
   ```

3. **分享項目**
   - 將文件commit到Git（除了`.db`文件）
   - `.gitignore` 已配置好排除數據庫

---

## ❌ 常見問題

### Q: 看到 "數據庫已存在" 的提示？
**A:** 輸入 `y` 刪除舊數據庫並重新創建

### Q: "找不到schema.sql"？
**A:** 確保文件在同一個目錄
```bash
ls
# 應該看到：
# schema.sql
# init_db.py
# requirements.txt
```

### Q: 想要重新初始化？
**A:** 
```bash
rm nutrition_system.db
python init_db.py
```

### Q: 怎樣查看數據庫內容？
**A:** 三種方式

方式1 - 命令行：
```bash
sqlite3 nutrition_system.db ".tables"
```

方式2 - Python：
```python
import sqlite3
conn = sqlite3.connect('nutrition_system.db')
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM ingredient_library")
print(cursor.fetchone())
```

方式3 - GUI工具（可選）：
- DBeaver
- SQLiteStudio
- VS Code SQLite擴展

---

## 📊 數據庫架構速覽

```
nutrition_system.db
├── 用戶管理（4表）
│   ├── users
│   ├── user_goal_history
│   ├── dietary_preferences
│   └── user_sport_preferences
├── 體重追蹤（1表）
│   └── weight_records
├── 運動追蹤（7表）
│   ├── exercise_sessions
│   ├── exercise_details
│   ├── exercise_item_library (25項)
│   ├── workout_templates
│   ├── template_details
│   ├── daily_steps
│   └── yoga_stretch_items (20項)
├── 食材管理（2表）
│   ├── ingredient_library (100+項)
│   └── ingredient_stock
├── 食譜管理（4表）
│   ├── recipes
│   ├── recipe_ingredients
│   ├── recipe_steps
│   └── recipe_nutrition
├── 購買管理（2表）
│   ├── purchase_locations (5個)
│   └── ingredient_location_preference
├── 週推薦和購物（7表）
│   ├── weekly_meal_plan
│   ├── daily_meal_detail
│   ├── meal_adjustments
│   ├── shopping_list
│   ├── shopping_list_items
│   └── shopping_list_history
└── 系統（1表）
    └── schema_version
```

---

## 🎯 下一步

### 立即可以做的：
- ✅ 連接數據庫並查詢數據
- ✅ 導出數據為JSON/CSV
- ✅ 備份和恢復數據庫

### 需要區塊2才能做的：
- ⬜ 建立Web API
- ⬜ 實現用戶認證
- ⬜ 創建前端界面

---

## 💡 提示

1. **備份重要數據**
   ```bash
   cp nutrition_system.db nutrition_system.db.$(date +%Y%m%d)
   ```

2. **監控數據庫大小**
   ```bash
   ls -lh nutrition_system.db
   ```

3. **定期驗證**
   ```bash
   python verify_db.py
   ```

4. **保持虛擬環境活躍**
   ```bash
   # 每次工作時激活
   source venv/bin/activate  # macOS/Linux
   venv\Scripts\activate      # Windows
   ```

---

## 📞 需要幫助？

查看完整文檔：
- `BLOCK1_README.md` - 詳細技術文檔
- `nutrition_system_architecture.md` - 系統架構設計

---

**準備好了嗎？運行以下命令開始：**

```bash
python init_db.py && python verify_db.py
```

祝賀！✨ 您已完成區塊1的開發！
