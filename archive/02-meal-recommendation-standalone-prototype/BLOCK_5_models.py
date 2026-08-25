"""
BLOCK_5: SQLAlchemy ORM 模型 - 獨立測試資料庫

這個模組故意使用自己的 Base（跟 BLOCK_2/BLOCK_3/BLOCK_4 一樣，各區塊各自獨立），
用來讓 BLOCK_5 的推薦引擎有一個真實、可持久化的資料庫可以測試，
而不需要等待跨區塊的資料庫整合。

包含：
- 用戶相關（表 1、表 4 的精簡版）：User, DietaryPreference
- 體重/運動相關（表 2、3a、3f 的精簡版）：WeightRecord, ExerciseSession, DailySteps
- 食譜相關（表 5a、5d 的精簡版，額外加 is_vegetarian/allergen_tags 方便篩選）：Recipe, RecipeNutrition
- 週推薦相關（表 5f、5g、5h，真正需要持久化的新表）：WeeklyMealPlan, DailyMealDetail, MealAdjustment
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Text, Date, DateTime, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


# ==================== 用戶相關 ====================

class User(Base):
    """表 1 精簡版：用戶基本資料"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    gender = Column(String(10), nullable=False)  # '男' / '女' / '其他'
    age = Column(Integer, nullable=False)
    height_cm = Column(Float, nullable=False)
    primary_goal = Column(String(20), nullable=False)  # '減脂' / '增肌' / '維持'
    activity_level = Column(String(10), nullable=False)  # '久坐' / '輕度' / '中度' / '高度'
    menstrual_cycle_length_days = Column(Integer, nullable=True)
    last_menstrual_date = Column(Date, nullable=True)
    menstrual_cycle_irregular = Column(Boolean, default=False)
    menstrual_luteal_phase_start_offset_days = Column(Integer, default=14)
    menstrual_luteal_phase_adjustment_calories = Column(Integer, default=150)
    menstrual_premenstrual_adjustment_calories = Column(Integer, default=120)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    dietary_preference = relationship("DietaryPreference", back_populates="user", uselist=False)

    def __repr__(self):
        return f"<User(id={self.id}, name={self.name})>"


class DietaryPreference(Base):
    """表 4：飲食偏好"""
    __tablename__ = "dietary_preferences"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    allergies = Column(Text, nullable=True)  # 逗號分隔，例："堅果, 海鮮"
    restrictions = Column(Text, nullable=True)  # 例："素食"
    preferences = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="dietary_preference")


# ==================== 體重/運動相關 ====================

class WeightRecord(Base):
    """表 2 精簡版：體重日誌"""
    __tablename__ = "weight_records"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    weight_kg = Column(Float, nullable=False)
    body_fat_percent = Column(Float, nullable=True)

    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_weight_user_date"),)


class ExerciseSession(Base):
    """表 3a 精簡版：運動紀錄"""
    __tablename__ = "exercise_sessions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    exercise_type = Column(String(50), nullable=False)  # '健身房' / '走路' / '瑜珈' / '拉伸'
    duration_min = Column(Integer, nullable=True)
    intensity = Column(String(10), nullable=True)  # '低' / '中' / '高'


class DailySteps(Base):
    """表 3f 精簡版：每日步數"""
    __tablename__ = "daily_steps"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    steps = Column(Integer, nullable=False)

    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_steps_user_date"),)


# ==================== 食譜相關 ====================

class Recipe(Base):
    """表 5a 精簡版：食譜庫（額外加 is_vegetarian/allergen_tags 供篩選邏輯使用）"""
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True)
    recipe_name = Column(String(255), nullable=False, unique=True)
    category = Column(String(20), nullable=False)  # '早餐' / '主食' / '肉' / '菜' / '飲料' / '點心'
    base_weight_g = Column(Integer, nullable=False)
    cost_level = Column(String(10), nullable=False)  # '低' / '中' / '高'
    is_vegetarian = Column(Boolean, default=False)
    allergen_tags = Column(String(255), default="")  # 逗號分隔，例："堅果, 海鮮"
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    nutrition = relationship("RecipeNutrition", back_populates="recipe", uselist=False, cascade="all, delete-orphan")
    ingredient_names_csv = Column(String(255), default="")  # 逗號分隔的食材名稱，僅供 Claude prompt 摘要使用

    def __repr__(self):
        return f"<Recipe {self.recipe_name}>"


