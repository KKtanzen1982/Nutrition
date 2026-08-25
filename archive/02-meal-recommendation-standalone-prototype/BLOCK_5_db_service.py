"""
BLOCK_5: 真正的資料庫存取層

取代 BLOCK_5_meal_plan_api.py / BLOCK_5_adjustment_api.py 裡原本寫死假資料的所有 `# TODO`。
只做「查詢／持久化」，計算邏輯（熱量、營養素、微調）仍然重用
BLOCK_5_recommendation_service.py / BLOCK_5_adjustment_service.py 裡既有的純函式。

注意：這裡刻意不呼叫 BLOCK_5_adjustment_service.MealPlanManager.build_meal_plan_from_claude_response()
來寫入資料庫——那個函式讀的是 meal.get("user_id")，但 Claude 回應（見 BLOCK_5_prompts.py 的
輸出格式）實際上只有 meal["user"] = "A"/"B"，兩邊對不上，永遠會存成 user_id=None。
save_meal_plan() 直接從 claude_response 自己解析、把 "A"/"B" 對應回真正的 user_id。
"""

import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from BLOCK_5_models import (
    User, DietaryPreference, WeightRecord, ExerciseSession, DailySteps,
    Recipe, RecipeNutrition, WeeklyMealPlan, DailyMealDetail, MealAdjustment,
)

logger = logging.getLogger(__name__)


class NotFoundError(Exception):
    """查無資料（呼叫端轉成 HTTP 404）"""
    pass


def _parse_date(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return datetime.strptime(value, "%Y-%m-%d").date()
    raise ValueError(f"無法解析日期：{value!r}")


# ==================== 用戶 / 運動資料查詢（給推薦引擎打包用） ====================

def get_user_profile_for_claude(db: Session, user_id: int) -> Dict[str, Any]:
    """取得用戶完整資料（含最新體重、飲食偏好），格式化成推薦引擎需要的 dict。"""
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise NotFoundError(f"用戶 {user_id} 不存在")

    latest_weight = (
        db.query(WeightRecord)
        .filter(WeightRecord.user_id == user_id)
        .order_by(WeightRecord.date.desc())
        .first()
    )
    pref = db.query(DietaryPreference).filter(DietaryPreference.user_id == user_id).first()

    return {
        "id": user.id,
        "name": user.name,
        "gender": user.gender,
        "age": user.age,
        "height_cm": user.height_cm,
        "weight_kg": latest_weight.weight_kg if latest_weight else 60.0,
        "primary_goal": user.primary_goal,
        "activity_level": user.activity_level,
        "allergies": (pref.allergies if pref and pref.allergies else "無"),
        "restrictions": (pref.restrictions if pref and pref.restrictions else "無"),
        "last_menstrual_date": user.last_menstrual_date,
        "menstrual_cycle_length_days": user.menstrual_cycle_length_days or 28,
        "menstrual_luteal_phase_start_offset_days": user.menstrual_luteal_phase_start_offset_days or 14,
        "menstrual_luteal_phase_adjustment_calories": user.menstrual_luteal_phase_adjustment_calories or 150,
        "menstrual_premenstrual_adjustment_calories": user.menstrual_premenstrual_adjustment_calories or 120,
    }


def get_week_exercise_summary(db: Session, user_id: int, week_start_date: date) -> Dict[str, int]:
    """
    取得「這週菜單」開始前一週（即目前實際已發生、可拿來估算 TDEE 的那週）的運動彙總。
    週一開始的計畫，用的是 week_start_date 前 7 天（週日往前算）的實際運動紀錄。
    """
    window_end = week_start_date - timedelta(days=1)
    window_start = window_end - timedelta(days=6)

    sessions = (
        db.query(ExerciseSession)
        .filter(ExerciseSession.user_id == user_id)
        .filter(ExerciseSession.date >= window_start, ExerciseSession.date <= window_end)
        .all()
    )
    gym_sessions = sum(1 for s in sessions if s.exercise_type == "健身房")
    yoga_sessions = sum(1 for s in sessions if s.exercise_type == "瑜珈")

    steps_total = (
        db.query(func.coalesce(func.sum(DailySteps.steps), 0))
        .filter(DailySteps.user_id == user_id)
        .filter(DailySteps.date >= window_start, DailySteps.date <= window_end)
        .scalar()
    )

    return {
        "gym_sessions": gym_sessions,
        "yoga_sessions": yoga_sessions,
        "walking_steps_total": int(steps_total or 0),
    }


# ==================== 食譜查詢 ====================

def _recipe_to_claude_dict(recipe: Recipe) -> Dict[str, Any]:
    nutrition = recipe.nutrition
    return {
        "id": recipe.id,
        "name": recipe.recipe_name,
        "category": recipe.category,
        "base_weight_g": recipe.base_weight_g,
        "cost_level": recipe.cost_level,
        "calories": nutrition.total_calories_kcal if nutrition else 0,
        "protein_g": nutrition.protein_g if nutrition else 0,
        "carbs_g": nutrition.carbs_g if nutrition else 0,
        "fat_g": nutrition.fat_g if nutrition else 0,
        "fiber_g": nutrition.fiber_g if nutrition else None,
        "ingredients": [x.strip() for x in (recipe.ingredient_names_csv or "").split(",") if x.strip()],
        "is_vegetarian": bool(recipe.is_vegetarian),
        "contains_allergens": [x.strip() for x in (recipe.allergen_tags or "").split(",") if x.strip()],
    }


def get_active_recipes(db: Session) -> List[Dict[str, Any]]:
    """取得所有上架中的食譜（推薦引擎的候選食譜資料庫）。"""
    recipes = db.query(Recipe).filter(Recipe.is_active.is_(True)).all()
    return [_recipe_to_claude_dict(r) for r in recipes]


def get_recipe_for_claude(db: Session, recipe_id: int) -> Dict[str, Any]:
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id, Recipe.is_active.is_(True)).first()
    if recipe is None:
        raise NotFoundError(f"食譜 {recipe_id} 不存在或已下架")
    return _recipe_to_claude_dict(recipe)


