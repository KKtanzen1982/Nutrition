from sqlalchemy.orm import Session
from datetime import timedelta
from typing import List, Optional, Dict

from users.models import User
from users.services import dietary_preference_service
from fitness.models import WeightRecord, ExerciseSession, DailySteps
from recipes.models import Recipe
from meal_plans.models import WeeklyMealPlan, DailyMealDetail, MealAdjustment
from meal_plans import nutrition_calc
from meal_plans.selection_algorithm import generate_week_plan, build_day_meals, scale_recipe


def _parse_csv(text: Optional[str]) -> List[str]:
    return [p.strip() for p in (text or "").split(",") if p.strip()]


class NutritionTargetService:
    """BMR/TDEE/巨量營養素目標"""

    def get_user_context(self, db: Session, user_id: int, target_date) -> Dict:
        user = db.get(User, user_id)
        if not user:
            raise ValueError(f"使用者 {user_id} 不存在")
        latest_weight = (
            db.query(WeightRecord).filter(WeightRecord.user_id == user_id)
            .order_by(WeightRecord.date.desc()).first()
        )
        weight_kg = latest_weight.weight_kg if latest_weight else 60.0

        window_start = target_date - timedelta(days=7)
        window_end = target_date - timedelta(days=1)
        sessions = db.query(ExerciseSession).filter(
            ExerciseSession.user_id == user_id, ExerciseSession.date >= window_start, ExerciseSession.date <= window_end
        ).all()
        gym_sessions = sum(1 for s in sessions if s.exercise_type == "健身房")
        yoga_sessions = sum(1 for s in sessions if s.exercise_type in ("瑜珈", "拉伸"))
        steps_rows = db.query(DailySteps).filter(
            DailySteps.user_id == user_id, DailySteps.date >= window_start, DailySteps.date <= window_end
        ).all()
        walking_steps_total = sum(s.step_count or 0 for s in steps_rows)

        bmr = nutrition_calc.calculate_bmr(user.gender, weight_kg, user.height_cm, user.age)
        tdee = nutrition_calc.calculate_tdee(bmr, user.activity_level, gym_sessions, yoga_sessions, walking_steps_total)
        goal_adjusted = nutrition_calc.adjust_for_goal(tdee, user.primary_goal)
        phase = nutrition_calc.calculate_menstrual_phase(
            user.gender, user.last_menstrual_date, user.menstrual_cycle_length_days,
            user.menstrual_luteal_phase_start_offset_days or 14, target_date,
        )
        final_calories = nutrition_calc.adjust_for_menstrual_phase(
            goal_adjusted, phase,
            user.menstrual_luteal_phase_adjustment_calories or 150,
            user.menstrual_premenstrual_adjustment_calories or 120,
        )
        macros = nutrition_calc.calculate_nutrient_targets(weight_kg, user.primary_goal, final_calories)

        return {
            "user_id": user_id, "bmr": round(bmr, 1), "tdee": round(tdee, 1),
            "goal_adjusted_calories": round(goal_adjusted, 1), "menstrual_phase": phase,
            "menstrual_adjusted_calories": round(final_calories, 1),
            "daily_calories_target": round(final_calories, 1),
            "daily_protein_g": macros["protein_g"],
            **macros,
        }


nutrition_target_service = NutritionTargetService()


