"""
BLOCK_5: Claude Prompt 模板 - 推薦邏輯指示
"""

from typing import Dict, Any
import json


def get_main_recommendation_prompt() -> str:
    """
    主推薦 Prompt - 生成完整一週菜單
    """
    return """你是一個專業的營養師和飲食規劃師。根據以下用戶數據和食譜資料庫，為 2 人生成最優化的一週飲食推薦。

【用戶 A 的目標】
- 名字：{user_a_name}
- 性別：{user_a_gender}
- 年齡：{user_a_age} 歲
- 身高：{user_a_height_cm} cm
- 主要目標：{user_a_goal}
- 活動等級：{user_a_activity_level}
- 推薦每日熱量：{user_a_daily_calories} kcal
- 推薦每日蛋白質：{user_a_daily_protein_g}g
- 推薦每日碳水：{user_a_daily_carbs_g}g
- 推薦每日脂肪：{user_a_daily_fat_g}g
- 生理期：{user_a_menstrual_phase}
- 飲食限制：{user_a_restrictions}
- 過敏原：{user_a_allergies}
- 本週運動：{user_a_exercise_summary}

【用戶 B 的目標】
- 名字：{user_b_name}
- 性別：{user_b_gender}
- 年齡：{user_b_age} 歲
- 身高：{user_b_height_cm} cm
- 主要目標：{user_b_goal}
- 活動等級：{user_b_activity_level}
- 推薦每日熱量：{user_b_daily_calories} kcal
- 推薦每日蛋白質：{user_b_daily_protein_g}g
- 推薦每日碳水：{user_b_daily_carbs_g}g
- 推薦每日脂肪：{user_b_daily_fat_g}g
- 生理期：{user_b_menstrual_phase}
- 飲食限制：{user_b_restrictions}
- 過敏原：{user_b_allergies}
- 本週運動：{user_b_exercise_summary}

【推薦規則】
1. 午餐/晚餐結構：1 主食 + 1 青菜 + 1 肉類 + 可選副食（飲料/點心）
2. 早餐：可選但建議每天都有，內容自由
3. 下午茶：每週至少 3-4 次，內容自由
4. 成本平衡：本週推薦的「高」和「中」成本食譜合計 < 「低」成本食譜數量
5. 食材效率：優先推薦已在其他餐出現的食材（減少購物種類、降低浪費）
6. 多樣性：同一食譜 7 天內最多出現 2 次
7. 生理期考量：
   - 月經期（{user_a_menstrual_phase}/{user_b_menstrual_phase}）：推薦含鐵食材（紅肉、菠菜、黑木耳、紅棗）
   - 黃體期：推薦高蛋白食譜，並增加 {user_a_luteal_adjustment}/{user_b_luteal_adjustment} kcal
   - 經前期：推薦含鎂、B6、鈣的食材（香蕉、黑巧克力、杏仁、牛奶）
   - 其他時期：自由推薦
8. 營養平衡：每天的營養素儘量接近目標值（±10% 內為佳）
9. 實用性：推薦的食材應易於購買，烹飪方式應不太複雜

【用戶 A 已預選菜色】
{user_a_preselected_summary}

【用戶 B 已預選菜色】
{user_b_preselected_summary}

【食譜資料庫】
共 {recipe_count} 個食譜可選，以下是簡摘：
{recipe_summary}

【生成指示】
請仔細考慮每個人的目標、生理狀態和飲食限制，生成一份平衡、實用、多樣化的一週菜單。
確保推薦結果符合所有規則，特別是成本平衡和食材效率。

【輸出格式】
請只返回有效的 JSON（不含任何 Markdown 或額外文本），結構必須完全符合以下格式：

{{
  "success": true,
  "recommendation": {{
    "week_start_date": "{week_start_date}",
    "analysis_notes": "簡短的推薦理由和考量點",
    "days": [
      {{
        "day": "Monday",
        "date": "2024-08-05",
        "meals": [
          {{
            "meal_type": "breakfast",
            "user": "A",
            "recipe_id": 5,
            "recipe_name": "燕麥粥",
            "serving_weight_g": 150,
            "calories": 250,
            "protein_g": 8,
            "carbs_g": 45,
            "fat_g": 3,
            "fiber_g": 2
          }},
          {{
            "meal_type": "lunch",
            "user": "A",
            "recipe_id": 12,
            "recipe_name": "番茄雞肉義大利麵",
            "serving_weight_g": 300,
            "calories": 450,
            "protein_g": 35,
            "carbs_g": 45,
            "fat_g": 12,
            "fiber_g": 3
          }},
          {{
            "meal_type": "lunch",
            "user": "B",
            "recipe_id": 18,
            "recipe_name": "牛肉炒飯",
            "serving_weight_g": 400,
            "calories": 650,
            "protein_g": 40,
            "carbs_g": 70,
            "fat_g": 20,
            "fiber_g": 2
          }},
          {{
            "meal_type": "afternoon_snack",
            "user": "A",
            "recipe_id": 101,
            "recipe_name": "香蕉",
            "serving_weight_g": 120,
            "calories": 107,
            "protein_g": 1,
            "carbs_g": 27,
            "fat_g": 0,
            "fiber_g": 1
          }},
          {{
            "meal_type": "dinner",
            "user": "A",
            "recipe_id": 25,
            "recipe_name": "蒸魚配糙米飯",
            "serving_weight_g": 350,
            "calories": 420,
            "protein_g": 40,
            "carbs_g": 48,
            "fat_g": 8,
            "fiber_g": 4
          }},
          {{
            "meal_type": "dinner",
            "user": "B",
            "recipe_id": 30,
            "recipe_name": "豬排飯",
            "serving_weight_g": 450,
            "calories": 750,
            "protein_g": 50,
            "carbs_g": 65,
            "fat_g": 25,
            "fiber_g": 2
          }}
        ],
        "day_summary": {{
          "user_a": {{
            "total_calories": 1227,
            "total_protein_g": 84,
            "total_carbs_g": 165,
            "total_fat_g": 23
          }},
          "user_b": {{
            "total_calories": 1400,
            "total_protein_g": 90,
            "total_carbs_g": 135,
            "total_fat_g": 45
          }}
        }}
      }},
      ... (其餘 6 天，結構同上) ...
    ],
    "weekly_summary": {{
      "total_recipes": 35,
      "unique_recipes": 20,
      "cost_distribution": {{
        "low": 15,
        "medium": 10,
        "high": 10
      }},
      "user_a_weekly_summary": {{
        "total_calories": 8400,
        "avg_daily_calories": 1200,
        "avg_protein_g": 120,
        "avg_carbs_g": 150,
        "avg_fat_g": 30
      }},
      "user_b_weekly_summary": {{
        "total_calories": 16100,
        "avg_daily_calories": 2300,
        "avg_protein_g": 160,
        "avg_carbs_g": 200,
        "avg_fat_g": 60
      }}
    }},
    "shopping_ingredients": [
      {{
        "ingredient_id": 1,
        "ingredient_name": "雞胸肉",
        "total_quantity_g": 800,
        "cost_level": "低",
        "reason": "多個菜色需要"
      }},
      ... (其他食材) ...
    ]
  }}
}}

⚠️ 重要提醒：
- 必須返回有效的 JSON，沒有任何 Markdown 標記或額外文本
- 所有菜色都必須來自提供的食譜資料庫
- 避免重複推薦同一個食譜超過 2 次（同一人或不同人皆然）
- 如果預選菜色衝突（例如某人某餐已預選 A，但推薦卻推薦 B），必須優先尊重預選菜色
"""


