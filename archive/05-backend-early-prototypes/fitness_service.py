"""
Block 3: 體重和運動追蹤 - 業務邏輯服務
================================================

包含體重、運動、模板、步數等的業務邏輯
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict

from app.models.fitness import (
    WeightRecord, ExerciseSession, ExerciseDetail, 
    ExerciseItemLibrary, WorkoutTemplate, TemplateDetail,
    DailySteps, YogaStretchItem
)
from app.schemas.fitness import (
    WeightRecordCreate, ExerciseSessionCreate, 
    WorkoutTemplateCreate, DailyStepsCreate,
    ExerciseItemLibraryCreate, YogaStretchItemCreate
)


class WeightService:
    """體重管理服務"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_weight_record(self, data: WeightRecordCreate) -> WeightRecord:
        """創建體重記錄"""
        db_record = WeightRecord(**data.model_dump())
        self.db.add(db_record)
        self.db.commit()
        self.db.refresh(db_record)
        return db_record
    
    def get_weight_records(self, user_id: int, skip: int = 0, limit: int = 10) -> List[WeightRecord]:
        """獲取用戶體重記錄"""
        return self.db.query(WeightRecord).filter(
            WeightRecord.user_id == user_id
        ).order_by(desc(WeightRecord.date)).offset(skip).limit(limit).all()
    
    def get_weight_record(self, record_id: int) -> Optional[WeightRecord]:
        """獲取特定體重記錄"""
        return self.db.query(WeightRecord).filter(WeightRecord.id == record_id).first()
    
    def update_weight_record(self, record_id: int, data: WeightRecordCreate) -> Optional[WeightRecord]:
        """更新體重記錄"""
        db_record = self.get_weight_record(record_id)
        if not db_record:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_record, field, value)
        
        db_record.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(db_record)
        return db_record


class ExerciseService:
    """運動管理服務"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_exercise_session(self, data: ExerciseSessionCreate) -> ExerciseSession:
        """創建運動會話"""
        session_data = data.model_dump(exclude={'details'})
        db_session = ExerciseSession(**session_data)
        
        # 添加訓練詳情
        if data.details:
            for detail in data.details:
                db_detail = ExerciseDetail(**detail.model_dump())
                db_session.details.append(db_detail)
        
        self.db.add(db_session)
        self.db.commit()
        self.db.refresh(db_session)
        return db_session
    
    def get_exercise_sessions(self, user_id: int, skip: int = 0, limit: int = 10) -> List[ExerciseSession]:
        """獲取用戶運動記錄"""
        return self.db.query(ExerciseSession).filter(
            ExerciseSession.user_id == user_id
        ).order_by(desc(ExerciseSession.date)).offset(skip).limit(limit).all()
    
    def get_exercise_session(self, session_id: int) -> Optional[ExerciseSession]:
        """獲取特定運動會話"""
        return self.db.query(ExerciseSession).filter(ExerciseSession.id == session_id).first()
    
    def get_weekly_stats(self, user_id: int) -> Dict:
        """獲取本週運動統計"""
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        
        sessions = self.db.query(ExerciseSession).filter(
            and_(
                ExerciseSession.user_id == user_id,
                ExerciseSession.date >= monday
            )
        ).all()
        
        total_duration = sum(s.duration_min for s in sessions)
        total_calories = sum(s.calories_burned or 0 for s in sessions)
        
        by_type = {}
        by_intensity = {}
        for session in sessions:
            by_type[session.exercise_type] = by_type.get(session.exercise_type, 0) + 1
            by_intensity[session.intensity] = by_intensity.get(session.intensity, 0) + 1
        
        return {
            "week_start": monday.isoformat(),
            "week_end": today.isoformat(),
            "total_sessions": len(sessions),
            "total_duration_min": total_duration,
            "total_calories": total_calories,
            "average_duration": total_duration / len(sessions) if sessions else 0,
            "by_type": by_type,
            "by_intensity": by_intensity
        }


class TemplateService:
    """訓練模板服務"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_template(self, data: WorkoutTemplateCreate) -> WorkoutTemplate:
        """創建訓練模板"""
        template_data = data.model_dump(exclude={'details'})
        db_template = WorkoutTemplate(**template_data)
        
        if data.details:
            for detail in data.details:
                db_detail = TemplateDetail(**detail.model_dump())
                db_template.details.append(db_detail)
        
        self.db.add(db_template)
        self.db.commit()
        self.db.refresh(db_template)
        return db_template
    
    def get_templates(self, user_id: int) -> List[WorkoutTemplate]:
        """獲取用戶的訓練模板"""
        return self.db.query(WorkoutTemplate).filter(
            WorkoutTemplate.user_id == user_id
        ).order_by(desc(WorkoutTemplate.created_at)).all()
    
    def get_template(self, template_id: int) -> Optional[WorkoutTemplate]:
        """獲取特定訓練模板"""
        return self.db.query(WorkoutTemplate).filter(WorkoutTemplate.id == template_id).first()
    
    def apply_template(self, template_id: int, user_id: int, apply_date: date) -> Optional[ExerciseSession]:
        """套用訓練模板為新的運動會話"""
        template = self.get_template(template_id)
        if not template:
            return None
        
        # 創建新的運動會話
        session = ExerciseSession(
            user_id=user_id,
            date=apply_date,
            exercise_type=template.exercise_type,
            duration_min=template.duration_min or 0,
            intensity=template.intensity
        )
        
        # 複製模板詳情到新會話
        for template_detail in template.details:
            detail = ExerciseDetail(
                exercise_name=template_detail.exercise_name,
                sets=template_detail.sets,
                reps=template_detail.reps,
                weight_kg=template_detail.weight_kg,
                notes=template_detail.notes,
                order=template_detail.order
            )
            session.details.append(detail)
        
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session


