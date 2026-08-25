from sqlalchemy.orm import Session
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict

from training.schemas import WorkoutTemplateCreate
from training.models import (
    WorkoutTemplate, TemplateDetail, ExerciseItemLibrary, YogaStretchItem, UserItemUsage,
    TrainingProgram, TrainingProgramDay, TrainingSchedule, TrainingTarget,
)
from fitness.models import ExerciseSession, ExerciseDetail

TRAINING_CATEGORIES = ["胸部", "背部", "下肢", "手臂", "核心", "有氧", "瑜珈", "拉伸"]
DEFAULT_WEEKLY_TARGET = 2


def _parse_reps_average(reps: Optional[str]) -> Optional[float]:
    """把「8-10」這種次數區間換成平均值；純數字直接回傳；無法解析回傳 None。"""
    if not reps:
        return None
    parts = reps.strip().replace("~", "-").split("-")
    try:
        numbers = [float(p.strip()) for p in parts if p.strip()]
    except ValueError:
        return None
    if not numbers:
        return None
    return sum(numbers) / len(numbers)


def _details_volume(details) -> float:
    """details 是 ExerciseDetail/TemplateDetail 的 ORM 物件列表"""
    total = 0.0
    for d in details or []:
        avg_reps = _parse_reps_average(d.reps)
        if d.sets is not None and avg_reps is not None:
            weight = d.weight_kg or 1
            total += d.sets * avg_reps * weight
        elif d.duration_min:
            total += d.duration_min
    return total


def _detail_to_dict(d) -> Dict:
    return {
        "id": d.id,
        "exercise_name": d.exercise_name,
        "sets": d.sets,
        "reps": d.reps,
        "weight_kg": d.weight_kg,
        "duration_min": d.duration_min,
        "notes": d.notes,
        "order": d.order,
        "exercise_item_id": d.exercise_item_id,
        "yoga_stretch_item_id": d.yoga_stretch_item_id,
    }


def _template_to_dict(t: WorkoutTemplate) -> Dict:
    return {
        "id": t.id,
        "user_id": t.user_id,
        "template_name": t.template_name,
        "description": t.description,
        "exercise_type": t.exercise_type,
        "duration_min": t.duration_min,
        "details": [_detail_to_dict(d) for d in t.details],
        "created_at": t.created_at,
        "updated_at": t.updated_at,
    }


