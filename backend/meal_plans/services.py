from sqlalchemy.orm import Session
from datetime import date, timedelta
from typing import List, Optional, Dict, Set

from users.models import User
from users.services import dietary_preference_service, weight_goal_service
from fitness.models import WeightRecord, ExerciseSession, DailySteps
from recipes.models import Recipe
from meal_plans.models import (
    WeeklyMealPlan, DailyMealDetail, MealAdjustment, FixedMealPreference,
    ExcludedRecipe, FavoriteRecipe, SoupDayPreference,
)
from shopping.models import ShoppingList
from meal_plans.schemas import FIXED_MEAL_TYPES
from meal_plans import nutrition_calc
from meal_plans.selection_algorithm import generate_week_plan, build_day_meals, scale_recipe, MEAL_SHARES, CATEGORY_VARIETY_CAP
from meal_plans.prep_planner import build_prep_plan


def _parse_csv(text: Optional[str]) -> List[str]:
    return [p.strip() for p in (text or "").split(",") if p.strip()]


def _recipe_to_candidate(recipe: Recipe) -> Dict:
    return {
        "id": recipe.id, "recipe_name": recipe.recipe_name, "category": recipe.category,
        "base_weight_g": recipe.base_weight_g, "cost_level": recipe.cost_level,
        "carb_source": recipe.carb_source,
        "calories": recipe.nutrition.total_calories_kcal if recipe.nutrition else 0,
        "protein_g": recipe.nutrition.protein_g if recipe.nutrition else 0,
        "carbs_g": recipe.nutrition.carbs_g if recipe.nutrition else 0,
        "fat_g": recipe.nutrition.fat_g if recipe.nutrition else 0,
        "fiber_g": recipe.nutrition.fiber_g if recipe.nutrition else 0,
    }


class ExcludedRecipeService:
    """黑名單：標記「不要再推薦」的食譜，兩人共用一份，產生/重推菜單時直接從候選池排除"""

    def list_all(self, db: Session) -> List[Dict]:
        rows = db.query(ExcludedRecipe).all()
        result = []
        for r in rows:
            recipe = db.get(Recipe, r.recipe_id)
            result.append({"id": r.id, "recipe_id": r.recipe_id, "recipe_name": recipe.recipe_name if recipe else None})
        return result

    def add(self, db: Session, recipe_id: int) -> Dict:
        if not db.get(Recipe, recipe_id):
            raise ValueError(f"食譜 {recipe_id} 不存在")
        existing = db.query(ExcludedRecipe).filter(ExcludedRecipe.recipe_id == recipe_id).first()
        row = existing or ExcludedRecipe(recipe_id=recipe_id)
        if not existing:
            db.add(row)
        db.commit()
        db.refresh(row)
        recipe = db.get(Recipe, recipe_id)
        return {"id": row.id, "recipe_id": row.recipe_id, "recipe_name": recipe.recipe_name}

    def remove(self, db: Session, exclusion_id: int) -> bool:
        row = db.get(ExcludedRecipe, exclusion_id)
        if not row:
            return False
        db.delete(row)
        db.commit()
        return True

    def excluded_recipe_ids(self, db: Session) -> Set[int]:
        return {r.recipe_id for r in db.query(ExcludedRecipe).all()}


excluded_recipe_service = ExcludedRecipeService()


class FavoriteRecipeService:
    """最愛清單：軟性加權，選餐評分時比較容易被選到，但不像 FixedMealPreference 那樣鎖死"""

    def list_for_user(self, db: Session, user_id: int) -> List[Dict]:
        rows = db.query(FavoriteRecipe).filter(FavoriteRecipe.user_id == user_id).all()
        result = []
        for r in rows:
            recipe = db.get(Recipe, r.recipe_id)
            result.append({"id": r.id, "user_id": r.user_id, "recipe_id": r.recipe_id, "recipe_name": recipe.recipe_name if recipe else None})
        return result

    def add(self, db: Session, user_id: int, recipe_id: int) -> Dict:
        if not db.get(Recipe, recipe_id):
            raise ValueError(f"食譜 {recipe_id} 不存在")
        existing = db.query(FavoriteRecipe).filter(FavoriteRecipe.user_id == user_id, FavoriteRecipe.recipe_id == recipe_id).first()
        row = existing or FavoriteRecipe(user_id=user_id, recipe_id=recipe_id)
        if not existing:
            db.add(row)
        db.commit()
        db.refresh(row)
        recipe = db.get(Recipe, recipe_id)
        return {"id": row.id, "user_id": row.user_id, "recipe_id": row.recipe_id, "recipe_name": recipe.recipe_name}

    def remove(self, db: Session, favorite_id: int) -> bool:
        row = db.get(FavoriteRecipe, favorite_id)
        if not row:
            return False
        db.delete(row)
        db.commit()
        return True

    def favorite_recipe_ids(self, db: Session, user_id_a: int, user_id_b: int) -> Set[int]:
        rows = db.query(FavoriteRecipe).filter(FavoriteRecipe.user_id.in_([user_id_a, user_id_b])).all()
        return {r.recipe_id for r in rows}


