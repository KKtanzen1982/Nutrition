"""
Block 2: 用戶管理 - Pydantic Schemas
"""

from datetime import datetime
from typing import Optional, List
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

class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True

class UserListResponse(BaseModel):
    total: int
    users: List[UserResponse]