def _recipe_name_map(db: Session, recipe_ids: List[int]) -> Dict[int, str]:
    if not recipe_ids:
        return {}
    rows = db.query(Recipe.id, Recipe.recipe_name).filter(Recipe.id.in_(set(recipe_ids))).all()
    return {rid: name for rid, name in rows}


def _user_name(db: Session, user_id: int) -> str:
    user = db.query(User).filter(User.id == user_id).first()
    return user.name if user else f"User {user_id}"


# ==================== 週計畫：寫入 ====================

def save_meal_plan(
    db: Session,
    claude_response: Dict[str, Any],
    week_start_date: date,
    user_a_id: int,
    user_b_id: int,
    calorie_calculation_method: str,
    user_a_daily_calories: float,
    user_b_daily_calories: float,
    user_a_menstrual_phase: str,
    user_b_menstrual_phase: str,
) -> int:
    """把 Claude（或 Mock）的推薦回應寫入 weekly_meal_plan + daily_meal_detail，回傳 plan_id。"""
    recommendation = claude_response.get("recommendation", {})

    plan = WeeklyMealPlan(
        plan_date=week_start_date,
        user_id_a=user_a_id,
        user_id_b=user_b_id,
        calorie_calculation_method=calorie_calculation_method,
        user_a_daily_calories_target=int(user_a_daily_calories),
        user_b_daily_calories_target=int(user_b_daily_calories),
        user_a_menstrual_phase=user_a_menstrual_phase,
        user_b_menstrual_phase=user_b_menstrual_phase,
        plan_status="草稿",
        claude_generated=True,
        recommendation_notes=recommendation.get("analysis_notes", ""),
    )
    db.add(plan)
    db.flush()  # 取得 plan.id

    user_label_to_id = {"A": user_a_id, "B": user_b_id}
    meal_rows = 0

    for day_data in recommendation.get("days", []):
        meal_date = _parse_date(day_data.get("date"))
        if meal_date is None:
            logger.warning("推薦結果有一天沒有 date 欄位，略過：%s", day_data.get("day"))
            continue

        for meal in day_data.get("meals", []):
            user_id = user_label_to_id.get(meal.get("user"))
            if user_id is None:
                logger.warning("推薦結果的餐次沒有合法的 user 欄位（%r），略過", meal.get("user"))
                continue

            db.add(DailyMealDetail(
                meal_plan_id=plan.id,
                meal_date=meal_date,
                meal_type=meal.get("meal_type"),
                recipe_id=meal.get("recipe_id"),
                assigned_user_id=user_id,
                serving_weight_g=meal.get("serving_weight_g"),
                total_calories=meal.get("calories"),
                protein_g=meal.get("protein_g"),
                carbs_g=meal.get("carbs_g"),
                fat_g=meal.get("fat_g"),
                fiber_g=meal.get("fiber_g"),
            ))
            meal_rows += 1

    db.commit()
    db.refresh(plan)
    logger.info("週計畫已存入資料庫：plan_id=%s，共 %d 個餐次", plan.id, meal_rows)
    return plan.id


