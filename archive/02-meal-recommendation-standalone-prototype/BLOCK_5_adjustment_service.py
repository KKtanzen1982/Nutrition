"""
BLOCK_5: 微調邏輯服務
- 方案 A：替換單菜色
- 方案 B：重推整天
- 方案 C：搜尋替換
- 方案 D：調整分量
"""

import logging
from datetime import date, datetime
from typing import Dict, List, Optional, Any, Tuple
import uuid

logger = logging.getLogger(__name__)


# ==================== 營養素計算輔助 ====================

class NutrientCalculator:
    """營養素計算"""
    
    @staticmethod
    def calculate_meal_nutrition(
        recipe: Dict[str, Any],
        serving_weight_g: int
    ) -> Dict[str, float]:
        """
        根據食譜和分量計算營養素
        
        Args:
            recipe: 食譜數據（包含基礎重量和營養素）
            serving_weight_g: 實際分量（克）
        
        Returns:
            {calories, protein_g, carbs_g, fat_g, fiber_g}
        """
        base_weight = recipe.get("base_weight_g", 100)
        ratio = serving_weight_g / base_weight if base_weight > 0 else 1
        
        return {
            "calories": recipe.get("calories", 0) * ratio,
            "protein_g": recipe.get("protein_g", 0) * ratio,
            "carbs_g": recipe.get("carbs_g", 0) * ratio,
            "fat_g": recipe.get("fat_g", 0) * ratio,
            "fiber_g": recipe.get("fiber_g", 0) * ratio if recipe.get("fiber_g") else None
        }
    
    @staticmethod
    def calculate_day_summary(meals: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
        """
        計算某一天的營養總和（按用戶分組）
        
        Args:
            meals: 該天的所有餐次 [{meal_type, user_id, calories, protein_g, ...}, ...]
        
        Returns:
            {user_id: {total_calories, total_protein_g, ...}, ...}
        """
        summary = {}
        
        for meal in meals:
            user_id = meal.get("user_id")
            if user_id not in summary:
                summary[user_id] = {
                    "total_calories": 0,
                    "total_protein_g": 0,
                    "total_carbs_g": 0,
                    "total_fat_g": 0,
                    "total_fiber_g": 0
                }
            
            summary[user_id]["total_calories"] += meal.get("calories", 0)
            summary[user_id]["total_protein_g"] += meal.get("protein_g", 0)
            summary[user_id]["total_carbs_g"] += meal.get("carbs_g", 0)
            summary[user_id]["total_fat_g"] += meal.get("fat_g", 0)
            if meal.get("fiber_g"):
                summary[user_id]["total_fiber_g"] += meal.get("fiber_g", 0)
        
        return summary


# ==================== 微調服務 ====================

class MealAdjustmentService:
    """微調服務 - 支持 4 種微調方案"""
    
    # ========== 方案 A：替換單菜色 ==========
    
    @staticmethod
    def replace_meal(
        current_meals: List[Dict[str, Any]],
        meal_date: date,
        meal_type: str,
        user_id: int,
        new_recipe: Dict[str, Any],
        original_recipe_id: int
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any], Dict[str, Any]]:
        """
        方案 A：替換單個菜色
        
        Args:
            current_meals: 當前週計畫的所有菜色
            meal_date: 要替換的日期
            meal_type: 餐次類型（breakfast, lunch, etc）
            user_id: 用戶 ID
            new_recipe: 新食譜數據
            original_recipe_id: 原食譜 ID（用於記錄）
        
        Returns:
            (更新後的餐次列表, 更新的餐次詳情, 微調記錄)
        """
        
        updated_meals = []
        updated_meal = None
        
        for meal in current_meals:
            meal_copy = meal.copy()
            
            # 找到要替換的餐次
            if (meal.get("meal_date") == meal_date and
                meal.get("meal_type") == meal_type and
                meal.get("user_id") == user_id):
                
                # 計算新餐次的營養素
                nutrition = NutrientCalculator.calculate_meal_nutrition(
                    new_recipe,
                    new_recipe.get("base_weight_g", 100)
                )
                
                # 更新餐次
                meal_copy.update({
                    "recipe_id": new_recipe.get("id"),
                    "recipe_name": new_recipe.get("name"),
                    "serving_weight_g": new_recipe.get("base_weight_g", 100),
                    "calories": nutrition["calories"],
                    "protein_g": nutrition["protein_g"],
                    "carbs_g": nutrition["carbs_g"],
                    "fat_g": nutrition["fat_g"],
                    "fiber_g": nutrition["fiber_g"],
                    "updated_at": datetime.now()
                })
                
                updated_meal = meal_copy
            
            updated_meals.append(meal_copy)
        
        # 記錄微調
        adjustment_record = {
            "adjustment_type": "替換",
            "meal_date": meal_date,
            "meal_type": meal_type,
            "user_id": user_id,
            "original_recipe_id": original_recipe_id,
            "adjusted_recipe_id": new_recipe.get("id"),
            "reason": "用戶手動替換",
            "adjusted_by": "user",
            "adjusted_at": datetime.now()
        }
        
        logger.info(f"替換菜色成功：{meal_date} {meal_type} (user {user_id})")
        
        return updated_meals, updated_meal, adjustment_record
    
    # ========== 方案 B：重推整天 ==========
    
    @staticmethod
    def prepare_for_day_regeneration(
        current_meals: List[Dict[str, Any]],
        meal_date: date,
        fixed_meals: Optional[List[Dict[str, str]]] = None
    ) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
        """
        方案 B：準備重推整天的數據
        
        構建用於重推的上下文，包括：
        1. 固定不變的餐次
        2. 其他 6 天已確認的菜色
        3. 該天需要重新推薦的餐次
        
        Args:
            current_meals: 當前週計畫的所有菜色
            meal_date: 要重推的日期
            fixed_meals: 固定不變的餐次 [{"meal_type": "breakfast", "user_id": 1, "recipe_id": 5}, ...]
        
        Returns:
            (job_id, 固定餐次摘要, 其他 6 天的菜色摘要)
        """
        
        job_id = str(uuid.uuid4())
        fixed_meals = fixed_meals or []
        
        # 提取該天的菜色和其他 6 天的菜色
        day_meals = [m for m in current_meals if m.get("meal_date") == meal_date]
        other_days_meals = [m for m in current_meals if m.get("meal_date") != meal_date]
        
        # 構建固定餐次摘要
        fixed_summary = "以下餐次固定不變：\n"
        fixed_meal_ids = set()
        for fixed_meal in fixed_meals:
            meal_type = fixed_meal.get("meal_type", "unknown")
            user_id = fixed_meal.get("user_id", 0)
            recipe_id = fixed_meal.get("recipe_id", 0)
            fixed_summary += f"  - {meal_type} (User {user_id}): Recipe ID {recipe_id}\n"
            fixed_meal_ids.add((meal_type, user_id))
        
        # 標記哪些餐次需要重推
        meals_to_regenerate = [
            m for m in day_meals
            if (m.get("meal_type"), m.get("user_id")) not in fixed_meal_ids
        ]
        
        regenerate_summary = f"以下 {len(meals_to_regenerate)} 個餐次需要重新推薦：\n"
        for meal in meals_to_regenerate:
            regenerate_summary += f"  - {meal.get('meal_type')} (User {meal.get('user_id')})\n"
        
        # 構建其他 6 天的摘要
        other_days_summary = "其他 6 天已推薦的菜色（參考）：\n"
        for meal in other_days_meals:
            other_days_summary += f"  - {meal.get('meal_date')} {meal.get('meal_type')} " \
                                 f"(User {meal.get('user_id')}): {meal.get('recipe_name')} " \
                                 f"({meal.get('calories')} kcal)\n"
        
        context = {
            "job_id": job_id,
            "meal_date": meal_date,
            "fixed_summary": fixed_summary,
            "regenerate_summary": regenerate_summary,
            "meals_to_regenerate": meals_to_regenerate,
            "other_days_summary": other_days_summary,
            "fixed_meal_ids": fixed_meal_ids
        }
        
        logger.info(f"準備重推整天：{meal_date} (job_id: {job_id})")
        
        return job_id, context, {"fixed_meals": fixed_meals}
    
    @staticmethod
    def apply_regenerated_day(
        current_meals: List[Dict[str, Any]],
        meal_date: date,
        regenerated_meals: List[Dict[str, Any]],
        fixed_meal_ids: set
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        應用重推的整天菜色
        
        Args:
            current_meals: 當前所有菜色
            meal_date: 重推的日期
            regenerated_meals: Claude 重新推薦的餐次
            fixed_meal_ids: 固定不變的餐次集合 {(meal_type, user_id), ...}
        
        Returns:
            (更新後的所有菜色, 微調記錄列表)
        """
        
        updated_meals = []
        adjustments = []
        
        # 先保留其他日期的菜色 + 該日的固定菜色
        for meal in current_meals:
            if meal.get("meal_date") != meal_date:
                updated_meals.append(meal)
            else:
                # 該日期：只保留固定的餐次
                if (meal.get("meal_type"), meal.get("user_id")) in fixed_meal_ids:
                    updated_meals.append(meal)
        
        # 加入重新推薦的餐次
        for regen_meal in regenerated_meals:
            updated_meals.append(regen_meal)
            
            # 記錄微調
            adjustments.append({
                "adjustment_type": "重推整天",
                "meal_date": meal_date,
                "meal_type": regen_meal.get("meal_type"),
                "user_id": regen_meal.get("user_id"),
                "original_recipe_id": None,
                "adjusted_recipe_id": regen_meal.get("recipe_id"),
                "reason": f"用戶重推 {meal_date}",
                "adjusted_by": "user",
                "adjusted_at": datetime.now()
            })
        
        logger.info(f"應用重推整天結果：{meal_date} ({len(regenerated_meals)} 個新餐次)")
        
        return updated_meals, adjustments
    
    # ========== 方案 C：搜尋替換 ==========
    
    @staticmethod
    def search_and_replace(
        current_meals: List[Dict[str, Any]],
        meal_date: date,
        meal_type: str,
        user_id: int,
        new_recipe: Dict[str, Any],
        original_recipe_id: int,
        search_query: str
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any], Dict[str, Any]]:
        """
        方案 C：搜尋並替換
        
        邏輯與方案 A 相同，但多記錄用戶的搜尋查詢
        
        Args:
            current_meals: 當前所有菜色
            meal_date: 餐次日期
            meal_type: 餐次類型
            user_id: 用戶 ID
            new_recipe: 新食譜
            original_recipe_id: 原食譜 ID
            search_query: 用戶搜尋的關鍵字
        
        Returns:
            (更新後的餐次列表, 更新的餐次詳情, 微調記錄)
        """
        
        # 使用相同邏輯替換
        updated_meals, updated_meal, adjustment = MealAdjustmentService.replace_meal(
            current_meals,
            meal_date,
            meal_type,
            user_id,
            new_recipe,
            original_recipe_id
        )
        
        # 補充搜尋信息
        adjustment["adjustment_type"] = "搜尋替換"
        adjustment["search_query"] = search_query
        
        logger.info(f"搜尋並替換完成：查詢='{search_query}'，{meal_date} {meal_type}")
        
        return updated_meals, updated_meal, adjustment
    
    # ========== 方案 D：調整分量 ==========
    
    @staticmethod
    def adjust_serving_weight(
        current_meals: List[Dict[str, Any]],
        meal_date: date,
        meal_type: str,
        user_id: int,
        new_serving_weight_g: int,
        recipe: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any], Dict[str, Any]]:
        """
        方案 D：調整分量
        
        修改 serving_weight_g，自動重新計算營養素
        
        Args:
            current_meals: 當前所有菜色
            meal_date: 餐次日期
            meal_type: 餐次類型
            user_id: 用戶 ID
            new_serving_weight_g: 新分量（克）
            recipe: 食譜數據
        
        Returns:
            (更新後的餐次列表, 更新的餐次詳情, 微調記錄)
        """
        
        updated_meals = []
        updated_meal = None
        original_weight = None
        
        for meal in current_meals:
            meal_copy = meal.copy()
            
            if (meal.get("meal_date") == meal_date and
                meal.get("meal_type") == meal_type and
                meal.get("user_id") == user_id):
                
                original_weight = meal.get("serving_weight_g", 100)
                
                # 重新計算營養素
                nutrition = NutrientCalculator.calculate_meal_nutrition(
                    recipe,
                    new_serving_weight_g
                )
                
                meal_copy.update({
                    "serving_weight_g": new_serving_weight_g,
                    "calories": nutrition["calories"],
                    "protein_g": nutrition["protein_g"],
                    "carbs_g": nutrition["carbs_g"],
                    "fat_g": nutrition["fat_g"],
                    "fiber_g": nutrition["fiber_g"],
                    "updated_at": datetime.now()
                })
                
                updated_meal = meal_copy
            
            updated_meals.append(meal_copy)
        
        # 記錄微調
        adjustment_record = {
            "adjustment_type": "調整分量",
            "meal_date": meal_date,
            "meal_type": meal_type,
            "user_id": user_id,
            "original_serving_weight_g": original_weight,
            "new_serving_weight_g": new_serving_weight_g,
            "recipe_id": recipe.get("id"),
            "reason": f"用戶調整分量：{original_weight}g → {new_serving_weight_g}g",
            "adjusted_by": "user",
            "adjusted_at": datetime.now()
        }
        
        logger.info(f"調整分量成功：{meal_date} {meal_type} (user {user_id}), " \
                   f"{original_weight}g → {new_serving_weight_g}g")
        
        return updated_meals, updated_meal, adjustment_record


# ==================== 週計畫管理 ====================

class MealPlanManager:
    """週計畫管理 - 儲存和查詢"""
    
    @staticmethod
    def build_meal_plan_from_claude_response(
        claude_response: Dict[str, Any],
        plan_date: date,
        user_a_id: int,
        user_b_id: int,
        calorie_calculation_method: str,
        user_a_daily_calories: float,
        user_b_daily_calories: float,
        user_a_menstrual_phase: str,
        user_b_menstrual_phase: str
    ) -> Dict[str, Any]:
        """
        從 Claude 回應構建完整的週計畫
        
        Args:
            claude_response: Claude 的推薦回應
            plan_date: 計畫開始日期
            user_a_id, user_b_id: 用戶 ID
            calorie_calculation_method: 使用的計算方法
            user_a_daily_calories, user_b_daily_calories: 目標熱量
            user_a_menstrual_phase, user_b_menstrual_phase: 生理期
        
        Returns:
            完整的週計畫數據結構
        """
        
        recommendation = claude_response.get("recommendation", {})
        
        # 提取所有餐次
        all_meals = []
        for day_data in recommendation.get("days", []):
            meal_date = day_data.get("date")
            for meal in day_data.get("meals", []):
                meal_record = {
                    "meal_date": meal_date,
                    "meal_type": meal.get("meal_type"),
                    "user_id": meal.get("user_id"),
                    "user_name": meal.get("user_name", ""),
                    "recipe_id": meal.get("recipe_id"),
                    "recipe_name": meal.get("recipe_name"),
                    "serving_weight_g": meal.get("serving_weight_g"),
                    "calories": meal.get("calories"),
                    "protein_g": meal.get("protein_g"),
                    "carbs_g": meal.get("carbs_g"),
                    "fat_g": meal.get("fat_g"),
                    "fiber_g": meal.get("fiber_g"),
                    "created_at": datetime.now()
                }
                all_meals.append(meal_record)
        
        # 構建週計畫摘要
        meal_plan = {
            "plan_date": plan_date,
            "user_a_id": user_a_id,
            "user_b_id": user_b_id,
            "calorie_calculation_method": calorie_calculation_method,
            "user_a_daily_calories_target": int(user_a_daily_calories),
            "user_b_daily_calories_target": int(user_b_daily_calories),
            "user_a_menstrual_phase": user_a_menstrual_phase,
            "user_b_menstrual_phase": user_b_menstrual_phase,
            "status": "draft",
            "claude_generated": True,
            "recommendation_notes": recommendation.get("analysis_notes", ""),
            "meals": all_meals,
            "created_at": datetime.now()
        }
        
        logger.info(f"構建週計畫：{plan_date}，共 {len(all_meals)} 個餐次")
        
        return meal_plan
    
    @staticmethod
    def recalculate_weekly_summary(meals: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
        """
        重新計算週的營養總和
        
        Args:
            meals: 整週的所有餐次
        
        Returns:
            {user_id: {total_calories, avg_daily_calories, ...}, ...}
        """
        
        summary = {}
        days_count = {}
        
        for meal in meals:
            user_id = meal.get("user_id")
            meal_date = meal.get("meal_date")
            
            if user_id not in summary:
                summary[user_id] = {
                    "total_calories": 0,
                    "total_protein_g": 0,
                    "total_carbs_g": 0,
                    "total_fat_g": 0,
                    "total_fiber_g": 0
                }
                days_count[user_id] = set()
            
            summary[user_id]["total_calories"] += meal.get("calories", 0)
            summary[user_id]["total_protein_g"] += meal.get("protein_g", 0)
            summary[user_id]["total_carbs_g"] += meal.get("carbs_g", 0)
            summary[user_id]["total_fat_g"] += meal.get("fat_g", 0)
            if meal.get("fiber_g"):
                summary[user_id]["total_fiber_g"] += meal.get("fiber_g", 0)
            
            days_count[user_id].add(meal_date)
        
        # 計算平均值
        for user_id in summary:
            days = len(days_count.get(user_id, set()))
            if days > 0:
                summary[user_id]["avg_daily_calories"] = summary[user_id]["total_calories"] / days
                summary[user_id]["avg_protein_g"] = summary[user_id]["total_protein_g"] / days
                summary[user_id]["avg_carbs_g"] = summary[user_id]["total_carbs_g"] / days
                summary[user_id]["avg_fat_g"] = summary[user_id]["total_fat_g"] / days
                if summary[user_id]["total_fiber_g"] > 0:
                    summary[user_id]["avg_fiber_g"] = summary[user_id]["total_fiber_g"] / days
        
        return summary
