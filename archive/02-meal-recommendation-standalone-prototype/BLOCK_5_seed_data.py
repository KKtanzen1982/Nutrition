"""
BLOCK_5 測試種子資料

灌入架構文檔範例的兩位使用者（小美/小明）+ 一組食譜資料庫，
讓推薦引擎、篩選邏輯、生理期計算、熱量計算都有真實資料可以測試。

`seed_if_empty()` 只在 users 表是空的時候才灌資料，可重複執行。
"""

from datetime import date, timedelta
from sqlalchemy.orm import Session

from BLOCK_5_models import (
    User, DietaryPreference, WeightRecord, ExerciseSession, DailySteps,
    Recipe, RecipeNutrition,
)

USER_A_ID = 1
USER_B_ID = 2


def _seed_users(db: Session) -> None:
    user_a = User(
        id=USER_A_ID,
        name="小美",
        gender="女",
        age=25,
        height_cm=160,
        primary_goal="減脂",
        activity_level="中度",
        menstrual_cycle_length_days=28,
        last_menstrual_date=date.today() - timedelta(days=10),
        menstrual_cycle_irregular=False,
        menstrual_luteal_phase_start_offset_days=14,
        menstrual_luteal_phase_adjustment_calories=150,
        menstrual_premenstrual_adjustment_calories=120,
    )
    user_b = User(
        id=USER_B_ID,
        name="小明",
        gender="男",
        age=28,
        height_cm=175,
        primary_goal="增肌",
        activity_level="高度",
    )
    db.add_all([user_a, user_b])
    db.flush()

    db.add_all([
        DietaryPreference(user_id=USER_A_ID, allergies="堅果", restrictions="無", preferences="喜歡亞洲料理"),
        DietaryPreference(user_id=USER_B_ID, allergies="無", restrictions="無", preferences="無特別偏好"),
    ])

    # 最新體重（TDEE 計算需要）
    db.add_all([
        WeightRecord(user_id=USER_A_ID, date=date.today() - timedelta(days=1), weight_kg=55.0, body_fat_percent=24.0),
        WeightRecord(user_id=USER_B_ID, date=date.today() - timedelta(days=1), weight_kg=75.0, body_fat_percent=15.0),
    ])


def _seed_this_week_activity(db: Session) -> None:
    """
    灌入「上週」（今天往前 7 天）的運動/步數資料，
    對應 db_service 用「計畫開始日前 7 天」當作本週運動量的邏輯。
    """
    today = date.today()

    exercise_rows = []
    steps_rows = []

    # 小美：3 次健身房、2 次瑜珈、每天走路
    gym_days_a = [1, 3, 5]
    yoga_days_a = [2, 6]
    for offset in range(1, 8):
        d = today - timedelta(days=offset)
        if offset in gym_days_a:
            exercise_rows.append(ExerciseSession(user_id=USER_A_ID, date=d, exercise_type="健身房", duration_min=60, intensity="中"))
        if offset in yoga_days_a:
            exercise_rows.append(ExerciseSession(user_id=USER_A_ID, date=d, exercise_type="瑜珈", duration_min=45, intensity="低"))
        steps_rows.append(DailySteps(user_id=USER_A_ID, date=d, steps=6500))

    # 小明：4 次健身房、1 次瑜珈、每天走路
    gym_days_b = [1, 2, 4, 6]
    yoga_days_b = [5]
    for offset in range(1, 8):
        d = today - timedelta(days=offset)
        if offset in gym_days_b:
            exercise_rows.append(ExerciseSession(user_id=USER_B_ID, date=d, exercise_type="健身房", duration_min=75, intensity="高"))
        if offset in yoga_days_b:
            exercise_rows.append(ExerciseSession(user_id=USER_B_ID, date=d, exercise_type="瑜珈", duration_min=30, intensity="低"))
        steps_rows.append(DailySteps(user_id=USER_B_ID, date=d, steps=8500))

    db.add_all(exercise_rows)
    db.add_all(steps_rows)


