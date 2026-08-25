from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from database import get_db
from training.schemas import (
    WorkoutTemplateCreate, WorkoutTemplateUpdate, WorkoutTemplateResponse,
    ExerciseItemLibraryCreate, ExerciseItemLibraryUpdate,
    TrainingProgramCreate, TrainingScheduleCreate, TrainingScheduleUpdate,
    TrainingScheduleLinkActual, TrainingTargetsUpdate,
)
from training.services import (
    TemplateService, exercise_item_service,
    TrainingProgramService, TrainingScheduleService, TrainingTargetService, TrainingProgressService,
)

router = APIRouter(tags=["training"])

template_service = TemplateService()
training_program_service = TrainingProgramService()
training_schedule_service = TrainingScheduleService()
training_target_service = TrainingTargetService()
training_progress_service = TrainingProgressService()


@router.post("/workout-templates", response_model=WorkoutTemplateResponse, status_code=201)
def create_workout_template(template: WorkoutTemplateCreate, db: Session = Depends(get_db)):
    """創建訓練模板"""
    try:
        return template_service.create_template(db, template)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/workout-templates", response_model=List[WorkoutTemplateResponse])
def list_workout_templates(user_id: int, db: Session = Depends(get_db)):
    """獲取用戶的訓練模板"""
    return template_service.get_templates(db, user_id)