favorite_recipe_service = FavoriteRecipeService()


class SoupDayPreferenceService:
    """勾選「這天想喝湯」，兩人共用一份設定，不分誰勾的"""

    def list_days(self, db: Session) -> List[int]:
        return sorted(r.day_of_week for r in db.query(SoupDayPreference).all())

    def set_days(self, db: Session, days: List[int]) -> List[int]:
        invalid = [d for d in days if d < 0 or d > 6]
        if invalid:
            raise ValueError("day_of_week 必須介於 0-6（0=週一...6=週日）")
        db.query(SoupDayPreference).delete()
        for d in sorted(set(days)):
            db.add(SoupDayPreference(day_of_week=d))
        db.commit()
        return self.list_days(db)

    def soup_days(self, db: Session) -> Set[int]:
        return {r.day_of_week for r in db.query(SoupDayPreference).all()}


soup_day_preference_service = SoupDayPreferenceService()


class FixedMealPreferenceService:
    """使用者固定餐點設定（例如「我早餐固定吃燕麥牛奶粥」），產生週菜單時優先套用，
    只調整份量、不會被規則式演算法換成別的食譜。"""

    def list_for_user(self, db: Session, user_id: int) -> List[Dict]:
        rows = db.query(FixedMealPreference).filter(FixedMealPreference.user_id == user_id).all()
        result = []
        for r in rows:
            recipe = db.get(Recipe, r.recipe_id)
            result.append({
                "id": r.id, "user_id": r.user_id, "meal_type": r.meal_type,
                "recipe_id": r.recipe_id, "recipe_name": recipe.recipe_name if recipe else None,
            })
        return result

    def set_preference(self, db: Session, user_id: int, meal_type: str, recipe_id: int) -> Dict:
        if meal_type not in FIXED_MEAL_TYPES:
            raise ValueError(f"meal_type 必須是 {FIXED_MEAL_TYPES} 其中之一")
        if not db.get(Recipe, recipe_id):
            raise ValueError(f"食譜 {recipe_id} 不存在")

        existing = db.query(FixedMealPreference).filter(
            FixedMealPreference.user_id == user_id, FixedMealPreference.meal_type == meal_type
        ).first()
        if existing:
            existing.recipe_id = recipe_id
            row = existing
        else:
            row = FixedMealPreference(user_id=user_id, meal_type=meal_type, recipe_id=recipe_id)
            db.add(row)
        db.commit()
        db.refresh(row)
        recipe = db.get(Recipe, recipe_id)
        return {"id": row.id, "user_id": row.user_id, "meal_type": row.meal_type, "recipe_id": row.recipe_id, "recipe_name": recipe.recipe_name}

    def delete_preference(self, db: Session, preference_id: int) -> bool:
        row = db.get(FixedMealPreference, preference_id)
        if not row:
            return False
        db.delete(row)
        db.commit()
        return True

    def build_preferred_recipes(self, db: Session, user_id_a: int, user_id_b: int) -> Dict:
        """回傳 selection_algorithm 要的格式：{(meal_type, 'A'|'B'): candidate_dict}"""
        preferred: Dict = {}
        for user_key, user_id in (("A", user_id_a), ("B", user_id_b)):
            rows = db.query(FixedMealPreference).filter(FixedMealPreference.user_id == user_id).all()
            for r in rows:
                recipe = db.get(Recipe, r.recipe_id)
                if recipe:
                    preferred[(r.meal_type, user_key)] = _recipe_to_candidate(recipe)
        return preferred


fixed_meal_preference_service = FixedMealPreferenceService()


