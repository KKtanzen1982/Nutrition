"""動作資料庫、訓練範本、多天訓練計畫、月曆排程、週目標"""

from sqlalchemy import Column, Integer, String, Float, Boolean, Date, DateTime, ForeignKey, UniqueConstraint, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from database import Base


class WorkoutTemplate(Base):
    __tablename__ = "workout_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    template_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    exercise_type = Column(String(50), nullable=False)
    duration_min = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    details = relationship("TemplateDetail", cascade="all, delete-orphan", order_by="TemplateDetail.order")


class TemplateDetail(Base):
    __tablename__ = "template_details"

    id = Column(Integer, primary_key=True, autoincrement=True)
    template_id = Column(Integer, ForeignKey("workout_templates.id"), nullable=False)
    exercise_name = Column(String(255), nullable=False)
    sets = Column(Integer, nullable=True)
    reps = Column(String(50), nullable=True)
    weight_kg = Column(Float, nullable=True)
    duration_min = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    order = Column(Integer, default=0)
    exercise_item_id = Column(Integer, ForeignKey("exercise_item_library.id"), nullable=True)
    yoga_stretch_item_id = Column(Integer, ForeignKey("yoga_stretch_items.id"), nullable=True)


class ExerciseItemLibrary(Base):
    __tablename__ = "exercise_item_library"

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_name = Column(String(255), nullable=False, unique=True)
    category = Column(String(50), nullable=False)
    muscle_group = Column(String(100), nullable=True)
    equipment = Column(String(100), nullable=True)
    default_sets = Column(Integer, nullable=True)
    default_reps = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class YogaStretchItem(Base):
    __tablename__ = "yoga_stretch_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_name = Column(String(255), nullable=False, unique=True)
    type = Column(String(20), nullable=False)
    duration_min = Column(Integer, nullable=True)
    difficulty = Column(String(20), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class UserItemUsage(Base):
    __tablename__ = "user_item_usage"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    item_type = Column(String(20), primary_key=True)
    item_id = Column(Integer, primary_key=True)
    use_count = Column(Integer, default=0)
    last_used_at = Column(DateTime, nullable=True)


class TrainingProgram(Base):
    __tablename__ = "training_programs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    program_name = Column(String(255), nullable=False)
    day_count = Column(Integer, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class TrainingProgramDay(Base):
    __tablename__ = "training_program_days"

    id = Column(Integer, primary_key=True, autoincrement=True)
    program_id = Column(Integer, ForeignKey("training_programs.id"), nullable=False)
    day_number = Column(Integer, nullable=False)
    day_label = Column(String(255), nullable=True)
    workout_template_id = Column(Integer, ForeignKey("workout_templates.id"), nullable=False)

    __table_args__ = (UniqueConstraint("program_id", "day_number", name="uq_program_day_number"),)


class TrainingSchedule(Base):
    __tablename__ = "training_schedule"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    program_day_id = Column(Integer, ForeignKey("training_program_days.id"), nullable=False)
    scheduled_date = Column(Date, nullable=False)
    status = Column(String(20), default="已排程")
    actual_exercise_session_id = Column(Integer, ForeignKey("exercise_sessions.id"), nullable=True)
    volume_adjustment_pct = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("user_id", "scheduled_date", name="uq_schedule_user_date"),)


class TrainingTarget(Base):
    __tablename__ = "training_targets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    category = Column(String(20), nullable=False)
    weekly_target_count = Column(Integer, default=2)

    __table_args__ = (UniqueConstraint("user_id", "category", name="uq_target_user_category"),)
