from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date

from database import get_db
from meal_plans.schemas import (
    GenerateMealPlanRequest, ReplaceMealRequest, SearchReplaceMealRequest,
    AdjustServingWeightRequest, RegenerateDayRequest,
)
from meal_plans.services import nutrition_target_service, meal_plan_service

router = APIRouter(tags=["meal-plans"])


@router.get("/users/{user_id}/nutrition-targets")
def get_nutrition_targets(user_id: int, target_date: Optional[date] = None, db: Session = Depends(get_db)):
    try:
        return nutrition_target_service.get_user_context(db, user_id, target_date or date.today())
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/meal-plans/generate")
def generate_meal_plan(payload: GenerateMealPlanRequest, db: Session = Depends(get_db)):
    try:
        return meal_plan_service.generate_plan(db, payload.user_id_a, payload.user_id_b, payload.week_start_date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/meal-plans/{plan_id}")
def get_meal_plan(plan_id: int, db: Session = Depends(get_db)):
    plan = meal_plan_service.get_plan(db, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="計畫不存在")
    return plan


@router.post("/meal-plans/{plan_id}/adjust/replace-meal")
def replace_meal(plan_id: int, payload: ReplaceMealRequest, db: Session = Depends(get_db)):
    try:
        return meal_plan_service.replace_meal(db, plan_id, payload.meal_id, payload.new_recipe_id, "替換")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/meal-plans/{plan_id}/adjust/search-replace")
def search_replace_meal(plan_id: int, payload: SearchReplaceMealRequest, db: Session = Depends(get_db)):
    try:
        return meal_plan_service.replace_meal(db, plan_id, payload.meal_id, payload.new_recipe_id, "搜尋替換", payload.search_query)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/meal-plans/{plan_id}/adjust/serving-weight")
def adjust_serving_weight(plan_id: int, payload: AdjustServingWeightRequest, db: Session = Depends(get_db)):
    try:
        return meal_plan_service.adjust_serving_weight(db, plan_id, payload.meal_id, payload.new_serving_weight_g)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/meal-plans/{plan_id}/adjust/regenerate-day")
def regenerate_day(plan_id: int, payload: RegenerateDayRequest, db: Session = Depends(get_db)):
    try:
        return meal_plan_service.regenerate_day(db, plan_id, payload.meal_date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