class NutritionTargetService:
    """BMR/TDEE/巨量營養素目標"""

    def _resolve_goal_adjusted_calories(self, db: Session, user: User, weight_kg: float, tdee: float, target_date) -> float:
        """減脂預設固定 -350kcal；如果有設定目標體重＋目標日期（WeightGoal），改用依 TDEE 動態算出的
        赤字（見 nutrition_calc.calculate_goal_based_deficit），每 30 天才依當時體重重新計算一次。"""
        if user.primary_goal != "減脂":
            return nutrition_calc.adjust_for_goal(tdee, user.primary_goal)

        goal = weight_goal_service.get_row(db, user.id)
        if not goal or not goal.target_weight_kg or not goal.target_date:
            return nutrition_calc.adjust_for_goal(tdee, user.primary_goal)

        needs_recalc = (
            goal.deficit_calculated_at is None
            or (target_date - goal.deficit_calculated_at).days >= nutrition_calc.DEFICIT_RECALC_INTERVAL_DAYS
        )
        if needs_recalc:
            deficit = nutrition_calc.calculate_goal_based_deficit(tdee, weight_kg, goal.target_weight_kg, goal.target_date, target_date)
            weight_goal_service.record_deficit(db, goal, deficit, target_date, weight_kg)
        else:
            deficit = goal.active_daily_deficit_kcal or 0.0
        return max(tdee - deficit, 1200)

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
        goal_adjusted = self._resolve_goal_adjusted_calories(db, user, weight_kg, tdee, target_date)
        phase = nutrition_calc.calculate_menstrual_phase(
            user.gender, user.last_menstrual_date, user.menstrual_cycle_length_days,
            user.menstrual_luteal_phase_start_offset_days or 14, target_date,
        )
        final_calories = nutrition_calc.adjust_for_menstrual_phase(
            goal_adjusted, phase,
            user.menstrual_luteal_phase_adjustment_calories or 150,
            user.menstrual_premenstrual_adjustment_calories or 120,
        )
        menstrual_adjusted_calories = final_calories
        if user.manual_calories_target:
            # 手動覆蓋：直接取代自動算出的目標熱量，BMR/TDEE 仍照算只是給你參考
            final_calories = user.manual_calories_target
        macros = nutrition_calc.calculate_nutrient_targets(weight_kg, user.primary_goal, final_calories)

        return {
            "user_id": user_id, "bmr": round(bmr, 1), "tdee": round(tdee, 1),
            "goal_adjusted_calories": round(goal_adjusted, 1), "menstrual_phase": phase,
            "menstrual_adjusted_calories": round(menstrual_adjusted_calories, 1),
            "manual_override": bool(user.manual_calories_target),
            "daily_calories_target": round(final_calories, 1),
            "daily_protein_g": macros["protein_g"],
            **macros,
        }

    def set_manual_override(self, db: Session, user_id: int, manual_calories_target: Optional[float]) -> Dict:
        user = db.get(User, user_id)
        if not user:
            raise ValueError(f"使用者 {user_id} 不存在")
        user.manual_calories_target = manual_calories_target
        db.commit()
        return self.get_user_context(db, user_id, date.today())


nutrition_target_service = NutritionTargetService()


