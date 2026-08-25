# 區塊 5：Claude 推薦引擎 - 完整代碼索引

**生成日期**：2024-08-06  
**版本**：1.0 - 完整版  
**總文件數**：9 份  
**總代碼行數**：2,500+ 行

---

## 📑 快速導航

### 📘 先讀這些（文檔）

| 序號 | 文件 | 用途 | 優先級 |
|------|------|------|--------|
| 1️⃣ | **BLOCK_5_COMPLETION_SUMMARY.md** | 區塊 5 完成總結（本索引） | ⭐⭐⭐ |
| 2️⃣ | **BLOCK_5_ARCHITECTURE_DESIGN.md** | 完整架構設計 | ⭐⭐⭐ |
| 3️⃣ | **BLOCK_5_INTEGRATION_GUIDE.md** | 集成指南 + 使用範例 | ⭐⭐⭐ |

### 💻 然後看這些（代碼）

#### 核心服務層

| 序號 | 文件 | 行數 | 關鍵類別 | 優先級 |
|------|------|------|---------|--------|
| 1️⃣ | **BLOCK_5_schemas.py** | 380+ | 15+ 數據模型 | ⭐⭐⭐ |
| 2️⃣ | **BLOCK_5_recommendation_service.py** | 550+ | CalorieCalculator, RecipeFilter, RecommendationDataPacker, ClaudeRecommendationService | ⭐⭐⭐ |
| 3️⃣ | **BLOCK_5_adjustment_service.py** | 480+ | MealAdjustmentService, NutrientCalculator, MealPlanManager | ⭐⭐⭐ |
| 4️⃣ | **BLOCK_5_prompts.py** | 320+ | Prompt 模板和動態構建 | ⭐⭐⭐ |

#### API 層

| 序號 | 文件 | 行數 | 端點數 | 優先級 |
|------|------|------|--------|--------|
| 1️⃣ | **BLOCK_5_meal_plan_api.py** | 320+ | 4 個推薦相關端點 | ⭐⭐⭐ |
| 2️⃣ | **BLOCK_5_adjustment_api.py** | 380+ | 4 個微調相關端點 | ⭐⭐⭐ |

---

## 📂 文件詳細說明

### 1️⃣ BLOCK_5_COMPLETION_SUMMARY.md
**📊 概覽和總結**

包含：
- ✅ 所有生成文件清單
- ✅ 架構概覽
- ✅ 關鍵設計決策
- ✅ 代碼統計
- ✅ 測試指南
- ✅ 後續計畫

**何時讀**：第一次接觸區塊 5 時

---

### 2️⃣ BLOCK_5_ARCHITECTURE_DESIGN.md
**🏗️ 完整架構設計文檔**

包含：
- ✅ 資料模型擴展
- ✅ 系統架構圖
- ✅ API 設計
- ✅ 非同步流程
- ✅ 推薦邏輯
- ✅ 微調邏輯
- ✅ 生理期調整
- ✅ 代碼組織

**何時讀**：需要理解完整設計時

---

### 3️⃣ BLOCK_5_INTEGRATION_GUIDE.md
**🚀 集成指南和使用範例**

包含：
- ✅ 集成步驟
- ✅ 數據庫集成（詳細的 TODO 填充方法）
- ✅ 8 個使用範例（curl 命令）
- ✅ 常見問題解決
- ✅ 性能優化建議
- ✅ 監控和日誌
- ✅ 測試清單

**何時讀**：開始集成區塊 5 時

---

### 4️⃣ BLOCK_5_schemas.py
**📋 Pydantic 數據模型（380+ 行）**

定義的模型：
- ✅ 列舉類型：`MealType`, `MenstrualPhase`, `PrimaryGoal` 等
- ✅ 請求模型：`GenerateMealPlanRequest`, `ReplaceMealRequest` 等
- ✅ 回應模型：`MealPlanResponse`, `AdjustmentResponse` 等
- ✅ Claude 內部模型：`UserDataForClaude`, `RecipeForClaude` 等

**關鍵特性**：
- 完整的類型檢查
- 詳細的字段說明
- 支援嵌套模型

**何時用**：定義 API 請求/回應時

---

### 5️⃣ BLOCK_5_recommendation_service.py
**🧠 核心推薦邏輯（550+ 行）**

包含的類別：

#### CalorieCalculator（熱量計算）
```python
- calculate_bmr()           # 基礎代謝率
- calculate_tdee()          # 每日總能量消耗
- adjust_for_goal()         # 根據目標調整
- adjust_for_menstrual_phase()  # 根據生理期調整
```

#### RecipeFilter（食譜篩選）
```python
- filter_candidate_recipes()  # 根據過敏、限制篩選
```

#### RecommendationDataPacker（數據打包）
```python
- pack_for_claude()         # 打包給 Claude 的 JSON
- calculate_nutrient_targets()  # 計算營養目標
```

