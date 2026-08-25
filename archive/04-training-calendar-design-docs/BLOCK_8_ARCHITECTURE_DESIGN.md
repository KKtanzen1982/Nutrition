# 區塊 8：動作庫 + 多天訓練計畫與月曆排程 — 架構設計

**版本**：0.2（設計定案，尚未實作）
**日期**：2026-08-13
**狀態**：📝 設計完成，等待在另一個工作環境開始實作

---

## 這份文件涵蓋兩個子系統

1. **動作庫（Exercise Item Library）**：把「訓練項目明細」從自由文字，改成有資料庫背書、可搜尋/自動完成的正式功能，健身房動作與瑜珈/拉伸招式都算在內。
2. **多天訓練計畫與月曆排程（Training Program & Calendar Scheduling）**：讓使用者一次規劃 3～5 天的訓練分割（例如「Push/Pull/Legs」），然後用月曆畫面把每一天拖到實際訓練日期上；「計畫」與「執行後的實際紀錄」是兩筆分開但可互相對照的資料。

兩者的關係：**訓練計畫的每一天，就是一份「動作庫項目 + 組數/次數」的清單——這正是區塊 2/7 已經做好的 `workout_templates`（訓練模板）**。區塊 8 不重造一個平行的資料結構，而是在既有的 `workout_templates` 之上加一層「把好幾個模板綁成一個多天計畫」+「把模板排到月曆日期上」。

---

## 目錄

