"""
BLOCK_5: 可切換的 Claude 服務

沒有設定 ANTHROPIC_API_KEY（或明確設定 BLOCK5_FORCE_MOCK_CLAUDE=1）時，
get_claude_service() 會回傳 MockClaudeService，讓整條推薦流程（含資料庫存取）
不需要真的呼叫 Anthropic API 也能端對端測試。

之後只要設定真的 ANTHROPIC_API_KEY，就會自動切換成
BLOCK_5_recommendation_service.ClaudeRecommendationService，不用改任何呼叫端程式碼。

兩種服務都實作同一個介面：
    async def call_claude(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]
`context` 帶著呼叫端已經算好的候選食譜清單等結構化資料，
真正的 Claude 服務會忽略它（只用 prompt 字串），Mock 服務則用它來產生
「看起來合理、且引用真實候選食譜 ID」的假回應，而不必去反解析 prompt 文字。
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

MEAL_TYPES = ["breakfast", "lunch", "afternoon_snack", "dinner"]
DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# meal_type -> 偏好的食譜 category（用來從候選食譜中挑一個看起來合理的選擇）
_MEAL_TYPE_CATEGORY_PREFERENCE = {
    "breakfast": ["早餐"],
    "lunch": ["主食", "肉"],
    "afternoon_snack": ["下午茶"],
    "dinner": ["肉", "主食"],
}


class MockClaudeService:
    """假的 Claude 服務：不呼叫網路，回傳結構正確、引用真實候選食譜的假推薦。"""

    def _pick_recipe(self, recipes: List[Dict[str, Any]], meal_type: str, index: int) -> Optional[Dict[str, Any]]:
        if not recipes:
            return None
        preferred_categories = _MEAL_TYPE_CATEGORY_PREFERENCE.get(meal_type, [])
        for category in preferred_categories:
            candidates = [r for r in recipes if r.get("category") == category]
            if candidates:
                return candidates[index % len(candidates)]
        # 沒有偏好分類的候選食譜時，退回任意食譜（保證一定有回傳值）
        return recipes[index % len(recipes)]

    def _build_meal(self, recipe: Dict[str, Any], meal_type: str, user_label: str, day: str = None) -> Dict[str, Any]:
        meal = {
            "meal_type": meal_type,
            "user": user_label,
            "recipe_id": recipe["id"],
            "recipe_name": recipe.get("name", recipe.get("recipe_name")),
            "serving_weight_g": recipe.get("base_weight_g", 100),
            "calories": recipe.get("calories", 0),
            "protein_g": recipe.get("protein_g", 0),
            "carbs_g": recipe.get("carbs_g", 0),
            "fat_g": recipe.get("fat_g", 0),
            "fiber_g": recipe.get("fiber_g"),
        }
        return meal

    def _day_summary(self, meals: List[Dict[str, Any]]) -> Dict[str, Any]:
        summary = {"user_a": {"total_calories": 0, "total_protein_g": 0, "total_carbs_g": 0, "total_fat_g": 0},
                   "user_b": {"total_calories": 0, "total_protein_g": 0, "total_carbs_g": 0, "total_fat_g": 0}}
        key_map = {"A": "user_a", "B": "user_b"}
        for meal in meals:
            key = key_map.get(meal["user"])
            if not key:
                continue
            summary[key]["total_calories"] += meal.get("calories", 0)
            summary[key]["total_protein_g"] += meal.get("protein_g", 0)
            summary[key]["total_carbs_g"] += meal.get("carbs_g", 0)
            summary[key]["total_fat_g"] += meal.get("fat_g", 0)
        return summary

    def _generate_weekly(self, context: Dict[str, Any]) -> Dict[str, Any]:
        recipes = context.get("candidate_recipes", [])
        week_start_date = context.get("week_start_date")
        week_start_obj = week_start_date
        if isinstance(week_start_obj, str):
            week_start_obj = datetime.strptime(week_start_obj, "%Y-%m-%d").date()
        days = []

        for day_index, day_name in enumerate(DAY_NAMES):
            meals = []
            for user_label in ("A", "B"):
                for meal_index, meal_type in enumerate(MEAL_TYPES):
                    # 下午茶只安排 4/7 天（符合 prompt 規則「每週至少 3-4 次」）
                    if meal_type == "afternoon_snack" and day_index % 2 == 1:
                        continue
                    recipe = self._pick_recipe(recipes, meal_type, day_index + meal_index)
                    if recipe is None:
                        continue
                    meals.append(self._build_meal(recipe, meal_type, user_label))

            meal_date = week_start_obj + timedelta(days=day_index) if week_start_obj else None

            days.append({
                "day": day_name,
                "date": meal_date.isoformat() if meal_date else None,
                "meals": meals,
                "day_summary": self._day_summary(meals),
            })

        return {
            "success": True,
            "recommendation": {
                "week_start_date": week_start_date,
                "analysis_notes": "[Mock] 依據候選食譜清單輪流分配，未實際呼叫 Claude API。",
                "days": days,
            },
        }

    def _generate_single_day(self, context: Dict[str, Any]) -> Dict[str, Any]:
        recipes = context.get("candidate_recipes", [])
        meals_to_regenerate = context.get("meals_to_regenerate", [])
        user_a_id = context.get("user_a_id")
        target_date = context.get("target_date")
        day_name = context.get("day_name")

        meals = []
        for i, slot in enumerate(meals_to_regenerate):
            meal_type = slot.get("meal_type")
            user_id = slot.get("user_id")
            user_label = "A" if user_id == user_a_id else "B"
            recipe = self._pick_recipe(recipes, meal_type, i)
            if recipe is None:
                continue
            meals.append(self._build_meal(recipe, meal_type, user_label))

        return {
            "success": True,
            "recommendation": {
                "day": day_name,
                "date": target_date,
                "meals": meals,
                "day_summary": self._day_summary(meals),
            },
        }

    async def call_claude(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        context = context or {}
        logger.info("[MockClaudeService] 產生假推薦（未呼叫真實 Claude API）")

        if context.get("target_date"):
            return self._generate_single_day(context)
        return self._generate_weekly(context)


def get_claude_service():
    """
    工廠函式：依環境變數決定回傳真的或假的 Claude 服務。

    - 有 ANTHROPIC_API_KEY 且沒有強制 mock -> 真的 ClaudeRecommendationService
    - 其他情況 -> MockClaudeService
    """
    force_mock = os.getenv("BLOCK5_FORCE_MOCK_CLAUDE", "").strip() == "1"
    has_api_key = bool(os.getenv("ANTHROPIC_API_KEY"))

    if has_api_key and not force_mock:
        from BLOCK_5_recommendation_service import ClaudeRecommendationService
        logger.info("使用真實 ClaudeRecommendationService（偵測到 ANTHROPIC_API_KEY）")
        return ClaudeRecommendationService()

    logger.info("使用 MockClaudeService（沒有 ANTHROPIC_API_KEY 或 BLOCK5_FORCE_MOCK_CLAUDE=1）")
    return MockClaudeService()
