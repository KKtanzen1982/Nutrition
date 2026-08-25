# 區塊 5：Claude 推薦引擎 - 完成總結

**完成日期**：2024-08-06  
**狀態**：✅ 架構確認 + 代碼全部生成  
**代碼行數**：~2,500+ 行（包含完整的類型註釋和文檔）

---

## 📋 生成的文件清單

| 文件名 | 用途 | 行數 | 狀態 |
|------|------|------|------|
| **BLOCK_5_ARCHITECTURE_DESIGN.md** | 完整架構設計文檔 | 600+ | ✅ |
| **BLOCK_5_schemas.py** | Pydantic 數據模型 | 380+ | ✅ |
| **BLOCK_5_prompts.py** | Claude Prompt 模板 | 320+ | ✅ |
| **BLOCK_5_recommendation_service.py** | 熱量計算 + 篩選 + Claude 調用 | 550+ | ✅ |
| **BLOCK_5_adjustment_service.py** | 4 種微調邏輯 + 週計畫管理 | 480+ | ✅ |
| **BLOCK_5_meal_plan_api.py** | 推薦相關 API endpoints | 320+ | ✅ |
| **BLOCK_5_adjustment_api.py** | 微調相關 API endpoints | 380+ | ✅ |
| **BLOCK_5_INTEGRATION_GUIDE.md** | 集成指南 + 使用範例 | 500+ | ✅ |
| **BLOCK_5_COMPLETION_SUMMARY.md** | 本文檔 | - | ✅ |

---

## 🏗️ 架構概覽

### 核心流程

```
用戶發起推薦
    ↓
[後台任務] 啟動並返回 job_id
    ↓
① 篩選食譜（根據過敏、限制）
    ↓
② 打包數據（熱量、營養素目標）
    ↓
③ 構建 Claude Prompt
    ↓
④ 調用 Claude API（非同步）
    ↓
⑤ 解析回應
    ↓
⑥ 存入數據庫
    ↓
用戶輪詢 job_id 並取得結果
```

### 核心類別

| 類別 | 職責 | 主要方法 |
|------|------|--------|
| **CalorieCalculator** | 熱量計算 | `calculate_bmr()`, `calculate_tdee()`, `adjust_for_goal()`, `adjust_for_menstrual_phase()` |
| **RecipeFilter** | 食譜篩選 | `filter_candidate_recipes()` |
| **RecommendationDataPacker** | 數據打包 | `pack_for_claude()`, `calculate_nutrient_targets()` |
| **ClaudeRecommendationService** | Claude API 調用 | `call_claude()` |
| **MealAdjustmentService** | 微調邏輯 | `replace_meal()`, `prepare_for_day_regeneration()`, `search_and_replace()`, `adjust_serving_weight()` |
| **MealPlanManager** | 週計畫管理 | `build_meal_plan_from_claude_response()`, `recalculate_weekly_summary()` |

---

## 🔌 API 端點速查表

### 推薦相關（5 個端點）

```bash
POST   /meal-plans/generate
       → 啟動推薦任務（返回 job_id）

GET    /meal-plans/jobs/{job_id}/status
       → 查詢任務進度

GET    /meal-plans/{plan_id}
       → 取得週推薦詳情

PUT    /meal-plans/{plan_id}/confirm
       → 確認推薦（生成購物清單）
```

### 微調相關（4 個端點）

```bash
# 方案 A：替換單菜色
POST   /meal-plans/{plan_id}/adjust/replace-meal
       Request: { meal_date, meal_type, user_id, new_recipe_id }

# 方案 B：重推整天
POST   /meal-plans/{plan_id}/adjust/regenerate-day
       Request: { meal_date, fixed_meals }
       → 返回 job_id（非同步）

# 方案 C：搜尋替換
POST   /meal-plans/{plan_id}/adjust/search-replace
       Request: { meal_date, meal_type, user_id, search_query, new_recipe_id }

# 方案 D：調整分量
PUT    /meal-plans/{plan_id}/adjust/serving-weight
       Request: { meal_date, meal_type, user_id, new_serving_weight_g }
       → 自動重新計算營養素
```

---

## 💡 關鍵設計決策和實現

### 1️⃣ 熱量計算

**實現的功能**：
- ✅ Harris-Benedict 公式（預設）
- ✅ Mifflin-St Jeor 公式（可選）
- ✅ 下拉式選單讓用戶選擇
- ✅ 根據活動等級調整（久坐/輕度/中度/高度）
- ✅ 根據目標調整（減脂 -350 kcal / 增肌 +250 kcal）
- ✅ 根據本週運動調整（健身房、瑜珈、步數）
- ✅ 根據生理期調整（黃體期 +150 kcal / 經前期 +120 kcal）

