"""
Block 3: 體重和運動追蹤 - ORM 模型
"""

from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class WeightRecord(Base):
    """體重記錄表"""
    __tablename__ = "weight_records"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    weight_kg = Column(Float, nullable=False)
    body_fat_percent = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ExerciseSession(Base):
    """運動會話表"""
    __tablename__ = "exercise_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    exercise_type = Column(String(50), nullable=False)
    duration_min = Column(Integer, nullable=False)
    intensity = Column(String(10), nullable=False)
    calories_burned = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ExerciseDetail(Base):
    """訓練詳情表"""
    __tablename__ = "exercise_details"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("exercise_sessions.id"), nullable=False)
    exercise_name = Column(String(100), nullable=False)
    sets = Column(Integer, nullable=False)
    reps = Column(String(50), nullable=False)
    weight_kg = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    order = Column(Integer, default=0)

class WorkoutTemplate(Base):
    """訓練模板表"""
    __tablename__ = "workout_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    template_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    exercise_type = Column(String(50), nullable=False)
    intensity = Column(String(10), nullable=False)
    duration_min = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class TemplateDetail(Base):
    """模板詳情表"""
    __tablename__ = "template_details"
    
    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("workout_templates.id"), nullable=False)
    exercise_name = Column(String(100), nullable=False)
    sets = Column(Integer, nullable=False)
    reps = Column(String(50), nullable=False)
    weight_kg = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    order = Column(Integer, default=0)

class DailySteps(Base):
    """每日步數表"""
    __tablename__ = "daily_steps"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    step_count = Column(Integer, nullable=False)
    calories_burned = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ExerciseItemLibrary(Base):
    """訓練項目庫"""
    __tablename__ = "exercise_item_library"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    category = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    difficulty_level = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class YogaStretchItem(Base):
    """瑜珈拉伸項目庫"""
    __tablename__ = "yoga_stretch_items"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    category = Column(String(50), nullable=False)
    duration_min = Column(Integer, nullable=True)
    difficulty_level = Column(String(20), nullable=True)
    description = Column(Text, nullable=True)
    benefits = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