def _seed_recipes(db: Session) -> None:
    recipes = [
        dict(recipe_name="燕麥粥", category="早餐", base_weight_g=150, cost_level="低",
             is_vegetarian=True, allergen_tags="", ingredient_names_csv="燕麥, 牛奶, 香蕉",
             nutrition=dict(total_calories_kcal=250, protein_g=8, carbs_g=45, fat_g=3, fiber_g=5)),
        dict(recipe_name="蔬菜蛋餅", category="早餐", base_weight_g=180, cost_level="低",
             is_vegetarian=True, allergen_tags="", ingredient_names_csv="雞蛋, 高麗菜, 麵粉",
             nutrition=dict(total_calories_kcal=320, protein_g=14, carbs_g=30, fat_g=15, fiber_g=3)),
        dict(recipe_name="番茄雞肉義大利麵", category="主食", base_weight_g=300, cost_level="低",
             is_vegetarian=False, allergen_tags="", ingredient_names_csv="義大利麵, 番茄, 雞胸肉",
             nutrition=dict(total_calories_kcal=450, protein_g=35, carbs_g=45, fat_g=12, fiber_g=3)),
        dict(recipe_name="牛肉炒飯", category="主食", base_weight_g=400, cost_level="中",
             is_vegetarian=False, allergen_tags="", ingredient_names_csv="白飯, 牛肉, 洋蔥",
             nutrition=dict(total_calories_kcal=650, protein_g=40, carbs_g=70, fat_g=20, fiber_g=2)),
        dict(recipe_name="雞胸肉沙拉", category="肉", base_weight_g=200, cost_level="低",
             is_vegetarian=False, allergen_tags="", ingredient_names_csv="雞胸肉, 生菜, 番茄",
             nutrition=dict(total_calories_kcal=350, protein_g=45, carbs_g=15, fat_g=12, fiber_g=3)),
        dict(recipe_name="蒸魚配糙米飯", category="肉", base_weight_g=350, cost_level="中",
             is_vegetarian=False, allergen_tags="", ingredient_names_csv="鱸魚, 糙米, 薑絲",
             nutrition=dict(total_calories_kcal=420, protein_g=40, carbs_g=48, fat_g=8, fiber_g=4)),
        dict(recipe_name="豬排飯", category="肉", base_weight_g=450, cost_level="中",
             is_vegetarian=False, allergen_tags="", ingredient_names_csv="豬排, 白飯, 高麗菜絲",
             nutrition=dict(total_calories_kcal=750, protein_g=50, carbs_g=65, fat_g=25, fiber_g=2)),
        dict(recipe_name="炒青菜", category="菜", base_weight_g=150, cost_level="低",
             is_vegetarian=True, allergen_tags="", ingredient_names_csv="地瓜葉, 蒜末",
             nutrition=dict(total_calories_kcal=80, protein_g=3, carbs_g=8, fat_g=4, fiber_g=4)),
        dict(recipe_name="涼拌黑木耳", category="菜", base_weight_g=120, cost_level="低",
             is_vegetarian=True, allergen_tags="", ingredient_names_csv="黑木耳, 醬油, 香菜",
             nutrition=dict(total_calories_kcal=60, protein_g=2, carbs_g=10, fat_g=1, fiber_g=5)),
        dict(recipe_name="香蕉", category="下午茶", base_weight_g=120, cost_level="低",
             is_vegetarian=True, allergen_tags="", ingredient_names_csv="香蕉",
             nutrition=dict(total_calories_kcal=107, protein_g=1, carbs_g=27, fat_g=0, fiber_g=1)),
        dict(recipe_name="堅果燕麥棒", category="下午茶", base_weight_g=60, cost_level="中",
             is_vegetarian=True, allergen_tags="堅果", ingredient_names_csv="燕麥, 杏仁, 蜂蜜",
             nutrition=dict(total_calories_kcal=240, protein_g=6, carbs_g=28, fat_g=12, fiber_g=3)),
    ]

    for r in recipes:
        nutrition_data = r.pop("nutrition")
        recipe = Recipe(**r)
        db.add(recipe)
        db.flush()
        db.add(RecipeNutrition(recipe_id=recipe.id, **nutrition_data))


def seed_if_empty(db: Session) -> bool:
    """如果 users 表是空的才灌種子資料。回傳是否有灌資料。"""
    if db.query(User).first() is not None:
        return False

    _seed_users(db)
    _seed_this_week_activity(db)
    _seed_recipes(db)
    db.commit()
    return True
