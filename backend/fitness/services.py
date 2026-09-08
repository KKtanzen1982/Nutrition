from sqlalchemy.orm import Session
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict

from fitness.models import WeightRecord, ExerciseSession, ExerciseDetail, DailySteps
from training.services import _validate_and_track_library_usage


class WeightService:
    """體重服務"""

    def create_weight_record(self, db: Session, data) -> WeightRecord:
        record = WeightRecord(**data.model_dump())
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    def get_weight_records(self, db: Session, user_id: int, skip: int = 0, limit: int = 10) -> List[WeightRecord]:
        return (
            db.query(WeightRecord)
            .filter(WeightRecord.user_id == user_id)
            .order_by(WeightRecord.date.desc())
            .offset(skip).limit(limit).all()
        )

    def get_weight_record(self, db: Session, record_id: int) -> Optional[WeightRecord]:
        return db.get(WeightRecord, record_id)

    def update_weight_record(self, db: Session, record_id: int, data) -> Optional[WeightRecord]:
        record = db.get(WeightRecord, record_id)
        if not record:
            return None
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(record, k, v)
        record.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(record)
        return record

    def delete_weight_record(self, db: Session, record_id: int) -> bool:
        record = db.get(WeightRecord, record_id)
        if not record:
            return False
        db.delete(record)
        db.commit()
        return True


class ExerciseService:
    """運動服務"""

    def create_exercise_session(self, db: Session, data) -> ExerciseSession:
        payload = data.model_dump()
        details = payload.pop("details", None) or []
        session = ExerciseSession(**payload)
        db.add(session)
        db.flush()  # 拿到 session.id 供明細的 FK 使用

        _validate_and_track_library_usage(db, session.user_id, details)
        for i, detail in enumerate(details, start=1):
            detail["order"] = detail.get("order") or i
            db.add(ExerciseDetail(session_id=session.id, **detail))

        db.commit()
        db.refresh(session)
        return session

    def get_exercise_sessions(self, db: Session, user_id: int, skip: int = 0, limit: int = 10) -> List[ExerciseSession]:
        return (
            db.query(ExerciseSession)
            .filter(ExerciseSession.user_id == user_id)
            .order_by(ExerciseSession.date.desc())
            .offset(skip).limit(limit).all()
        )

    def get_exercise_session(self, db: Session, session_id: int) -> Optional[ExerciseSession]:
        return db.get(ExerciseSession, session_id)

    def update_exercise_session(self, db: Session, session_id: int, data) -> Optional[ExerciseSession]:
        """更新運動紀錄；帶 details 就整份取代明細"""
        session = db.get(ExerciseSession, session_id)
        if not session:
            return None

        update_data = data.model_dump(exclude_unset=True, exclude={"details"})
        for k, v in update_data.items():
            setattr(session, k, v)

        if data.details is not None:
            details = [d.model_dump() for d in data.details]
            _validate_and_track_library_usage(db, session.user_id, details)
            for d in session.details:
                db.delete(d)
            db.flush()
            for i, detail in enumerate(details, start=1):
                detail["order"] = detail.get("order") or i
                db.add(ExerciseDetail(session_id=session.id, **detail))

        session.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(session)
        return session

    def delete_exercise_session(self, db: Session, session_id: int) -> bool:
        session = db.get(ExerciseSession, session_id)
        if not session:
            return False
        db.delete(session)
        db.commit()
        return True

    def get_weekly_stats(self, db: Session, user_id: int) -> Dict:
        today = date.today()
        monday = today - timedelta(days=today.weekday())

        sessions = (
            db.query(ExerciseSession)
            .filter(ExerciseSession.user_id == user_id, ExerciseSession.date >= monday)
            .all()
        )

        total_duration = sum(e.duration_min or 0 for e in sessions)
        total_calories = sum(e.calories_burned for e in sessions if e.calories_burned)

        return {
            "week_start": monday.isoformat(),
            "week_end": today.isoformat(),
            "total_sessions": len(sessions),
            "total_duration_min": total_duration,
            "total_calories": total_calories,
            "average_duration": total_duration / len(sessions) if sessions else 0,
        }


class StepsService:
    """步數服務"""

    def create_steps(self, db: Session, data) -> DailySteps:
        """記錄步數；同一使用者同一天已有紀錄時拒絕重複建立（前端應改呼叫更新）"""
        if self.get_by_user_and_date(db, data.user_id, data.date):
            raise ValueError(f"使用者 {data.user_id} 在 {data.date} 已經有步數紀錄，請改用更新")
        steps = DailySteps(**data.model_dump())
        db.add(steps)
        db.commit()
        db.refresh(steps)
        return steps

    def get_by_user_and_date(self, db: Session, user_id: int, target_date) -> Optional[DailySteps]:
        return db.query(DailySteps).filter(
            DailySteps.user_id == user_id, DailySteps.date == target_date
        ).first()

    def update_steps(self, db: Session, steps_id: int, data) -> Optional[DailySteps]:
        """更新步數紀錄"""
        steps = db.get(DailySteps, steps_id)
        if not steps:
            return None
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(steps, k, v)
        steps.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(steps)
        return steps

    def delete_steps(self, db: Session, steps_id: int) -> bool:
        steps = db.get(DailySteps, steps_id)
        if not steps:
            return False
        db.delete(steps)
        db.commit()
        return True

    def get_steps(self, db: Session, user_id: int, skip: int = 0, limit: int = 10) -> List[DailySteps]:
        return (
            db.query(DailySteps)
            .filter(DailySteps.user_id == user_id)
            .order_by(DailySteps.date.desc())
            .offset(skip).limit(limit).all()
        )

    def get_weekly_stats(self, db: Session, user_id: int) -> Dict:
        today = date.today()
        monday = today - timedelta(days=today.weekday())

        steps_records = (
            db.query(DailySteps)
            .filter(DailySteps.user_id == user_id, DailySteps.date >= monday)
            .all()
        )

        total_steps = sum(s.step_count or 0 for s in steps_records)

        return {
            "week_start": monday.isoformat(),
            "week_end": today.isoformat(),
            "total_days": len(steps_records),
            "total_steps": total_steps,
            "average_steps": total_steps / len(steps_records) if steps_records else 0,
        }