def get_single_day_regeneration_prompt() -> str:
    """
    單日重推 Prompt - 重新生成某一天的菜單，保留其他 6 天
    """
    return """你是一個專業的營養師。用戶要求重新推薦某一天的菜單，同時保留其他已確認的菜色。

【任務】
重新生成 {target_date} ({day_name}) 的菜色，以下菜色固定不變：
{fixed_meals_summary}

其他 6 天已推薦的菜色：
{other_days_summary}

【用戶 A 的目標】
- 每日熱量目標：{user_a_daily_calories} kcal
- 推薦蛋白質：{user_a_daily_protein_g}g
- 推薦碳水：{user_a_daily_carbs_g}g
- 推薦脂肪：{user_a_daily_fat_g}g
- 生理期：{user_a_menstrual_phase}
- 飲食限制：{user_a_restrictions}
- 過敏原：{user_a_allergies}

【用戶 B 的目標】
- 每日熱量目標：{user_b_daily_calories} kcal
- 推薦蛋白質：{user_b_daily_protein_g}g
- 推薦碳水：{user_b_daily_carbs_g}g
- 推薦脂肪：{user_b_daily_fat_g}g
- 生理期：{user_b_menstrual_phase}
- 飲食限制：{user_b_restrictions}
- 過敏原：{user_b_allergies}

【食譜資料庫】
{recipe_summary}

【輸出格式】
請只返回有效的 JSON，結構如下（只需要 {target_date} 這一天的菜色）：

{{
  "success": true,
  "recommendation": {{
    "day": "{day_name}",
    "date": "{target_date}",
    "meals": [
      {{
        "meal_type": "breakfast",
        "user": "A",
        "recipe_id": 5,
        "recipe_name": "...",
        "serving_weight_g": 150,
        "calories": 250,
        "protein_g": 8,
        "carbs_g": 45,
        "fat_g": 3
      }},
      ... (其他餐次) ...
    ],
    "day_summary": {{
      "user_a": {{
        "total_calories": 1200,
        "total_protein_g": 120,
        "total_carbs_g": 150,
        "total_fat_g": 30
      }},
      "user_b": {{
        "total_calories": 2300,
        "total_protein_g": 160,
        "total_carbs_g": 200,
        "total_fat_g": 60
      }}
    }}
  }}
}}
"""


