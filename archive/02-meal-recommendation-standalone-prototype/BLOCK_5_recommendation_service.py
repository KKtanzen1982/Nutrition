"""
BLOCK_5: 核心推薦服務
- 熱量計算（TDEE、生理期調整）
- 食譜篩選
- Claude API 調用
- 推薦結果解析和儲存
"""

import os
import json
import logging
from datetime import date, timedelta, datetime
from typing import Dict, List, Optional, Any, Tuple
import asyncio
import anthropic

logger = logging.getLogger(__name__)


# ==================== 熱量計算器 ====================

class CalorieCalculator:
    """熱量計算服務"""
    
    # 活動等級係數
    HARRIS_BENEDICT_COEFFICIENTS = {
        "久坐": 1.2,
        "輕度": 1.375,
        "中度": 1.55,
        "高度": 1.725
    }
    
    MIFFLIN_ST_JEOR_COEFFICIENTS = {
        "久坐": 1.2,
        "輕度": 1.375,
        "中度": 1.55,
        "高度": 1.725
    }
    
    @staticmethod
    def calculate_bmr(user_data: Dict[str, Any]) -> float:
        """
        計算基礎代謝率 (BMR)
        
        Args:
            user_data: 包含 gender, age, weight_kg, height_cm, calorie_calculation_method
        
        Returns:
            BMR (kcal/day)
        """
        gender = user_data.get("gender", "女")
        age = user_data.get("age", 30)
        height_cm = user_data.get("height_cm", 160)
        weight_kg = user_data.get("weight_kg", 60)  # 需要從 weight_records 取最新值
        method = user_data.get("calorie_calculation_method", "harris_benedict")
        
        if method == "harris_benedict":
            if gender == "女":
                bmr = 655 + (9.6 * weight_kg) + (1.8 * height_cm) - (4.7 * age)
            else:  # 男
                bmr = 88 + (13.4 * weight_kg) + (4.8 * height_cm) - (5.7 * age)
        elif method == "mifflin_st_jeor":
            if gender == "女":
                bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 161
            else:
                bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5
        else:
            # 預設使用 Harris-Benedict
            if gender == "女":
                bmr = 655 + (9.6 * weight_kg) + (1.8 * height_cm) - (4.7 * age)
            else:
                bmr = 88 + (13.4 * weight_kg) + (4.8 * height_cm) - (5.7 * age)
        
        return bmr
    
    @staticmethod
    def calculate_tdee(user_data: Dict[str, Any], exercise_data: Dict[str, int]) -> float:
        """
        計算每日總能量消耗 (TDEE)
        
        Args:
            user_data: 用戶基本信息
            exercise_data: {gym_sessions, walking_steps_total, yoga_sessions}
        
        Returns:
            TDEE (kcal/day)
        """
        bmr = CalorieCalculator.calculate_bmr(user_data)
        
        # 活動等級係數
        activity_level = user_data.get("activity_level", "中度")
        method = user_data.get("calorie_calculation_method", "harris_benedict")
        
        if method == "harris_benedict":
            activity_coeff = CalorieCalculator.HARRIS_BENEDICT_COEFFICIENTS.get(activity_level, 1.55)
        else:
            activity_coeff = CalorieCalculator.MIFFLIN_ST_JEOR_COEFFICIENTS.get(activity_level, 1.55)
        
        tdee = bmr * activity_coeff
        
        # 根據本週運動調整（額外消耗）
        gym_sessions = exercise_data.get("gym_sessions", 0)
        yoga_sessions = exercise_data.get("yoga_sessions", 0)
        walking_steps = exercise_data.get("walking_steps_total", 0)
        
        # 健身房：每次約 300-400 kcal（依強度）
        # 瑜珈：每次約 150-200 kcal
        # 步數：約每 1000 步 50 kcal
        
        extra_calories = (gym_sessions * 75) + (yoga_sessions * 50) + (walking_steps / 1000 * 10)
        
        return tdee + extra_calories
    
    @staticmethod
    def adjust_for_goal(tdee: float, goal: str) -> float:
        """
        根據目標調整熱量
        
        Args:
            tdee: 每日總能量消耗
            goal: '減脂' / '增肌' / '維持'
        
        Returns:
            調整後的熱量目標
        """
        if goal == "減脂":
            adjustment = -350  # 每天減 350 kcal，約一週減 0.5 kg
        elif goal == "增肌":
            adjustment = +250  # 每天增加 250 kcal
        else:  # 維持
            adjustment = 0
        
        adjusted = tdee + adjustment
        # 最低 1200 kcal（避免過度限制）
        return max(adjusted, 1200)
    
    @staticmethod
    def adjust_for_menstrual_phase(
        calories: float,
        menstrual_phase: str,
        luteal_adjustment: int = 150,
        premenstrual_adjustment: int = 120
    ) -> float:
        """
        根據生理期調整熱量
        
        Args:
            calories: 基礎熱量
            menstrual_phase: 生理期階段
            luteal_adjustment: 黃體期調整熱量（預設 +150）
            premenstrual_adjustment: 經前期調整熱量（預設 +120）
        
        Returns:
            調整後的熱量
        """
        if menstrual_phase == "黃體期":
            return calories + luteal_adjustment
        elif menstrual_phase == "經前期":
            return calories + premenstrual_adjustment
        # 月經期、卵泡期、排卵期：無特殊調整
        return calories


