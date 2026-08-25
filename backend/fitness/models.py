"""體重紀錄、運動紀錄、每日步數"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Date, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime

from database import Base


class WeightRecord(Base):
    __tablename__ = "weight_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)
    weight_kg = Column(Float, nullable=False)
    body_fat_percent = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ExerciseSession(Base):
    __tablename__ = "exercise_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)
    exercise_type = Column(String(50), nullable=False)
    duration_min = Column(Integer, nullable=False)
    intensity = Column(String(10), nullable=True)
    calories_burned = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    details = relationship("ExerciseDetail", cascade="all, delete-orphan", order_by="ExerciseDetail.order")


class ExerciseDetail(Base):
    __tablename__ = "exercise_details"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("exercise_sessions.id"), nullable=False)
    exercise_name = Column(String(255), nullable=False)
    sets = Column(Integer, nullable=True)
    reps = Column(String(50), nullable=True)
    weight_kg = Column(Float, nullable=True)
    duration_min = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    order = Column(Integer, default=0)
    exercise_item_id = Column(Integer, ForeignKey("exercise_item_library.id"), nullable=True)
    yoga_stretch_item_id = Column(Integer, ForeignKey("yoga_stretch_items.id"), nullable=True)


class DailySteps(Base):
    __tablename__ = "daily_steps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)
    step_count = Column(Integer, nullable=False)
    calories_burned = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_steps_user_date"),)
