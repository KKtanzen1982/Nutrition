"""熱量／巨量營養素計算（純函式）"""

from datetime import date as date_cls
from typing import Optional, Dict

ACTIVITY_COEFFICIENTS = {"久坐": 1.2, "輕度": 1.375, "中度": 1.55, "高度": 1.725,
                          "低": 1.2, "中": 1.55, "高": 1.725}  # 本專案 activity_level 實際用「低/中/高」


def calculate_bmr(gender: str, weight_kg: float, height_cm: float, age: int, method: str = "harris_benedict") -> float:
    if method == "mifflin":
        base = 10 * weight_kg + 6.25 * height_cm - 5 * age
        return base + 5 if gender == "男" else base - 161
    if gender == "男":
        return 88 + 13.4 * weight_kg + 4.8 * height_cm - 5.7 * age
    return 655 + 9.6 * weight_kg + 1.8 * height_cm - 4.7 * age


def calculate_tdee(bmr: float, activity_level: str, gym_sessions: int = 0, yoga_sessions: int = 0, walking_steps_total: int = 0) -> float:
    coef = ACTIVITY_COEFFICIENTS.get(activity_level, 1.375)
    extra = gym_sessions * 75 + yoga_sessions * 50 + (walking_steps_total / 1000) * 10
    return bmr * coef + extra


def adjust_for_goal(tdee: float, goal: str) -> float:
    delta = {"減脂": -350, "增肌": 250, "維持": 0}.get(goal, 0)
    return max(tdee + delta, 1200)


def calculate_menstrual_phase(gender: str, last_menstrual_date: Optional[date_cls], cycle_length_days: Optional[int],
                               luteal_offset: int, target_date: date_cls) -> str:
    if gender != "女" or not last_menstrual_date or not cycle_length_days:
        return "無"
    days_since_start = (target_date - last_menstrual_date).days % cycle_length_days
    if days_since_start < 5:
        return "月經期"
    if days_since_start >= cycle_length_days - 3:
        return "經前期"
    if days_since_start >= luteal_offset:
        return "黃體期"
    if days_since_start >= 12:
        return "排卵期"
    return "卵泡期"


def adjust_for_menstrual_phase(calories: float, phase: str, luteal_adj: int, premenstrual_adj: int) -> float:
    if phase == "黃體期":
        return calories + luteal_adj
    if phase == "經前期":
        return calories + premenstrual_adj
    return calories


def calculate_nutrient_targets(weight_kg: float, goal: str, daily_calories: float) -> Dict[str, float]:
    protein_per_kg = {"減脂": 1.8, "增肌": 2.2, "維持": 1.6}.get(goal, 1.6)
    protein_g = weight_kg * protein_per_kg
    fat_g = daily_calories * 0.27 / 9
    carbs_g = max((daily_calories - protein_g * 4 - fat_g * 9) / 4, 0)
    return {"protein_g": round(protein_g, 1), "carbs_g": round(carbs_g, 1), "fat_g": round(fat_g, 1)}