#### ClaudeRecommendationService（Claude API）
```python
- __init__()                # 初始化客戶端
- call_claude()             # 非同步調用 Claude
```

#### 輔助函數
```python
- calculate_menstrual_phase()    # 計算生理期
- generate_meal_plan_recommendation()  # 整合函數
```

**何時用**：實現推薦邏輯時

---

### 6️⃣ BLOCK_5_adjustment_service.py
**🔧 微調邏輯（480+ 行）**

包含的類別：

#### NutrientCalculator（營養計算）
```python
- calculate_meal_nutrition()  # 根據分量計算營養
- calculate_day_summary()    # 計算日營養總和
```

#### MealAdjustmentService（微調服務）
```python
# 方案 A：替換單菜色
- replace_meal()

# 方案 B：重推整天
- prepare_for_day_regeneration()
- apply_regenerated_day()

# 方案 C：搜尋替換
- search_and_replace()

# 方案 D：調整分量
- adjust_serving_weight()
```

#### MealPlanManager（週計畫管理）
```python
- build_meal_plan_from_claude_response()  # 構建週計畫
- recalculate_weekly_summary()            # 重新計算統計
```

**何時用**：實現微調邏輯時

---

### 7️⃣ BLOCK_5_prompts.py
**📝 Claude Prompt 模板（320+ 行）**

包含的函數：

```python
get_main_recommendation_prompt()
  → 生成完整一週菜單的 prompt

get_single_day_regeneration_prompt()
  → 重推整天的 prompt

build_claude_prompt()
  → 動態構建 prompt（替換佔位符）
```

**特點**：
- ✅ 詳細的營養規則
- ✅ 生理期考量
- ✅ 食材效率最優化
- ✅ 強制 JSON 輸出格式

**何時用**：調整推薦邏輯或改進 prompt 時

---

### 8️⃣ BLOCK_5_meal_plan_api.py
**🎯 推薦相關 API Endpoints（320+ 行）**

實現的端點：

```
POST   /meal-plans/generate
       啟動推薦任務（非同步）
       回應：{ success, job_id, message }

GET    /meal-plans/jobs/{job_id}/status
       查詢任務進度
       回應：{ job_id, status, plan_id, error_message, ... }

GET    /meal-plans/{plan_id}
       取得週推薦詳情
       回應：完整的 MealPlanResponse

PUT    /meal-plans/{plan_id}/confirm
       確認推薦（生成購物清單）
       回應：{ success, plan_id, shopping_list_id }
```

**關鍵實現**：
- ✅ 後台任務管理（`_jobs_cache`）
- ✅ 推薦流程整合（9 步）
- ✅ 完整的錯誤處理

**何時用**：部署推薦相關 API 時

---

### 9️⃣ BLOCK_5_adjustment_api.py
**⚙️ 微調相關 API Endpoints（380+ 行）**

實現的端點：

```
# 方案 A：替換單菜色
POST   /meal-plans/{plan_id}/adjust/replace-meal
       Request: ReplaceMealRequest
       回應：AdjustmentResponse

# 方案 B：重推整天
POST   /meal-plans/{plan_id}/adjust/regenerate-day
       Request：RegenerateDay Request
       回應：AdjustmentResponse (含 job_id)

# 方案 C：搜尋替換
POST   /meal-plans/{plan_id}/adjust/search-replace
       Request：SearchAndReplaceRequest
       回應：AdjustmentResponse

# 方案 D：調整分量
PUT    /meal-plans/{plan_id}/adjust/serving-weight
       Request：AdjustServingWeightRequest
       回應：AdjustmentResponse（含自動計算的營養）
```

**特點**：
- ✅ 完整的驗證邏輯
- ✅ 營養素自動重新計算（方案 D）
- ✅ 非同步支援（方案 B）

**何時用**：部署微調相關 API 時

---

## 🔀 類別依賴關係

```
Schemas（基礎）
    ↑
    └─→ RecommendationService
            ├→ CalorieCalculator
            ├→ RecipeFilter
            ├→ RecommendationDataPacker
            └→ ClaudeRecommendationService
                 ↑
                 └→ Prompts

    └─→ AdjustmentService
            ├→ NutrientCalculator
            ├→ MealAdjustmentService（4 種方案）
            └→ MealPlanManager

APIs（最外層）
    ├→ MealPlanApi
    │   └→ RecommendationService + Prompts
    │
    └→ AdjustmentApi
        └→ AdjustmentService
```

---

## 🎯 快速開始（3 步）

### 步驟 1：了解架構（10 分鐘）
```
閱讀：BLOCK_5_COMPLETION_SUMMARY.md（第「區塊 5 的主要成就」部分）
```

### 步驟 2：學習集成（30 分鐘）
```
閱讀：BLOCK_5_INTEGRATION_GUIDE.md（第「集成步驟」和「使用範例」部分）
```

