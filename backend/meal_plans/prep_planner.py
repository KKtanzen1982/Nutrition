"""備料規劃：把已確認的週菜單換算成「哪一天要做什麼」的每日卡片。

背景（使用者實際作息，見對話紀錄）：
- 週一到週五中午要帶便當，便當內容就是系統算好的「午餐」那組（主食/肉/菜）。
- 便當不是每天早上現做，是提前在週二/週四/週日備好接下來 1-2 天的份：
  週二 -> 備週三、週四；週四 -> 備週五；週日 -> 備下週一、下週二。
- 肉統一在週日一次做完，涵蓋「下一週」全部的午餐+晚餐用肉，平日只要微波退冰。
  也就是說週日備料的對象是「即將開始的那一週」，時間點在該週 week_start_date 的前一天。
- 每天晚上現煮晚餐的主食/菜，肉一樣微波週日做好的。
- 週六、週日中午不是便當，主食/菜現煮，肉照樣微波。
- 電鍋一次最多煮 5 杯米。煮飯要盡量集中、減少煮飯次數：能在同一次多煮一點、蓋過後面場次的
  需求，就不要拆成好幾次煮（見 allocate_rice_cooking）。

這裡只處理「飯」這個碳水來源（Recipe.carb_source == '飯'）的杯數換算，麵/其他主食不套用杯數，
直接列出菜名跟重量即可。杯數換算的公克數是概略假設，之後可依實際狀況調整 RICE_COOKED_G_PER_CUP。

輸出以「日期」為單位組成卡片（days），每張卡片包含當天的備料場次（如果當天是週日/週二/週四）
跟當天晚餐（或週末午餐）的現煮/微波提示，方便照著日曆順序一天一天看。
"""

from datetime import timedelta, date as date_cls
from typing import Dict, List, Optional

RICE_COOKED_G_PER_CUP = 350  # 假設：電鍋 1 杯生米約可煮出 350g 熟飯
MAX_RICE_CUPS = 5
WEEKDAY_LABELS = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]  # date.weekday() 0=週一


def grams_to_rice_cups(total_grams: float) -> float:
    if total_grams <= 0:
        return 0.0
    cups = total_grams / RICE_COOKED_G_PER_CUP
    return round(cups * 2) / 2  # 取到最近 0.5 杯


def split_rice_cups(total_cups: float) -> List[float]:
    """超過電鍋上限（5 杯）就分成多鍋，回傳每鍋要煮的杯數"""
    if total_cups <= 0:
        return []
    if total_cups <= MAX_RICE_CUPS:
        return [total_cups]
    batches = []
    remaining = total_cups
    while remaining > 0:
        batch = min(remaining, MAX_RICE_CUPS)
        batches.append(batch)
        remaining -= batch
    return batches


def allocate_rice_cooking(needs: List[float]) -> List[float]:
    """needs 是依時間順序排列的每個備料場次「原本各自要煮的杯數」（週日/週二/週四）。
    盡量集中煮：能在較早的場次一次煮到電鍋上限（5 杯）、蓋過後面場次的需求，
    後面場次就不用再煮飯（只需要炒菜、退冰肉即可）。回傳每個場次「這次實際要煮」的杯數，
    0 代表這場次的飯已經在更早之前備好了。"""
    n = len(needs)
    cooked = [0.0] * n
    carry = 0.0
    i = 0
    while i < n:
        owed = needs[i] - carry
        if owed <= 1e-9:
            carry = -owed
            i += 1
            continue
        carry = 0.0
        batch = owed
        j = i + 1
        while j < n and batch + needs[j] <= MAX_RICE_CUPS + 1e-9:
            batch += needs[j]
            j += 1
        cooked[i] = round(batch * 2) / 2
        i = j
    return cooked


