"""週菜單推薦：週計畫、日菜單明細、微調紀錄"""

from sqlalchemy import Column, Integer, String, Float, Boolean, Date, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime

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
