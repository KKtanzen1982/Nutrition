"""
Block 2: 用戶管理 - ORM 模型
================================================

包含用戶信息表的 SQLAlchemy ORM 定義
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Boolean, Text
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    """
    用戶信息表
    
    存儲用戶的基本信息和健身目標
    """
    
    __tablename__ = "users"
    
    # 基本字段
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    gender = Column(String(10), nullable=False)  # 男/女
    age = Column(Integer, nullable=False)
    height_cm = Column(Float, nullable=False)
    
    # 健身目標
    primary_goal = Column(String(50), nullable=False)  # 減脂/增肌/維持
    activity_level = Column(String(50), nullable=False)  # 低/中/高
    
    # 其他信息
    email = Column(String(100), unique=True, nullable=True)
    phone = Column(String(20), nullable=True)
    notes = Column(Text, nullable=True)
    
    # 系統字段
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # 關係
    weight_records = relationship("WeightRecord", back_populates="user", cascade="all, delete-orphan")
    exercise_sessions = relationship("ExerciseSession", back_populates="user", cascade="all, delete-orphan")
    workout_templates = relationship("WorkoutTemplate", back_populates="user", cascade="all, delete-orphan")
    daily_steps = relationship("DailySteps", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, name={self.name}, age={self.age})>"
