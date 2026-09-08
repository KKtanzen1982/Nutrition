from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from users.schemas import (
    UserCreate, UserResponse, UserUpdate,
    DietaryPreferenceUpdate, DietaryPreferenceResponse,
    WeightGoalUpdate, WeightGoalResponse,
)
from users.services import user_service, dietary_preference_service, weight_goal_service

router = APIRouter(tags=["users"])


@router.post("/users", response_model=UserResponse, status_code=201)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """創建新用戶"""
    return user_service.create_user(db, user)


@router.get("/users", response_model=List[UserResponse])
def list_users(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    """列出所有用戶"""
    return user_service.get_all_users(db, skip=skip, limit=limit)


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """獲取特定用戶"""
    user = user_service.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用戶不存在")
    return user


@router.put("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: int, user: UserUpdate, db: Session = Depends(get_db)):
    """更新用戶信息"""
    updated_user = user_service.update_user(db, user_id, user)
    if not updated_user:
        raise HTTPException(status_code=404, detail="用戶不存在")
    return updated_user


@router.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    """刪除用戶"""
    success = user_service.delete_user(db, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="用戶不存在")
    return None


@router.get("/users/{user_id}/history")
def get_user_goal_history(user_id: int, db: Session = Depends(get_db)):
    """獲取用戶目標變化歷史（示範用，尚未實作歷史紀錄儲存）"""
    if not user_service.get_user(db, user_id):
        raise HTTPException(status_code=404, detail="用戶不存在")
    return []


@router.get("/users/{user_id}/weight-goal", response_model=WeightGoalResponse)
def get_weight_goal(user_id: int, db: Session = Depends(get_db)):
    """減脂的目標體重＋目標日期，用來動態算每日熱量赤字（見 nutrition_calc.py）"""
    if not user_service.get_user(db, user_id):
        raise HTTPException(status_code=404, detail="使用者不存在")
    return weight_goal_service.get(db, user_id)


@router.put("/users/{user_id}/weight-goal", response_model=WeightGoalResponse)
def set_weight_goal(user_id: int, payload: WeightGoalUpdate, db: Session = Depends(get_db)):
    if not user_service.get_user(db, user_id):
        raise HTTPException(status_code=404, detail="使用者不存在")
    return weight_goal_service.set(db, user_id, payload)


@router.get("/users/{user_id}/dietary-preferences", response_model=DietaryPreferenceResponse)
def get_dietary_preferences(user_id: int, db: Session = Depends(get_db)):
    if not user_service.get_user(db, user_id):
        raise HTTPException(status_code=404, detail="使用者不存在")
    return dietary_preference_service.get(db, user_id)


@router.put("/users/{user_id}/dietary-preferences", response_model=DietaryPreferenceResponse)
def set_dietary_preferences(user_id: int, payload: DietaryPreferenceUpdate, db: Session = Depends(get_db)):
    if not user_service.get_user(db, user_id):
        raise HTTPException(status_code=404, detail="使用者不存在")
    return dietary_preference_service.set(db, user_id, payload)