class ExerciseItemService:
    """動作庫服務（健身房動作庫 + 瑜珈/拉伸庫），兩張庫全體共用一份，
    依 user_id 的個人使用頻率調整搜尋排序。"""

    def _model(self, item_type: str):
        if item_type == "gym":
            return ExerciseItemLibrary
        if item_type == "yoga_stretch":
            return YogaStretchItem
        raise ValueError("type 必須是 gym 或 yoga_stretch")

    def _item_to_dict(self, item_type: str, item) -> Dict:
        if item_type == "gym":
            return {
                "id": item.id, "item_name": item.item_name, "category": item.category,
                "muscle_group": item.muscle_group, "equipment": item.equipment,
                "default_sets": item.default_sets, "default_reps": item.default_reps,
                "description": item.description, "is_active": item.is_active,
                "created_at": item.created_at,
            }
        return {
            "id": item.id, "item_name": item.item_name, "type": item.type,
            "duration_min": item.duration_min, "difficulty": item.difficulty,
            "description": item.description, "created_at": item.created_at,
        }

    def _usage_counts(self, db: Session, user_id: Optional[int], item_type: str) -> Dict[int, int]:
        if user_id is None:
            return {}
        rows = db.query(UserItemUsage).filter(
            UserItemUsage.user_id == user_id, UserItemUsage.item_type == item_type
        ).all()
        return {r.item_id: r.use_count for r in rows}

    def list_items(self, db: Session, item_type: str, category: Optional[str] = None,
                    muscle_group: Optional[str] = None, user_id: Optional[int] = None):
        model = self._model(item_type)
        category_attr = model.category if item_type == "gym" else model.type
        query = db.query(model).filter(model.is_active == True) if item_type == "gym" else db.query(model)
        if category:
            query = query.filter(category_attr == category)
        if muscle_group:
            query = query.filter(model.muscle_group == muscle_group)
        items = query.all()
        usage = self._usage_counts(db, user_id, item_type)
        items.sort(key=lambda i: (-usage.get(i.id, 0), i.item_name))
        return [self._item_to_dict(item_type, i) for i in items]

    def search_items(self, db: Session, item_type: str, query: str, category: Optional[str] = None,
                      user_id: Optional[int] = None, limit: int = 10):
        model = self._model(item_type)
        category_attr = model.category if item_type == "gym" else model.type
        q = db.query(model).filter(model.is_active == True) if item_type == "gym" else db.query(model)
        if category:
            q = q.filter(category_attr == category)
        items = q.all()
        query_lower = (query or "").strip().lower()
        if query_lower:
            items = [i for i in items if query_lower in i.item_name.lower()]
        usage = self._usage_counts(db, user_id, item_type)

        def sort_key(i):
            name = i.item_name.lower()
            relevance = 0 if name.startswith(query_lower) else 1
            return (relevance, -usage.get(i.id, 0), name)

        items.sort(key=sort_key)
        return [self._item_to_dict(item_type, i) for i in items[:limit]]

    def create_item(self, db: Session, item_type: str, payload: Dict):
        model = self._model(item_type)
        item_name = payload["item_name"]
        existing = db.query(model).filter(model.item_name == item_name).first()
        if existing:
            return self._item_to_dict(item_type, existing)

        if item_type == "gym":
            item = ExerciseItemLibrary(
                item_name=item_name,
                category=payload.get("category") or "其他",
                muscle_group=payload.get("muscle_group"),
                equipment=payload.get("equipment"),
                default_sets=payload.get("default_sets"),
                default_reps=payload.get("default_reps"),
                description=payload.get("description"),
                is_active=True,
            )
        else:
            item = YogaStretchItem(
                item_name=item_name,
                type=payload.get("yoga_type") or "瑜珈",
                duration_min=payload.get("duration_min"),
                difficulty=payload.get("difficulty"),
                description=payload.get("description"),
            )
        db.add(item)
        db.commit()
        db.refresh(item)
        return self._item_to_dict(item_type, item)

    def item_exists(self, db: Session, item_type: str, item_id: int) -> bool:
        model = self._model(item_type)
        return db.get(model, item_id) is not None

    def get_item(self, db: Session, item_type: str, item_id: int):
        model = self._model(item_type)
        item = db.get(model, item_id)
        return self._item_to_dict(item_type, item) if item else None

    def update_item(self, db: Session, item_type: str, item_id: int, payload: Dict):
        model = self._model(item_type)
        item = db.get(model, item_id)
        if not item:
            return None
        fields = ("category", "muscle_group", "equipment", "default_sets", "default_reps", "description") \
            if item_type == "gym" else ("type", "duration_min", "difficulty", "description")
        for key in fields:
            if key in payload and payload[key] is not None:
                setattr(item, key, payload[key])
        db.commit()
        db.refresh(item)
        return self._item_to_dict(item_type, item)

    def get_user_history(self, db: Session, item_type: str, item_id: int, user_id: int):
        """單一使用者對某個動作庫項目的歷史紀錄，依日期彙總成訓練量序列。
        健身房：組數 x 次數區間平均 x 重量（徒手動作無重量時以 1 計，退化成純次數量）；
        瑜珈/拉伸：當天累計時長（分鐘）。"""
        id_attr = ExerciseDetail.exercise_item_id if item_type == "gym" else ExerciseDetail.yoga_stretch_item_id
        rows = (
            db.query(ExerciseSession, ExerciseDetail)
            .join(ExerciseDetail, ExerciseDetail.session_id == ExerciseSession.id)
            .filter(ExerciseSession.user_id == user_id, id_attr == item_id)
            .all()
        )
        totals: Dict = {}
        for session, detail in rows:
            session_date = session.date
            if item_type == "gym":
                avg_reps = _parse_reps_average(detail.reps)
                if detail.sets is None or avg_reps is None:
                    continue
                weight = detail.weight_kg or 1
                volume = detail.sets * avg_reps * weight
            else:
                volume = detail.duration_min or 0
            totals[session_date] = totals.get(session_date, 0) + volume

        return [{"date": d, "volume": round(v, 1)} for d, v in sorted(totals.items())]

    def record_usage(self, db: Session, user_id: int, item_type: str, item_id: int):
        record = db.get(UserItemUsage, (user_id, item_type, item_id))
        now = datetime.utcnow()
        if record:
            record.use_count += 1
            record.last_used_at = now
        else:
            db.add(UserItemUsage(
                user_id=user_id, item_type=item_type, item_id=item_id,
                use_count=1, last_used_at=now,
            ))
        db.commit()


exercise_item_service = ExerciseItemService()


