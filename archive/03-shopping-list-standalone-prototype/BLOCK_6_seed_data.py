"""
BLOCK_6 測試種子資料

灌入：
- 兩位使用者（小美/小明，沿用 BLOCK_5 的 USER_A_ID=1 / USER_B_ID=2 慣例）
- 4 個購買地點（表 6a）
- 11 種食材（食材庫唯讀參照簡化版）+ 2 筆庫存（其中 1 筆刻意設成快見底，示範補貨警告）
- 2 筆食材地點偏好（表 6b，示範「優先度」邏輯）
- 4 道食譜 + 食譜食材明細（唯讀參照簡化版）
- 1 個已確認的週計畫（weekly_meal_plan + daily_meal_detail，7 天 x 2 人 x 早/午/晚）

`seed_if_empty()` 只在 users 表是空的時候才灌資料，可重複執行。
灌完資料後即可呼叫 BLOCK_6_db_service.generate_shopping_list_for_plan(db, plan_id=1)
或直接打 POST /meal-plans/1/confirm 端對端測試。
"""

from datetime import date, timedelta
from sqlalchemy.orm import Session

from BLOCK_6_models import (
    User,
    PurchaseLocation,
    IngredientLibrary,
    IngredientStock,
    IngredientLocationPreference,
    Recipe,
    RecipeIngredient,
    WeeklyMealPlan,
    DailyMealDetail,
)

USER_A_ID = 1
USER_B_ID = 2
PLAN_ID = 1


def _seed_users(db: Session) -> None:
    db.add_all([
        User(id=USER_A_ID, name="小美"),
        User(id=USER_B_ID, name="小明"),
    ])


def _seed_purchase_locations(db: Session) -> None:
    db.add_all([
        PurchaseLocation(id=1, location_name="全聯福利中心", description="日常生鮮/乾貨", priority_order=1),
        PurchaseLocation(id=2, location_name="傳統市場", description="新鮮蔬菜/肉類", priority_order=2),
        PurchaseLocation(id=3, location_name="家樂福", description="大宗採購/特價品", priority_order=3),
        PurchaseLocation(id=4, location_name="網路商店", description="不易取得的特殊食材", priority_order=4),
    ])
    db.flush()


def _seed_ingredients(db: Session) -> None:
    ingredients = [
        dict(id=1, ingredient_name="燕麥", category="穀物", unit="g", needs_stock_tracking=True,
             preferred_purchase_location="全聯福利中心"),
        dict(id=2, ingredient_name="牛奶", category="乳製品", unit="ml", needs_stock_tracking=False,
             preferred_purchase_location="全聯福利中心"),
        dict(id=3, ingredient_name="香蕉", category="其他", unit="g", needs_stock_tracking=False,
             preferred_purchase_location="傳統市場"),
        dict(id=4, ingredient_name="義大利麵", category="穀物", unit="g", needs_stock_tracking=True,
             preferred_purchase_location="全聯福利中心"),
        dict(id=5, ingredient_name="番茄", category="蔬菜", unit="g", needs_stock_tracking=False,
             preferred_purchase_location="傳統市場"),
        dict(id=6, ingredient_name="雞胸肉", category="肉類", unit="g", needs_stock_tracking=False,
             preferred_purchase_location="傳統市場"),
        dict(id=7, ingredient_name="白飯", category="穀物", unit="g", needs_stock_tracking=True,
             preferred_purchase_location="全聯福利中心"),
        dict(id=8, ingredient_name="牛肉", category="肉類", unit="g", needs_stock_tracking=False,
             preferred_purchase_location="家樂福"),
        dict(id=9, ingredient_name="洋蔥", category="蔬菜", unit="g", needs_stock_tracking=False,
             preferred_purchase_location="傳統市場"),
        dict(id=10, ingredient_name="地瓜葉", category="蔬菜", unit="g", needs_stock_tracking=False,
             preferred_purchase_location="傳統市場"),
        dict(id=11, ingredient_name="蒜末", category="調味料", unit="g", needs_stock_tracking=True,
             preferred_purchase_location="全聯福利中心"),
    ]
    db.add_all(IngredientLibrary(**i) for i in ingredients)
    db.flush()

    # 庫存：白飯庫存快見底（示範補貨警告），蒜末庫存充足
    db.add_all([
        IngredientStock(ingredient_id=7, current_quantity_g=300, min_threshold_g=500),
        IngredientStock(ingredient_id=11, current_quantity_g=1000, min_threshold_g=50),
    ])

    # 食材地點偏好（表 6b）：番茄優先傳統市場、次選全聯；牛肉優先家樂福
    db.add_all([
        IngredientLocationPreference(ingredient_id=5, preferred_location_id=2, priority=1, notes="傳統市場比較新鮮"),
        IngredientLocationPreference(ingredient_id=5, preferred_location_id=1, priority=2),
        IngredientLocationPreference(ingredient_id=8, preferred_location_id=3, priority=1, notes="家樂福常有特價"),
    ])