def build_claude_prompt(
    recommendation_data: Dict[str, Any],
    target_date: str = None,
    single_day_context: Dict[str, Any] = None,
) -> str:
    """
    根據打包的推薦數據動態構建 Claude prompt

    Args:
        recommendation_data: 包含用戶、運動、食譜等數據的字典
        target_date: 如果指定，則生成單日重推 prompt；否則生成主推薦 prompt
        single_day_context: 單日重推才需要，{day_name, fixed_meals_summary, other_days_summary}
            （來自 BLOCK_5_adjustment_service.MealAdjustmentService.prepare_for_day_regeneration）

    Returns:
        構建好的 prompt 字串
    """

    if target_date:
        # 單日重推 prompt
        prompt_template = get_single_day_regeneration_prompt()
    else:
        # 主推薦 prompt
        prompt_template = get_main_recommendation_prompt()
    
    # 準備替換值
    user_a = recommendation_data["user_a"]
    user_b = recommendation_data["user_b"]
    week_start = recommendation_data["week_start_date"]
    
    # 運動摘要
    exercise_a = user_a.get("this_week_exercise", {})
    exercise_summary_a = f"健身房 {exercise_a.get('gym_sessions', 0)} 次，" \
                         f"步數 {exercise_a.get('walking_steps_total', 0)} 步，" \
                         f"瑜珈 {exercise_a.get('yoga_sessions', 0)} 次"
    
    exercise_b = user_b.get("this_week_exercise", {})
    exercise_summary_b = f"健身房 {exercise_b.get('gym_sessions', 0)} 次，" \
                         f"步數 {exercise_b.get('walking_steps_total', 0)} 步，" \
                         f"瑜珈 {exercise_b.get('yoga_sessions', 0)} 次"
    
    # 預選菜色摘要
    preselected_a = recommendation_data.get("user_a_preselected_meals", [])
    preselected_summary_a = "\n".join([
        f"  - {meal['day']} {meal['meal_type']}: {meal.get('recipe_name', 'ID ' + str(meal['recipe_id']))}"
        for meal in preselected_a
    ]) if preselected_a else "  無"
    
    preselected_b = recommendation_data.get("user_b_preselected_meals", [])
    preselected_summary_b = "\n".join([
        f"  - {meal['day']} {meal['meal_type']}: {meal.get('recipe_name', 'ID ' + str(meal['recipe_id']))}"
        for meal in preselected_b
    ]) if preselected_b else "  無"
    
    # 食譜摘要
    recipes = recommendation_data.get("recipe_database", [])
    recipe_summary = f"共 {len(recipes)} 個食譜。主要類別：\n"
    categories = {}
    for recipe in recipes:
        cat = recipe.get("category", "未分類")
        categories[cat] = categories.get(cat, 0) + 1
    recipe_summary += "\n".join([f"  - {cat}: {count} 個" for cat, count in categories.items()])
    
    # 替換所有佔位符
    replace_map = {
        "user_a_name": user_a.get("name", "A"),
        "user_a_gender": user_a.get("gender", "未指定"),
        "user_a_age": user_a.get("age", 0),
        "user_a_height_cm": user_a.get("height_cm", 0),
        "user_a_goal": user_a.get("primary_goal", "維持"),
        "user_a_activity_level": user_a.get("activity_level", "中度"),
        "user_a_daily_calories": user_a.get("daily_calories_target", 0),
        "user_a_daily_protein_g": user_a.get("daily_protein_g", 0),
        "user_a_daily_carbs_g": user_a.get("daily_carbs_g", 0),
        "user_a_daily_fat_g": user_a.get("daily_fat_g", 0),
        "user_a_menstrual_phase": user_a.get("menstrual_phase", "無"),
        "user_a_restrictions": user_a.get("restrictions", "無"),
        "user_a_allergies": user_a.get("allergies", "無"),
        "user_a_exercise_summary": exercise_summary_a,
        "user_a_preselected_summary": preselected_summary_a,
        "user_a_luteal_adjustment": user_a.get("menstrual_luteal_phase_adjustment_calories", 150),
        
        "user_b_name": user_b.get("name", "B"),
        "user_b_gender": user_b.get("gender", "未指定"),
        "user_b_age": user_b.get("age", 0),
        "user_b_height_cm": user_b.get("height_cm", 0),
        "user_b_goal": user_b.get("primary_goal", "維持"),
        "user_b_activity_level": user_b.get("activity_level", "中度"),
        "user_b_daily_calories": user_b.get("daily_calories_target", 0),
        "user_b_daily_protein_g": user_b.get("daily_protein_g", 0),
        "user_b_daily_carbs_g": user_b.get("daily_carbs_g", 0),
        "user_b_daily_fat_g": user_b.get("daily_fat_g", 0),
        "user_b_menstrual_phase": user_b.get("menstrual_phase", "無"),
        "user_b_restrictions": user_b.get("restrictions", "無"),
        "user_b_allergies": user_b.get("allergies", "無"),
        "user_b_exercise_summary": exercise_summary_b,
        "user_b_preselected_summary": preselected_summary_b,
        "user_b_luteal_adjustment": user_b.get("menstrual_luteal_phase_adjustment_calories", 150),
        
        "week_start_date": week_start,
        "recipe_count": len(recipes),
        "recipe_summary": recipe_summary,
    }

    if target_date:
        single_day_context = single_day_context or {}
        replace_map.update({
            "target_date": target_date,
            "day_name": single_day_context.get("day_name", ""),
            "fixed_meals_summary": single_day_context.get("fixed_meals_summary", "  無"),
            "other_days_summary": single_day_context.get("other_days_summary", "  無"),
        })

    # 執行替換
    result = prompt_template
    for key, value in replace_map.items():
        result = result.replace("{" + key + "}", str(value))
    
    return result
