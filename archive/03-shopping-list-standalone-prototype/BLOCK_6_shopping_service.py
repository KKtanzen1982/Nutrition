"""
BLOCK_6: 購物清單純計算邏輯

這個模組不碰資料庫、不 import SQLAlchemy，只吃/吐 plain dict，方便單元測試。
BLOCK_6_db_service.py 負責把 ORM 查詢結果轉成這裡要的 dict 格式，再呼叫這裡的函式，
最後把結果寫回資料庫。

涵蓋的規則（架構文件沒寫死細節，這裡是本區塊補的實作決策，詳見 BLOCK_6_ARCHITECTURE_DESIGN.md）：
- 2 人食材合併加總：跨 7 天、跨 A/B 兩人的所有餐次，依食譜基準份量比例換算後加總
- 成本等級：食材出現在多道食譜、且成本等級不同 -> 取最高者（保守估算）
- assigned_user_id：食材只出現在單一使用者的餐點 -> 標記該人；兩人都用到 -> None（共用）
- 購買地點：優先採用 ingredient_location_preference priority=1；查無則退回
  ingredient_library.preferred_purchase_location 文字比對；都沒有則 None
- 補貨警告：needs_stock_tracking=True 且「目前庫存 - 本週所需量 < 最低閾值」-> True
"""

from typing import Any, Dict, List, Optional, Set

COST_LEVEL_RANK = {"低": 0, "中": 1, "高": 2}
COST_LEVEL_BY_RANK = {v: k for k, v in COST_LEVEL_RANK.items()}


def aggregate_ingredient_quantities(
    meal_rows: List[Dict[str, Any]],
    recipe_ingredients_by_recipe: Dict[int, List[Dict[str, Any]]],
    recipe_base_weight_by_id: Dict[int, float],
) -> Dict[int, Dict[str, Any]]:
    """
    把一週所有餐次（meal_rows）依食譜食材明細展開、按比例換算、加總成每個食材的總用量。

    meal_rows: [{"recipe_id": int, "serving_weight_g": float, "assigned_user_id": int}, ...]
    recipe_ingredients_by_recipe: {recipe_id: [{"ingredient_id": int, "quantity_g": float}, ...]}
    recipe_base_weight_by_id: {recipe_id: base_weight_g}

    回傳: {ingredient_id: {"quantity_needed_g": float, "user_ids": set, "recipe_ids": set}}
    """
    result: Dict[int, Dict[str, Any]] = {}

    for meal in meal_rows:
        recipe_id = meal["recipe_id"]
        serving_weight_g = meal.get("serving_weight_g")
        assigned_user_id = meal.get("assigned_user_id")

        base_weight_g = recipe_base_weight_by_id.get(recipe_id)
        ingredients = recipe_ingredients_by_recipe.get(recipe_id, [])
        if not base_weight_g or not ingredients:
            continue

        scale = (serving_weight_g or base_weight_g) / base_weight_g

        for ing in ingredients:
            ingredient_id = ing["ingredient_id"]
            scaled_qty = ing["quantity_g"] * scale

            entry = result.setdefault(
                ingredient_id, {"quantity_needed_g": 0.0, "user_ids": set(), "recipe_ids": set()}
            )
            entry["quantity_needed_g"] += scaled_qty
            entry["recipe_ids"].add(recipe_id)
            if assigned_user_id is not None:
                entry["user_ids"].add(assigned_user_id)

    for entry in result.values():
        entry["quantity_needed_g"] = round(entry["quantity_needed_g"], 1)

    return result


def determine_assigned_user(user_ids: Set[int]) -> Optional[int]:
    """食材只被單一使用者的餐點用到 -> 標記該人；兩人都用到（或查無使用者）-> None（共用）"""
    if len(user_ids) == 1:
        return next(iter(user_ids))
    return None