# ==================== 週計畫：讀取 ====================

def get_meal_plan_full(db: Session, plan_id: int) -> Optional[Dict[str, Any]]:
    """組出可以直接餵給 MealPlanResponse(**result) 的完整字典。查無資料回傳 None。"""
    plan = db.query(WeeklyMealPlan).filter(WeeklyMealPlan.id == plan_id).first()
    if plan is None:
        return None

    meals = (
        db.query(DailyMealDetail)
        .filter(DailyMealDetail.meal_plan_id == plan_id)
        .order_by(DailyMealDetail.meal_date)
        .all()
    )

    recipe_names = _recipe_name_map(db, [m.recipe_id for m in meals])
    user_names = {
        plan.user_id_a: _user_name(db, plan.user_id_a),
        plan.user_id_b: _user_name(db, plan.user_id_b),
    }

    by_date: Dict[date, List[DailyMealDetail]] = {}
    for m in meals:
        by_date.setdefault(m.meal_date, []).append(m)

    totals = {
        plan.user_id_a: {"calories": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0, "fiber_g": 0.0},
        plan.user_id_b: {"calories": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0, "fiber_g": 0.0},
    }

    daily_details = []
    for meal_date in sorted(by_date.keys()):
        day_meals = by_date[meal_date]
        day_totals = {
            plan.user_id_a: {"calories": 0.0, "protein_g": 0.0},
            plan.user_id_b: {"calories": 0.0, "protein_g": 0.0},
        }
        meal_dicts = []
        for m in day_meals:
            meal_dicts.append({
                "meal_type": m.meal_type,
                "user_id": m.assigned_user_id,
                "user_name": user_names.get(m.assigned_user_id, ""),
                "recipe_id": m.recipe_id,
                "recipe_name": recipe_names.get(m.recipe_id, "未知食譜"),
                "serving_weight_g": int(m.serving_weight_g or 0),
                "calories": m.total_calories or 0,
                "protein_g": m.protein_g or 0,
                "carbs_g": m.carbs_g or 0,
                "fat_g": m.fat_g or 0,
                "fiber_g": m.fiber_g,
            })
            if m.assigned_user_id in day_totals:
                day_totals[m.assigned_user_id]["calories"] += m.total_calories or 0
                day_totals[m.assigned_user_id]["protein_g"] += m.protein_g or 0
            if m.assigned_user_id in totals:
                totals[m.assigned_user_id]["calories"] += m.total_calories or 0
                totals[m.assigned_user_id]["protein_g"] += m.protein_g or 0
                totals[m.assigned_user_id]["carbs_g"] += m.carbs_g or 0
                totals[m.assigned_user_id]["fat_g"] += m.fat_g or 0
                totals[m.assigned_user_id]["fiber_g"] += m.fiber_g or 0

        daily_details.append({
            "meal_date": meal_date,
            "day_name": meal_date.strftime("%A"),
            "meals": meal_dicts,
            "day_total_calories_a": day_totals[plan.user_id_a]["calories"],
            "day_total_calories_b": day_totals[plan.user_id_b]["calories"],
            "day_total_protein_a": day_totals[plan.user_id_a]["protein_g"],
            "day_total_protein_b": day_totals[plan.user_id_b]["protein_g"],
        })

    days_count = max(len(by_date), 1)

    def _summary(user_id: int) -> Dict[str, Any]:
        t = totals[user_id]
        return {
            "total_calories": t["calories"],
            "avg_calories": t["calories"] / days_count,
            "total_protein_g": t["protein_g"],
            "avg_protein_g": t["protein_g"] / days_count,
            "total_carbs_g": t["carbs_g"],
            "avg_carbs_g": t["carbs_g"] / days_count,
            "total_fat_g": t["fat_g"],
            "avg_fat_g": t["fat_g"] / days_count,
            "total_fiber_g": t["fiber_g"],
        }

    status_map = {"草稿": "draft", "待微調": "pending_adjustment", "已確認": "confirmed"}

    return {
        "success": True,
        "plan_id": plan.id,
        "week_start_date": plan.plan_date,
        "status": status_map.get(plan.plan_status, plan.plan_status),
        "user_a_id": plan.user_id_a,
        "user_b_id": plan.user_id_b,
        "user_a_daily_calories_target": plan.user_a_daily_calories_target or 0,
        "user_b_daily_calories_target": plan.user_b_daily_calories_target or 0,
        "user_a_menstrual_phase": plan.user_a_menstrual_phase or "無",
        "user_b_menstrual_phase": plan.user_b_menstrual_phase or "無",
        "daily_details": daily_details,
        "nutrition_summary": {
            "user_a": _summary(plan.user_id_a),
            "user_b": _summary(plan.user_id_b),
        },
        "recommendation_notes": plan.recommendation_notes,
        "created_at": plan.created_at,
    }


