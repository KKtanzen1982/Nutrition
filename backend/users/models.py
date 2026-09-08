"""使用者：基本資料 + 生理期欄位 + 飲食偏好"""

from sqlalchemy import Column, Integer, String, Float, Boolean, Date, DateTime, ForeignKey, Text
from datetime import datetime

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    gender = Column(String(10), nullable=False)
    age = Column(Integer, nullable=False)
    height_cm = Column(Float, nullable=False)
    primary_goal = Column(String(20), nullable=False)
    activity_level = Column(String(10), nullable=False)
    manual_calories_target = Column(Float, nullable=True)  # 手動覆蓋每日目標攝取熱量，設定後取代自動算出的值
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 生理期相關
    last_menstrual_date = Column(Date, nullable=True)
    menstrual_cycle_length_days = Column(Integer, nullable=True)
    menstrual_cycle_irregular = Column(Boolean, default=False)
    menstrual_luteal_phase_start_offset_days = Column(Integer, default=14)
    menstrual_luteal_phase_adjustment_calories = Column(Integer, default=150)
    menstrual_premenstrual_adjustment_calories = Column(Integer, default=120)


class WeightGoal(Base):
    """減脂的目標體重＋目標日期，讓每日熱量赤字可以依 TDEE 動態算，而不是固定 -350kcal。
    赤字每 30 天才重新計算一次（見 nutrition_calc.DEFICIT_RECALC_INTERVAL_DAYS），
    active_daily_deficit_kcal/deficit_calculated_at/deficit_calculated_weight_kg 是上次算出來的快取值。"""

    __tablename__ = "weight_goals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    target_weight_kg = Column(Float, nullable=True)
    target_date = Column(Date, nullable=True)
    active_daily_deficit_kcal = Column(Float, nullable=True)
    deficit_calculated_at = Column(Date, nullable=True)
    deficit_calculated_weight_kg = Column(Float, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DietaryPreference(Base):
    __tablename__ = "dietary_preferences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    allergies = Column(Text, nullable=True)
    restrictions = Column(Text, nullable=True)
    preferences = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