def _aggregate_dishes(rows: List[Dict]) -> List[Dict]:
    """把同一道菜的多筆份量（不同使用者/天數）加總成一筆，附總重量與筆數"""
    agg: Dict[int, Dict] = {}
    for m in rows:
        entry = agg.setdefault(m["recipe_id"], {"recipe_id": m["recipe_id"], "recipe_name": m["recipe_name"], "total_weight_g": 0.0, "servings": 0})
        entry["total_weight_g"] += m.get("serving_weight_g") or 0
        entry["servings"] += 1
    for entry in agg.values():
        entry["total_weight_g"] = round(entry["total_weight_g"], 1)
    return sorted(agg.values(), key=lambda x: -x["total_weight_g"])


def _rice_and_other_staple(rows: List[Dict]) -> Dict:
    """飯類主食（carb_source=='飯'）仍是完整的一道菜（例如「鮭魚炊飯」），不是純白飯——
    杯數只是額外算給你抓電鍋容量用的，實際要煮的還是這些菜名本身。"""
    rice_rows = [m for m in rows if m["recipe_category"] == "主食" and m.get("carb_source") == "飯"]
    other_rows = [m for m in rows if m["recipe_category"] == "主食" and m.get("carb_source") != "飯"]
    total_g = sum(m.get("serving_weight_g") or 0 for m in rice_rows)
    return {
        "rice_dishes": _aggregate_dishes(rice_rows),
        "rice_cups_needed": grams_to_rice_cups(total_g),
        "other_staple_dishes": _aggregate_dishes(other_rows),
    }


def _bento_prep_session(prep_date: date_cls, target_dates: List[date_cls], all_rows: List[Dict]) -> Dict:
    lunch_rows = [m for m in all_rows if m["meal_date"] in target_dates and m["meal_type"] == "lunch"]
    veg_rows = [m for m in lunch_rows if m["recipe_category"] in ("菜", "湯")]
    staple_info = _rice_and_other_staple(lunch_rows)
    return {
        "prep_date": prep_date,
        "for_dates": target_dates,
        **staple_info,
        "veg_dishes": _aggregate_dishes(veg_rows),
    }


def _steps_for_bento_session(session: Dict) -> List[str]:
    steps = []
    if session["rice_cups_to_cook"] > 0:
        batches = "、".join(f"{c:g} 杯" for c in split_rice_cups(session["rice_cups_to_cook"]))
        rice_names = "、".join(d["recipe_name"] for d in session["rice_dishes"]) or "飯類主食"
        steps.append(f"電鍋煮飯（{rice_names}）：共 {session['rice_cups_to_cook']:g} 杯米（{batches}），順便多煮一點給後面幾天用")
    elif session["rice_dishes"]:
        rice_names = "、".join(d["recipe_name"] for d in session["rice_dishes"])
        steps.append(f"飯類主食（{rice_names}）已經在更早之前煮好了，不用再煮，直接分裝")
    for d in session["other_staple_dishes"]:
        steps.append(f"準備主食：{d['recipe_name']}（約 {d['total_weight_g']:g}g）")
    for d in session["veg_dishes"]:
        steps.append(f"炒／煮菜：{d['recipe_name']}（約 {d['total_weight_g']:g}g）")
    steps.append("肉從冰箱取出退冰、分裝進便當盒即可，不用再煮")
    steps.append("全部放涼後分裝冷藏，標註要吃的日期")
    return steps


def _steps_for_sunday_batch(meat_items: List[Dict]) -> List[str]:
    steps = ["處理所有肉類食材（洗、切、醃）"]
    for d in meat_items:
        steps.append(f"烹煮：{d['recipe_name']}（約 {d['total_weight_g']:g}g，供 {d['servings']} 份）")
    steps.append("全部放涼，依食用日期分裝冷藏／冷凍，平日晚餐、便當直接微波取用")
    return steps


