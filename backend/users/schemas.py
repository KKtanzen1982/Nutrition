from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, Field


class UserBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    gender: str = Field(..., description="男/女")
    age: int = Field(..., ge=1, le=150)
    height_cm: float = Field(..., ge=100, le=250)
    primary_goal: str = Field(..., description="減脂/增肌/維持")
    activity_level: str = Field(..., description="低/中/高")
    email: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = None


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    name: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    height_cm: Optional[float] = None
    primary_goal: Optional[str] = None
    activity_level: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = None
    last_menstrual_date: Optional[date] = None
    menstrual_cycle_length_days: Optional[int] = None
    menstrual_cycle_irregular: Optional[bool] = None
    menstrual_luteal_phase_start_offset_days: Optional[int] = None
    menstrual_luteal_phase_adjustment_calories: Optional[int] = None
    menstrual_premenstrual_adjustment_calories: Optional[int] = None
    manual_calories_target: Optional[float] = None


class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    last_menstrual_date: Optional[date] = None
    menstrual_cycle_length_days: Optional[int] = None
    menstrual_cycle_irregular: bool = False
    menstrual_luteal_phase_start_offset_days: int = 14
    menstrual_luteal_phase_adjustment_calories: int = 150
    menstrual_premenstrual_adjustment_calories: int = 120
    manual_calories_target: Optional[float] = None

    class Config:
        from_attributes = True


class WeightGoalUpdate(BaseModel):
    target_weight_kg: Optional[float] = Field(None, gt=0)
    target_date: Optional[date] = None


class WeightGoalResponse(BaseModel):
    user_id: int
    target_weight_kg: Optional[float] = None
    target_date: Optional[date] = None
    active_daily_deficit_kcal: Optional[float] = None
    deficit_calculated_at: Optional[date] = None
    deficit_calculated_weight_kg: Optional[float] = None

    class Config:
        from_attributes = True


class DietaryPreferenceUpdate(BaseModel):
    allergies: Optional[str] = None
    restrictions: Optional[str] = None
    preferences: Optional[str] = None


class DietaryPreferenceResponse(BaseModel):
    user_id: int
    allergies: Optional[str] = None
    restrictions: Optional[str] = None
    preferences: Optional[str] = None

    class Config:
        from_attributes = True