@router.get("/workout-templates/{template_id}", response_model=WorkoutTemplateResponse)
def get_workout_template(template_id: int, db: Session = Depends(get_db)):
    """獲取特定訓練模板"""
    template = template_service.get_template(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    return template


@router.put("/workout-templates/{template_id}", response_model=WorkoutTemplateResponse)
def update_workout_template(template_id: int, template: WorkoutTemplateUpdate, db: Session = Depends(get_db)):
    """更新訓練模板（含明細整份取代）"""
    try:
        updated = template_service.update_template(db, template_id, template)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not updated:
        raise HTTPException(status_code=404, detail="模板不存在")
    return updated


@router.delete("/workout-templates/{template_id}", status_code=204)
def delete_workout_template(template_id: int, db: Session = Depends(get_db)):
    """刪除訓練模板"""
    success = template_service.delete_template(db, template_id)
    if not success:
        raise HTTPException(status_code=404, detail="模板不存在")
    return None


def _validate_item_type(item_type: str):
    if item_type not in ("gym", "yoga_stretch"):
        raise HTTPException(status_code=400, detail="type 必須是 gym 或 yoga_stretch")


@router.get("/exercise-items")
def list_exercise_items(type: str, category: Optional[str] = None, muscle_group: Optional[str] = None,
                         user_id: Optional[int] = None, db: Session = Depends(get_db)):
    """列出動作庫項目（健身房動作 / 瑜珈拉伸），帶 user_id 時依個人使用頻率排序"""
    _validate_item_type(type)
    return exercise_item_service.list_items(db, type, category=category, muscle_group=muscle_group, user_id=user_id)


@router.get("/exercise-items/search")
def search_exercise_items(type: str, q: str = "", category: Optional[str] = None,
                           user_id: Optional[int] = None, limit: int = 10, db: Session = Depends(get_db)):
    """動作庫自動完成搜尋，可另外帶 category 縮小範圍"""
    _validate_item_type(type)
    return exercise_item_service.search_items(db, type, q, category=category, user_id=user_id, limit=limit)


@router.post("/exercise-items", status_code=201)
def create_exercise_item(payload: ExerciseItemLibraryCreate, db: Session = Depends(get_db)):
    """新增自訂項目到共用動作庫"""
    _validate_item_type(payload.type)
    return exercise_item_service.create_item(db, payload.type, payload.model_dump())


@router.get("/exercise-items/{item_type}/{item_id}")
def get_exercise_item(item_type: str, item_id: int, db: Session = Depends(get_db)):
    """取得單一動作庫項目"""
    _validate_item_type(item_type)
    item = exercise_item_service.get_item(db, item_type, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="項目不存在")
    return item


@router.put("/exercise-items/{item_type}/{item_id}")
def update_exercise_item(item_type: str, item_id: int, payload: ExerciseItemLibraryUpdate, db: Session = Depends(get_db)):
    """更新動作庫項目的基本資料與備註（全體共用）"""
    _validate_item_type(item_type)
    item = exercise_item_service.update_item(db, item_type, item_id, payload.model_dump())
    if not item:
        raise HTTPException(status_code=404, detail="項目不存在")
    return item


@router.get("/exercise-items/{item_type}/{item_id}/history")
def get_exercise_item_history(item_type: str, item_id: int, user_id: int, db: Session = Depends(get_db)):
    """單一使用者對這個動作庫項目的歷史紀錄，依日期彙總成訓練量序列"""
    _validate_item_type(item_type)
    if not exercise_item_service.item_exists(db, item_type, item_id):
        raise HTTPException(status_code=404, detail="項目不存在")
    return exercise_item_service.get_user_history(db, item_type, item_id, user_id)


@router.post("/training-programs", status_code=201)
def create_training_program(program: TrainingProgramCreate, db: Session = Depends(get_db)):
    """一次建立整個計畫（含 N 天，每天各自建立一個 workout_templates）"""
    try:
        return training_program_service.create_program(db, program)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/training-programs")
def list_training_programs(user_id: int, db: Session = Depends(get_db)):
    """列出使用者的所有計畫（含每天摘要）"""
    return training_program_service.get_programs(db, user_id)


@router.get("/training-programs/{program_id}")
def get_training_program(program_id: int, db: Session = Depends(get_db)):
    """取得單一計畫完整內容"""
    program = training_program_service.get_program(db, program_id)
    if not program:
        raise HTTPException(status_code=404, detail="計畫不存在")
    return program


@router.delete("/training-programs/{program_id}", status_code=204)
def delete_training_program(program_id: int, db: Session = Depends(get_db)):
    """刪除整個計畫（連動刪除天數與已排上月曆的排程；範本本身不動）"""
    success = training_program_service.delete_program(db, program_id)
    if not success:
        raise HTTPException(status_code=404, detail="計畫不存在")
    return None


@router.post("/training-schedule", status_code=201)
def create_training_schedule(schedule: TrainingScheduleCreate, db: Session = Depends(get_db)):
    """把某個 program_day 排到某個日期"""
    try:
        return training_schedule_service.create_schedule(db, schedule.program_day_id, schedule.scheduled_date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/training-schedule/{schedule_id}")
def update_training_schedule(schedule_id: int, schedule: TrainingScheduleUpdate, db: Session = Depends(get_db)):
    """搬到另一天，或手動改狀態（例如標記「已跳過」）"""
    try:
        updated = training_schedule_service.update_schedule(
            db, schedule_id, scheduled_date=schedule.scheduled_date, status=schedule.status
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not updated:
        raise HTTPException(status_code=404, detail="排程不存在")
    return updated


@router.delete("/training-schedule/{schedule_id}", status_code=204)
def delete_training_schedule(schedule_id: int, db: Session = Depends(get_db)):
    """從月曆移除排程（不影響計畫本身）"""
    success = training_schedule_service.delete_schedule(db, schedule_id)
    if not success:
        raise HTTPException(status_code=404, detail="排程不存在")
    return None


@router.get("/training-schedule")
def list_training_schedule(user_id: int, month: str, db: Session = Depends(get_db)):
    """取得該月所有排程，給月曆畫面一次渲染；month 格式 YYYY-MM"""
    return training_schedule_service.list_schedule(db, user_id, month)


@router.get("/training-schedule/{schedule_id}")
def get_training_schedule(schedule_id: int, db: Session = Depends(get_db)):
    """取得單一排程（含所屬計畫/範本資訊），給「補登實際紀錄」深連結預填表單用"""
    schedule = training_schedule_service.get_schedule(db, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="排程不存在")
    return schedule


@router.put("/training-schedule/{schedule_id}/link-actual")
def link_actual_schedule(schedule_id: int, payload: TrainingScheduleLinkActual, db: Session = Depends(get_db)):
    """執行完後，把當天實際紀錄的 exercise_session_id 綁回排程"""
    try:
        result = training_schedule_service.link_actual(db, schedule_id, payload.exercise_session_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if result is None:
        raise HTTPException(status_code=404, detail="排程不存在")
    return result


@router.get("/training-targets")
def get_training_targets(user_id: int, db: Session = Depends(get_db)):
    """每週訓練目標，永遠回傳完整 8 個分類（沒設定過的補預設值 2）"""
    return training_target_service.get_targets(db, user_id)


@router.put("/training-targets")
def set_training_targets(user_id: int, payload: TrainingTargetsUpdate, db: Session = Depends(get_db)):
    """設定每週訓練目標"""
    try:
        return training_target_service.set_targets(db, user_id, payload.targets)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/training-progress")
def get_training_progress(user_id: int, week_start: Optional[date] = None, db: Session = Depends(get_db)):
    """本週達成度：每分類次數 vs 目標；健身房六分類另外附本週/上週訓練量"""
    return training_progress_service.get_weekly_progress(db, user_id, week_start)
