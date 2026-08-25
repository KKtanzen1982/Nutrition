from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field


class WeightRecordBase(BaseModel):
    user_id: int
    date: date
    weight_kg: float = Field(..., gt=0, lt=1000)
    body_fat_percent: Optional[float] = Field(None, ge=0, le=100)
    notes: Optional[str] = None


class WeightRecordCreate(WeightRecordBase):
    pass


class WeightRecordUpdate(BaseModel):
    weight_kg: Optional[float] = Field(None, gt=0, lt=1000)
    body_fat_percent: Optional[float] = Field(None, ge=0, le=100)
    notes: Optional[str] = None


class WeightRecordResponse(WeightRecordBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ExerciseDetailBase(BaseModel):
    exercise_name: str
    sets: Optional[int] = Field(None, ge=1)
    reps: Optional[str] = None
    weight_kg: Optional[float] = None
    duration_min: Optional[int] = Field(None, ge=1)
    notes: Optional[str] = None
    order: int = 0
    exercise_item_id: Optional[int] = None
    yoga_stretch_item_id: Optional[int] = None


class ExerciseDetailCreate(ExerciseDetailBase):
    pass


class ExerciseDetailResponse(ExerciseDetailBase):
    id: int
    session_id: int

    class Config:
        from_attributes = True


class ExerciseSessionBase(BaseModel):
    user_id: int
    date: date
    exercise_type: str
    duration_min: int = Field(..., ge=1)
    intensity: Optional[str] = None
    calories_burned: Optional[float] = None
    notes: Optional[str] = None


class ExerciseSessionCreate(ExerciseSessionBase):
    details: Optional[List[ExerciseDetailCreate]] = None


class ExerciseSessionResponse(ExerciseSessionBase):
    id: int
    details: List[ExerciseDetailResponse]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DailyStepsBase(BaseModel):
    user_id: int
    date: date
    step_count: int = Field(..., ge=0)
    calories_burned: Optional[float] = None
    notes: Optional[str] = None


class DailyStepsCreate(DailyStepsBase):
    pass


class DailyStepsUpdate(BaseModel):
    step_count: Optional[int] = Field(None, ge=0)
    calories_burned: Optional[float] = None
    notes: Optional[str] = None


class DailyStepsResponse(DailyStepsBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