class MealPlanService:
    """規則式週菜單推薦（取代 Claude API 呼叫，見 selection_algorithm.py）"""

    def _candidate_recipes(self, db: Session, user_id_a: int, user_id_b: int) -> List[Dict]:
        pref_a = dietary_preference_service.get(db, user_id_a)
        pref_b = dietary_preference_service.get(db, user_id_b)
        allergens = set(_parse_csv(pref_a["allergies"])) | set(_parse_csv(pref_b["allergies"]))
        needs_veg = "素食" in _parse_csv(pref_a["restrictions"]) or "素食" in _parse_csv(pref_b["restrictions"])

        recipes = db.query(Recipe).filter(Recipe.is_active == True).all()
        candidates = []
        for r in recipes:
            tags = set(_parse_csv(r.allergen_tags))
            if tags & allergens:
                continue
            if needs_veg and not r.is_vegetarian:
                continue
            candidates.append({
                "id": r.id, "recipe_name": r.recipe_name, "category": r.category,
                "base_weight_g": r.base_weight_g, "cost_level": r.cost_level,
                "calories": r.nutrition.total_calories_kcal if r.nutrition else 0,
                "protein_g": r.nutrition.protein_g if r.nutrition else 0,
                "carbs_g": r.nutrition.carbs_g if r.nutrition else 0,
                "fat_g": r.nutrition.fat_g if r.nutrition else 0,
                "fiber_g": r.nutrition.fiber_g if r.nutrition else 0,
            })
        return candidates

    def _write_meal(self, db: Session, plan_id: int, user_id_by_key: Dict[str, int], meal: Dict) -> DailyMealDetail:
        row = DailyMealDetail(
            meal_plan_id=plan_id, meal_date=meal["meal_date"], meal_type=meal["meal_type"],
            recipe_id=meal["recipe_id"], assigned_user_id=user_id_by_key[meal["user"]],
            serving_weight_g=meal["serving_weight_g"], calories=meal["calories"],
            protein_g=meal["protein_g"], carbs_g=meal["carbs_g"], fat_g=meal["fat_g"], fiber_g=meal["fiber_g"],
        )
        db.add(row)
        return row

    def generate_plan(self, db: Session, user_id_a: int, user_id_b: int, week_start_date) -> Dict:
        ctx_a = nutrition_target_service.get_user_context(db, user_id_a, week_start_date)
        ctx_b = nutrition_target_service.get_user_context(db, user_id_b, week_start_date)
        candidates = self._candidate_recipes(db, user_id_a, user_id_b)
        if not candidates:
            raise ValueError("目前沒有符合過敏/飲食限制的候選食譜，無法生成推薦")

        days = generate_week_plan(candidates, ctx_a, ctx_b, week_start_date)

        plan = WeeklyMealPlan(
            plan_date=week_start_date, user_id_a=user_id_a, user_id_b=user_id_b,
            user_a_daily_calories_target=round(ctx_a["daily_calories_target"]),
            user_b_daily_calories_target=round(ctx_b["daily_calories_target"]),
            user_a_menstrual_phase=ctx_a["menstrual_phase"], user_b_menstrual_phase=ctx_b["menstrual_phase"],
            plan_status="待微調", claude_generated=True,
        )
        db.add(plan)
        db.flush()

        user_id_by_key = {"A": user_id_a, "B": user_id_b}
        for day in days:
            for meal in day["meals"]:
                self._write_meal(db, plan.id, user_id_by_key, meal)
        db.commit()
        return self.get_plan(db, plan.id)

    def get_plan(self, db: Session, plan_id: int) -> Optional[Dict]:
        plan = db.get(WeeklyMealPlan, plan_id)
        if not plan:
            return None
        meals = db.query(DailyMealDetail).filter(DailyMealDetail.meal_plan_id == plan_id).all()
        days: Dict = {}
        for m in meals:
            recipe = db.get(Recipe, m.recipe_id)
            day_key = m.meal_date.isoformat()
            days.setdefault(day_key, []).append({
                "id": m.id, "meal_type": m.meal_type, "assigned_user_id": m.assigned_user_id,
                "recipe_id": m.recipe_id, "recipe_name": recipe.recipe_name if recipe else None,
                "serving_weight_g": m.serving_weight_g, "calories": m.calories,
                "protein_g": m.protein_g, "carbs_g": m.carbs_g, "fat_g": m.fat_g, "fiber_g": m.fiber_g,
            })
        return {
            "id": plan.id, "plan_date": plan.plan_date, "user_id_a": plan.user_id_a, "user_id_b": plan.user_id_b,
            "user_a_daily_calories_target": plan.user_a_daily_calories_target,
            "user_b_daily_calories_target": plan.user_b_daily_calories_target,
            "user_a_menstrual_phase": plan.user_a_menstrual_phase, "user_b_menstrual_phase": plan.user_b_menstrual_phase,
            "plan_status": plan.plan_status, "days": [{"date": k, "meals": v} for k, v in sorted(days.items())],
        }

    def _log_adjustment(self, db: Session, plan_id: int, adjustment_type: str, meal_date, meal_type,
                         user_id: Optional[int], original_recipe_id: Optional[int], adjusted_recipe_id: Optional[int],
                         reason: Optional[str] = None):
        db.add(MealAdjustment(
            plan_id=plan_id, adjustment_type=adjustment_type, meal_date=meal_date, meal_type=meal_type,
            user_id=user_id, original_recipe_id=original_recipe_id, adjusted_recipe_id=adjusted_recipe_id,
            reason=reason, adjusted_by="user",
        ))

    def replace_meal(self, db: Session, plan_id: int, meal_id: int, new_recipe_id: int, adjustment_type: str = "替換",
                      search_query: Optional[str] = None) -> Dict:
        meal = db.get(DailyMealDetail, meal_id)
        if not meal or meal.meal_plan_id != plan_id:
            raise ValueError("找不到這筆餐點")
        new_recipe = db.get(Recipe, new_recipe_id)
        if not new_recipe:
            raise ValueError(f"食譜 {new_recipe_id} 不存在")
        original_recipe_id = meal.recipe_id
        scaled = scale_recipe({
            "id": new_recipe.id, "recipe_name": new_recipe.recipe_name, "base_weight_g": new_recipe.base_weight_g,
            "calories": new_recipe.nutrition.total_calories_kcal if new_recipe.nutrition else 0,
            "protein_g": new_recipe.nutrition.protein_g if new_recipe.nutrition else 0,
            "carbs_g": new_recipe.nutrition.carbs_g if new_recipe.nutrition else 0,
            "fat_g": new_recipe.nutrition.fat_g if new_recipe.nutrition else 0,
            "fiber_g": new_recipe.nutrition.fiber_g if new_recipe.nutrition else 0,
        }, new_recipe.nutrition.total_calories_kcal if new_recipe.nutrition else new_recipe.base_weight_g)
        meal.recipe_id = new_recipe.id
        meal.serving_weight_g = new_recipe.base_weight_g
        meal.calories = scaled["calories"]
        meal.protein_g = scaled["protein_g"]
        meal.carbs_g = scaled["carbs_g"]
        meal.fat_g = scaled["fat_g"]
        meal.fiber_g = scaled["fiber_g"]
        self._log_adjustment(db, plan_id, adjustment_type, meal.meal_date, meal.meal_type, meal.assigned_user_id,
                              original_recipe_id, new_recipe.id, reason=search_query)
        db.commit()
        return self.get_plan(db, plan_id)

    def adjust_serving_weight(self, db: Session, plan_id: int, meal_id: int, new_serving_weight_g: float) -> Dict:
        meal = db.get(DailyMealDetail, meal_id)
        if not meal or meal.meal_plan_id != plan_id:
            raise ValueError("找不到這筆餐點")
        recipe = db.get(Recipe, meal.recipe_id)
        scaled = scale_recipe({
            "id": recipe.id, "recipe_name": recipe.recipe_name, "base_weight_g": recipe.base_weight_g,
            "calories": recipe.nutrition.total_calories_kcal if recipe.nutrition else 0,
            "protein_g": recipe.nutrition.protein_g if recipe.nutrition else 0,
            "carbs_g": recipe.nutrition.carbs_g if recipe.nutrition else 0,
            "fat_g": recipe.nutrition.fat_g if recipe.nutrition else 0,
            "fiber_g": recipe.nutrition.fiber_g if recipe.nutrition else 0,
        }, new_serving_weight_g / recipe.base_weight_g * (recipe.nutrition.total_calories_kcal if recipe.nutrition else 1))
        meal.serving_weight_g = new_serving_weight_g
        meal.calories = scaled["calories"]
        meal.protein_g = scaled["protein_g"]
        meal.carbs_g = scaled["carbs_g"]
        meal.fat_g = scaled["fat_g"]
        meal.fiber_g = scaled["fiber_g"]
        self._log_adjustment(db, plan_id, "調整分量", meal.meal_date, meal.meal_type, meal.assigned_user_id,
                              recipe.id, recipe.id)
        db.commit()
        return self.get_plan(db, plan_id)

    def regenerate_day(self, db: Session, plan_id: int, meal_date) -> Dict:
        plan = db.get(WeeklyMealPlan, plan_id)
        if not plan:
            raise ValueError("計畫不存在")
        ctx_a = nutrition_target_service.get_user_context(db, plan.user_id_a, meal_date)
        ctx_b = nutrition_target_service.get_user_context(db, plan.user_id_b, meal_date)
        candidates = self._candidate_recipes(db, plan.user_id_a, plan.user_id_b)

        all_meals = db.query(DailyMealDetail).filter(DailyMealDetail.meal_plan_id == plan_id).all()
        usage_counter: Dict[int, int] = {}
        cost_counter: Dict[str, int] = {}
        recipe_cost = {r["id"]: r["cost_level"] for r in candidates}
        for m in all_meals:
            if m.meal_date != meal_date:
                usage_counter[m.recipe_id] = usage_counter.get(m.recipe_id, 0) + 1
                cost = recipe_cost.get(m.recipe_id)
                if cost:
                    cost_counter[cost] = cost_counter.get(cost, 0) + 1

        yesterday_meals = [m for m in all_meals if m.meal_date == meal_date - timedelta(days=1)]
        yesterday_ids = {m.recipe_id for m in yesterday_meals}

        old_meals = [m for m in all_meals if m.meal_date == meal_date]
        for m in old_meals:
            db.delete(m)
        db.flush()

        meals, _ = build_day_meals(candidates, ctx_a, ctx_b, meal_date, usage_counter, cost_counter, yesterday_ids)
        user_id_by_key = {"A": plan.user_id_a, "B": plan.user_id_b}
        for meal in meals:
            self._write_meal(db, plan_id, user_id_by_key, meal)
            self._log_adjustment(db, plan_id, "重推整天", meal_date, meal["meal_type"],
                                  user_id_by_key[meal["user"]], None, meal["recipe_id"])
        db.commit()
        return self.get_plan(db, plan_id)


meal_plan_service = MealPlanService()