def determine_cost_level(recipe_ids: Set[int], recipe_cost_level_by_id: Dict[int, str]) -> Optional[str]:
    """食材出現在多道食譜、且成本等級不同 -> 取最高者（保守估算，避免低估總成本）"""
    ranks = [
        COST_LEVEL_RANK[recipe_cost_level_by_id[rid]]
        for rid in recipe_ids
        if rid in recipe_cost_level_by_id and recipe_cost_level_by_id[rid] in COST_LEVEL_RANK
    ]
    if not ranks:
        return None
    return COST_LEVEL_BY_RANK[max(ranks)]


def determine_purchase_location(
    ingredient_id: int,
    location_preferences: List[Dict[str, Any]],
    fallback_location_name: Optional[str],
    location_id_by_name: Dict[str, int],
) -> Optional[int]:
    """
    location_preferences: 該食材在 ingredient_location_preference 的所有列，
        [{"priority": int, "preferred_location_id": int}, ...]（可能跨多個食材，呼叫端需先篩過）
    fallback_location_name / location_id_by_name: 查無結構化偏好時的文字備援比對
    """
    my_prefs = [p for p in location_preferences if p.get("ingredient_id", ingredient_id) == ingredient_id]
    if my_prefs:
        best = min(my_prefs, key=lambda p: p["priority"])
        return best["preferred_location_id"]

    if fallback_location_name and fallback_location_name in location_id_by_name:
        return location_id_by_name[fallback_location_name]

    return None


def determine_needs_restocking(
    needs_stock_tracking: bool,
    current_quantity_g: Optional[float],
    min_threshold_g: Optional[float],
    quantity_needed_g: float,
) -> bool:
    """扣掉本週所需量後，剩餘庫存若低於最低閾值 -> 需要補購"""
    if not needs_stock_tracking:
        return False
    remaining = (current_quantity_g or 0.0) - quantity_needed_g
    return remaining < (min_threshold_g or 0.0)


def build_shopping_list_items(
    aggregated: Dict[int, Dict[str, Any]],
    recipe_cost_level_by_id: Dict[int, str],
    ingredient_info_by_id: Dict[int, Dict[str, Any]],
    location_preferences_by_ingredient: Dict[int, List[Dict[str, Any]]],
    location_id_by_name: Dict[str, int],
    stock_by_ingredient_id: Dict[int, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    把 aggregate_ingredient_quantities() 的結果，組成可直接寫入 ShoppingListItem 的 dict 列表。

    ingredient_info_by_id: {ingredient_id: {"unit": str, "needs_stock_tracking": bool,
                                             "preferred_purchase_location": Optional[str]}}
    stock_by_ingredient_id: {ingredient_id: {"current_quantity_g": float, "min_threshold_g": float}}
    """
    items: List[Dict[str, Any]] = []

    for ingredient_id, entry in aggregated.items():
        info = ingredient_info_by_id.get(ingredient_id, {})
        stock = stock_by_ingredient_id.get(ingredient_id, {})
        quantity_needed_g = entry["quantity_needed_g"]

        purchase_location_id = determine_purchase_location(
            ingredient_id=ingredient_id,
            location_preferences=location_preferences_by_ingredient.get(ingredient_id, []),
            fallback_location_name=info.get("preferred_purchase_location"),
            location_id_by_name=location_id_by_name,
        )

        items.append({
            "ingredient_id": ingredient_id,
            "quantity_needed_g": quantity_needed_g,
            "unit": info.get("unit", "g"),
            "purchase_location_id": purchase_location_id,
            "cost_level": determine_cost_level(entry["recipe_ids"], recipe_cost_level_by_id),
            "needs_restocking": determine_needs_restocking(
                needs_stock_tracking=bool(info.get("needs_stock_tracking", False)),
                current_quantity_g=stock.get("current_quantity_g"),
                min_threshold_g=stock.get("min_threshold_g"),
                quantity_needed_g=quantity_needed_g,
            ),
            "assigned_user_id": determine_assigned_user(entry["user_ids"]),
        })

    return items