def _fresh_meal(all_rows: List[Dict], d: date_cls, meal_type: str) -> Dict:
    rows = [m for m in all_rows if m["meal_date"] == d and m["meal_type"] == meal_type]
    staple = _aggregate_dishes([m for m in rows if m["recipe_category"] == "主食"])
    veg = _aggregate_dishes([m for m in rows if m["recipe_category"] in ("菜", "湯")])
    meat = _aggregate_dishes([m for m in rows if m["recipe_category"] == "肉"])
    return {"cook_fresh": staple + veg, "reheat_from_batch": meat}


def build_prep_plan(plan_days: List[Dict], week_start_date: date_cls) -> Dict:
    """plan_days: MealPlanService.get_plan() 回傳的 days 結構（含 recipe_category/carb_source）。
    回傳以日期為單位的卡片列表（days），每張卡片是週日曆上實際的一天。"""
    all_rows: List[Dict] = []
    for day in plan_days:
        for m in day["meals"]:
            all_rows.append({**m, "meal_date": date_cls.fromisoformat(day["date"]) if isinstance(day["date"], str) else day["date"]})

    prep_sunday = week_start_date - timedelta(days=1)
    mon, tue, wed, thu, fri, sat, sun = (week_start_date + timedelta(days=i) for i in range(7))

    meat_rows = [m for m in all_rows if m["meal_type"] in ("lunch", "dinner") and m["recipe_category"] == "肉"]
    meat_batch = _aggregate_dishes(meat_rows)

    sunday_session = _bento_prep_session(prep_sunday, [mon, tue], all_rows)
    tuesday_session = _bento_prep_session(tue, [wed, thu], all_rows)
    thursday_session = _bento_prep_session(thu, [fri], all_rows)
    sessions = [sunday_session, tuesday_session, thursday_session]

    # 煮飯集中煮：把三個場次原本各自要煮的杯數，盡量往前合併成更少次、每次煮到接近上限
    cooked_cups = allocate_rice_cooking([s["rice_cups_needed"] for s in sessions])
    for session, cups in zip(sessions, cooked_cups):
        session["rice_cups_to_cook"] = cups

    sunday_session["meat_batch"] = meat_batch
    sunday_session["steps"] = _steps_for_sunday_batch(meat_batch) + ["—— 以下是同時要備的便當 ——"] + _steps_for_bento_session(sunday_session)
    tuesday_session["steps"] = _steps_for_bento_session(tuesday_session)
    thursday_session["steps"] = _steps_for_bento_session(thursday_session)

    session_by_date = {s["prep_date"]: s for s in sessions}

    def serialize_session(s: Dict) -> Dict:
        return {
            "prep_date": s["prep_date"].isoformat(),
            "for_dates": [d.isoformat() for d in s["for_dates"]],
            "rice_dishes": s["rice_dishes"],
            "rice_cups_to_cook": s["rice_cups_to_cook"],
            "rice_cook_batches": split_rice_cups(s["rice_cups_to_cook"]),
            "other_staple_dishes": s["other_staple_dishes"],
            "veg_dishes": s["veg_dishes"],
            "meat_batch": s.get("meat_batch"),
            "steps": s["steps"],
        }

    all_dates = [prep_sunday] + [week_start_date + timedelta(days=i) for i in range(7)]
    days = []
    for d in all_dates:
        card: Dict = {"date": d.isoformat(), "weekday_label": WEEKDAY_LABELS[d.weekday()]}
        session = session_by_date.get(d)
        card["prep_session"] = serialize_session(session) if session else None
        if d >= week_start_date:
            card["dinner"] = _fresh_meal(all_rows, d, "dinner")
            card["lunch_fresh"] = _fresh_meal(all_rows, d, "lunch") if d.weekday() >= 5 else None
            card["lunch_is_bento"] = d.weekday() < 5
        else:
            card["dinner"] = None
            card["lunch_fresh"] = None
            card["lunch_is_bento"] = False
        days.append(card)

    return {
        "week_start_date": week_start_date.isoformat(),
        "rice_cup_assumption_g": RICE_COOKED_G_PER_CUP,
        "days": days,
    }
