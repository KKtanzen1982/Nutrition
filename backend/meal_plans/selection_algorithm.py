"""規則式週菜單選餐演算法（取代 Claude API 呼叫）
================================================
純函式，dict 進 dict 出，同步呼叫。設計依據見 plan §4.3。

簡化說明（相對原規劃文件）：「可選副食」的隨機觸發拿掉了，固定用主食/肉/菜（+湯，當天有安排時）的
固定比例，理由是隨機性會讓「同輸入跑兩次結果一致」這個可測性要求變複雜，而這個簡化不影響核心邏輯
（熱量/蛋白質貼合、不重複上限、成本比例）。之後想加可選副食，在 build_day_meals 的
LUNCH_DINNER_CATEGORIES 常數旁加邏輯即可。
"""

from datetime import timedelta
from typing import List, Dict, Optional, Set, Tuple

MEAL_SHARES = {"breakfast": 0.20, "lunch": 0.35, "dinner": 0.35, "afternoon_snack": 0.10}
LUNCH_DINNER_CATEGORIES = [("主食", 0.4), ("肉", 0.4), ("菜", 0.2)]
LUNCH_DINNER_CATEGORIES_WITH_SOUP = [("主食", 0.35), ("肉", 0.35), ("菜", 0.15), ("湯", 0.15)]
SERVING_SCALE_MIN, SERVING_SCALE_MAX = 0.6, 1.6

# 候選4：重複次數上限依候選池大小動態調整——池子夠大就不需要靠「反正吃完 2 次都還能選」撐候選池
MAX_RECIPE_REUSE_LARGE_POOL = 1
MAX_RECIPE_REUSE_SMALL_POOL = 2
LARGE_POOL_THRESHOLD = 12

FAVORITE_BONUS = 0.12  # 候選3：最愛清單軟性加權，從分數中扣掉，讓最愛食譜比較容易勝出但不保證
CARB_SOURCE_REPEAT_PENALTY = 0.12  # 候選1：主食類昨天用過的碳水來源今天扣分
OVERSHOOT_PENALTY_MULTIPLIER = 1.5  # 熱量超過目標比不足目標扣更多分：使用者在意的是「推薦熱量高於目標」，同等幅度下優先閃避超標

# 整週菜色多樣性上限：這幾個類別一週最多出現幾種「不同」食譜（不是次數上限，是種類上限）。
# 一旦某類別已經用滿上限種類，候選池會限縮成只剩已經用過的那幾種，之後只在這幾種裡面選。
CATEGORY_VARIETY_CAP = {"主食": 3, "肉": 3, "菜": 3, "下午茶": 2}

# 主食白飯規則：週一到週五中午是便當（見 prep_planner.py），便當主食一律白飯，方便備料；
# 其他餐（週末午餐＋每天晚餐）白飯占比抓 80%，用累積比例決定每一格要不要白飯，維持「同輸入跑兩次結果一致」。
BENTO_CARB_SOURCE = "飯"
# 便當主食要選「純白飯」這道，不能選咖哩雞肉飯/打拋豬肉飯這種本身已經帶肉的一鍋飯料理——
# 便當是主食/肉/菜三格分開裝（見 prep_planner.py:4），主食格選到帶肉的飯會跟另外配的「肉」格重複，
# 備料上也沒辦法把肉單獨退冰/微波。純白飯食譜需要另外用 create_recipe API 新增（carb_source="飯"）。
BENTO_PLAIN_STAPLE_NAMES = {"白飯"}
BENTO_WEEKDAY_CUTOFF = 5  # date.weekday() < 5 為週一~週五
OTHER_MEAL_RICE_RATIO = 0.8


def _should_pick_rice(tracker: Dict[str, int]) -> bool:
    total = tracker.get("total", 0)
    rice = tracker.get("rice", 0)
    target_rice_count = round(OTHER_MEAL_RICE_RATIO * (total + 1))
    return rice < target_rice_count


def get_max_reuse(pool_size: int) -> int:
    return MAX_RECIPE_REUSE_LARGE_POOL if pool_size >= LARGE_POOL_THRESHOLD else MAX_RECIPE_REUSE_SMALL_POOL


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


def _cal_penalty(actual_calories: float, target_calories: float) -> float:
    """熱量偏差比例，超過目標的部分加權放大（見 OVERSHOOT_PENALTY_MULTIPLIER）"""
    diff = actual_calories - target_calories
    pct = abs(diff) / max(target_calories, 1)
    return pct * OVERSHOOT_PENALTY_MULTIPLIER if diff > 0 else pct