# ==================== 食譜篩選器 ====================

class RecipeFilter:
    """食譜篩選服務"""
    
    @staticmethod
    def filter_candidate_recipes(
        user_a: Dict[str, Any],
        user_b: Dict[str, Any],
        all_recipes: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        根據過敏、飲食限制篩選候選食譜
        
        Args:
            user_a: 用戶 A 的數據
            user_b: 用戶 B 的數據
            all_recipes: 完整食譜資料庫
        
        Returns:
            篩選過的食譜列表
        """
        # 收集過敏和限制
        def parse_csv(text: str) -> set:
            """解析逗號分隔的字串"""
            if not text or text == "無":
                return set()
            return set(item.strip() for item in text.split(",") if item.strip())
        
        allergens_a = parse_csv(user_a.get("allergies", ""))
        allergens_b = parse_csv(user_b.get("allergies", ""))
        all_allergens = allergens_a | allergens_b
        
        restrictions_a = parse_csv(user_a.get("restrictions", ""))
        restrictions_b = parse_csv(user_b.get("restrictions", ""))
        
        candidates = []
        
        for recipe in all_recipes:
            # 檢查過敏
            recipe_allergens = set(recipe.get("contains_allergens", []))
            if all_allergens & recipe_allergens:
                continue
            
            # 檢查素食限制
            if ("素食" in restrictions_a or "素食" in restrictions_b):
                if not recipe.get("is_vegetarian", False):
                    continue
            
            candidates.append(recipe)
        
        logger.info(f"食譜篩選完成：{len(all_recipes)} → {len(candidates)} 個候選")
        return candidates


# ==================== 數據打包器 ====================

class RecommendationDataPacker:
    """將用戶數據打包成 Claude 可用的格式"""
    
    @staticmethod
    def calculate_nutrient_targets(user_data: Dict[str, Any], daily_calories: float) -> Dict[str, float]:
        """
        計算用戶的營養素目標
        
        Args:
            user_data: 用戶數據
            daily_calories: 每日熱量目標
        
        Returns:
            {protein_g, carbs_g, fat_g}
        """
        goal = user_data.get("primary_goal", "維持")
        weight_kg = user_data.get("weight_kg", 60)
        
        # 根據目標設定蛋白質目標
        if goal == "減脂":
            protein_per_kg = 1.8  # 減脂時提高蛋白質，防止肌肉流失
        elif goal == "增肌":
            protein_per_kg = 2.2  # 增肌需要更多蛋白質
        else:
            protein_per_kg = 1.6  # 維持
        
        protein_g = weight_kg * protein_per_kg
        
        # 脂肪目標：每日熱量的 25-30%
        fat_percent = 0.27
        fat_g = (daily_calories * fat_percent) / 9  # 脂肪每克 9 kcal
        
        # 碳水：剩餘熱量
        carbs_calories = daily_calories - (protein_g * 4) - (fat_g * 9)
        carbs_g = carbs_calories / 4  # 碳水每克 4 kcal
        
        return {
            "protein_g": round(protein_g, 1),
            "carbs_g": round(carbs_g, 1),
            "fat_g": round(fat_g, 1)
        }
    
    @staticmethod
    def pack_for_claude(
        user_a: Dict[str, Any],
        user_b: Dict[str, Any],
        week_start_date: date,
        exercise_data_a: Dict[str, int],
        exercise_data_b: Dict[str, int],
        preselected_meals_a: List[Dict[str, Any]],
        preselected_meals_b: List[Dict[str, Any]],
        candidate_recipes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        打包推薦所需的所有數據為 JSON
        
        Args:
            user_a: 用戶 A 的完整數據（包括 weight_kg）
            user_b: 用戶 B 的完整數據
            week_start_date: 週開始日期
            exercise_data_a: {gym_sessions, walking_steps_total, yoga_sessions}
            exercise_data_b: 同上
            preselected_meals_a: [{day, meal_type, recipe_id}, ...]
            preselected_meals_b: 同上
            candidate_recipes: 篩選過的食譜列表
        
        Returns:
            可直接發送給 Claude 的 JSON 字典
        """
        
        # 計算熱量目標
        tdee_a = CalorieCalculator.calculate_tdee(user_a, exercise_data_a)
        daily_calories_a = CalorieCalculator.adjust_for_goal(tdee_a, user_a.get("primary_goal", "維持"))
        
        tdee_b = CalorieCalculator.calculate_tdee(user_b, exercise_data_b)
        daily_calories_b = CalorieCalculator.adjust_for_goal(tdee_b, user_b.get("primary_goal", "維持"))
        
        # 計算生理期和調整
        menstrual_phase_a = calculate_menstrual_phase(user_a, week_start_date)
        daily_calories_a = CalorieCalculator.adjust_for_menstrual_phase(
            daily_calories_a,
            menstrual_phase_a,
            user_a.get("menstrual_luteal_phase_adjustment_calories", 150),
            user_a.get("menstrual_premenstrual_adjustment_calories", 120)
        )
        
        menstrual_phase_b = calculate_menstrual_phase(user_b, week_start_date)
        daily_calories_b = CalorieCalculator.adjust_for_menstrual_phase(
            daily_calories_b,
            menstrual_phase_b,
            user_b.get("menstrual_luteal_phase_adjustment_calories", 150),
            user_b.get("menstrual_premenstrual_adjustment_calories", 120)
        )
        
        # 計算營養目標
        nutrients_a = RecommendationDataPacker.calculate_nutrient_targets(user_a, daily_calories_a)
        nutrients_b = RecommendationDataPacker.calculate_nutrient_targets(user_b, daily_calories_b)
        
        return {
            "analysis_date": date.today().isoformat(),
            "week_start_date": week_start_date.isoformat(),
            
            "user_a": {
                "id": user_a.get("id"),
                "name": user_a.get("name", "A"),
                "gender": user_a.get("gender", "女"),
                "age": user_a.get("age", 30),
                "height_cm": user_a.get("height_cm", 160),
                "weight_kg": user_a.get("weight_kg", 60),
                "primary_goal": user_a.get("primary_goal", "維持"),
                "activity_level": user_a.get("activity_level", "中度"),
                "menstrual_phase": menstrual_phase_a,
                "allergies": user_a.get("allergies", "無"),
                "restrictions": user_a.get("restrictions", "無"),
                "daily_calories_target": int(daily_calories_a),
                "daily_protein_g": int(nutrients_a["protein_g"]),
                "daily_carbs_g": int(nutrients_a["carbs_g"]),
                "daily_fat_g": int(nutrients_a["fat_g"]),
                "menstrual_luteal_phase_adjustment_calories": user_a.get("menstrual_luteal_phase_adjustment_calories", 150),
                "this_week_exercise": exercise_data_a
            },
            
            "user_b": {
                "id": user_b.get("id"),
                "name": user_b.get("name", "B"),
                "gender": user_b.get("gender", "男"),
                "age": user_b.get("age", 30),
                "height_cm": user_b.get("height_cm", 175),
                "weight_kg": user_b.get("weight_kg", 75),
                "primary_goal": user_b.get("primary_goal", "維持"),
                "activity_level": user_b.get("activity_level", "中度"),
                "menstrual_phase": menstrual_phase_b,
                "allergies": user_b.get("allergies", "無"),
                "restrictions": user_b.get("restrictions", "無"),
                "daily_calories_target": int(daily_calories_b),
                "daily_protein_g": int(nutrients_b["protein_g"]),
                "daily_carbs_g": int(nutrients_b["carbs_g"]),
                "daily_fat_g": int(nutrients_b["fat_g"]),
                "menstrual_luteal_phase_adjustment_calories": user_b.get("menstrual_luteal_phase_adjustment_calories", 150),
                "this_week_exercise": exercise_data_b
            },
            
            "user_a_preselected_meals": preselected_meals_a,
            "user_b_preselected_meals": preselected_meals_b,
            
            "recipe_database": candidate_recipes
        }


# ==================== 生理期計算 ====================

def calculate_menstrual_phase(user_data: Dict[str, Any], target_date: date) -> str:
    """
    根據用戶的月經週期計算某一日期是哪個生理期
    
    週期階段劃分（假設 28 天週期）：
    - 第 1-5 天：月經期
    - 第 6-12 天：卵泡期
    - 第 13-14 天：排卵期
    - 第 15-28 天：黃體期
    - 最後 3-4 天：經前期
    
    用戶可自訂黃體期開始日期（menstrual_luteal_phase_start_offset_days）
    
    Args:
        user_data: 用戶數據（包括 gender, last_menstrual_date, cycle_length）
        target_date: 要計算的日期
    
    Returns:
        生理期階段字串
    """
    gender = user_data.get("gender", "女")
    
    # 非女性或沒有月經數據，返回 "無"
    if gender != "女":
        return "無"
    
    last_menstrual_date = user_data.get("last_menstrual_date")
    if not last_menstrual_date:
        return "無"
    
    # 轉換為 date 物件
    if isinstance(last_menstrual_date, str):
        from datetime import datetime
        last_menstrual_date = datetime.strptime(last_menstrual_date, "%Y-%m-%d").date()
    
    cycle_length = user_data.get("menstrual_cycle_length_days", 28)
    
    # 計算距離月經開始的天數
    days_since_start = (target_date - last_menstrual_date).days % cycle_length
    
    # 月經期：第 1-5 天（0-4）
    if days_since_start < 5:
        return "月經期"
    
    # 黃體期開始的偏移日期（可由用戶修改，預設 14）
    luteal_start = user_data.get("menstrual_luteal_phase_start_offset_days", 14)
    
    # 經前期：最後 3-4 天
    premenstrual_start = cycle_length - 3
    
    if days_since_start >= premenstrual_start:
        return "經前期"
    elif days_since_start >= luteal_start:
        return "黃體期"
    elif days_since_start >= 12:
        return "排卵期"
    else:
        return "卵泡期"


# ==================== Claude API 服務 ====================

class ClaudeRecommendationService:
    """Claude API 調用服務"""
    
    def __init__(self, api_key: str = None):
        """初始化 Claude 客戶端"""
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.client = anthropic.Anthropic(api_key=self.api_key)
    
    async def call_claude(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        非同步調用 Claude API

        Args:
            prompt: 完整的 prompt
            context: 未使用（僅為了與 MockClaudeService 介面一致，方便呼叫端無腦切換）

        Returns:
            Claude 的回應（已解析為 JSON）
        """
        try:
            logger.info("開始調用 Claude API...")
            
            # 使用 Sonnet 模型
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # 提取回應內容
            response_text = message.content[0].text
            logger.info(f"Claude 回應長度：{len(response_text)} 字符")
            
            # 解析 JSON
            try:
                # 嘗試直接解析
                claude_data = json.loads(response_text)
            except json.JSONDecodeError:
                # 如果有 Markdown 標記，嘗試提取
                if "```json" in response_text:
                    json_start = response_text.index("```json") + 7
                    json_end = response_text.index("```", json_start)
                    json_str = response_text[json_start:json_end].strip()
                    claude_data = json.loads(json_str)
                elif "```" in response_text:
                    json_start = response_text.index("```") + 3
                    json_end = response_text.index("```", json_start)
                    json_str = response_text[json_start:json_end].strip()
                    claude_data = json.loads(json_str)
                else:
                    raise ValueError("無法從回應中提取 JSON")
            
            if not claude_data.get("success"):
                raise ValueError(f"Claude 推薦失敗：{claude_data.get('error', '未知錯誤')}")
            
            logger.info("Claude 推薦成功")
            return claude_data
        
        except Exception as e:
            logger.error(f"Claude API 調用失敗：{str(e)}")
            raise


# ==================== 整合函數 ====================

async def generate_meal_plan_recommendation(
    user_a: Dict[str, Any],
    user_b: Dict[str, Any],
    week_start_date: date,
    exercise_data_a: Dict[str, int],
    exercise_data_b: Dict[str, int],
    preselected_meals_a: List[Dict[str, Any]],
    preselected_meals_b: List[Dict[str, Any]],
    all_recipes: List[Dict[str, Any]],
    prompt_builder: Any,
    claude_service: Any = None
) -> Dict[str, Any]:
    """
    完整的推薦流程

    1. 篩選食譜
    2. 打包數據
    3. 構建 Prompt
    4. 調用 Claude
    5. 解析回應

    Args:
        user_a, user_b: 用戶完整數據
        week_start_date: 週開始日期
        exercise_data_a, exercise_data_b: 運動數據
        preselected_meals_a, preselected_meals_b: 預選菜色
        all_recipes: 完整食譜資料庫
        prompt_builder: Prompt 構建器（來自 BLOCK_5_prompts）
        claude_service: 實作 call_claude(prompt, context) 的服務。
            未提供時預設建立真正的 ClaudeRecommendationService；
            測試時可傳入 BLOCK_5_claude_client.MockClaudeService()。

    Returns:
        推薦結果（Claude 回應）
    """

    try:
        # 1. 篩選食譜
        logger.info("開始篩選食譜...")
        candidate_recipes = RecipeFilter.filter_candidate_recipes(
            user_a, user_b, all_recipes
        )

        # 2. 打包數據
        logger.info("打包推薦數據...")
        recommendation_data = RecommendationDataPacker.pack_for_claude(
            user_a, user_b,
            week_start_date,
            exercise_data_a, exercise_data_b,
            preselected_meals_a, preselected_meals_b,
            candidate_recipes
        )

        # 3. 構建 Prompt
        logger.info("構建 Claude Prompt...")
        prompt = prompt_builder.build_claude_prompt(recommendation_data)

        # 4. 調用 Claude
        logger.info("調用 Claude API...")
        service = claude_service if claude_service is not None else ClaudeRecommendationService()
        claude_response = await service.call_claude(prompt, context={
            "candidate_recipes": candidate_recipes,
            "week_start_date": recommendation_data["week_start_date"],
            "user_a_id": user_a.get("id"),
            "user_b_id": user_b.get("id"),
        })

        logger.info("推薦完成")
        return claude_response

    except Exception as e:
        logger.error(f"推薦流程失敗：{str(e)}")
        raise