class StepsService:
    """步數管理服務"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_steps(self, data: DailyStepsCreate) -> DailySteps:
        """記錄每日步數"""
        db_steps = DailySteps(**data.model_dump())
        self.db.add(db_steps)
        self.db.commit()
        self.db.refresh(db_steps)
        return db_steps
    
    def get_steps(self, user_id: int, skip: int = 0, limit: int = 10) -> List[DailySteps]:
        """獲取用戶步數記錄"""
        return self.db.query(DailySteps).filter(
            DailySteps.user_id == user_id
        ).order_by(desc(DailySteps.date)).offset(skip).limit(limit).all()
    
    def get_weekly_stats(self, user_id: int) -> Dict:
        """獲取本週步數統計"""
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        
        steps_records = self.db.query(DailySteps).filter(
            and_(
                DailySteps.user_id == user_id,
                DailySteps.date >= monday
            )
        ).all()
        
        total_steps = sum(s.step_count for s in steps_records)
        total_calories = sum(s.calories_burned or 0 for s in steps_records)
        
        return {
            "week_start": monday.isoformat(),
            "week_end": today.isoformat(),
            "total_days": len(steps_records),
            "total_steps": total_steps,
            "total_calories": total_calories,
            "average_steps": total_steps / len(steps_records) if steps_records else 0,
            "daily_breakdown": [
                {
                    "date": s.date.isoformat(),
                    "steps": s.step_count,
                    "calories": s.calories_burned
                } for s in sorted(steps_records, key=lambda x: x.date)
            ]
        }


class ExerciseItemService:
    """訓練項目庫服務"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_item(self, data: ExerciseItemLibraryCreate) -> ExerciseItemLibrary:
        """添加訓練項目"""
        db_item = ExerciseItemLibrary(**data.model_dump())
        self.db.add(db_item)
        self.db.commit()
        self.db.refresh(db_item)
        return db_item
    
    def get_items(self, skip: int = 0, limit: int = 50) -> List[ExerciseItemLibrary]:
        """獲取訓練項目庫"""
        return self.db.query(ExerciseItemLibrary).offset(skip).limit(limit).all()


class YogaStretchItemService:
    """瑜珈拉伸項目庫服務"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_item(self, data: YogaStretchItemCreate) -> YogaStretchItem:
        """添加瑜珈拉伸項目"""
        db_item = YogaStretchItem(**data.model_dump())
        self.db.add(db_item)
        self.db.commit()
        self.db.refresh(db_item)
        return db_item
    
    def get_items(self, skip: int = 0, limit: int = 50) -> List[YogaStretchItem]:
        """獲取瑜珈拉伸項目庫"""
        return self.db.query(YogaStretchItem).offset(skip).limit(limit).all()