def select_recipe_for_slot(candidates: List[Dict], category: str, target_calories: float, target_protein: float,
                            usage_counter: Dict[int, int], cost_counter: Dict[str, int],
                            yesterday_recipe_ids: Set[int], favorite_recipe_ids: Optional[Set[int]] = None,
                            yesterday_carb_sources: Optional[Set[str]] = None,
                            weekly_variety: Optional[Dict[str, Set[int]]] = None,
                            secondary_target: Optional[Tuple[float, float]] = None,
                            require_carb_source: Optional[str] = None,
                            exclude_carb_source: Optional[str] = None,
                            require_recipe_name_in: Optional[Set[str]] = None,
                            require_pairing_style: Optional[str] = None) -> Optional[Dict]:
    """secondary_target: (calories, protein_g)，共食類餐點（午餐/晚餐）兩人熱量目標常常差很多，
    只用平均值選菜會讓熱量需求較低那方的份量在後續各自縮放時撞到 SERVING_SCALE_MIN 下限、實際熱量超出他自己的目標。
    傳入的話評分改採「兩人之中縮放後偏差較大者」（worst-case），挑對兩人都合理的食譜，而不是只顧平均值。
    require_carb_source/exclude_carb_source/require_recipe_name_in：主食白飯規則用，
    require_pairing_style：跟當餐主食搭配用（見 build_day_meals），三者都篩不到就退回原候選池
    （安全防呆，避免因為食譜庫選項不夠而選不到菜）；pairing_style 沒標的食譜（None）視為百搭，不會被篩掉。"""
    pool = [r for r in candidates if r["category"] == category]
    if not pool:
        return None
    favorite_recipe_ids = favorite_recipe_ids or set()
    yesterday_carb_sources = yesterday_carb_sources or set()

    if require_recipe_name_in is not None:
        filtered = [r for r in pool if r.get("recipe_name") in require_recipe_name_in]
        if filtered:
            pool = filtered
    if require_carb_source is not None:
        filtered = [r for r in pool if r.get("carb_source") == require_carb_source]
        if filtered:
            pool = filtered
    if exclude_carb_source is not None:
        filtered = [r for r in pool if r.get("carb_source") != exclude_carb_source]
        if filtered:
            pool = filtered
    if require_pairing_style is not None:
        filtered = [r for r in pool if r.get("pairing_style") in (None, require_pairing_style)]
        if filtered:
            pool = filtered

    variety_cap = CATEGORY_VARIETY_CAP.get(category)
    used_variety = None
    if variety_cap is not None and weekly_variety is not None:
        used_variety = weekly_variety.setdefault(category, set())
        if len(used_variety) >= variety_cap:
            restricted = [r for r in pool if r["id"] in used_variety]
            if restricted:
                pool = restricted

    max_reuse = get_max_reuse(len(pool))
    not_capped = [r for r in pool if usage_counter.get(r["id"], 0) < max_reuse]
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
        cal_diff = _cal_penalty(scaled["calories"], target_calories)
        protein_diff = abs(scaled["protein_g"] - target_protein) / max(target_protein, 1)
        score = cal_diff + 0.5 * protein_diff
        if secondary_target is not None:
            sec_cal, sec_protein = secondary_target
            sec_scaled = scale_recipe(r, sec_cal)
            sec_cal_diff = _cal_penalty(sec_scaled["calories"], sec_cal)
            sec_protein_diff = abs(sec_scaled["protein_g"] - sec_protein) / max(sec_protein, 1)
            score = max(score, sec_cal_diff + 0.5 * sec_protein_diff)
        if r["id"] in yesterday_recipe_ids:
            score += 0.15
        if category == "主食" and r.get("carb_source") and r["carb_source"] in yesterday_carb_sources:
            score += CARB_SOURCE_REPEAT_PENALTY
        if r["id"] in favorite_recipe_ids:
            score -= FAVORITE_BONUS
        scored.append((score, usage_counter.get(r["id"], 0), r["id"], r))
    scored.sort(key=lambda t: (t[0], t[1], t[2]))
    chosen = scored[0][3]

    usage_counter[chosen["id"]] = usage_counter.get(chosen["id"], 0) + 1
    cost_counter[chosen["cost_level"]] = cost_counter.get(chosen["cost_level"], 0) + 1
    if used_variety is not None:
        used_variety.add(chosen["id"])
    return chosen