def _seed_recipes(db: Session) -> None:
    recipes = [
        dict(id=1, recipe_name="燕麥粥", base_weight_g=150, cost_level="低",
             ingredients=[(1, 100), (2, 200), (3, 50)]),  # 燕麥, 牛奶, 香蕉
        dict(id=2, recipe_name="番茄雞肉義大利麵", base_weight_g=300, cost_level="低",
             ingredients=[(4, 120), (5, 80), (6, 100)]),  # 義大利麵, 番茄, 雞胸肉
        dict(id=3, recipe_name="牛肉炒飯", base_weight_g=400, cost_level="中",
             ingredients=[(7, 250), (8, 100), (9, 50)]),  # 白飯, 牛肉, 洋蔥
        dict(id=4, recipe_name="炒青菜", base_weight_g=150, cost_level="低",
             ingredients=[(10, 140), (11, 10)]),  # 地瓜葉, 蒜末
    ]
    for r in recipes:
        ingredient_pairs = r.pop("ingredients")
        recipe = Recipe(**r)
        db.add(recipe)
        db.flush()
        db.add_all(
            RecipeIngredient(recipe_id=recipe.id, ingredient_id=ing_id, quantity_g=qty)
            for ing_id, qty in ingredient_pairs
        )


def _next_monday() -> date:
    today = date.today()
    return today + timedelta(days=(7 - today.weekday()) % 7 or 7)


def _seed_weekly_meal_plan(db: Session) -> None:
    """1 個已確認的週計畫：7 天 x 2 人，早餐 1 道、午餐 2 道（主食+菜）、晚餐 2 道（主食+菜）"""
    plan = WeeklyMealPlan(
        id=PLAN_ID,
        plan_date=_next_monday(),
        user_id_a=USER_A_ID,
        user_id_b=USER_B_ID,
        plan_status="待微調",  # 尚未呼叫 /confirm，保留讓 API 示範狀態轉換
    )
    db.add(plan)
    db.flush()

    meal_rows = []
    for day_offset in range(7):
        meal_date = plan.plan_date + timedelta(days=day_offset)
        for user_id, serving_scale in ((USER_A_ID, 0.9), (USER_B_ID, 1.2)):
            meal_rows.append(DailyMealDetail(
                meal_plan_id=PLAN_ID, meal_date=meal_date, meal_type="breakfast",
                recipe_id=1, assigned_user_id=user_id, serving_weight_g=round(150 * serving_scale),
            ))
            meal_rows.append(DailyMealDetail(
                meal_plan_id=PLAN_ID, meal_date=meal_date, meal_type="lunch",
                recipe_id=2, assigned_user_id=user_id, serving_weight_g=round(300 * serving_scale),
            ))
            meal_rows.append(DailyMealDetail(
                meal_plan_id=PLAN_ID, meal_date=meal_date, meal_type="lunch",
                recipe_id=4, assigned_user_id=user_id, serving_weight_g=round(150 * serving_scale),
            ))
            meal_rows.append(DailyMealDetail(
                meal_plan_id=PLAN_ID, meal_date=meal_date, meal_type="dinner",
                recipe_id=3, assigned_user_id=user_id, serving_weight_g=round(400 * serving_scale),
            ))
            meal_rows.append(DailyMealDetail(
                meal_plan_id=PLAN_ID, meal_date=meal_date, meal_type="dinner",
                recipe_id=4, assigned_user_id=user_id, serving_weight_g=round(150 * serving_scale),
            ))
    db.add_all(meal_rows)


def seed_if_empty(db: Session) -> bool:
    """如果 users 表是空的才灌種子資料。回傳是否有灌資料。"""
    if db.query(User).first() is not None:
        return False

    _seed_users(db)
    _seed_purchase_locations(db)
    _seed_ingredients(db)
    _seed_recipes(db)
    _seed_weekly_meal_plan(db)
    db.commit()
    return True
