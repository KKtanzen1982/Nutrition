"""規則式週菜單選餐演算法（取代 Claude API 呼叫）
================================================
純函式，dict 進 dict 出，同步呼叫。設計依據見 plan §4.3。

簡化說明（相對原規劃文件）：「可選副食」的隨機觸發拿掉了，固定用主食40%+肉40%+菜20%，
理由是隨機性會讓「同輸入跑兩次結果一致」這個可測性要求變複雜，而這個簡化不影響核心邏輯
（熱量/蛋白質貼合、不重複上限、成本比例）。之後想加可選副食，在 build_day_meals 的
LUNCH_DINNER_CATEGORIES 常數旁加邏輯即可。
"""

from datetime import timedelta
from typing import List, Dict, Optional, Set, Tuple

MEAL_SHARES = {"breakfast": 0.20, "lunch": 0.35, "dinner": 0.35, "afternoon_snack": 0.10}
LUNCH_DINNER_CATEGORIES = [("主食", 0.4), ("肉", 0.4), ("菜", 0.2)]
SERVING_SCALE_MIN, SERVING_SCALE_MAX = 0.6, 1.6
MAX_RECIPE_REUSE = 2


def scale_recipe(recipe: Dict, target_calories: float) -> Dict:
    calories = recipe.get("calories") or 0
    scale = target_calories / calories if calories > 0 else 1.0
    scale = min(max(scale, SERVING_SCALE_MIN), SERVING_SCALE_MAX)
    return {
        "recipe_id": recipe["id"], "recipe_name": recipe["recipe_name"],
        "serving_weight_g": round(recipe["base_weight_g"] * scale),
        "calories": round(calories * scale, 1),
        "protein_g": round((recipe.get("protein_g") or 0) * scale, 1),
        "carbs_g": round((recipe.get("carbs_g") or 0) * scale, 1),
        "fat_g": round((recipe.get("fat_g") or 0) * scale, 1),
        "fiber_g": round((recipe.get("fiber_g") or 0) * scale, 1),
    }


def select_recipe_for_slot(candidates: List[Dict], category: str, target_calories: float, target_protein: float,
                            usage_counter: Dict[int, int], cost_counter: Dict[str, int],
                            yesterday_recipe_ids: Set[int]) -> Optional[Dict]:
    pool = [r for r in candidates if r["category"] == category]
    if not pool:
        return None

    not_capped = [r for r in pool if usage_counter.get(r["id"], 0) < MAX_RECIPE_REUSE]
    pool = not_capped or pool

    low_count = cost_counter.get("低", 0)
    midhigh_count = cost_counter.get("中", 0) + cost_counter.get("高", 0)
    if midhigh_count + 1 >= low_count:
        low_only = [r for r in pool if r["cost_level"] == "低"]
        if low_only:
            pool = low_only

    scored = []
    for r in pool:
        scaled = scale_recipe(r, target_calories)
        cal_diff = abs(scaled["calories"] - target_calories) / max(target_calories, 1)
        protein_diff = abs(scaled["protein_g"] - target_protein) / max(target_protein, 1)
        score = cal_diff + 0.5 * protein_diff
        penalty = 0.15 if r["id"] in yesterday_recipe_ids else 0.0
        scored.append((score + penalty, usage_counter.get(r["id"], 0), r["id"], r))
    scored.sort(key=lambda t: (t[0], t[1], t[2]))
    chosen = scored[0][3]

    usage_counter[chosen["id"]] = usage_counter.get(chosen["id"], 0) + 1
    cost_counter[chosen["cost_level"]] = cost_counter.get(chosen["cost_level"], 0) + 1
    return chosen


def build_day_meals(candidates: List[Dict], user_a_ctx: Dict, user_b_ctx: Dict, meal_date,
                     usage_counter: Dict[int, int], cost_counter: Dict[str, int],
                     yesterday_recipe_ids: Set[int], fixed_meals: Optional[Set[Tuple[str, str]]] = None
                     ) -> Tuple[List[Dict], Set[int]]:
    """fixed_meals: {(meal_type, 'A'|'B')} 這組不重新產生，重推整天時用。"""
    fixed_meals = fixed_meals or set()
    meals: List[Dict] = []
    today_recipe_ids: Set[int] = set()

    for user_key, ctx in (("A", user_a_ctx), ("B", user_b_ctx)):
        for meal_type, category in (("breakfast", "早餐"), ("afternoon_snack", "下午茶")):
            if (meal_type, user_key) in fixed_meals:
                continue
            share = MEAL_SHARES[meal_type]
            target_cal = ctx["daily_calories_target"] * share
            target_protein = ctx["daily_protein_g"] * share
            recipe = select_recipe_for_slot(candidates, category, target_cal, target_protein,
                                             usage_counter, cost_counter, yesterday_recipe_ids)
            if not recipe:
                continue
            scaled = scale_recipe(recipe, target_cal)
            meals.append({"meal_date": meal_date, "meal_type": meal_type, "user": user_key, "category": category, **scaled})
            today_recipe_ids.add(recipe["id"])

    for meal_type in ("lunch", "dinner"):
        if (meal_type, "A") in fixed_meals or (meal_type, "B") in fixed_meals:
            continue
        share = MEAL_SHARES[meal_type]
        avg_cal = (user_a_ctx["daily_calories_target"] + user_b_ctx["daily_calories_target"]) / 2 * share
        max_protein = max(user_a_ctx["daily_protein_g"], user_b_ctx["daily_protein_g"]) * share
        for category, cat_share in LUNCH_DINNER_CATEGORIES:
            slot_cal = avg_cal * cat_share
            slot_protein = max_protein * cat_share
            recipe = select_recipe_for_slot(candidates, category, slot_cal, slot_protein,
                                             usage_counter, cost_counter, yesterday_recipe_ids)
            if not recipe:
                continue
            today_recipe_ids.add(recipe["id"])
            for user_key, ctx in (("A", user_a_ctx), ("B", user_b_ctx)):
                user_target_cal = ctx["daily_calories_target"] * share * cat_share
                scaled = scale_recipe(recipe, user_target_cal)
                meals.append({"meal_date": meal_date, "meal_type": meal_type, "user": user_key, "category": category, **scaled})

    return meals, today_recipe_ids


def generate_week_plan(candidates: List[Dict], user_a_ctx: Dict, user_b_ctx: Dict, week_start_date) -> List[Dict]:
    usage_counter: Dict[int, int] = {}
    cost_counter: Dict[str, int] = {}
    yesterday_ids: Set[int] = set()
    days = []
    for i in range(7):
        d = week_start_date + timedelta(days=i)
        meals, today_ids = build_day_meals(candidates, user_a_ctx, user_b_ctx, d, usage_counter, cost_counter, yesterday_ids)
        days.append({"date": d, "meals": meals})
        yesterday_ids = today_ids
    return days