def build_day_meals(candidates: List[Dict], user_a_ctx: Dict, user_b_ctx: Dict, meal_date,
                     usage_counter: Dict[int, int], cost_counter: Dict[str, int],
                     yesterday_recipe_ids: Set[int], fixed_meals: Optional[Set[Tuple[str, str]]] = None,
                     preferred_recipes: Optional[Dict[Tuple[str, str], Dict]] = None,
                     favorite_recipe_ids: Optional[Set[int]] = None,
                     yesterday_carb_sources: Optional[Set[str]] = None,
                     include_soup: bool = False,
                     weekly_variety: Optional[Dict[str, Set[int]]] = None,
                     other_meal_rice_tracker: Optional[Dict[str, int]] = None
                     ) -> Tuple[List[Dict], Set[int], Set[str]]:
    """fixed_meals: {(meal_type, 'A'|'B')} 這組不重新產生，重推整天時用。
    preferred_recipes: {(meal_type, 'A'|'B'): candidate_dict} 使用者固定吃的餐點（見 FixedMealPreference），
    直接套用這份食譜、只依當天熱量目標調整份量，不跑選餐演算法、也不占用重複次數/成本比例的名額。
    favorite_recipe_ids: 兩人最愛清單的聯集，選餐評分時軟性加權。
    yesterday_carb_sources: 昨天午餐+晚餐用過的主食碳水來源（飯/麵/其他），今天主食選餐時扣分避免連續重複。
    include_soup: 這天午餐/晚餐要不要多排一道湯（湯天由 SoupDayPreference 決定，兩人任一人勾選即算）。
    weekly_variety: 整週跨天累積的「肉/菜/下午茶已用過哪些食譜 id」，見 CATEGORY_VARIETY_CAP，
    呼叫端要用同一個 dict 物件跨整週傳入（會被原地修改），這樣才能累積整週上限。
    other_meal_rice_tracker: {"rice": int, "total": int}，累積「便當以外」主食格子選過幾次白飯，
    用來把整週白飯占比逼近 OTHER_MEAL_RICE_RATIO，呼叫端要用同一個 dict 物件跨整週傳入（會被原地修改）。
    回傳 (meals, today_recipe_ids, today_carb_sources)。"""
    fixed_meals = fixed_meals or set()
    preferred_recipes = preferred_recipes or {}
    favorite_recipe_ids = favorite_recipe_ids or set()
    yesterday_carb_sources = yesterday_carb_sources or set()
    weekly_variety = weekly_variety if weekly_variety is not None else {}
    other_meal_rice_tracker = other_meal_rice_tracker if other_meal_rice_tracker is not None else {}
    meals: List[Dict] = []
    today_recipe_ids: Set[int] = set()
    today_carb_sources: Set[str] = set()

    for user_key, ctx in (("A", user_a_ctx), ("B", user_b_ctx)):
        for meal_type, category in (("breakfast", "早餐"), ("afternoon_snack", "下午茶")):
            if (meal_type, user_key) in fixed_meals:
                continue
            share = MEAL_SHARES[meal_type]
            target_cal = ctx["daily_calories_target"] * share
            target_protein = ctx["daily_protein_g"] * share

            preferred = preferred_recipes.get((meal_type, user_key))
            if preferred:
                recipe = preferred
            else:
                recipe = select_recipe_for_slot(candidates, category, target_cal, target_protein,
                                                 usage_counter, cost_counter, yesterday_recipe_ids,
                                                 favorite_recipe_ids, weekly_variety=weekly_variety)
            if not recipe:
                continue
            scaled = scale_recipe(recipe, target_cal)
            meals.append({"meal_date": meal_date, "meal_type": meal_type, "user": user_key, "category": category, **scaled})
            today_recipe_ids.add(recipe["id"])

    categories = LUNCH_DINNER_CATEGORIES_WITH_SOUP if include_soup else LUNCH_DINNER_CATEGORIES
    for meal_type in ("lunch", "dinner"):
        if (meal_type, "A") in fixed_meals or (meal_type, "B") in fixed_meals:
            continue
        share = MEAL_SHARES[meal_type]
        staple_pairing_style = None  # 這餐主食的搭配風格（家常/西式），主食類（categories 第一項）選出後才會有值,
        # 用來限制肉/菜/湯只從跟主食搭的風格裡選（見 select_recipe_for_slot 的 require_pairing_style）
        for category, cat_share in categories:
            a_slot_cal = user_a_ctx["daily_calories_target"] * share * cat_share
            a_slot_protein = user_a_ctx["daily_protein_g"] * share * cat_share
            b_slot_cal = user_b_ctx["daily_calories_target"] * share * cat_share
            b_slot_protein = user_b_ctx["daily_protein_g"] * share * cat_share
            require_carb_source = None
            exclude_carb_source = None
            require_recipe_name_in = None
            is_bento_lunch = category == "主食" and meal_type == "lunch" and meal_date.weekday() < BENTO_WEEKDAY_CUTOFF
            if category == "主食":
                if is_bento_lunch:
                    require_recipe_name_in = BENTO_PLAIN_STAPLE_NAMES
                elif _should_pick_rice(other_meal_rice_tracker):
                    require_carb_source = BENTO_CARB_SOURCE
                else:
                    exclude_carb_source = BENTO_CARB_SOURCE

            # 這個類別有固定餐點設定（見 FixedMealPreference）：直接套用，不跑選餐演算法，
            # 也就不受白飯規則/重複次數/成本比例限制——使用者刻意固定的選擇，尊重到底。
            preferred = preferred_recipes.get((meal_type, category))
            if preferred:
                recipe = preferred
            else:
                # 兩人熱量目標常差很多，選菜時看兩人各自的偏差（worst-case），不是只看平均值，
                # 避免熱量需求較低那方的份量之後被迫縮到 SERVING_SCALE_MIN 下限、實際熱量超出他自己的目標
                recipe = select_recipe_for_slot(candidates, category, a_slot_cal, a_slot_protein,
                                                 usage_counter, cost_counter, yesterday_recipe_ids,
                                                 favorite_recipe_ids, yesterday_carb_sources, weekly_variety,
                                                 secondary_target=(b_slot_cal, b_slot_protein),
                                                 require_carb_source=require_carb_source,
                                                 exclude_carb_source=exclude_carb_source,
                                                 require_recipe_name_in=require_recipe_name_in,
                                                 require_pairing_style=None if category == "主食" else staple_pairing_style)
            if not recipe:
                continue
            if category == "主食":
                staple_pairing_style = recipe.get("pairing_style")
            today_recipe_ids.add(recipe["id"])
            if category == "主食" and recipe.get("carb_source"):
                today_carb_sources.add(recipe["carb_source"])
            if category == "主食" and not is_bento_lunch:
                other_meal_rice_tracker["total"] = other_meal_rice_tracker.get("total", 0) + 1
                if recipe.get("carb_source") == BENTO_CARB_SOURCE:
                    other_meal_rice_tracker["rice"] = other_meal_rice_tracker.get("rice", 0) + 1
            for user_key, ctx in (("A", user_a_ctx), ("B", user_b_ctx)):
                user_target_cal = ctx["daily_calories_target"] * share * cat_share
                scaled = scale_recipe(recipe, user_target_cal)
                meals.append({"meal_date": meal_date, "meal_type": meal_type, "user": user_key, "category": category, **scaled})

    return meals, today_recipe_ids, today_carb_sources