class RecipeNutrition(Base):
    """表 5d 精簡版：食譜營養素"""
    __tablename__ = "recipe_nutrition"

    id = Column(Integer, primary_key=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False, unique=True)
    total_calories_kcal = Column(Float, nullable=False)
    protein_g = Column(Float, nullable=False)
    carbs_g = Column(Float, nullable=False)
    fat_g = Column(Float, nullable=False)
    fiber_g = Column(Float, nullable=True)

    recipe = relationship("Recipe", back_populates="nutrition")


# ==================== 週推薦相關（本區塊真正新增的表） ====================

class WeeklyMealPlan(Base):
    """表 5f：週菜單安排"""
    __tablename__ = "weekly_meal_plan"

    id = Column(Integer, primary_key=True)
    plan_date = Column(Date, nullable=False)  # 週一的日期
    user_id_a = Column(Integer, ForeignKey("users.id"), nullable=False)
    user_id_b = Column(Integer, ForeignKey("users.id"), nullable=False)
    calorie_calculation_method = Column(String(30), default="harris_benedict")
    user_a_daily_calories_target = Column(Integer, nullable=True)
    user_b_daily_calories_target = Column(Integer, nullable=True)
    user_a_menstrual_phase = Column(String(10), nullable=True)
    user_b_menstrual_phase = Column(String(10), nullable=True)
    plan_status = Column(String(20), default="草稿")  # '草稿' / '待微調' / '已確認'
    claude_generated = Column(Boolean, default=True)
    recommendation_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (UniqueConstraint("plan_date", "user_id_a", "user_id_b", name="uq_plan_date_users"),)

    meals = relationship("DailyMealDetail", back_populates="plan", cascade="all, delete-orphan")
    adjustments = relationship("MealAdjustment", back_populates="plan", cascade="all, delete-orphan")


class DailyMealDetail(Base):
    """表 5g：日菜單詳情"""
    __tablename__ = "daily_meal_detail"

    id = Column(Integer, primary_key=True)
    meal_plan_id = Column(Integer, ForeignKey("weekly_meal_plan.id"), nullable=False, index=True)
    meal_date = Column(Date, nullable=False, index=True)
    meal_type = Column(String(20), nullable=False)  # 'breakfast' / 'lunch' / 'afternoon_snack' / 'dinner'
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    assigned_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    serving_weight_g = Column(Float, nullable=True)
    total_calories = Column(Float, nullable=True)
    protein_g = Column(Float, nullable=True)
    carbs_g = Column(Float, nullable=True)
    fat_g = Column(Float, nullable=True)
    fiber_g = Column(Float, nullable=True)

    plan = relationship("WeeklyMealPlan", back_populates="meals")
    recipe = relationship("Recipe")


class MealAdjustment(Base):
    """表 5h：推薦微調紀錄"""
    __tablename__ = "meal_adjustments"

    id = Column(Integer, primary_key=True)
    plan_id = Column(Integer, ForeignKey("weekly_meal_plan.id"), nullable=False, index=True)
    adjustment_type = Column(String(20), nullable=False)  # '替換' / '搜尋替換' / '調整分量' / '重推整天'
    meal_date = Column(Date, nullable=True)
    meal_type = Column(String(20), nullable=True)
    user_id = Column(Integer, nullable=True)
    original_recipe_id = Column(Integer, nullable=True)
    adjusted_recipe_id = Column(Integer, nullable=True)
    reason = Column(Text, nullable=True)
    adjusted_by = Column(String(10), default="user")  # 'user' / 'System'
    adjusted_at = Column(DateTime, default=datetime.utcnow)

    plan = relationship("WeeklyMealPlan", back_populates="adjustments")
