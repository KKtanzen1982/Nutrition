"""
BLOCK_5: 端對端測試腳本
========================

仿 BLOCK_4/extracted/BLOCK_4_TEST_EXAMPLES.py。需要先啟動測試伺服器：
    uvicorn BLOCK_5_test_app:app --reload --port 8123
（或用 .claude/launch.json 的 block5-test-server 設定）

然後執行：
    python BLOCK_5_TEST_EXAMPLES.py

跑過完整流程：生成推薦 → 取得詳情 → 方案 A/C/D 微調 → 方案 B 重推整天 → 確認推薦。
沒有設定 ANTHROPIC_API_KEY 時全程使用 MockClaudeService，不會呼叫真的 Anthropic API。
"""

import json
import sys
import time
from datetime import date, timedelta

import requests

# Windows 主控台預設編碼（cp950/cp936）印不出中文和 emoji，改成 UTF-8 避免 print() 直接崩潰
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_URL = "http://localhost:8123"


def print_json(title: str, data) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))


def wait_for_job(job_id: str, timeout: float = 30.0) -> dict:
    start = time.time()
    while time.time() - start < timeout:
        r = requests.get(f"{BASE_URL}/meal-plans/jobs/{job_id}/status")
        r.raise_for_status()
        data = r.json()
        if data["status"] in ("completed", "failed"):
            return data
        time.sleep(0.5)
    raise TimeoutError(f"job {job_id} 逾時未完成")


def find_meal(day: dict, meal_type: str, user_id: int):
    for m in day["meals"]:
        if m["meal_type"] == meal_type and m["user_id"] == user_id:
            return m
    return None


def main():
    next_monday = date.today() + timedelta(days=(7 - date.today().weekday()) % 7 or 7)

    # ========== 1. 生成推薦 ==========
    resp = requests.post(f"{BASE_URL}/meal-plans/generate", json={
        "week_start_date": next_monday.isoformat(),
        "user_a_id": 1,
        "user_b_id": 2,
    })
    resp.raise_for_status()
    gen = resp.json()
    print_json("POST /meal-plans/generate", gen)

    job = wait_for_job(gen["job_id"])
    print_json("生成任務狀態（輪詢結果）", job)
    assert job["status"] == "completed", f"生成任務失敗：{job.get('error_message')}"
    plan_id = job["plan_id"]
    assert isinstance(plan_id, int), "plan_id 應該是資料庫自增的整數 ID，不是模擬值"

    # ========== 2. 取得週計畫 ==========
    plan = requests.get(f"{BASE_URL}/meal-plans/{plan_id}").json()
    print_json("GET /meal-plans/{plan_id}（生成後）", plan)
    assert len(plan["daily_details"]) == 7, "應該要有完整 7 天的菜單"

    monday = plan["daily_details"][0]
    user_a_id, user_b_id = plan["user_a_id"], plan["user_b_id"]

    breakfast_a = find_meal(monday, "breakfast", user_a_id)
    lunch_a = find_meal(monday, "lunch", user_a_id)
    dinner_b = find_meal(monday, "dinner", user_b_id)
    assert breakfast_a and lunch_a and dinner_b, "週一應該要有早餐/午餐(A)、晚餐(B)"

    # ========== 3. 方案 A：替換早餐 ==========
    alt_breakfast_id = 2 if breakfast_a["recipe_id"] != 2 else 1
    r = requests.post(f"{BASE_URL}/meal-plans/{plan_id}/adjust/replace-meal", json={
        "meal_date": monday["meal_date"],
        "meal_type": "breakfast",
        "user_id": user_a_id,
        "new_recipe_id": alt_breakfast_id,
    })
    r.raise_for_status()
    replace_result = r.json()
    print_json("方案 A：POST .../adjust/replace-meal", replace_result)
    assert replace_result["updated_meal"]["recipe_id"] == alt_breakfast_id

    # ========== 4. 方案 C：搜尋替換午餐 ==========
    r = requests.post(f"{BASE_URL}/meal-plans/{plan_id}/adjust/search-replace", json={
        "meal_date": monday["meal_date"],
        "meal_type": "lunch",
        "user_id": user_a_id,
        "search_query": "魚",
        "new_recipe_id": 6,  # 蒸魚配糙米飯
    })
    r.raise_for_status()
    search_result = r.json()
    print_json("方案 C：POST .../adjust/search-replace", search_result)
    assert search_result["updated_meal"]["recipe_id"] == 6

    # ========== 5. 方案 D：調整晚餐分量 ==========
    r = requests.put(f"{BASE_URL}/meal-plans/{plan_id}/adjust/serving-weight", json={
        "meal_date": monday["meal_date"],
        "meal_type": "dinner",
        "user_id": user_b_id,
        "new_serving_weight_g": 500,
    })
    r.raise_for_status()
    weight_result = r.json()
    print_json("方案 D：PUT .../adjust/serving-weight", weight_result)
    assert weight_result["updated_meal"]["serving_weight_g"] == 500

    # ========== 6. 方案 B：重推週二整天 ==========
    tuesday = plan["daily_details"][1]
    r = requests.post(f"{BASE_URL}/meal-plans/{plan_id}/adjust/regenerate-day", json={
        "meal_date": tuesday["meal_date"],
        "fixed_meals": [],
    })
    r.raise_for_status()
    regen = r.json()
    print_json("方案 B：POST .../adjust/regenerate-day", regen)

    regen_job = wait_for_job(regen["job_id"])
    print_json("重推整天任務狀態（輪詢結果）", regen_job)
    assert regen_job["status"] == "completed", f"重推整天失敗：{regen_job.get('error_message')}"

    # ========== 7. 再次取得週計畫，驗證變更 ==========
    plan_after = requests.get(f"{BASE_URL}/meal-plans/{plan_id}").json()
    print_json("GET /meal-plans/{plan_id}（微調後）", plan_after)

    other_days_unchanged = all(
        plan_after["daily_details"][i] == plan["daily_details"][i]
        for i in range(2, 7)
    )
    print(f"\n週三～週日維持不變：{other_days_unchanged}")
    assert other_days_unchanged, "重推週二不應該影響其他天"

    # ========== 8. 確認推薦 ==========
    r = requests.put(f"{BASE_URL}/meal-plans/{plan_id}/confirm")
    r.raise_for_status()
    print_json("PUT /meal-plans/{plan_id}/confirm", r.json())

    print("\n[PASS] BLOCK_5 端對端測試全部通過")


if __name__ == "__main__":
    main()