def generate_week_plan(candidates: List[Dict], user_a_ctx: Dict, user_b_ctx: Dict, week_start_date,
                        preferred_recipes_by_day: Optional[Dict] = None,
                        favorite_recipe_ids: Optional[Set[int]] = None,
                        soup_days: Optional[Set[int]] = None) -> List[Dict]:
    """preferred_recipes_by_day: {date: {(meal_type, 'A'|'B'): candidate_dict}}——固定餐點設定可以有
    「執行天數」限制（見 FixedMealPreference），所以每天套用的固定餐點不一定相同，改由呼叫端
    （MealPlanService）依日期算好每天各自的 preferred_recipes 再傳進來，這裡逐天取當天那份。"""
    usage_counter: Dict[int, int] = {}
    cost_counter: Dict[str, int] = {}
    yesterday_ids: Set[int] = set()
    yesterday_carb_sources: Set[str] = set()
    weekly_variety: Dict[str, Set[int]] = {}
    other_meal_rice_tracker: Dict[str, int] = {"rice": 0, "total": 0}
    soup_days = soup_days or set()
    preferred_recipes_by_day = preferred_recipes_by_day or {}
    days = []
    for i in range(7):
        d = week_start_date + timedelta(days=i)
        meals, today_ids, today_carb_sources = build_day_meals(
            candidates, user_a_ctx, user_b_ctx, d, usage_counter, cost_counter, yesterday_ids,
            preferred_recipes=preferred_recipes_by_day.get(d), favorite_recipe_ids=favorite_recipe_ids,
            yesterday_carb_sources=yesterday_carb_sources, include_soup=d.weekday() in soup_days,
            weekly_variety=weekly_variety, other_meal_rice_tracker=other_meal_rice_tracker,
        )
        days.append({"date": d, "meals": meals})
        yesterday_ids = today_ids
        yesterday_carb_sources = today_carb_sources
    return days