def _validate_and_track_library_usage(db: Session, user_id: int, details: List[Dict]):
    """明細若引用動作庫項目，驗證存在性並累計該使用者的使用次數；
    找不到對應項目時丟出 ValueError，由 API 層轉成 400。"""
    for detail in details or []:
        exercise_item_id = detail.get("exercise_item_id")
        if exercise_item_id is not None:
            if not exercise_item_service.item_exists(db, "gym", exercise_item_id):
                raise ValueError(f"exercise_item_id {exercise_item_id} 不存在")
            exercise_item_service.record_usage(db, user_id, "gym", exercise_item_id)

        yoga_stretch_item_id = detail.get("yoga_stretch_item_id")
        if yoga_stretch_item_id is not None:
            if not exercise_item_service.item_exists(db, "yoga_stretch", yoga_stretch_item_id):
                raise ValueError(f"yoga_stretch_item_id {yoga_stretch_item_id} 不存在")
            exercise_item_service.record_usage(db, user_id, "yoga_stretch", yoga_stretch_item_id)


class TemplateService:
    """訓練模板服務"""

    def create_template(self, db: Session, data) -> WorkoutTemplate:
        payload = data.model_dump()
        details = payload.pop("details", None) or []
        template = WorkoutTemplate(**payload)
        db.add(template)
        db.flush()

        _validate_and_track_library_usage(db, template.user_id, details)
        for i, detail in enumerate(details, start=1):
            detail["order"] = detail.get("order") or i
            db.add(TemplateDetail(template_id=template.id, **detail))

        db.commit()
        db.refresh(template)
        return template

    def get_templates(self, db: Session, user_id: int) -> List[WorkoutTemplate]:
        return db.query(WorkoutTemplate).filter(WorkoutTemplate.user_id == user_id).all()

    def get_template(self, db: Session, template_id: int) -> Optional[WorkoutTemplate]:
        return db.get(WorkoutTemplate, template_id)

    def update_template(self, db: Session, template_id: int, data) -> Optional[WorkoutTemplate]:
        """更新訓練模板；帶 details 就整份取代明細"""
        template = db.get(WorkoutTemplate, template_id)
        if not template:
            return None

        update_data = data.model_dump(exclude_unset=True, exclude={"details"})
        for k, v in update_data.items():
            setattr(template, k, v)

        if data.details is not None:
            details = [d.model_dump() for d in data.details]
            _validate_and_track_library_usage(db, template.user_id, details)
            for d in template.details:
                db.delete(d)
            db.flush()
            for i, detail in enumerate(details, start=1):
                detail["order"] = detail.get("order") or i
                db.add(TemplateDetail(template_id=template.id, **detail))

        template.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(template)
        return template

    def delete_template(self, db: Session, template_id: int) -> bool:
        template = db.get(WorkoutTemplate, template_id)
        if not template:
            return False
        db.delete(template)
        db.commit()
        return True