class MealPlanService:
    """規則式週菜單推薦（取代 Claude API 呼叫，見 selection_algorithm.py）"""

    def _candidate_recipes(self, db: Session, user_id_a: int, user_id_b: int) -> List[Dict]:
        pref_a = dietary_preference_service.get(db, user_id_a)
        pref_b = dietary_preference_service.get(db, user_id_b)
        allergens = set(_parse_csv(pref_a["allergies"])) | set(_parse_csv(pref_b["allergies"]))
        needs_veg = "素食" in _parse_csv(pref_a["restrictions"]) or "素食" in _parse_csv(pref_b["restrictions"])
        excluded_ids = excluded_recipe_service.excluded_recipe_ids(db)

        recipes = db.query(Recipe).filter(Recipe.is_active == True).all()
        candidates = []
        for r in recipes:
            if r.id in excluded_ids:
                continue
            tags = set(_parse_csv(r.allergen_tags))
            if tags & allergens:
                continue
            if needs_veg and not r.is_vegetarian:
                continue
            candidates.append(_recipe_to_candidate(r))
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
        preferred_recipes = fixed_meal_preference_service.build_preferred_recipes(db, user_id_a, user_id_b)
        favorite_ids = favorite_recipe_service.favorite_recipe_ids(db, user_id_a, user_id_b)
        soup_days = soup_day_preference_service.soup_days(db)

        days = generate_week_plan(candidates, ctx_a, ctx_b, week_start_date, preferred_recipes=preferred_recipes,
                                   favorite_recipe_ids=favorite_ids, soup_days=soup_days)

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

    def list_plans(self, db: Session, user_id: Optional[int] = None,
                    start_date: Optional[date] = None, end_date: Optional[date] = None) -> List[Dict]:
        """依日期區間查詢已產生的週菜單摘要（不含逐餐明細），預設回傳最近的在前"""
        query = db.query(WeeklyMealPlan)
        if user_id is not None:
            query = query.filter(
                (WeeklyMealPlan.user_id_a == user_id) | (WeeklyMealPlan.user_id_b == user_id)
            )
        if start_date is not None:
            query = query.filter(WeeklyMealPlan.plan_date >= start_date)
        if end_date is not None:
            query = query.filter(WeeklyMealPlan.plan_date <= end_date)
        plans = query.order_by(WeeklyMealPlan.plan_date.desc()).all()
        return [
            {
                "id": p.id, "plan_date": p.plan_date, "user_id_a": p.user_id_a, "user_id_b": p.user_id_b,
                "plan_status": p.plan_status,
            }
            for p in plans
        ]

    def delete_plan(self, db: Session, plan_id: int) -> bool:
        """刪除整週菜單：先清掉引用這個 plan_id 的調整紀錄／購物清單關聯，再刪 plan
        （meals 是 cascade="all, delete-orphan" 會跟著刪，購物清單本身不刪，只是把來源參照設 null）"""
        plan = db.get(WeeklyMealPlan, plan_id)
        if not plan:
            return False
        db.query(MealAdjustment).filter(MealAdjustment.plan_id == plan_id).delete()
        db.query(ShoppingList).filter(ShoppingList.created_from_plan_id == plan_id).update({"created_from_plan_id": None})
        db.delete(plan)
        db.commit()
        return True

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
                "recipe_category": recipe.category if recipe else None,
                "carb_source": recipe.carb_source if recipe else None,
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
        recipe_carb_source = {r["id"]: r["carb_source"] for r in candidates}
        yesterday_carb_sources = {
            recipe_carb_source.get(m.recipe_id) for m in yesterday_meals
            if recipe_carb_source.get(m.recipe_id)
        }

        recipe_category = {r["id"]: r["category"] for r in candidates}
        weekly_variety: Dict[str, Set[int]] = {cat: set() for cat in CATEGORY_VARIETY_CAP}
        for m in all_meals:
            if m.meal_date == meal_date:
                continue
            cat = recipe_category.get(m.recipe_id)
            if cat in weekly_variety:
                weekly_variety[cat].add(m.recipe_id)

        old_meals = [m for m in all_meals if m.meal_date == meal_date]
        for m in old_meals:
            db.delete(m)
        db.flush()

        preferred_recipes = fixed_meal_preference_service.build_preferred_recipes(db, plan.user_id_a, plan.user_id_b)
        favorite_ids = favorite_recipe_service.favorite_recipe_ids(db, plan.user_id_a, plan.user_id_b)
        soup_days = soup_day_preference_service.soup_days(db)
        meals, _, _ = build_day_meals(candidates, ctx_a, ctx_b, meal_date, usage_counter, cost_counter, yesterday_ids,
                                       preferred_recipes=preferred_recipes, favorite_recipe_ids=favorite_ids,
                                       yesterday_carb_sources=yesterday_carb_sources,
                                       include_soup=meal_date.weekday() in soup_days,
                                       weekly_variety=weekly_variety)
        user_id_by_key = {"A": plan.user_id_a, "B": plan.user_id_b}
        for meal in meals:
            self._write_meal(db, plan_id, user_id_by_key, meal)
            self._log_adjustment(db, plan_id, "重推整天", meal_date, meal["meal_type"],
                                  user_id_by_key[meal["user"]], None, meal["recipe_id"])
        db.commit()
        return self.get_plan(db, plan_id)

    def add_dish(self, db: Session, plan_id: int, meal_date, meal_type: str, recipe_id: int,
                 user_id: Optional[int] = None) -> Dict:
        """單一餐別內自由新增一道菜。早餐/下午茶各自一份，需指定 user_id；午餐/晚餐兩人共用，忽略 user_id。
        新菜的份量先依「這餐目前有幾道菜」平均分配，跟其他菜的份量精準度可能有落差，
        之後可呼叫 rebalance_day 依當天熱量目標重新計算整天所有菜的份量。"""
        plan = db.get(WeeklyMealPlan, plan_id)
        if not plan:
            raise ValueError("計畫不存在")
        recipe = db.get(Recipe, recipe_id)
        if not recipe:
            raise ValueError(f"食譜 {recipe_id} 不存在")
        candidate = _recipe_to_candidate(recipe)

        if meal_type in FIXED_MEAL_TYPES:
            if not user_id:
                raise ValueError(f"{meal_type} 是各自一份，新增餐點需指定 user_id")
            target_user_ids = [user_id]
        else:
            target_user_ids = [plan.user_id_a, plan.user_id_b]

        for uid in target_user_ids:
            ctx = nutrition_target_service.get_user_context(db, uid, meal_date)
            share = MEAL_SHARES.get(meal_type)
            if share is None:
                raise ValueError(f"不支援的 meal_type：{meal_type}")
            existing_count = db.query(DailyMealDetail).filter(
                DailyMealDetail.meal_plan_id == plan_id, DailyMealDetail.meal_date == meal_date,
                DailyMealDetail.meal_type == meal_type, DailyMealDetail.assigned_user_id == uid,
            ).count()
            target_cal = ctx["daily_calories_target"] * share / (existing_count + 1)
            scaled = scale_recipe(candidate, target_cal)
            row = DailyMealDetail(
                meal_plan_id=plan_id, meal_date=meal_date, meal_type=meal_type, recipe_id=recipe.id,
                assigned_user_id=uid, serving_weight_g=scaled["serving_weight_g"], calories=scaled["calories"],
                protein_g=scaled["protein_g"], carbs_g=scaled["carbs_g"], fat_g=scaled["fat_g"], fiber_g=scaled["fiber_g"],
            )
            db.add(row)
            self._log_adjustment(db, plan_id, "新增餐點", meal_date, meal_type, uid, None, recipe.id)
        db.commit()
        return self.get_plan(db, plan_id)

    def remove_dish(self, db: Session, plan_id: int, meal_id: int) -> Dict:
        """移除單一道菜。午餐/晚餐是兩人共用的同一道菜，連同對方那份一起移除，早餐/下午茶只移除該筆。"""
        meal = db.get(DailyMealDetail, meal_id)
        if not meal or meal.meal_plan_id != plan_id:
            raise ValueError("找不到這筆餐點")
        to_delete = [meal]
        if meal.meal_type not in FIXED_MEAL_TYPES:
            sibling = db.query(DailyMealDetail).filter(
                DailyMealDetail.meal_plan_id == plan_id, DailyMealDetail.meal_date == meal.meal_date,
                DailyMealDetail.meal_type == meal.meal_type, DailyMealDetail.recipe_id == meal.recipe_id,
                DailyMealDetail.id != meal.id,
            ).first()
            if sibling:
                to_delete.append(sibling)
        for m in to_delete:
            self._log_adjustment(db, plan_id, "移除餐點", m.meal_date, m.meal_type, m.assigned_user_id, m.recipe_id, None)
            db.delete(m)
        db.commit()
        return self.get_plan(db, plan_id)

    def rebalance_day(self, db: Session, plan_id: int, meal_date) -> Dict:
        """重新依當天熱量目標分配份量：每個使用者、每一餐，把該餐目前有的菜平均分配熱量佔比並重新
        scale_recipe，不改變菜色組成，只調整份量。用在「新增/移除某一餐的菜之後，其他菜份量需要跟著調整」。"""
        plan = db.get(WeeklyMealPlan, plan_id)
        if not plan:
            raise ValueError("計畫不存在")
        all_meals = db.query(DailyMealDetail).filter(
            DailyMealDetail.meal_plan_id == plan_id, DailyMealDetail.meal_date == meal_date,
        ).all()
        if not all_meals:
            raise ValueError("這天沒有任何餐點")

        for uid in (plan.user_id_a, plan.user_id_b):
            ctx = nutrition_target_service.get_user_context(db, uid, meal_date)
            for meal_type, share in MEAL_SHARES.items():
                rows = [m for m in all_meals if m.assigned_user_id == uid and m.meal_type == meal_type]
                if not rows:
                    continue
                target_per_dish = ctx["daily_calories_target"] * share / len(rows)
                for m in rows:
                    recipe = db.get(Recipe, m.recipe_id)
                    if not recipe:
                        continue
                    scaled = scale_recipe(_recipe_to_candidate(recipe), target_per_dish)
                    m.serving_weight_g = scaled["serving_weight_g"]
                    m.calories = scaled["calories"]
                    m.protein_g = scaled["protein_g"]
                    m.carbs_g = scaled["carbs_g"]
                    m.fat_g = scaled["fat_g"]
                    m.fiber_g = scaled["fiber_g"]
        self._log_adjustment(db, plan_id, "重新計算份量", meal_date, None, None, None, None)
        db.commit()
        return self.get_plan(db, plan_id)

    def get_prep_plan(self, db: Session, plan_id: int) -> Dict:
        """把已確認的週菜單換算成備料場次（週日整週肉類批次、週二/週四備便當、每日晚餐提示）。
        見 prep_planner.py 開頭說明。"""
        plan = db.get(WeeklyMealPlan, plan_id)
        if not plan:
            raise ValueError("計畫不存在")
        full_plan = self.get_plan(db, plan_id)
        return build_prep_plan(full_plan["days"], plan.plan_date)


meal_plan_service = MealPlanService()
