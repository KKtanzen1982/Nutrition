# -*- coding: utf-8 -*-
"""
通用版：抓出所有 base_weight_g 跟食材加總差距 >10% 或 >10g 的啟用中食譜，
「湯」類別且食材加總不足時，補上/調整一項「水」食材補齊差額；其他類別依比例縮放
現有食材份量，讓加總等於 base_weight_g。

用法：
    python fix_recipe_base_weight.py <API_BASE_URL>              # 預設 dry-run，只印出會做的事
    python fix_recipe_base_weight.py <API_BASE_URL> --apply      # 真的寫入

例如正式環境：
    python fix_recipe_base_weight.py http://your-api-host/api --apply
"""
import json
import sys
import urllib.request

THRESHOLD_PCT = 0.10
THRESHOLD_ABS = 10.0
WATER_NAME = "水"


def call(base, method, path, body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method,
                                  headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else None


def list_all_recipes(base):
    recipes, page = [], 1
    while True:
        data = call(base, "GET", f"/recipes?is_active=true&page={page}")
        recipes.extend(data["items"])
        if len(recipes) >= data["total"]:
            break
        page += 1
    return recipes


def find_or_create_water(base, apply):
    found = call(base, "GET", f"/ingredients/search?query={WATER_NAME}")
    for ing in found:
        if ing["ingredient_name"] == WATER_NAME:
            return ing["id"]
    if not apply:
        return None  # dry-run：先不建立，之後真的要補水的食譜只印出提示
    created = call(base, "POST", "/ingredients", {
        "ingredient_name": WATER_NAME, "category": "調味料", "unit": "g",
        "calories_per_100g": 0, "protein_per_100g": 0, "carbs_per_100g": 0,
        "fat_per_100g": 0, "fiber_per_100g": 0,
        "needs_stock_tracking": False, "cost_level": "低",
    })
    return created["id"]


def main():
    if len(sys.argv) < 2:
        print("用法: python fix_recipe_base_weight.py <API_BASE_URL> [--apply]")
        sys.exit(1)
    base = sys.argv[1].rstrip("/")
    apply = "--apply" in sys.argv[2:]

    summaries = list_all_recipes(base)
    mismatched = []
    for s in summaries:
        r = call(base, "GET", f"/recipes/{s['id']}")
        current_sum = sum(i["quantity_g"] for i in r["ingredients"])
        base_w = r["base_weight_g"]
        if base_w == 0 or abs(current_sum - base_w) > max(THRESHOLD_ABS, base_w * THRESHOLD_PCT):
            mismatched.append((r, current_sum))

    print(f"共 {len(summaries)} 道啟用中食譜，{len(mismatched)} 道差距超標。")
    if not mismatched:
        return

    water_id = None
    soup_needing_water = [(r, cur) for r, cur in mismatched if r["category"] == "湯" and cur < r["base_weight_g"]]
    if soup_needing_water:
        water_id = find_or_create_water(base, apply)
        print(f"「水」食材 id = {water_id}{'（dry-run 尚未建立）' if water_id is None else ''}")

    for r, current_sum in mismatched:
        rid, name, base_w = r["id"], r["recipe_name"], r["base_weight_g"]
        if r["category"] == "湯" and current_sum < base_w:
            missing = round(base_w - current_sum, 1)
            new_ingredients = [
                {"ingredient_id": i["ingredient_id"], "quantity_g": i["quantity_g"], "unit": i["unit"], "notes": i["notes"]}
                for i in r["ingredients"]
            ]
            if water_id is not None:
                new_ingredients.append({"ingredient_id": water_id, "quantity_g": missing, "unit": "g", "notes": None})
            print(f"[湯][{rid}] {name}: 原加總={current_sum}g，補水={missing}g -> 新加總={current_sum + missing}g（base_weight_g={base_w}）")
        else:
            scale = base_w / current_sum
            new_ingredients = [
                {"ingredient_id": i["ingredient_id"], "quantity_g": round(i["quantity_g"] * scale, 1),
                 "unit": i["unit"], "notes": i["notes"]}
                for i in r["ingredients"]
            ]
            new_sum = round(sum(i["quantity_g"] for i in new_ingredients), 1)
            print(f"[{rid}] {name}: 原加總={current_sum}g -> 縮放係數={scale:.3f} -> 新加總={new_sum}g（base_weight_g={base_w}）")

        if apply:
            call(base, "PUT", f"/recipes/{rid}/ingredients", new_ingredients)

    if not apply:
        print("\n（dry-run，尚未寫入任何資料，加上 --apply 才會真的更新）")


if __name__ == "__main__":
    main()
