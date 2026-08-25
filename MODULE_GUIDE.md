# 功能模組地圖與局部修改指南

這份文件把整個專案依照功能領域列成清單，並說明「只想改一個功能」時該碰哪些檔案、不該碰哪些檔案、怎麼在不啟動整個系統的情況下驗證修改。跟 [README.md](README.md) 的差異：README 講的是「怎麼啟動整個專案」，這份文件講的是「怎麼只動一個功能」。

## 怎麼用這份文件

1. 找到你想改的功能對應下面哪一個區塊。
2. 看該區塊的「後端檔案」/「前端檔案」——只打開這些檔案，不要跨到別的區塊。
3. 看「跨領域依賴」——如果別的領域會讀你要改的資料表/API，改之前先確認不會弄壞它們。
4. 看「怎麼獨立驗證」——不用整個 app 都測一遍，照著做就能確認這個功能本身沒壞。

---

## 1. `users` — 使用者基本資料與飲食偏好

**用途**：使用者姓名/性別/生理期相關欄位、飲食偏好設定（過敏原、忌口、偏好標籤）。

- **後端** `backend/users/`：`models.py`（User、DietaryPreference）、`schemas.py`、`services.py`（UserService、DietaryPreferenceService）、`router.py`（`/api/users*`、`/api/users/{id}/dietary-preferences`）
- **前端** `frontend/src/users/`：`ProfileView.vue`、`users_api.ts`、`dietary_preference_api.ts`

**跨領域依賴**：`meal_plans` 會讀 `User`（算熱量目標）和 `DietaryPreference`（推薦引擎排除忌口食材）。改 `User`/`DietaryPreference` 的欄位或刪除欄位前，先確認 `backend/meal_plans/services.py` 有沒有引用。

**怎麼獨立驗證**：
```bash
curl http://127.0.0.1:8000/api/users
curl http://127.0.0.1:8000/api/users/1/dietary-preferences
```
前端開 `/profile` 頁面看資料是否正確顯示、儲存後是否生效。

---

## 2. `fitness` — 體重、運動、步數紀錄

**用途**：體重歷史紀錄、運動紀錄（含動作明細）、每日步數。

- **後端** `backend/fitness/`：`models.py`（WeightRecord、ExerciseSession、ExerciseDetail、DailySteps）、`schemas.py`、`services.py`（WeightService、ExerciseService、StepsService）、`router.py`（`/api/weight-records*`、`/api/exercise-*`、`/api/daily-steps*`）
- **前端** `frontend/src/fitness/`：`WeightView.vue`、`ExerciseView.vue`、`CardWeight.vue`、`CardExercise.vue`、`weight_api.ts`、`exercise_api.ts`

**跨領域依賴**：`ExerciseService` 會 import `training.services._validate_and_track_library_usage`（記錄動作庫使用次數）。`training` 的排程調整邏輯（`TrainingScheduleService`）會讀寫這裡的 `ExerciseSession`/`ExerciseDetail`。`meal_plans` 會讀 `WeightRecord`/`ExerciseSession`/`DailySteps` 算熱量消耗。改這三張表的欄位前，先搜尋這三個地方有沒有引用。

**怎麼獨立驗證**：
```bash
curl http://127.0.0.1:8000/api/weight-records?user_id=1
curl http://127.0.0.1:8000/api/exercise-sessions?user_id=1
```
前端開 `/weight`、`/exercise` 頁面，測試新增/刪除紀錄（刪除會跳自訂的 `ConfirmDialog`，不是瀏覽器原生 confirm）。

---

## 3. `training` — 動作資料庫、訓練計畫、月曆排程

**用途**：重訓/瑜伽動作庫、訓練範本、多天訓練計畫、月曆排程與自動調整、週目標與達成度。這是 6 個領域裡最大的一個。

- **後端** `backend/training/`：`models.py`（WorkoutTemplate、TemplateDetail、ExerciseItemLibrary、YogaStretchItem、UserItemUsage、TrainingProgram、TrainingProgramDay、TrainingSchedule、TrainingTarget）、`schemas.py`、`services.py`（ExerciseItemService、TemplateService、TrainingProgramService、TrainingScheduleService、TrainingTargetService、TrainingProgressService）、`seed_data.py`、`router.py`
- **前端** `frontend/src/training/`：`ExerciseLibraryView.vue`、`TrainingCalendarView.vue`、`AddExerciseItemModal.vue`、`ExerciseItemAutocomplete.vue`、`ExerciseItemDetailModal.vue`、`StepsEditModal.vue`、`TemplateFormModal.vue`、`TrainingProgramFormModal.vue`、對應 6 個 `*_api.ts`

**跨領域依賴**：`TrainingScheduleService._apply_adaptive_rebalancing` 會讀寫 `fitness.models.ExerciseSession`/`ExerciseDetail`（排程跟實際運動紀錄對照，自動調整未來排程）。`fitness.services.ExerciseService` 反過來會呼叫這裡的 `_validate_and_track_library_usage`。這兩個領域是雙向依賴，改任何一邊的資料結構都要交叉檢查另一邊。