class TrainingProgramService:
    """訓練計畫服務：多天計畫的每一天就是一個既有的 workout_templates，
    這裡只負責把好幾天綁在一起，不重造一套平行的動作清單編輯器。"""

    def __init__(self):
        self.template_service = TemplateService()

    def _expand_program(self, db: Session, program: TrainingProgram) -> Dict:
        day_rows = (
            db.query(TrainingProgramDay)
            .filter(TrainingProgramDay.program_id == program.id)
            .order_by(TrainingProgramDay.day_number)
            .all()
        )
        days = []
        for d in day_rows:
            template = db.get(WorkoutTemplate, d.workout_template_id)
            days.append({
                "id": d.id, "program_id": d.program_id, "day_number": d.day_number,
                "day_label": d.day_label, "workout_template_id": d.workout_template_id,
                "template": _template_to_dict(template) if template else None,
            })
        return {
            "id": program.id, "user_id": program.user_id, "program_name": program.program_name,
            "day_count": program.day_count, "description": program.description,
            "created_at": program.created_at, "days": days,
        }

    def create_program(self, db: Session, data) -> Dict:
        """一次建立整個計畫：依序幫每一天各自建立一個 workout_templates，再建立 program + program_days 把它們綁起來。
        先把每一天的動作庫引用都驗證過一輪，任何一筆無效就整批都不建立，避免半成品計畫殘留。"""
        for day in data.days:
            for detail in day.details or []:
                if detail.exercise_item_id is not None and not exercise_item_service.item_exists(db, "gym", detail.exercise_item_id):
                    raise ValueError(f"exercise_item_id {detail.exercise_item_id} 不存在")
                if detail.yoga_stretch_item_id is not None and not exercise_item_service.item_exists(db, "yoga_stretch", detail.yoga_stretch_item_id):
                    raise ValueError(f"yoga_stretch_item_id {detail.yoga_stretch_item_id} 不存在")

        program = TrainingProgram(
            user_id=data.user_id, program_name=data.program_name,
            day_count=len(data.days), description=data.description,
        )
        db.add(program)
        db.flush()

        for day in data.days:
            template_create = WorkoutTemplateCreate(
                user_id=data.user_id,
                template_name=day.day_label or f"{data.program_name} · Day{day.day_number}",
                description=None,
                exercise_type=day.exercise_type,
                duration_min=day.duration_min,
                details=day.details,
            )
            template = self.template_service.create_template(db, template_create)
            db.add(TrainingProgramDay(
                program_id=program.id, day_number=day.day_number,
                day_label=day.day_label, workout_template_id=template.id,
            ))

        db.commit()
        db.refresh(program)
        return self._expand_program(db, program)

    def get_programs(self, db: Session, user_id: int) -> List[Dict]:
        programs = db.query(TrainingProgram).filter(TrainingProgram.user_id == user_id).all()
        return [self._expand_program(db, p) for p in programs]

    def get_program(self, db: Session, program_id: int) -> Optional[Dict]:
        program = db.get(TrainingProgram, program_id)
        if not program:
            return None
        return self._expand_program(db, program)

    def delete_program(self, db: Session, program_id: int) -> bool:
        """刪除整個計畫：連動刪除 program_days 與已排上月曆的 schedule；範本本身不動（共用資源）"""
        program = db.get(TrainingProgram, program_id)
        if not program:
            return False
        day_ids = [d.id for d in db.query(TrainingProgramDay).filter(TrainingProgramDay.program_id == program_id)]
        if day_ids:
            db.query(TrainingSchedule).filter(TrainingSchedule.program_day_id.in_(day_ids)).delete(synchronize_session=False)
            db.query(TrainingProgramDay).filter(TrainingProgramDay.program_id == program_id).delete(synchronize_session=False)
        db.delete(program)
        db.commit()
        return True


