"""
BLOCK_6: 端對端測試腳本
========================

仿 BLOCK_5/BLOCK_5_TEST_EXAMPLES.py。需要先啟動測試伺服器：
    uvicorn main:app --reload --port 8126
（或用 .claude/launch.json 的 block6-test-server 設定）

然後執行：
    python BLOCK_6_TEST_EXAMPLES.py

跑過完整流程：確認推薦 → 生成購物清單 → 讀取（按地點分組）→ 新增/編輯/刪除項目
→ 標記已購 → 狀態轉換到歸檔 → 讀取採購歷史 → 購買地點 CRUD → 食材地點偏好設定。
"""

import json
import sys

import requests

# Windows 主控台預設編碼（cp950/cp936）印不出中文，改成 UTF-8 避免 print() 直接崩潰
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_URL = "http://localhost:8126"
SEED_PLAN_ID = 1  # 見 BLOCK_6_seed_data.py 的 PLAN_ID


def print_json(title: str, data) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))


def main():
    # ========== 1. 確認推薦 → 生成購物清單 ==========
    r = requests.post(f"{BASE_URL}/meal-plans/{SEED_PLAN_ID}/confirm")
    r.raise_for_status()
    confirm_result = r.json()
    print_json("POST /meal-plans/{plan_id}/confirm", confirm_result)
    assert confirm_result["success"] is True
    shopping_list_id = confirm_result["shopping_list_id"]
    assert isinstance(shopping_list_id, int), "shopping_list_id 應該是資料庫自增的整數 ID"

    # 重複確認應該沿用同一份清單（冪等）
    r2 = requests.post(f"{BASE_URL}/meal-plans/{SEED_PLAN_ID}/confirm")
    r2.raise_for_status()
    assert r2.json()["shopping_list_id"] == shopping_list_id, "重複確認不應該產生新的購物清單"

    # ========== 2. 讀取購物清單（按地點分組） ==========
    r = requests.get(f"{BASE_URL}/shopping-lists/{shopping_list_id}")
    r.raise_for_status()
    shopping_list = r.json()
    print_json("GET /shopping-lists/{id}", shopping_list)
    assert shopping_list["total_items"] > 0, "應該要有食材項目"
    assert len(shopping_list["items_by_location"]) > 0, "應該要有依地點分組"

    first_location = next(iter(shopping_list["items_by_location"]))
    first_group = shopping_list["items_by_location"][first_location][0]
    first_item = first_group["items"][0]
    print(f"\n第一個項目：{first_item['ingredient_name']}（{first_item['quantity_needed_g']}{first_item['unit']}），"
          f"地點：{first_location}，成本：{first_item['cost_level']}，需補購：{first_item['needs_restocking']}")

    # ========== 3. 新增臨時食材項目 ==========
    r = requests.post(f"{BASE_URL}/shopping-lists/{shopping_list_id}/items", json={
        "ingredient_id": 3,  # 香蕉
        "quantity_needed_g": 300,
        "notes": "臨時想加購的水果",
    })
    r.raise_for_status()
    new_item = r.json()
    print_json("POST /shopping-lists/{id}/items", new_item)
    new_item_id = new_item["id"]

    # ========== 4. 編輯項目分量 ==========
    r = requests.put(f"{BASE_URL}/shopping-lists/{shopping_list_id}/items/{new_item_id}", json={
        "quantity_needed_g": 400,
    })
    r.raise_for_status()
    print_json("PUT /shopping-lists/{id}/items/{item_id}", r.json())

    # ========== 5. 標記已購 ==========
    r = requests.put(f"{BASE_URL}/shopping-lists/{shopping_list_id}/items/{new_item_id}/purchased", json={
        "is_purchased": True,
    })
    r.raise_for_status()
    print_json("PUT /shopping-lists/{id}/items/{item_id}/purchased", r.json())

    # ========== 6. 刪除項目 ==========
    r = requests.delete(f"{BASE_URL}/shopping-lists/{shopping_list_id}/items/{new_item_id}")
    r.raise_for_status()
    print_json("DELETE /shopping-lists/{id}/items/{item_id}", r.json())

    # ========== 7. 狀態轉換：草稿 → 已確認 → 採購中 → 已採購 → 歸檔 ==========
    for status in ["已確認", "採購中", "已採購", "歸檔"]:
        r = requests.put(f"{BASE_URL}/shopping-lists/{shopping_list_id}/status", json={"status": status})
        r.raise_for_status()
        print(f"狀態改為「{status}」：{r.json()['message']}")

    # ========== 8. 讀取採購歷史（歸檔快照） ==========
    r = requests.get(f"{BASE_URL}/shopping-lists/history")
    r.raise_for_status()
    history = r.json()
    print_json("GET /shopping-lists/history", history)
    assert history["total"] >= 1, "歸檔後應該至少有一筆採購歷史"

    # ========== 9. 購買地點 CRUD ==========
    r = requests.post(f"{BASE_URL}/purchase-locations", json={"location_name": "有機商店", "priority_order": 5})
    r.raise_for_status()
    new_location = r.json()
    print_json("POST /purchase-locations", new_location)

    r = requests.put(f"{BASE_URL}/purchase-locations/{new_location['id']}", json={"description": "假日限定"})
    r.raise_for_status()
    print_json("PUT /purchase-locations/{id}", r.json())

    r = requests.get(f"{BASE_URL}/purchase-locations")
    r.raise_for_status()
    print(f"\n目前購買地點數量：{len(r.json())}")

    # ========== 10. 食材地點偏好設定 ==========
    r = requests.put(f"{BASE_URL}/ingredients/6/location-preference", json={
        "preferences": [
            {"preferred_location_id": new_location["id"], "priority": 1, "notes": "測試改用有機商店"},
        ],
    })
    r.raise_for_status()
    print_json("PUT /ingredients/{id}/location-preference", r.json())

    # 刪除地點前先示範一個沒有被任何食材偏好引用的臨時地點，避免留下懸空的外鍵參照
    r = requests.post(f"{BASE_URL}/purchase-locations", json={"location_name": "臨時測試地點", "priority_order": 9})
    r.raise_for_status()
    throwaway_location_id = r.json()["id"]
    r = requests.delete(f"{BASE_URL}/purchase-locations/{throwaway_location_id}")
    r.raise_for_status()
    print_json("DELETE /purchase-locations/{id}", r.json())

    print("\n[PASS] BLOCK_6 端對端測試全部通過")


if __name__ == "__main__":
    main()
