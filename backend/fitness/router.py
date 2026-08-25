from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from fitness.schemas import (
    WeightRecordCreate, WeightRecordUpdate, WeightRecordResponse,
    ExerciseSessionCreate, ExerciseSessionResponse,
    DailyStepsCreate, DailyStepsUpdate, DailyStepsResponse,
)
from fitness.services import WeightService, ExerciseService, StepsService

router = APIRouter(tags=["fitness"])

weight_service = WeightService()
exercise_service = ExerciseService()
steps_service = StepsService()


@router.post("/weight-records", response_model=WeightRecordResponse, status_code=201)
def create_weight_record(record: WeightRecordCreate, db: Session = Depends(get_db)):
    """記錄體重"""
    return weight_service.create_weight_record(db, record)


@router.get("/weight-records", response_model=List[WeightRecordResponse])
def list_weight_records(user_id: int, skip: int = 0, limit: int = 500, db: Session = Depends(get_db)):
    """獲取用戶體重記錄"""
    return weight_service.get_weight_records(db, user_id, skip=skip, limit=limit)


@router.get("/weight-records/{record_id}", response_model=WeightRecordResponse)
def get_weight_record(record_id: int, db: Session = Depends(get_db)):
    """獲取特定體重記錄"""
    record = weight_service.get_weight_record(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="記錄不存在")
    return record


@router.put("/weight-records/{record_id}", response_model=WeightRecordResponse)
def update_weight_record(record_id: int, record: WeightRecordUpdate, db: Session = Depends(get_db)):
    """更新體重記錄"""
    updated_record = weight_service.update_weight_record(db, record_id, record)
    if not updated_record:
        raise HTTPException(status_code=404, detail="記錄不存在")
    return updated_record


@router.delete("/weight-records/{record_id}", status_code=204)
def delete_weight_record(record_id: int, db: Session = Depends(get_db)):
    """刪除體重記錄"""
    success = weight_service.delete_weight_record(db, record_id)
    if not success:
        raise HTTPException(status_code=404, detail="記錄不存在")
    return None


@router.post("/exercise-sessions", response_model=ExerciseSessionResponse, status_code=201)
def create_exercise_session(session: ExerciseSessionCreate, db: Session = Depends(get_db)):
    """創建運動會話"""
    try:
        return exercise_service.create_exercise_session(db, session)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/exercise-sessions", response_model=List[ExerciseSessionResponse])
def list_exercise_sessions(user_id: int, skip: int = 0, limit: int = 500, db: Session = Depends(get_db)):
    """獲取用戶運動記錄"""
    return exercise_service.get_exercise_sessions(db, user_id, skip=skip, limit=limit)


@router.get("/exercise-sessions/{session_id}", response_model=ExerciseSessionResponse)
def get_exercise_session(session_id: int, db: Session = Depends(get_db)):
    """獲取特定運動會話"""
    session = exercise_service.get_exercise_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="運動記錄不存在")
    return session


@router.get("/exercise-weekly-stats")
def get_weekly_stats(user_id: int, db: Session = Depends(get_db)):
    """獲取本週運動統計"""
    return exercise_service.get_weekly_stats(db, user_id)


@router.post("/daily-steps", response_model=DailyStepsResponse, status_code=201)
def create_daily_steps(steps: DailyStepsCreate, db: Session = Depends(get_db)):
    """記錄每日步數；同一使用者同一天重複建立會回 400（前端應改用 PUT 更新）"""
    try:
        return steps_service.create_steps(db, steps)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/daily-steps", response_model=List[DailyStepsResponse])
def list_daily_steps(user_id: int, skip: int = 0, limit: int = 500, db: Session = Depends(get_db)):
    """獲取用戶步數記錄"""
    return steps_service.get_steps(db, user_id, skip=skip, limit=limit)


@router.put("/daily-steps/{steps_id}", response_model=DailyStepsResponse)
def update_daily_steps(steps_id: int, steps: DailyStepsUpdate, db: Session = Depends(get_db)):
    """更新步數紀錄"""
    updated = steps_service.update_steps(db, steps_id, steps)
    if not updated:
        raise HTTPException(status_code=404, detail="紀錄不存在")
    return updated


@router.get("/daily-steps/weekly-stats")
def get_weekly_steps_stats(user_id: int, db: Session = Depends(get_db)):
    """獲取本週步數統計"""
    return steps_service.get_weekly_stats(db, user_id)