**怎麼獨立驗證**：
```bash
curl http://127.0.0.1:8000/api/exercise-items
curl http://127.0.0.1:8000/api/training-programs?user_id=1
curl http://127.0.0.1:8000/api/training-schedules?user_id=1
```
前端開 `/exercise-library`、`/training-calendar`，測試新增動作、建立訓練計畫、月曆上標記完成。

---

## 4. `recipes` — 食材庫與食譜

**用途**：食材庫（含庫存量）、食譜（含步驟、版本控制、營養素計算）。

- **後端** `backend/recipes/`：`models.py`（IngredientLibrary、IngredientStock、Recipe、RecipeIngredient、RecipeStep、RecipeNutrition）、`schemas.py`、`services.py`（IngredientService、RecipeService）、`seed_data.py`、`router.py`
- **前端** `frontend/src/recipes/`：`RecipeView.vue`、`IngredientView.vue`、`recipe_api.ts`、`ingredient_api.ts`

**跨領域依賴**：`meal_plans` 的推薦引擎會讀 `Recipe`/`IngredientLibrary`。`shopping` 的購物清單彙總會讀 `Recipe`/`RecipeIngredient`/`IngredientLibrary`/`IngredientStock`。改食譜/食材的欄位或刪除食譜前，先確認這兩個領域的查詢邏輯。

**注意**：`router.py` 裡 `/ingredients/search`、`/ingredients/low-stock` 必須註冊在 `/ingredients/{ingredient_id}` 之前，`/recipes/search` 必須在 `/recipes/{recipe_id}` 之前——這是 FastAPI 路徑比對的硬性規則，改動這個檔案時保留原本的函式順序。

**怎麼獨立驗證**：
```bash
curl http://127.0.0.1:8000/api/recipes
curl http://127.0.0.1:8000/api/ingredients/low-stock
```
前端開 `/recipes`、`/ingredients`。

---

## 5. `meal_plans` / `meal-plans` — 週推薦引擎

**用途**：熱量與巨量營養素計算、規則式週菜單推薦演算法、每日菜單明細、手動調整紀錄。

- **後端** `backend/meal_plans/`：`models.py`（WeeklyMealPlan、DailyMealDetail、MealAdjustment）、`schemas.py`、`nutrition_calc.py`（純函式：熱量/BMR/TDEE 計算）、`selection_algorithm.py`（選餐演算法）、`services.py`（NutritionTargetService、MealPlanService）、`router.py`
- **前端** `frontend/src/meal-plans/`：`MealPlanView.vue`、`CardTodayMeals.vue`、`meal_plan_api.ts`

**跨領域依賴**：這是依賴最多的領域——讀 `users.models.User`、`users.services.dietary_preference_service`、`fitness.models.{WeightRecord,ExerciseSession,DailySteps}`、`recipes.models.Recipe`。反過來，`shopping` 會讀這裡的 `WeeklyMealPlan`/`DailyMealDetail` 來彙總購物清單。改 `MealPlanService`/`NutritionTargetService` 的邏輯前，先確認這 4 個上游依賴沒被動過；改 `WeeklyMealPlan`/`DailyMealDetail` 的欄位前，先確認 `shopping.services.ShoppingListService` 沒有引用要刪的欄位。

**怎麼獨立驗證**：
```bash
curl -X POST http://127.0.0.1:8000/api/meal-plans/generate -H "Content-Type: application/json" -d "{\"user_id\":1}"
curl http://127.0.0.1:8000/api/meal-plans/current?user_id=1
```
前端開 `/meal-plan`，測試產生新一週菜單、手動調整某一餐。

---

## 6. `shopping` — 購買地點與購物清單

**用途**：購買地點（超市/市場等）、食材對地點的偏好設定、由週菜單彙總而成的購物清單、採購歷史。

- **後端** `backend/shopping/`：`models.py`（PurchaseLocation、IngredientLocationPreference、ShoppingList、ShoppingListItem、ShoppingListHistory）、`schemas.py`（含 `ConfirmMealPlanResponse`）、`aggregation.py`（彙總邏輯）、`services.py`（PurchaseLocationService、ShoppingListService）、`router.py`（含 `POST /meal-plans/{plan_id}/confirm`——雖然路徑不是 `/shopping` 開頭，但邏輯歸屬購物清單服務，刻意放在這裡）
- **前端** `frontend/src/shopping/`：`ShoppingListView.vue`、`ShoppingHistoryView.vue`、`CardShoppingList.vue`、`shopping_list_api.ts`、`purchase_location_api.ts`、`ingredient_location_preference_api.ts`

**跨領域依賴**：讀 `recipes.models.{Recipe,RecipeIngredient,IngredientLibrary,IngredientStock}` 和 `meal_plans.models.{WeeklyMealPlan,DailyMealDetail}`。這個領域是「下游」，只讀不寫別的領域的表，所以改這裡的邏輯通常不會影響別的領域——但反過來，改 `recipes`/`meal_plans` 的表結構時要記得檢查這裡。