### 步驟 3：開始編碼（2-3 小時）
```
1. 複製所有 .py 文件到你的項目
2. 根據 INTEGRATION_GUIDE 填入所有 TODO
3. 測試 API 端點
```

---

## 🔍 按用途查找代碼

### 「我需要實現熱量計算」
→ **BLOCK_5_recommendation_service.py** - `CalorieCalculator` 類

### 「我需要調用 Claude」
→ **BLOCK_5_recommendation_service.py** - `ClaudeRecommendationService` 類  
→ **BLOCK_5_prompts.py** - `build_claude_prompt()` 函數

### 「我需要實現推薦 API」
→ **BLOCK_5_meal_plan_api.py**

### 「我需要實現替換菜色」
→ **BLOCK_5_adjustment_api.py** - `replace_meal()` 端點  
→ **BLOCK_5_adjustment_service.py** - `MealAdjustmentService.replace_meal()` 方法

### 「我需要計算生理期」
→ **BLOCK_5_recommendation_service.py** - `calculate_menstrual_phase()` 函數

### 「我需要定義數據模型」
→ **BLOCK_5_schemas.py**

### 「我需要篩選食譜」
→ **BLOCK_5_recommendation_service.py** - `RecipeFilter` 類

---

## 📊 代碼複雜度評估

| 文件 | 複雜度 | 優先級 | 預計閱讀時間 |
|------|--------|--------|------------|
| schemas.py | ⭐☆☆ 低 | 高 | 15 分鐘 |
| prompts.py | ⭐⭐☆ 中 | 中 | 20 分鐘 |
| recommendation_service.py | ⭐⭐⭐ 高 | 高 | 45 分鐘 |
| adjustment_service.py | ⭐⭐☆ 中 | 高 | 35 分鐘 |
| meal_plan_api.py | ⭐⭐⭐ 高 | 高 | 40 分鐘 |
| adjustment_api.py | ⭐⭐☆ 中 | 中 | 30 分鐘 |

---

## 🐛 常見集成問題和解決方案

### Q1: 「ImportError: cannot import name 'XXX'」
**解決**：確認所有文件都在同一目錄，或調整導入路徑

### Q2: 「Claude API 返回無效 JSON」
**解決**：檢查 prompts.py 中的 JSON 格式要求

### Q3: 「熱量計算數字不對」
**解決**：檢查 weight_kg（體重）是否正確取自最新的 weight_records

### Q4: 「生理期計算錯誤」
**解決**：檢查 last_menstrual_date 是否正確，以及 menstrual_cycle_length_days

---

## ✅ 完成度檢查

- [x] 架構設計
- [x] 數據模型
- [x] 推薦邏輯
- [x] 微調邏輯
- [x] API 設計
- [x] 提示詞工程
- [x] 完整文檔
- [x] 使用範例

---

## 📞 文檔快速查閱

| 問題 | 查閱文檔 | 位置 |
|------|--------|------|
| 「系統架構是什麼？」 | ARCHITECTURE_DESIGN.md | 系統架構 |
| 「如何集成到我的項目？」 | INTEGRATION_GUIDE.md | 集成步驟 |
| 「如何使用 API？」 | INTEGRATION_GUIDE.md | 使用範例 |
| 「生理期是怎麼計算的？」 | ARCHITECTURE_DESIGN.md | 生理期調整 |
| 「4 種微調方案如何實現？」 | ADJUSTMENT_SERVICE.py | MealAdjustmentService 類 |
| 「Claude 的 Prompt 是什麼？」 | PROMPTS.py | 模板函數 |

---

## 🎓 學習路徑

**適合新手的學習順序**：

1. COMPLETION_SUMMARY.md（概覽）
2. ARCHITECTURE_DESIGN.md（深入理解）
3. INTEGRATION_GUIDE.md（實踐）
4. schemas.py（定義數據）
5. recommendation_service.py（理解邏輯）
6. adjustment_service.py（理解微調）
7. meal_plan_api.py / adjustment_api.py（實現 API）

---

## 🚀 下一步

### 短期（本周）
- [ ] 閱讀所有文檔
- [ ] 整合代碼到項目
- [ ] 測試基礎功能

### 中期（1-2 周）
- [ ] 完成數據庫集成
- [ ] 測試所有 API 端點
- [ ] 調整 Prompt 和參數

### 長期（3-4 周）
- [ ] 開發區塊 6（購物清單）
- [ ] 開發區塊 7（前端）
- [ ] 完整系統測試和優化

---

## 📈 版本控制

```
BLOCK_5_v1.0 (2024-08-06)
├─ ✅ 完整架構設計
├─ ✅ 所有代碼完成
├─ ✅ 完整文檔
└─ ✅ 使用範例
```

---

**區塊 5 生成完成！** 🎉

所有 9 份文件已準備好，共 2,500+ 行代碼。祝集成順利！

*如需幫助，請參考 BLOCK_5_INTEGRATION_GUIDE.md 的「常見問題」部分。*
