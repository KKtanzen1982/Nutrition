"""週菜單推薦：週計畫、日菜單明細、微調紀錄"""

from sqlalchemy import Column, Integer, String, Float, Boolean, Date, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime, date

from database import Base


class WeeklyMealPlan(Base):
    __tablename__ = "weekly_meal_plan"

    id = Column(Integer, primary_key=True, autoincrement=True)
    plan_date = Column(Date, nullable=False)
    user_id_a = Column(Integer, ForeignKey("users.id"), nullable=False)
    user_id_b = Column(Integer, ForeignKey("users.id"), nullable=False)
    user_a_daily_calories_target = Column(Integer, nullable=True)
    user_b_daily_calories_target = Column(Integer, nullable=True)
    user_a_menstrual_phase = Column(String(10), nullable=True)
    user_b_menstrual_phase = Column(String(10), nullable=True)
    plan_status = Column(String(20), default="草稿")
    claude_generated = Column(Boolean, default=True)
    recommendation_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    meals = relationship("DailyMealDetail", cascade="all, delete-orphan")


class DailyMealDetail(Base):
    __tablename__ = "daily_meal_detail"

    id = Column(Integer, primary_key=True, autoincrement=True)
    meal_plan_id = Column(Integer, ForeignKey("weekly_meal_plan.id"), nullable=False)
    meal_date = Column(Date, nullable=False)
    meal_type = Column(String(20), nullable=False)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    assigned_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    serving_weight_g = Column(Float, nullable=True)
    calories = Column(Float, nullable=True)
    protein_g = Column(Float, nullable=True)
    carbs_g = Column(Float, nullable=True)
    fat_g = Column(Float, nullable=True)
    fiber_g = Column(Float, nullable=True)


class FixedMealPreference(Base):
    """固定吃的餐點（例如「我早餐固定吃燕麥牛奶粥」）：產生週菜單時這一餐直接套用這份食譜，
    只依當天熱量目標調整份量，不會被規則式選餐演算法換掉。

    早餐/下午茶（breakfast/afternoon_snack）是個人餐點，user_id 必填、category 留空，
    一人一份設定（uq user_id+meal_type）。午餐/晚餐（lunch/dinner）是兩人共用的主食+肉+菜(+湯)
    組合，固定的是其中一個類別的菜（例如「午餐主食固定吃白飯」），user_id 留空（不分誰），
    category 必填（依選定食譜的 category 自動帶入），一個 meal_type+category 一份設定，
    兩者用不同的鍵所以沒有共用同一個 DB UniqueConstraint，唯一性由 FixedMealPreferenceService
    的查詢比對（找到就更新、找不到才新增）保證。

    start_date + duration_days：可選的執行天數限制，從設定當下算起連續套用幾天，超過天數後
    這一餐自動改回規則式演算法選餐（不用手動刪除）。duration_days 為 None 表示永久套用，
    維持既有行為（向下相容）。"""

    __tablename__ = "fixed_meal_preferences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    meal_type = Column(String(20), nullable=False)
    category = Column(String(20), nullable=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    start_date = Column(Date, nullable=False, default=date.today)
    duration_days = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (UniqueConstraint("user_id", "meal_type", name="uq_fixed_meal_preferences_user_meal_type"),)


class ExcludedRecipe(Base):
    """黑名單：標記「不要再推薦」的食譜，兩人共用一份清單，往後產生/重推菜單一律排除（跟 FixedMealPreference 相反）"""

    __tablename__ = "excluded_recipes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class FavoriteRecipe(Base):
    """最愛清單：軟性加權，選餐時比較容易被選到，但不像 FixedMealPreference 那樣鎖死"""

    __tablename__ = "favorite_recipes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("user_id", "recipe_id", name="uq_favorite_recipes_user_recipe"),)


class SoupDayPreference(Base):
    """勾選「這天想喝湯」（午餐/晚餐），兩人共用一份設定，不分誰勾的"""

    __tablename__ = "soup_day_preferences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    day_of_week = Column(Integer, nullable=False, unique=True)  # 0=週一...6=週日，對應 date.weekday()
    created_at = Column(DateTime, default=datetime.utcnow)


class MealAdjustment(Base):
    __tablename__ = "meal_adjustments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    plan_id = Column(Integer, ForeignKey("weekly_meal_plan.id"), nullable=False)
    adjustment_type = Column(String(20), nullable=False)
    meal_date = Column(Date, nullable=True)
    meal_type = Column(String(20), nullable=True)
    user_id = Column(Integer, nullable=True)
    original_recipe_id = Column(Integer, nullable=True)
    adjusted_recipe_id = Column(Integer, nullable=True)
    reason = Column(Text, nullable=True)
    adjusted_by = Column(String(10), default="user")
    adjusted_at = Column(DateTime, default=datetime.utcnow)