1. [設計決策紀錄](#設計決策紀錄)
2. [子系統一：動作庫](#子系統一動作庫)
3. [子系統二：多天訓練計畫與月曆排程](#子系統二多天訓練計畫與月曆排程)
4. [與既有資料的相容策略](#與既有資料的相容策略)
5. [實作順序建議](#實作順序建議)

---

## 設計決策紀錄

以下 3 點已由你確認，本文件依此定案（取代草案版的「未決問題」）：

| # | 問題 | 決定 |
|---|------|------|
| 1 | 要不要順便做瑜珈/拉伸的動作庫 | ✅ 要。`yoga_stretch_items`（區塊 1 已設計 20 項）比照 `exercise_item_library` 同樣接上搜尋/自動完成 |
| 2 | 動作庫是全體共用還是各自獨立 | ✅ **全體共用一份**，但依「使用者個人使用頻率」提升該使用者搜尋時的推薦排序（見〈個人化推薦排序〉） |
| 3 | 自訂動作要不要自動存入庫裡 | 沿用草案建議：**手動**——使用者打完自訂文字後，另外按「加入動作庫」才會存進共用庫，避免庫裡塞滿一次性打錯字的垃圾資料。若你在區塊 8 實際開發時想改成自動加入，只要把 `POST /api/exercise-items` 的呼叫時機從「使用者按按鈕」改成「送出當下自動呼叫」即可，不影響其他設計 |

---

## 子系統一：動作庫

### 為什麼需要

目前「新增運動紀錄」的「訓練項目明細」是**純自由輸入文字欄位**：使用者打什麼字就存什麼字，沒有資料庫背書、沒有驗證。實測時 `123`、`ddd`、`afaf` 這種測試字也照樣存下來、顯示在歷史紀錄裡——這是目前設計本來就沒有動作庫可挑選的必然結果，不是 bug。

有趣的是，區塊 1 的 `schema.sql` 其實**已經設計了** `exercise_item_library`（訓練項目庫，25 個預設健身動作）與 `yoga_stretch_items`（瑜珈/拉伸庫，20 項），但 `exercise_details.exercise_item` / `template_details.exercise_item` 從頭到尾都只是 `TEXT` 欄位，從未真的用外鍵接上——庫存在，但沒人在用。而且區塊 2 目前是純記憶體儲存，完全沒接上區塊 1 的 SQLite，所以這兩張表對現在跑的程式來說形同不存在。

### 資料模型

沿用並修正區塊 1 的 `exercise_item_library`：

```sql
CREATE TABLE exercise_item_library (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  item_name TEXT NOT NULL UNIQUE,       -- 動作名稱，例：「槓鈴臥推」
  category TEXT NOT NULL,               -- '胸部'/'背部'/'下肢'/'手臂'/'核心'/'有氧'
  muscle_group TEXT,                    -- 主要肌群，例：「胸大肌、三頭肌」
  equipment TEXT,                       -- 器材，例：「槓鈴」「啞鈴」「自身體重」（新增）
  default_sets INTEGER,                 -- 建議組數
  default_reps TEXT,                    -- 建議次數，例：「8-12」（改成 TEXT，原本是 INTEGER 但次數常是區間）
  description TEXT,
  is_active BOOLEAN DEFAULT 1,          -- 軟刪除，避免刪掉還有歷史紀錄在用的項目（新增）
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

瑜珈/拉伸庫比照辦理（沿用區塊 1 原設計，不用修改）：

```sql
CREATE TABLE yoga_stretch_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  type TEXT NOT NULL CHECK(type IN ('瑜珈', '拉伸')),
  item_name TEXT NOT NULL UNIQUE,       -- 例：「下犬式」「貓牛式」
  duration_min INTEGER,
  description TEXT,
  difficulty TEXT CHECK(difficulty IN ('初級', '中級', '進階')),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

兩張庫表結構不同（健身動作有組數/次數，瑜珈拉伸有時長/難度），所以**不合併成一張表**，而是在 API 層用同一種呼叫方式包裝、由 `exercise_type` 決定查哪張表（見下方 API 設計）。

`exercise_details` / `template_details`：改成「可選 FK + 自由文字」並存，兩張庫都可能被引用，所以用兩個各自可為空的外鍵、同時只會有一個非空：

```sql
ALTER TABLE exercise_details ADD COLUMN exercise_item_id INTEGER REFERENCES exercise_item_library(id);
ALTER TABLE exercise_details ADD COLUMN yoga_stretch_item_id INTEGER REFERENCES yoga_stretch_items(id);
-- exercise_item 文字欄位保留：有選庫項目時存快照名稱（避免之後改名影響歷史顯示）；自訂輸入時存使用者打的文字

ALTER TABLE template_details ADD COLUMN exercise_item_id INTEGER REFERENCES exercise_item_library(id);
ALTER TABLE template_details ADD COLUMN yoga_stretch_item_id INTEGER REFERENCES yoga_stretch_items(id);
```

### 個人化推薦排序

庫本身全體共用、只存一份，但**搜尋結果的排序**要依照使用者自己的使用頻率調整。用一張輕量的使用統計表，不複製庫項目本身：

```sql
CREATE TABLE user_item_usage (
  user_id INTEGER NOT NULL,
  item_type TEXT NOT NULL CHECK(item_type IN ('exercise', 'yoga_stretch')),
  item_id INTEGER NOT NULL,             -- 對應 exercise_item_library.id 或 yoga_stretch_items.id
  use_count INTEGER NOT NULL DEFAULT 0,
  last_used_at TIMESTAMP,
  PRIMARY KEY (user_id, item_type, item_id)
);
```

規則：
- 每次使用者在「新增運動紀錄」或「另存為範本」時實際用到某個庫項目（`exercise_item_id` / `yoga_stretch_item_id` 非空），該筆 `use_count += 1`、`last_used_at` 更新。
- 搜尋 `/api/exercise-items/search` 若帶 `user_id`，排序規則改成：**先比對文字相關度，同樣相關度時，該使用者 `use_count` 高的排前面**；沒有使用紀錄的項目正常排在文字比對結果裡，不會被排除。
- 這張表只是排序用的輔助統計，刪除它不影響庫本身或任何歷史紀錄的正確性——之後想拿掉「個人化」這個功能，直接砍表即可。

### API 設計

```
GET  /api/exercise-items?type=gym|yoga_stretch&category=&user_id=
     列表 + 個人化排序（不帶 user_id 就是預設排序）

GET  /api/exercise-items/search?type=gym|yoga_stretch&q=&user_id=&limit=10
     自動完成用的模糊搜尋，同樣支援個人化排序

POST /api/exercise-items
     新增自訂項目到共用庫（type 決定寫進哪張表）
```

`exercise-sessions` / `workout-templates` 的既有建立端點，`details` 陣列裡每個項目新增可選欄位（向後相容，不傳就跟現在行為一樣）：

```jsonc
// 健身房動作
{ "exercise_item_id": 3, "exercise_name": "臥推", "sets": 4, "reps": "8-10", "weight_kg": 60 }
// 瑜珈/拉伸招式
{ "yoga_stretch_item_id": 7, "exercise_name": "下犬式", "duration_min": 3 }
```

### 前端整合（BLOCK_7）

「動作名稱」欄位從純文字 input 改成**帶自動完成建議的 input**（debounce 300ms 呼叫 search API）；選了建議項目就帶入對應的 `exercise_item_id`/`yoga_stretch_item_id`，並可把 `default_sets`/`default_reps` 當預設值帶入（使用者仍可覆蓋）。沒選、直接打完字送出，行為跟現在完全一樣。打的文字庫裡沒有時，旁邊顯示「加入動作庫」按鈕（呼叫 `POST /api/exercise-items`）。

這一版不規劃獨立的「動作庫管理頁面」，先用自動完成 + 隨手加入解決最痛的問題，管理頁面留到有實際需求時再做。

---

## 子系統二：多天訓練計畫與月曆排程

### 使用情境

你描述的流程：

1. 建立一個「訓練計畫」，一次規劃 3～5 天（例如 Push/Pull/Legs 三天分割，或 5 天分部位）。點一下「新增訓練計畫」，跳出一個小視窗，裡面可以直接把這 3～5 天全部設定完（每天各自的動作、組數、次數），一次送出。
2. 切到公版月曆畫面，把剛剛建好的「Day 1 / Day 2 / Day 3…」卡片，用拖曳的方式放到實際想訓練的日期格子上——這是**規劃**階段，先把整個週期排好。
3. 到了那天真的去運動，再回來補上**實際**發生的內容（可能跟計畫一樣、也可能有出入，例如少做一組、換了動作），這筆「實際紀錄」就是區塊 2/3 現有的「新增運動紀錄」（`exercise_sessions`），跟「計畫」是兩筆分開的資料，但會互相關聯，之後能對照「計畫 vs 實際」。

### 為什麼直接疊在 `workout_templates` 上，而不是另外造一組平行結構

`workout_templates`（+ `template_details`）已經是「一天份的訓練組合」這個概念了，而且區塊 7 前端已經做好建立範本、從範本快速填寫的完整流程（見〈與既有資料的相容策略〉）。多天計畫的「一天」就是一個 `workout_templates`；「計畫」只是把好幾個 `workout_templates` 綁在一起、按順序編號；「排程」只是把某個 `workout_templates` 貼到月曆上的某一天。這樣設計可以直接重用你已經在用的範本建立/套用邏輯，不用重寫一套新的「動作清單編輯器」。

### 資料模型

```sql
-- 訓練計畫（容器，不存實際動作內容）
CREATE TABLE training_programs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  program_name TEXT NOT NULL,           -- 例：「秋季增肌 PPL」
  day_count INTEGER NOT NULL CHECK(day_count BETWEEN 1 AND 7),  -- 通常 3~5，但不寫死上限
  description TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 計畫裡的每一天，指到一個既有的 workout_templates
CREATE TABLE training_program_days (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  program_id INTEGER NOT NULL,
  day_number INTEGER NOT NULL,          -- 1, 2, 3...（計畫內的相對天數，不是星期幾）
  day_label TEXT,                       -- 例：「Day 1 · 推」，未填就顯示範本名稱
  workout_template_id INTEGER NOT NULL,
  FOREIGN KEY(program_id) REFERENCES training_programs(id) ON DELETE CASCADE,
  FOREIGN KEY(workout_template_id) REFERENCES workout_templates(id) ON DELETE CASCADE,
  UNIQUE(program_id, day_number)
);

-- 月曆排程：把某個 program_day 貼到實際日期
CREATE TABLE training_schedule (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  program_day_id INTEGER NOT NULL,
  scheduled_date DATE NOT NULL,
  status TEXT NOT NULL DEFAULT '已排程' CHECK(status IN ('已排程', '已完成', '已跳過')),
  actual_exercise_session_id INTEGER,   -- 執行後補登，關聯到實際的 exercise_sessions
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY(program_day_id) REFERENCES training_program_days(id) ON DELETE CASCADE,
  FOREIGN KEY(actual_exercise_session_id) REFERENCES exercise_sessions(id) ON DELETE SET NULL,
  UNIQUE(user_id, scheduled_date)  -- 同一人同一天只能排一個訓練日（先簡化成這樣，之後要放寬再拿掉）
);
```

`status` 的變化時機：拖上月曆時建立為「已排程」；日期已過、且該筆被連結到一個 `actual_exercise_session_id` 時自動變「已完成」；使用者手動標記不練那天則設「已跳過」。

### API 設計

```
POST /api/training-programs
     一次建立整個計畫（含 N 天，每天各自的訓練項目明細），對應「小視窗一次設定 3~5 天」的需求：
     {
       "user_id": 1,
       "program_name": "秋季增肌 PPL",
       "days": [
         { "day_number": 1, "day_label": "Day 1 · 推", "exercise_type": "健身房", "duration_min": 60,
           "details": [{ "exercise_item_id": 3, "sets": 4, "reps": "8-10", "weight_kg": 60 }, ...] },
         { "day_number": 2, "day_label": "Day 2 · 拉", ... },
         { "day_number": 3, "day_label": "Day 3 · 腿", ... }
       ]
     }
     後端在同一次呼叫裡，依序幫每一天各自建立一個 workout_templates（重用既有的
     TemplateService.create_template），再建立 training_programs + training_program_days 把它們綁起來。

GET  /api/training-programs?user_id=
     列出使用者的所有計畫（含每天摘要，給「小視窗」或計畫清單頁用）

GET  /api/training-programs/{id}
     取得單一計畫完整內容（含每天的完整動作明細，展開展示用）

DELETE /api/training-programs/{id}
     刪除整個計畫（連動刪除 training_program_days；已排上月曆的 training_schedule 一併移除）

POST /api/training-schedule
     把某個 program_day 拖到某個日期：{ "program_day_id": 5, "scheduled_date": "2026-09-01" }

PUT  /api/training-schedule/{id}
     搬到另一天（拖曳移動），或手動改狀態（標記「已跳過」）

DELETE /api/training-schedule/{id}
     從月曆移除排程（不影響計畫本身）

GET  /api/training-schedule?user_id=&month=2026-09
     取得該月所有排程，給月曆畫面一次渲染

PUT  /api/training-schedule/{id}/link-actual
     執行完後，把當天實際紀錄的 exercise_session_id 綁回排程：{ "exercise_session_id": 42 }
     （也可以反過來：在「新增運動紀錄」頁偵測到當天有排程但還沒補登，主動問「這是不是在補
     ○○計畫 Day 2 的紀錄？」，選是的話呼叫這支 API，同時把計畫內容帶進表單當預設值）
```

### 前端整合（BLOCK_7）

**建立計畫的小視窗**：「新增訓練計畫」按鈕開一個 modal；先選天數（3/4/5，也開放自訂），依天數動態產生 N 個區塊（例如用分頁或直向排列），每個區塊長得跟現有「新增運動紀錄」裡的「訓練項目明細」表單一樣（重用同一套元件與子系統一的自動完成 input），填完全部天數後一次送出，呼叫 `POST /api/training-programs`。

**訓練月曆頁面**（新增一個路由，例如 `/training-calendar`）：標準月曆網格；側邊欄列出使用者的計畫，每個計畫展開成 N 張「Day 卡片」；卡片可拖曳（HTML5 drag-and-drop 或現成的拖放函式庫）到月曆格子上，放開時呼叫 `POST /api/training-schedule`；已排程的格子顯示 day_label；拖曳已排程的卡片到別的日期 = 呼叫 `PUT /api/training-schedule/{id}` 更新日期。

**計畫 vs 實際的銜接**：日期已過、該天有排程但 `actual_exercise_session_id` 還是空的格子，顯示「補登實際紀錄」提示；點下去導到「新增運動紀錄」頁，並把 `program_day_id` 透過 query string 帶過去，頁面偵測到這個參數就用該天的範本內容預填表單（跟現在「從範本快速填寫」共用同一段邏輯），使用者送出後前端再呼叫一次 `link-actual` 把兩筆資料綁起來。

---

## 與既有資料的相容策略

現在 BLOCK_2 完全是記憶體儲存、也還沒接上 BLOCK_1 的 SQLite（這是整個專案目前的已知狀況，不是區塊 8 特有問題）。區塊 8 的所有新表格設計要能在兩種情境都不出錯：

1. **短期（在記憶體版 BLOCK_2 上做）**：`exercise_item_library`、`yoga_stretch_items`、`user_item_usage`、`training_programs`、`training_program_days`、`training_schedule` 都先各自用一個記憶體 dict 起步（跟 `users_db`/`weight_db` 同套路），啟動時 seed 區塊 1 原本設計的 25 個健身動作 + 20 個瑜珈拉伸項目。
2. **長期（等專案真的接上 SQLite/SQLAlchemy 之後）**：直接套用上面的 SQL 設計，全部改成真表 + 真外鍵。

API 形狀從一開始就照長期版本設計，短期先用記憶體實作撐著，之後換成真資料庫不需要動前端或 API 合約。

---

## 實作順序建議

1. **子系統一（動作庫）先做**，因為子系統二的「一天」內容本來就要用到動作庫的自動完成。
   1. `ExerciseItemService` / `YogaStretchItemService`（記憶體版）+ 開機 seed + 3 個端點（list/search/create）。
   2. `user_item_usage` 記錄與個人化排序邏輯。
   3. `exercise-sessions` / `workout-templates` 的 create 端點接受可選 `exercise_item_id` / `yoga_stretch_item_id`，並做存在性驗證＋順便更新使用次數。
   4. BLOCK_7：動作名稱 input 換成自動完成元件（「新增運動紀錄」與「另存為範本」共用）。
2. **子系統二（訓練計畫 + 月曆）**
   1. `training_programs` / `training_program_days` / `training_schedule`（記憶體版）+ `POST /api/training-programs` 批次建立端點。
   2. 月曆讀取/排程/搬移/刪除的 4 支 API。
   3. BLOCK_7：新增訓練計畫小視窗（重用子系統一的自動完成元件 + 現有的訓練項目明細表單）。
   4. BLOCK_7：訓練月曆頁面（月曆網格 + 拖放）。
   5. 「補登實際紀錄」的銜接流程（`link-actual`）。
3. （可選，之後再做）等專案真的做資料庫整合時，把記憶體版全部換成 SQLite 表 + 外鍵——因為 API 合約沒變，這步只動後端內部實作，前端不用改。