**代碼位置**：`BLOCK_5_recommendation_service.py` - `CalorieCalculator` 類

### 2️⃣ 生理期支持

**實現的功能**：
- ✅ 計算當前生理期階段（月經期/卵泡期/排卵期/黃體期/經前期）
- ✅ 根據生理期調整熱量
- ✅ 用戶可自訂經前期時間
- ✅ 用戶可自訂黃體期調整熱量
- ✅ 用戶可自訂經前期調整熱量
- ✅ Claude 會根據生理期推薦特定食材

**代碼位置**：`BLOCK_5_recommendation_service.py` - `calculate_menstrual_phase()` 函數

### 3️⃣ 非同步任務架構

**實現方式**：
- ✅ 用戶請求 → FastAPI 立即返回 `job_id`
- ✅ 後台啟動 `asyncio.create_task()` 執行推薦
- ✅ 用戶輪詢 `/jobs/{job_id}/status` 查詢進度
- ✅ 支援任務狀態：pending → processing → completed/failed

**優點**：
- 快速回應，避免 API 超時
- 用戶體驗良好（漸進式載入）
- 可輕鬆升級到 Celery（Redis）

**代碼位置**：`BLOCK_5_meal_plan_api.py` - `generate_meal_plan()` 和 `run_recommendation_background()`

### 4️⃣ 4 種微調方案

| 方案 | 操作 | 實現 | 複雜度 |
|------|------|------|--------|
| **A** | 替換單菜色 | 直接替換 + 自動計算營養 | 低 |
| **B** | 重推整天 | 保留其他 6 天 + Claude 重推該天 | 中 |
| **C** | 搜尋替換 | 用戶搜尋 + 替換 | 低 |
| **D** | 調整分量 | 修改 g 數 + 自動重新計算營養 | 低 |

**代碼位置**：`BLOCK_5_adjustment_service.py` - `MealAdjustmentService` 類

### 5️⃣ 食譜篩選邏輯

**支持的篩選條件**：
- ✅ 過敏原檢查（交集：只要有任何一人過敏就排除）
- ✅ 飲食限制（素食等）
- ✅ 成本等級（未來可用於購物清單）

**代碼位置**：`BLOCK_5_recommendation_service.py` - `RecipeFilter.filter_candidate_recipes()`

---

## 🚀 準備好集成

### 需要從區塊 1-4 的資訊

| 資訊 | 來源 | 用途 |
|------|------|------|
| 用戶基本資料 | `users` 表 | 計算熱量、取得偏好 |
| 最新體重 | `weight_records` 表 | TDEE 計算 |
| 本週運動 | `exercise_sessions`, `daily_steps` | 運動調整 |
| 所有食譜 | `recipes` 表 + `recipe_nutrition` 表 | 候選菜色 |
| 食材過敏原 | `recipes` + `ingredient_library` | 食譜篩選 |
| 飲食偏好 | `dietary_preferences` 表 | 食譜篩選 |

### 集成清單

- [ ] 在 `requirements.txt` 中添加 `anthropic` 依賴
- [ ] 在 `.env` 中設置 `ANTHROPIC_API_KEY`
- [ ] 在 `main.py` 中註冊 `meal_plan_router` 和 `adjustment_router`
- [ ] 實現 `get_db()` 函數，連接真實數據庫
- [ ] 填入 `BLOCK_5_meal_plan_api.py` 中的所有 `TODO` 部分
- [ ] 根據實際數據庫模型調整查詢邏輯
- [ ] 測試所有 9 個 API 端點
- [ ] 驗證推薦邏輯是否符合預期

---

## 📊 代碼統計

```
總行數：        2,500+
其中：
  - Python代碼：  1,600+ 行
  - 文檔/註釋：   900+ 行

Pydantic 模型：  60+ 個
API 端點：       9 個
業務類別：       6 個
輔助函數：       15+ 個
```

---

## 🎯 區塊 5 的主要成就

✅ **完整的推薦流程**
- 從用戶數據到 Claude 推薦，無缝銜接

✅ **靈活的熱量計算**
- 支援多個公式，可由用戶選擇
- 考慮運動、生理期等多重因素

✅ **全面的生理期支持**
- 不只計算生理期，還可調整飲食
- 用戶可自訂參數

✅ **非同步推薦架構**
- 不會阻塞 API
- 用戶體驗良好

✅ **4 種微調方案**
- 涵蓋所有常見的微調需求
- 方案 B（重推整天）支援 Claude 再次參與

✅ **清晰的代碼結構**
- 模組化設計，易於測試和維護
- 完整的類型註釋
- 詳細的文檔

---

## 📝 後續計畫