def get_plan_header(db: Session, plan_id: int) -> Optional[Dict[str, Any]]:
    """輕量版：只取週計畫本身的欄位（不含餐次），給重推整天的背景任務組 prompt 用。"""
    plan = db.query(WeeklyMealPlan).filter(WeeklyMealPlan.id == plan_id).first()
    if plan is None:
        return None
    return {
        "id": plan.id,
        "plan_date": plan.plan_date,
        "user_id_a": plan.user_id_a,
        "user_id_b": plan.user_id_b,
        "user_a_daily_calories_target": plan.user_a_daily_calories_target,
        "user_b_daily_calories_target": plan.user_b_daily_calories_target,
        "user_a_menstrual_phase": plan.user_a_menstrual_phase,
        "user_b_menstrual_phase": plan.user_b_menstrual_phase,
        "plan_status": plan.plan_status,
    }


def get_meal_plan_meals(db: Session, plan_id: int) -> List[Dict[str, Any]]:
    """
    給微調邏輯（BLOCK_5_adjustment_service.MealAdjustmentService）用的 current_meals，
    dict 格式對齊該模組預期的欄位。
    """
    meals = db.query(DailyMealDetail).filter(DailyMealDetail.meal_plan_id == plan_id).all()
    recipe_names = _recipe_name_map(db, [m.recipe_id for m in meals])

    return [
        {
            "meal_date": m.meal_date,
            "meal_type": m.meal_type,
            "user_id": m.assigned_user_id,
            "recipe_id": m.recipe_id,
            "recipe_name": recipe_names.get(m.recipe_id, ""),
            "serving_weight_g": m.serving_weight_g,
            "calories": m.total_calories,
            "protein_g": m.protein_g,
            "carbs_g": m.carbs_g,
            "fat_g": m.fat_g,
            "fiber_g": m.fiber_g,
        }
        for m in meals
    ]


def get_single_meal(
    db: Session, plan_id: int, meal_date: date, meal_type: str, user_id: int
) -> Optional[DailyMealDetail]:
    return (
        db.query(DailyMealDetail)
        .filter(DailyMealDetail.meal_plan_id == plan_id)
        .filter(DailyMealDetail.meal_date == meal_date)
        .filter(DailyMealDetail.meal_type == meal_type)
        .filter(DailyMealDetail.assigned_user_id == user_id)
        .first()
    )


