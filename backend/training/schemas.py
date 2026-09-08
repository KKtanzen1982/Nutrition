from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field


class TemplateDetailBase(BaseModel):
    exercise_name: str
    sets: Optional[int] = Field(None, ge=1)
    reps: Optional[str] = None
    weight_kg: Optional[float] = None
    duration_min: Optional[int] = Field(None, ge=1)
    notes: Optional[str] = None
    order: int = 0
    exercise_item_id: Optional[int] = None
    yoga_stretch_item_id: Optional[int] = None


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
    duration_min: Optional[int] = None


class WorkoutTemplateCreate(WorkoutTemplateBase):
    details: Optional[List[TemplateDetailCreate]] = None


class WorkoutTemplateUpdate(BaseModel):
    template_name: Optional[str] = None
    description: Optional[str] = None
    exercise_type: Optional[str] = None
    duration_min: Optional[int] = None
    details: Optional[List[TemplateDetailCreate]] = None


class WorkoutTemplateResponse(WorkoutTemplateBase):
    id: int
    details: List[TemplateDetailResponse]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ExerciseItemBase(BaseModel):
    item_name: str = Field(..., min_length=1)
    category: str = Field(..., description="胸部/背部/下肢/手臂/核心/有氧")
    muscle_group: Optional[str] = None
    equipment: Optional[str] = None
    default_sets: Optional[int] = None
    default_reps: Optional[str] = None
    description: Optional[str] = None


class ExerciseItemCreate(ExerciseItemBase):
    pass


class ExerciseItemResponse(ExerciseItemBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class YogaStretchItemBase(BaseModel):
    item_name: str = Field(..., min_length=1)
    type: str = Field(..., description="瑜珈/拉伸")
    duration_min: Optional[int] = None
    difficulty: Optional[str] = Field(None, description="初級/中級/進階")
    description: Optional[str] = None


class YogaStretchItemCreate(YogaStretchItemBase):
    pass


class YogaStretchItemResponse(YogaStretchItemBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ExerciseItemLibraryCreate(BaseModel):
    """POST /api/exercise-items 統一入口，由 type 決定寫進哪張庫。"""
    type: str = Field(..., description="gym / yoga_stretch")
    item_name: str = Field(..., min_length=1)
    description: Optional[str] = None
    # type == "gym" 時使用
    category: Optional[str] = None
    muscle_group: Optional[str] = None
    equipment: Optional[str] = None
    default_sets: Optional[int] = None
    default_reps: Optional[str] = None
    # type == "yoga_stretch" 時使用
    yoga_type: Optional[str] = Field(None, description="瑜珈/拉伸")
    duration_min: Optional[int] = None
    difficulty: Optional[str] = None


class ExerciseItemLibraryUpdate(BaseModel):
    """PUT /api/exercise-items/{type}/{item_id} 統一入口，欄位皆選填，只更新有帶的欄位。"""
    # type == "gym" 時使用
    category: Optional[str] = None
    muscle_group: Optional[str] = None
    equipment: Optional[str] = None
    default_sets: Optional[int] = None
    default_reps: Optional[str] = None
    # type == "yoga_stretch" 時使用
    duration_min: Optional[int] = None
    difficulty: Optional[str] = None
    # 共用（備註）
    description: Optional[str] = None


class TrainingProgramDayCreate(BaseModel):
    day_number: int
    day_label: Optional[str] = None
    exercise_type: str
    duration_min: Optional[int] = None
    details: Optional[List[TemplateDetailCreate]] = None


class TrainingProgramCreate(BaseModel):
    user_id: int
    program_name: str = Field(..., min_length=1)
    description: Optional[str] = None
    days: List[TrainingProgramDayCreate] = Field(..., min_length=1, max_length=7)


class TrainingScheduleCreate(BaseModel):
    program_day_id: int
    scheduled_date: date


class TrainingScheduleUpdate(BaseModel):
    scheduled_date: Optional[date] = None
    status: Optional[str] = None


class TrainingScheduleLinkActual(BaseModel):
    exercise_session_id: int


class NotionScheduleItem(BaseModel):
    schedule_id: int


class TrainingTargetItem(BaseModel):
    category: str
    weekly_target_count: int = Field(..., ge=0)


class TrainingTargetsUpdate(BaseModel):
    targets: List[TrainingTargetItem]