### 區塊 6（購物清單管理）

將依賴區塊 5 的推薦結果：
1. 自動計算 2 人所需食材和用量
2. 根據偏好地點分配購買位置
3. 考慮現有庫存
4. 按購買地點和分類組織清單

**預計代碼行數**：500-600 行

### 區塊 7（前端應用）

將使用區塊 5 的所有 API：
1. 推薦生成（輪詢 job_id）
2. 週菜單預覽（簡表 + 詳情）
3. 4 種微調界面
4. 營養素可視化

**預計代碼行數**：1,500-2,000 行

---

## 🔍 測試指南

### 單元測試範例

```python
# test_block_5.py
import pytest
from BLOCK_5_recommendation_service import CalorieCalculator

def test_calculate_bmr_female():
    user = {
        "gender": "女",
        "age": 25,
        "height_cm": 160,
        "weight_kg": 55
    }
    bmr = CalorieCalculator.calculate_bmr(user)
    assert 1200 < bmr < 1400  # 預期範圍

def test_calculate_tdee_with_exercise():
    user = {
        "gender": "女",
        "age": 25,
        "height_cm": 160,
        "weight_kg": 55,
        "activity_level": "中度",
        "calorie_calculation_method": "harris_benedict"
    }
    exercise = {
        "gym_sessions": 3,
        "walking_steps_total": 45000,
        "yoga_sessions": 2
    }
    tdee = CalorieCalculator.calculate_tdee(user, exercise)
    # TDEE 應該比基礎 × 1.55 高出運動額外消耗
    assert tdee > 1800
```

### 集成測試流程

```python
# test_integration.py
@pytest.mark.asyncio
async def test_full_recommendation_flow():
    # 1. 準備測試數據
    # 2. 調用推薦 API
    # 3. 輪詢任務狀態
    # 4. 驗證推薦結果
    # 5. 測試微調
```

---

## 📚 技術參考

### 熱量計算公式

**Harris-Benedict（女性）**：
```
BMR = 655 + (9.6 × 體重 kg) + (1.8 × 身高 cm) - (4.7 × 年齡)
```

**TDEE** = BMR × 活動係數

**活動係數**：
- 久坐（無運動）：1.2
- 輕度（1-3 日/週）：1.375
- 中度（3-5 日/週）：1.55
- 高度（6-7 日/週）：1.725

### 生理期計算

基於最後月經開始日期 + 平均週期天數：

```
天數 = (目標日期 - 最後月經日期) % 週期
```

- 第 1-5 天：月經期
- 第 6-12 天：卵泡期
- 第 13-14 天：排卵期
- 第 15-28 天：黃體期
- 最後 3-4 天：經前期

---

## ✨ 亮點功能

### 1. 智能食譜篩選

不是簡單地排除過敏原，而是：
- 2 人的過敏求交集（只要有一人過敏就排除）
- 支援多人的飲食限制協議

### 2. 靈活的微調

方案 B 特別厲害：
- 固定某些菜色（例如用戶一定要吃的）
- 其他菜色由 Claude 重新推薦
- 自動保持整體營養平衡

### 3. 實時營養計算

分量調整後自動計算：
```
新營養 = 原營養 × (新分量 / 基礎分量)
```

---

## 🎓 學習要點

如果你之後要改進或擴展這個系統，重點注意：

1. **非同步模式**：FastAPI + asyncio 的搭配
2. **Claude API 集成**：Prompt 工程 + JSON 解析
3. **生理期計算**：模運算在日期計算中的應用
4. **營養素計算**：按比例縮放（關鍵是 base_weight_g）

---

## 🚦 檢查清單

在開始使用前：

- [ ] 所有文件都已下載到本地
- [ ] 環境已配置（Python 3.12, FastAPI, SQLAlchemy 等）
- [ ] Claude API 金鑰已設置
- [ ] 數據庫已初始化（BLOCK_1）
- [ ] 食譜和食材已導入（BLOCK_4）
- [ ] 已閱讀集成指南（BLOCK_5_INTEGRATION_GUIDE.md）

---

## 📞 聯繫和支援

如有問題：

1. 檢查 **BLOCK_5_INTEGRATION_GUIDE.md** 的「常見問題」部分
2. 查看日誌文件尋找錯誤線索
3. 驗證所有 TODO 部分是否正確實現

---

## 📈 版本和更新

| 版本 | 日期 | 內容 |
|------|------|------|
| 1.0 | 2024-08-06 | 初始版本，所有核心功能完成 |

---

**區塊 5 已完成！準備好進入區塊 6（購物清單管理）了嗎？** 🚀

---

*生成於 2024-08-06*  
*飲食管理系統 v1.0*
