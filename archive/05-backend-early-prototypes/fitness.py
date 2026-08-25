"""
Block 3: 體重和運動追蹤 - ORM 模型
================================================

包含：
- 體重記錄
- 運動會話
- 訓練詳情
- 訓練模板
- 每日步數
- 訓練項目庫
- 瑜珈拉伸項目庫
"""

from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Boolean, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class ExerciseTypeEnum(str, enum.Enum):
    """運動類型"""
    GYM = "健身房"
    RUNNING = "跑步"
    YOGA = "瑜珈"
    CYCLING = "騎自行車"
    SWIMMING = "游泳"
    HOME = "居家運動"
    OTHER = "其他"


class IntensityEnum(str, enum.Enum):
    """運動強度"""
    LOW = "低"
    MEDIUM = "中"
    HIGH = "高"


class WeightRecord(Base):
    """
    體重記錄表
    
    記錄每次測量的體重和體脂率
    """
    
    __tablename__ = "weight_records"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    weight_kg = Column(Float, nullable=False)
    body_fat_percent = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 關係
    user = relationship("User", back_populates="weight_records")
    
    __table_args__ = (
        # 每個用戶每天只能有一條記錄
        # UniqueConstraint('user_id', 'date', name='uq_user_date'),
    )


class ExerciseSession(Base):
    """
    運動會話表
    
    記錄每次運動的基本信息
    """
    
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
    
    # 關係
    user = relationship("User", back_populates="exercise_sessions")
    details = relationship("ExerciseDetail", back_populates="session", cascade="all, delete-orphan")


class ExerciseDetail(Base):
    """
    訓練詳情表
    
    記錄每次運動中的具體訓練項目（組數、次數、重量等）
    """
    
    __tablename__ = "exercise_details"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("exercise_sessions.id"), nullable=False)
    exercise_name = Column(String(100), nullable=False)
    sets = Column(Integer, nullable=False)
    reps = Column(String(50), nullable=False)  # 例如: "10-8-6-4"
    weight_kg = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    order = Column(Integer, default=0)
    
    # 關係
    session = relationship("ExerciseSession", back_populates="details")


class ExerciseItemLibrary(Base):
    """
    訓練項目庫
    
    存儲所有可用的訓練項目（啞鈴臥推、深蹲等）
    """
    
    __tablename__ = "exercise_item_library"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    category = Column(String(50), nullable=False)  # 胸/背/腿/肩/手臂等
    description = Column(Text, nullable=True)
    equipment_needed = Column(String(200), nullable=True)
    difficulty_level = Column(String(20), nullable=True)  # 初級/中級/高級
    created_at = Column(DateTime, default=datetime.utcnow)


class WorkoutTemplate(Base):
    """
    訓練模板表
    
    存儲用戶保存的訓練計劃模板
    """
    
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
    
    # 關係
    user = relationship("User", back_populates="workout_templates")
    details = relationship("TemplateDetail", back_populates="template", cascade="all, delete-orphan")


class TemplateDetail(Base):
    """
    模板詳情表
    
    訓練模板中的具體訓練項目
    """
    
    __tablename__ = "template_details"
    
    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("workout_templates.id"), nullable=False)
    exercise_name = Column(String(100), nullable=False)
    sets = Column(Integer, nullable=False)
    reps = Column(String(50), nullable=False)
    weight_kg = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    order = Column(Integer, default=0)
    
    # 關係
    template = relationship("WorkoutTemplate", back_populates="details")


class DailySteps(Base):
    """
    每日步數表
    
    記錄每天的步數
    """
    
    __tablename__ = "daily_steps"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    step_count = Column(Integer, nullable=False)
    calories_burned = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 關係
    user = relationship("User", back_populates="daily_steps")


class YogaStretchItem(Base):
    """
    瑜珈拉伸項目庫
    
    存儲所有可用的瑜珈和拉伸項目
    """
    
    __tablename__ = "yoga_stretch_items"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    category = Column(String(50), nullable=False)  # 瑜珈/拉伸
    duration_min = Column(Integer, nullable=True)
    difficulty_level = Column(String(20), nullable=True)
    description = Column(Text, nullable=True)
    benefits = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