# ==================== 微調：持久化 ====================

def apply_single_meal_update(
    db: Session,
    plan_id: int,
    updated_meal: Dict[str, Any],
    adjustment_record: Dict[str, Any],
) -> DailyMealDetail:
    """
    把 MealAdjustmentService.replace_meal / search_and_replace / adjust_serving_weight
    算出來的單一餐次結果寫回資料庫，並新增一筆 meal_adjustments 記錄。
    """
    row = get_single_meal(db, plan_id, updated_meal["meal_date"], updated_meal["meal_type"], updated_meal["user_id"])
    if row is None:
        raise NotFoundError(
            f"找不到要更新的餐次：plan_id={plan_id}, "
            f"date={updated_meal['meal_date']}, meal_type={updated_meal['meal_type']}, "
            f"user_id={updated_meal['user_id']}"
        )

    row.recipe_id = updated_meal.get("recipe_id", row.recipe_id)
    row.serving_weight_g = updated_meal.get("serving_weight_g", row.serving_weight_g)
    row.total_calories = updated_meal.get("calories", row.total_calories)
    row.protein_g = updated_meal.get("protein_g", row.protein_g)
    row.carbs_g = updated_meal.get("carbs_g", row.carbs_g)
    row.fat_g = updated_meal.get("fat_g", row.fat_g)
    row.fiber_g = updated_meal.get("fiber_g", row.fiber_g)

    db.add(MealAdjustment(
        plan_id=plan_id,
        adjustment_type=adjustment_record.get("adjustment_type", "替換"),
        meal_date=updated_meal["meal_date"],
        meal_type=updated_meal["meal_type"],
        user_id=updated_meal["user_id"],
        original_recipe_id=adjustment_record.get("original_recipe_id"),
        adjusted_recipe_id=updated_meal.get("recipe_id"),
        reason=adjustment_record.get("reason") or adjustment_record.get("search_query"),
        adjusted_by="user",
    ))
    db.commit()
    db.refresh(row)
    return row


def apply_day_regeneration(
    db: Session,
    plan_id: int,
    meal_date: date,
    regenerated_meals: List[Dict[str, Any]],
    fixed_meal_ids: Set[Tuple[str, int]],
) -> None:
    """
    刪掉當天「非固定」的餐次，換成 Claude 重新推薦的結果，並記錄微調。
    fixed_meal_ids 是 {(meal_type, user_id), ...}，那些餐次原封不動保留。
    """
    rows = (
        db.query(DailyMealDetail)
        .filter(DailyMealDetail.meal_plan_id == plan_id)
        .filter(DailyMealDetail.meal_date == meal_date)
        .all()
    )
    for row in rows:
        if (row.meal_type, row.assigned_user_id) not in fixed_meal_ids:
            db.delete(row)

    for meal in regenerated_meals:
        db.add(DailyMealDetail(
            meal_plan_id=plan_id,
            meal_date=meal_date,
            meal_type=meal["meal_type"],
            recipe_id=meal["recipe_id"],
            assigned_user_id=meal["user_id"],
            serving_weight_g=meal.get("serving_weight_g"),
            total_calories=meal.get("calories"),
            protein_g=meal.get("protein_g"),
            carbs_g=meal.get("carbs_g"),
            fat_g=meal.get("fat_g"),
            fiber_g=meal.get("fiber_g"),
        ))
        db.add(MealAdjustment(
            plan_id=plan_id,
            adjustment_type="重推整天",
            meal_date=meal_date,
            meal_type=meal["meal_type"],
            user_id=meal["user_id"],
            original_recipe_id=None,
            adjusted_recipe_id=meal.get("recipe_id"),
            reason=f"用戶重推 {meal_date}",
            adjusted_by="user",
        ))

    db.commit()


def confirm_plan(db: Session, plan_id: int) -> bool:
    plan = db.query(WeeklyMealPlan).filter(WeeklyMealPlan.id == plan_id).first()
    if plan is None:
        return False
    plan.plan_status = "已確認"
    db.commit()
    return True
