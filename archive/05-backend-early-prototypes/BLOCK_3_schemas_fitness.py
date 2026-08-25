"""
Block 3: 體重和運動追蹤 - Pydantic Schemas
"""

from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field

# ==================== 體重相關 ====================

class WeightRecordBase(BaseModel):
    user_id: int
    date: date
    weight_kg: float = Field(..., gt=0, lt=1000)
    body_fat_percent: Optional[float] = Field(None, ge=0, le=100)
    notes: Optional[str] = None

class WeightRecordCreate(WeightRecordBase):
    pass

class WeightRecordResponse(WeightRecordBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# ==================== 運動詳情 ====================

class ExerciseDetailBase(BaseModel):
    exercise_name: str
    sets: int = Field(..., ge=1)
    reps: str
    weight_kg: Optional[float] = None
    notes: Optional[str] = None
    order: int = 0

class ExerciseDetailCreate(ExerciseDetailBase):
    pass

class ExerciseDetailResponse(ExerciseDetailBase):
    id: int
    session_id: int
    
    class Config:
        from_attributes = True

# ==================== 運動會話 ====================

class ExerciseSessionBase(BaseModel):
    user_id: int
    date: date
    exercise_type: str
    duration_min: int = Field(..., ge=1)
    intensity: str
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

# ==================== 訓練模板 ====================

class TemplateDetailBase(BaseModel):
    exercise_name: str
    sets: int = Field(..., ge=1)
    reps: str
    weight_kg: Optional[float] = None
    notes: Optional[str] = None
    order: int = 0

class TemplateDetailCreate(TemplateDetailBase):
    pass

class TemplateDetailResponse(TemplateDetailBase):
    id: int
    template_id: int
    
    class Config:
        from_attributes = True

class WorkoutTemplateBase(BaseModel):
    user_id: int
    template_name: str
    description: Optional[str] = None
    exercise_type: str
    intensity: str
    duration_min: Optional[int] = None

class WorkoutTemplateCreate(WorkoutTemplateBase):
    details: Optional[List[TemplateDetailCreate]] = None

class WorkoutTemplateResponse(WorkoutTemplateBase):
    id: int
    details: List[TemplateDetailResponse]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# ==================== 每日步數 ====================

class DailyStepsBase(BaseModel):
    user_id: int
    date: date
    step_count: int = Field(..., ge=0)
    calories_burned: Optional[float] = None
    notes: Optional[str] = None

class DailyStepsCreate(DailyStepsBase):
    pass

class DailyStepsResponse(DailyStepsBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