class TrainingScheduleService:
    """月曆排程服務：把某個 program_day 貼到實際日期上"""

    def _expand_schedule(self, db: Session, schedule: TrainingSchedule) -> Dict:
        program_day = db.get(TrainingProgramDay, schedule.program_day_id)
        program = db.get(TrainingProgram, program_day.program_id) if program_day else None
        return {
            "id": schedule.id, "user_id": schedule.user_id, "program_day_id": schedule.program_day_id,
            "scheduled_date": schedule.scheduled_date, "status": schedule.status,
            "actual_exercise_session_id": schedule.actual_exercise_session_id,
            "volume_adjustment_pct": schedule.volume_adjustment_pct, "created_at": schedule.created_at,
            "day_label": program_day.day_label if program_day else None,
            "workout_template_id": program_day.workout_template_id if program_day else None,
            "program_id": program.id if program else None,
            "program_name": program.program_name if program else None,
        }

    def _assert_date_free(self, db: Session, user_id: int, scheduled_date, exclude_schedule_id: Optional[int] = None):
        q = db.query(TrainingSchedule).filter(
            TrainingSchedule.user_id == user_id, TrainingSchedule.scheduled_date == scheduled_date
        )
        if exclude_schedule_id is not None:
            q = q.filter(TrainingSchedule.id != exclude_schedule_id)
        if q.first():
            raise ValueError(f"使用者 {user_id} 在 {scheduled_date} 已經有排程，同一天只能排一個訓練日")

    def create_schedule(self, db: Session, program_day_id: int, scheduled_date) -> Dict:
        program_day = db.get(TrainingProgramDay, program_day_id)
        if not program_day:
            raise ValueError(f"program_day_id {program_day_id} 不存在")
        program = db.get(TrainingProgram, program_day.program_id)
        user_id = program.user_id
        self._assert_date_free(db, user_id, scheduled_date)

        schedule = TrainingSchedule(
            user_id=user_id, program_day_id=program_day_id, scheduled_date=scheduled_date,
            status="已排程", actual_exercise_session_id=None, volume_adjustment_pct=None,
        )
        db.add(schedule)
        db.commit()
        db.refresh(schedule)
        return self._expand_schedule(db, schedule)

    def update_schedule(self, db: Session, schedule_id: int, scheduled_date=None, status=None) -> Optional[Dict]:
        schedule = db.get(TrainingSchedule, schedule_id)
        if not schedule:
            return None
        if scheduled_date is not None and scheduled_date != schedule.scheduled_date:
            self._assert_date_free(db, schedule.user_id, scheduled_date, exclude_schedule_id=schedule_id)
            schedule.scheduled_date = scheduled_date
        if status is not None:
            schedule.status = status
        db.commit()
        db.refresh(schedule)
        return self._expand_schedule(db, schedule)

    def link_actual(self, db: Session, schedule_id: int, exercise_session_id: int) -> Optional[Dict]:
        """執行完後，把實際紀錄的 session 綁回排程；狀態轉「已完成」；實際量不如範本基準時，
        把落後的量以 advisory 的形式分攤給這輪剩下還沒執行的天，不動共用範本本身。"""
        schedule = db.get(TrainingSchedule, schedule_id)
        if not schedule:
            return None
        session = db.get(ExerciseSession, exercise_session_id)
        if not session:
            raise ValueError(f"運動紀錄 {exercise_session_id} 不存在")
        if session.user_id != schedule.user_id:
            raise ValueError("運動紀錄與排程不屬於同一使用者")
        schedule.actual_exercise_session_id = exercise_session_id
        schedule.status = "已完成"
        db.flush()
        self._apply_adaptive_rebalancing(db, schedule, session)
        db.commit()
        db.refresh(schedule)
        return self._expand_schedule(db, schedule)

    def _apply_adaptive_rebalancing(self, db: Session, schedule: TrainingSchedule, session: ExerciseSession):
        program_day = db.get(TrainingProgramDay, schedule.program_day_id)
        if not program_day:
            return
        template = db.get(WorkoutTemplate, program_day.workout_template_id)
        if not template:
            return

        baseline_volume = _details_volume(template.details)
        actual_volume = _details_volume(session.details)
        if baseline_volume <= 0 or actual_volume >= baseline_volume:
            return
        deficit_pct = (baseline_volume - actual_volume) / baseline_volume

        program = db.get(TrainingProgram, program_day.program_id)
        if not program:
            return
        day_count = program.day_count

        program_day_ids = [d.id for d in db.query(TrainingProgramDay).filter(TrainingProgramDay.program_id == program.id)]
        round_rows = (
            db.query(TrainingSchedule)
            .filter(TrainingSchedule.program_day_id.in_(program_day_ids))
            .order_by(TrainingSchedule.scheduled_date)
            .all()
        )
        row_ids = [s.id for s in round_rows]
        if schedule.id not in row_ids:
            return
        chunk_index = row_ids.index(schedule.id) // day_count
        round_chunk = round_rows[chunk_index * day_count: (chunk_index + 1) * day_count]

        remaining = [
            s for s in round_chunk
            if s.status == "已排程" and s.scheduled_date > schedule.scheduled_date
        ]
        if not remaining:
            return
        share = deficit_pct / len(remaining)
        for s in remaining:
            s.volume_adjustment_pct = (s.volume_adjustment_pct or 0) + share

    def delete_schedule(self, db: Session, schedule_id: int) -> bool:
        schedule = db.get(TrainingSchedule, schedule_id)
        if not schedule:
            return False
        db.delete(schedule)
        db.commit()
        return True

    def list_schedule(self, db: Session, user_id: int, month: str) -> List[Dict]:
        """month 格式 'YYYY-MM'"""
        rows = (
            db.query(TrainingSchedule)
            .filter(TrainingSchedule.user_id == user_id)
            .order_by(TrainingSchedule.scheduled_date)
            .all()
        )
        results = [self._expand_schedule(db, s) for s in rows if s.scheduled_date.isoformat().startswith(month)]
        return results

    def get_schedule(self, db: Session, schedule_id: int) -> Optional[Dict]:
        schedule = db.get(TrainingSchedule, schedule_id)
        return self._expand_schedule(db, schedule) if schedule else None