**注意**：`/shopping-lists/history` 必須註冊在 `/shopping-lists/{list_id}` 之前，同樣是路徑比對順序問題。

**怎麼獨立驗證**：
```bash
curl http://127.0.0.1:8000/api/purchase-locations
curl http://127.0.0.1:8000/api/shopping-lists/history?user_id=1
```
前端開 `/shopping-list`、`/shopping-list/history`。

---

## 7. 前端專屬：`dashboard`、`settings`、`trends`、`shared`

這 4 個資料夾在後端沒有對應（後端沒有獨立的 dashboard/settings/trends 領域），純粹是前端的組織單位：

- **`dashboard/`**：總覽頁 + 卡片自訂排版（`DashboardView.vue`、`DashboardCustomizer.vue`、`useDashboardLayout.ts`）。會 import 各領域的 Card 元件（`fitness/CardWeight.vue` 等），但自己不擁有任何資料表。
- **`settings/`**：設定頁（`SettingsView.vue`），本來就是跨功能頁面（使用者設定 + 購買地點 + 資料備份），會 import `users`/`shopping` 的 api，加上自己專屬的 `backup_api.ts`（對應後端 `backup_router.py`，跟 7 個功能領域都無關的獨立小工具）。
- **`trends/`**：趨勢圖表頁（`TrendsView.vue`、`TrendChart.vue`、`DateRangeButton.vue`），讀 `fitness` 的體重/運動資料畫圖，自己不擁有資料。
- **`shared/`**：跨功能共用元件/composable/型別（`Modal.vue`、`ConfirmDialog.vue`、`UserSwitcher.vue`、`http.ts`、`date_utils.ts`、`useConfirmDialog.ts`、`useHouseholdConfig.ts`、`useLocalStorage.ts`、`types.ts`）。**这裡的檔案被多個領域 import，改之前要搜尋全部呼叫端**，例如改 `http.ts` 的錯誤處理邏輯會影響所有 `*_api.ts`。

**改 `dashboard`/`settings`/`trends` 時**：只要沒有動到它們 import 的來源領域（`fitness`、`shopping` 等）的 api 回傳格式，通常不會波及其他頁面。

**改 `shared/` 時**：風險最高，因為是唯一一個「所有領域都可能依賴」的資料夾。改之前用 Grep 搜尋這個檔案在其他資料夾裡被 import 的地方，全部看過一遍再動手。

---

## 通用修改流程

1. **鎖定資料夾**：對照上面表格，只打開你要改的功能對應的後端資料夾 + 前端資料夾，兩邊都在，不用開別的。
2. **檢查跨領域依賴**：看該區塊的「跨領域依賴」段落，如果要刪欄位/改回傳格式，先用 Grep 搜尋依賴方有沒有引用。
3. **改後端**：改完存檔，重啟 `uvicorn`（沒有 `--reload` 的話）；用該區塊「怎麼獨立驗證」的 curl 指令確認端點行為正常，不用整個系統的端點都測一遍。
4. **改前端**：改完存檔，Vite dev server 有 HMR 會自動更新，瀏覽器開對應路由確認畫面正常、console 沒有紅字。
5. **`main.py` / `router.ts` 通常不用動**：這兩個檔案只在「新增一整個領域」或「刪除一整個領域」時才需要改（加/刪一行 `include_router` 或一條路由）。單純改某個領域內部的邏輯不會碰到這兩個檔案。
6. **`database.py` / `shared/http.ts` 幾乎不用動**：這是最底層的共用基礎設施，7 個功能領域都靠它運作，除非要換資料庫或改全站的 API 呼叫方式，否則不會需要碰。

## 名稱對照速查

| 功能 | 後端資料夾 | 前端資料夾 | API 路徑前綴 |
|---|---|---|---|
| 使用者/飲食偏好 | `backend/users/` | `frontend/src/users/` | `/api/users` |
| 體重/運動/步數 | `backend/fitness/` | `frontend/src/fitness/` | `/api/weight-records`、`/api/exercise-*`、`/api/daily-steps` |
| 動作庫/訓練計畫/月曆 | `backend/training/` | `frontend/src/training/` | `/api/exercise-items`、`/api/training-*` |
| 食材/食譜 | `backend/recipes/` | `frontend/src/recipes/` | `/api/recipes`、`/api/ingredients` |
| 週推薦引擎 | `backend/meal_plans/` | `frontend/src/meal-plans/` | `/api/meal-plans` |
| 購買地點/購物清單 | `backend/shopping/` | `frontend/src/shopping/` | `/api/purchase-locations`、`/api/shopping-lists` |
| 資料備份（無領域） | `backend/backup_router.py` | `frontend/src/settings/backup_api.ts` | `/api/backup` |
| 總覽頁（前端專屬） | — | `frontend/src/dashboard/` | — |
| 設定頁（前端專屬） | — | `frontend/src/settings/` | — |
| 趨勢圖表（前端專屬） | — | `frontend/src/trends/` | — |
| 跨功能共用（前端專屬） | — | `frontend/src/shared/` | — |
