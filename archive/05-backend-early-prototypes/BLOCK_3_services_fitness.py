"""
Block 3: 體重和運動追蹤 - 業務邏輯服務
"""

from datetime import date, datetime, timedelta
from typing import List, Optional, Dict

# 模擬數據存儲
weight_db = {}
exercise_db = {}
template_db = {}
steps_db = {}
next_weight_id = 1
next_exercise_id = 1
next_template_id = 1
next_steps_id = 1

class WeightService:
    """體重管理服務"""
    
    def __init__(self, db = None):
        self.db = db
    
    def create_weight_record(self, data):
        """創建體重記錄"""
        global next_weight_id
        record_id = next_weight_id
        record = {"id": record_id, **data.model_dump()}
        weight_db[record_id] = record
        next_weight_id += 1
        return record
    
    def get_weight_records(self, user_id: int, skip: int = 0, limit: int = 10):
        """獲取用戶體重記錄"""
        user_records = [r for r in weight_db.values() if r.get("user_id") == user_id]
        return sorted(user_records, key=lambda x: str(x.get("date")), reverse=True)[skip:skip + limit]
    
    def get_weight_record(self, record_id: int):
        """獲取特定體重記錄"""
        return weight_db.get(record_id)
    
    def update_weight_record(self, record_id: int, data):
        """更新體重記錄"""
        if record_id not in weight_db:
            return None
        weight_db[record_id].update(data.model_dump(exclude_unset=True))
        return weight_db[record_id]

class ExerciseService:
    """運動管理服務"""
    
    def __init__(self, db = None):
        self.db = db
    
    def create_exercise_session(self, data):
        """創建運動會話"""
        global next_exercise_id
        session_id = next_exercise_id
        session = {"id": session_id, **data.model_dump()}
        exercise_db[session_id] = session
        next_exercise_id += 1
        return session
    
    def get_exercise_sessions(self, user_id: int, skip: int = 0, limit: int = 10):
        """獲取用戶運動記錄"""
        user_sessions = [e for e in exercise_db.values() if e.get("user_id") == user_id]
        return sorted(user_sessions, key=lambda x: str(x.get("date")), reverse=True)[skip:skip + limit]
    
    def get_exercise_session(self, session_id: int):
        """獲取特定運動會話"""
        return exercise_db.get(session_id)
    
    def get_weekly_stats(self, user_id: int) -> Dict:
        """獲取本週運動統計"""
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        
        sessions = []
        for e in exercise_db.values():
            if e.get("user_id") == user_id:
                try:
                    session_date = e.get("date") if isinstance(e.get("date"), date) else date.fromisoformat(str(e.get("date")))
                    if session_date >= monday:
                        sessions.append(e)
                except:
                    pass
        
        total_duration = sum(e.get("duration_min", 0) for e in sessions)
        total_calories = sum(e.get("calories_burned", 0) for e in sessions if e.get("calories_burned"))
        
        return {
            "week_start": monday.isoformat(),
            "week_end": today.isoformat(),
            "total_sessions": len(sessions),
            "total_duration_min": total_duration,
            "total_calories": total_calories,
            "average_duration": total_duration / len(sessions) if sessions else 0
        }

class TemplateService:
    """訓練模板服務"""
    
    def __init__(self, db = None):
        self.db = db
    
    def create_template(self, data):
        """創建訓練模板"""
        global next_template_id
        template_id = next_template_id
        template = {"id": template_id, **data.model_dump()}
        template_db[template_id] = template
        next_template_id += 1
        return template
    
    def get_templates(self, user_id: int):
        """獲取用戶的訓練模板"""
        return [t for t in template_db.values() if t.get("user_id") == user_id]
    
    def get_template(self, template_id: int):
        """獲取特定訓練模板"""
        return template_db.get(template_id)

class StepsService:
    """步數服務"""
    
    def __init__(self, db = None):
        self.db = db
    
    def create_steps(self, data):
        """記錄步數"""
        global next_steps_id
        steps_id = next_steps_id
        steps = {"id": steps_id, **data.model_dump()}
        steps_db[steps_id] = steps
        next_steps_id += 1
        return steps
    
    def get_steps(self, user_id: int, skip: int = 0, limit: int = 10):
        """獲取用戶步數記錄"""
        user_steps = [s for s in steps_db.values() if s.get("user_id") == user_id]
        return sorted(user_steps, key=lambda x: str(x.get("date")), reverse=True)[skip:skip + limit]
    
    def get_weekly_stats(self, user_id: int) -> Dict:
        """獲取本週步數統計"""
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        
        steps_records = []
        for s in steps_db.values():
            if s.get("user_id") == user_id:
                try:
                    steps_date = s.get("date") if isinstance(s.get("date"), date) else date.fromisoformat(str(s.get("date")))
                    if steps_date >= monday:
                        steps_records.append(s)
                except:
                    pass
        
        total_steps = sum(s.get("step_count", 0) for s in steps_records)
        
        return {
            "week_start": monday.isoformat(),
            "week_end": today.isoformat(),
            "total_days": len(steps_records),
            "total_steps": total_steps,
            "average_steps": total_steps / len(steps_records) if steps_records else 0
        }