class TrainingTargetService:
    """每週訓練目標服務：每個分類各自一個每週次數目標，各使用者獨立"""

    def get_targets(self, db: Session, user_id: int) -> List[Dict]:
        """永遠回傳完整 8 筆，沒設定過的分類補預設值"""
        rows = {
            t.category: t for t in
            db.query(TrainingTarget).filter(TrainingTarget.user_id == user_id).all()
        }
        return [
            {
                "user_id": user_id,
                "category": category,
                "weekly_target_count": rows[category].weekly_target_count if category in rows else DEFAULT_WEEKLY_TARGET,
            }
            for category in TRAINING_CATEGORIES
        ]

    def set_targets(self, db: Session, user_id: int, targets: List) -> List[Dict]:
        for item in targets:
            if item.category not in TRAINING_CATEGORIES:
                raise ValueError(f"category 必須是 {TRAINING_CATEGORIES} 其中之一")
        for item in targets:
            row = db.query(TrainingTarget).filter(
                TrainingTarget.user_id == user_id, TrainingTarget.category == item.category
            ).first()
            if row:
                row.weekly_target_count = item.weekly_target_count
            else:
                db.add(TrainingTarget(
                    user_id=user_id, category=item.category, weekly_target_count=item.weekly_target_count,
                ))
        db.commit()
        return self.get_targets(db, user_id)


class TrainingProgressService:
    """每週達成度服務：每分類次數 vs 目標，健身房六分類的量另外跟上週比"""

    GYM_CATEGORIES = [c for c in TRAINING_CATEGORIES if c not in ("瑜珈", "拉伸")]

    def __init__(self):
        self.target_service = TrainingTargetService()

    def _category_of_detail(self, db: Session, detail: ExerciseDetail) -> Optional[str]:
        if detail.exercise_item_id is not None:
            item = db.get(ExerciseItemLibrary, detail.exercise_item_id)
            return item.category if item else None
        if detail.yoga_stretch_item_id is not None:
            item = db.get(YogaStretchItem, detail.yoga_stretch_item_id)
            return item.type if item else None
        return None

    def _week_sessions(self, db: Session, user_id: int, week_start, week_end) -> List[ExerciseSession]:
        return (
            db.query(ExerciseSession)
            .filter(
                ExerciseSession.user_id == user_id,
                ExerciseSession.date >= week_start,
                ExerciseSession.date <= week_end,
            )
            .all()
        )

    def _week_category_counts(self, db: Session, user_id: int, week_start, week_end) -> Dict[str, int]:
        """每分類本週次數：distinct 日期，該天有對應分類的動作庫項目被引用"""
        dates_by_category: Dict[str, set] = {}
        for session in self._week_sessions(db, user_id, week_start, week_end):
            for detail in session.details:
                category = self._category_of_detail(db, detail)
                if category:
                    dates_by_category.setdefault(category, set()).add(session.date)
        return {cat: len(dates) for cat, dates in dates_by_category.items()}

    def _week_volume_by_category(self, db: Session, user_id: int, week_start, week_end) -> Dict[str, float]:
        """健身房分類各自的訓練量加總（sets x 次數區間平均 x 重量）"""
        totals: Dict[str, float] = {}
        for session in self._week_sessions(db, user_id, week_start, week_end):
            for detail in session.details:
                if detail.exercise_item_id is None:
                    continue
                item = db.get(ExerciseItemLibrary, detail.exercise_item_id)
                if not item:
                    continue
                avg_reps = _parse_reps_average(detail.reps)
                if detail.sets is None or avg_reps is None:
                    continue
                weight = detail.weight_kg or 1
                totals[item.category] = totals.get(item.category, 0) + detail.sets * avg_reps * weight
        return totals

    def get_weekly_progress(self, db: Session, user_id: int, week_start=None) -> Dict:
        if week_start is None:
            today_ = date.today()
            week_start = today_ - timedelta(days=today_.weekday())
        week_end = week_start + timedelta(days=6)
        prev_week_start = week_start - timedelta(days=7)
        prev_week_end = week_start - timedelta(days=1)

        targets = {t["category"]: t["weekly_target_count"] for t in self.target_service.get_targets(db, user_id)}
        this_week_counts = self._week_category_counts(db, user_id, week_start, week_end)
        this_week_volume = self._week_volume_by_category(db, user_id, week_start, week_end)
        last_week_volume = self._week_volume_by_category(db, user_id, prev_week_start, prev_week_end)

        categories = []
        for category in TRAINING_CATEGORIES:
            actual_count = this_week_counts.get(category, 0)
            target_count = targets.get(category, DEFAULT_WEEKLY_TARGET)
            entry = {
                "category": category,
                "actual_count": actual_count,
                "target_count": target_count,
                "met": actual_count >= target_count,
            }
            if category in self.GYM_CATEGORIES:
                tw = round(this_week_volume.get(category, 0), 1)
                lw = round(last_week_volume.get(category, 0), 1)
                entry["this_week_volume"] = tw
                entry["last_week_volume"] = lw
                entry["volume_met"] = tw >= lw
            categories.append(entry)

        return {
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "categories": categories,
        }
