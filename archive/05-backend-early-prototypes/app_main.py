"""
飲食管理系統 - FastAPI 簡化版
完全獨立，無複雜導入
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict
from datetime import date, datetime

# ==================== 應用初始化 ====================

app = FastAPI(
    title="飲食管理系統",
    description="完整的營養和健身管理系統",
    version="1.0.0"
)

# 添加 CORS 中間件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== 數據存儲（內存中） ====================

users_db = {}
weight_db = {}
exercise_db = {}
template_db = {}
steps_db = {}

next_user_id = 1
next_weight_id = 1
next_exercise_id = 1
next_template_id = 1
next_steps_id = 1

# ==================== 根路由 ====================

@app.get("/")
def read_root():
    """根路由 - API 信息"""
    return {
        "message": "飲食管理系統後端 v1.0 ✅",
        "api_docs": "http://localhost:8000/docs",
        "status": "應用正在運行",
        "endpoints": 41
    }

@app.get("/health")
def health_check():
    """健康檢查"""
    return {"status": "✅ 健康"}

# ==================== Block 2: 用戶管理 ====================

@app.post("/api/v1/users", status_code=201)
def create_user(
    name: str,
    gender: str,
    age: int,
    height_cm: float,
    primary_goal: str,
    activity_level: str,
    email: Optional[str] = None
):
    """創建新用戶"""
    global next_user_id
    user_id = next_user_id
    user = {
        "id": user_id,
        "name": name,
        "gender": gender,
        "age": age,
        "height_cm": height_cm,
        "primary_goal": primary_goal,
        "activity_level": activity_level,
        "email": email,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "is_active": True
    }
    users_db[user_id] = user
    next_user_id += 1
    return user

@app.get("/api/v1/users")
def list_users(skip: int = 0, limit: int = 10):
    """列出所有用戶"""
    users_list = list(users_db.values())
    return {
        "total": len(users_list),
        "users": sorted(users_list, key=lambda x: x['id'], reverse=True)[skip:skip + limit]
    }

@app.get("/api/v1/users/{user_id}")
def get_user(user_id: int):
    """獲取特定用戶"""
    user = users_db.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用戶不存在")
    return user

@app.put("/api/v1/users/{user_id}")
def update_user(user_id: int, **kwargs):
    """更新用戶"""
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="用戶不存在")
    
    for key, value in kwargs.items():
        if value is not None:
            users_db[user_id][key] = value
    
    users_db[user_id]["updated_at"] = datetime.utcnow().isoformat()
    return users_db[user_id]

@app.delete("/api/v1/users/{user_id}", status_code=204)
def delete_user(user_id: int):
    """刪除用戶"""
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="用戶不存在")
    del users_db[user_id]

# ==================== Block 3: 體重管理 ====================

@app.post("/api/v1/weight-records", status_code=201)
def create_weight_record(
    user_id: int,
    date: str,
    weight_kg: float,
    body_fat_percent: Optional[float] = None
):
    """記錄體重"""
    global next_weight_id
    record_id = next_weight_id
    record = {
        "id": record_id,
        "user_id": user_id,
        "date": date,
        "weight_kg": weight_kg,
        "body_fat_percent": body_fat_percent,
        "created_at": datetime.utcnow().isoformat()
    }
    weight_db[record_id] = record
    next_weight_id += 1
    return record

@app.get("/api/v1/weight-records")
def list_weight_records(user_id: int, skip: int = 0, limit: int = 10):
    """獲取用戶體重記錄"""
    user_records = [r for r in weight_db.values() if r.get("user_id") == user_id]
    return sorted(user_records, key=lambda x: x.get("date"), reverse=True)[skip:skip + limit]

@app.get("/api/v1/weight-records/{record_id}")
def get_weight_record(record_id: int):
    """獲取特定體重記錄"""
    record = weight_db.get(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="記錄不存在")
    return record

@app.put("/api/v1/weight-records/{record_id}")
def update_weight_record(record_id: int, weight_kg: Optional[float] = None, body_fat_percent: Optional[float] = None):
    """更新體重記錄"""
    if record_id not in weight_db:
        raise HTTPException(status_code=404, detail="記錄不存在")
    
    if weight_kg is not None:
        weight_db[record_id]["weight_kg"] = weight_kg
    if body_fat_percent is not None:
        weight_db[record_id]["body_fat_percent"] = body_fat_percent
    
    return weight_db[record_id]

# ==================== Block 3: 運動管理 ====================

@app.post("/api/v1/exercise-sessions", status_code=201)
def create_exercise_session(
    user_id: int,
    date: str,
    exercise_type: str,
    duration_min: int,
    intensity: str,
    calories_burned: Optional[float] = None
):
    """創建運動會話"""
    global next_exercise_id
    session_id = next_exercise_id
    session = {
        "id": session_id,
        "user_id": user_id,
        "date": date,
        "exercise_type": exercise_type,
        "duration_min": duration_min,
        "intensity": intensity,
        "calories_burned": calories_burned,
        "details": [],
        "created_at": datetime.utcnow().isoformat()
    }
    exercise_db[session_id] = session
    next_exercise_id += 1
    return session

@app.get("/api/v1/exercise-sessions")
def list_exercise_sessions(user_id: int, skip: int = 0, limit: int = 10):
    """獲取用戶運動記錄"""
    user_sessions = [e for e in exercise_db.values() if e.get("user_id") == user_id]
    return sorted(user_sessions, key=lambda x: x.get("date"), reverse=True)[skip:skip + limit]

@app.get("/api/v1/exercise-sessions/{session_id}")
def get_exercise_session(session_id: int):
    """獲取特定運動會話"""
    session = exercise_db.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="運動記錄不存在")
    return session

@app.get("/api/v1/exercise-weekly-stats")
def get_weekly_stats(user_id: int):
    """獲取本週運動統計"""
    from datetime import timedelta
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    
    sessions = []
    for e in exercise_db.values():
        if e.get("user_id") == user_id:
            try:
                session_date = date.fromisoformat(e.get("date"))
                if session_date >= monday:
                    sessions.append(e)
            except:
                pass
    
    total_duration = sum(e.get("duration_min", 0) for e in sessions)
    total_calories = sum(e.get("calories_burned", 0) for e in sessions if e.get("calories_burned"))
    
    return {
        "week_start": monday.isoformat(),
        "total_sessions": len(sessions),
        "total_duration_min": total_duration,
        "total_calories": total_calories,
        "average_duration": total_duration / len(sessions) if sessions else 0
    }

# ==================== Block 3: 訓練模板 ====================

@app.post("/api/v1/workout-templates", status_code=201)
def create_workout_template(
    user_id: int,
    template_name: str,
    exercise_type: str,
    intensity: str,
    duration_min: Optional[int] = None
):
    """創建訓練模板"""
    global next_template_id
    template_id = next_template_id
    template = {
        "id": template_id,
        "user_id": user_id,
        "template_name": template_name,
        "exercise_type": exercise_type,
        "intensity": intensity,
        "duration_min": duration_min,
        "details": [],
        "created_at": datetime.utcnow().isoformat()
    }
    template_db[template_id] = template
    next_template_id += 1
    return template

@app.get("/api/v1/workout-templates")
def list_workout_templates(user_id: int):
    """獲取用戶的訓練模板"""
    return [t for t in template_db.values() if t.get("user_id") == user_id]

@app.get("/api/v1/workout-templates/{template_id}")
def get_workout_template(template_id: int):
    """獲取特定訓練模板"""
    template = template_db.get(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    return template

# ==================== Block 3: 步數管理 ====================

@app.post("/api/v1/daily-steps", status_code=201)
def create_daily_steps(
    user_id: int,
    date: str,
    step_count: int,
    calories_burned: Optional[float] = None
):
    """記錄每日步數"""
    global next_steps_id
    steps_id = next_steps_id
    steps = {
        "id": steps_id,
        "user_id": user_id,
        "date": date,
        "step_count": step_count,
        "calories_burned": calories_burned,
        "created_at": datetime.utcnow().isoformat()
    }
    steps_db[steps_id] = steps
    next_steps_id += 1
    return steps

@app.get("/api/v1/daily-steps")
def list_daily_steps(user_id: int, skip: int = 0, limit: int = 10):
    """獲取用戶步數記錄"""
    user_steps = [s for s in steps_db.values() if s.get("user_id") == user_id]
    return sorted(user_steps, key=lambda x: x.get("date"), reverse=True)[skip:skip + limit]

@app.get("/api/v1/daily-steps/weekly-stats")
def get_weekly_steps_stats(user_id: int):
    """獲取本週步數統計"""
    from datetime import timedelta
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    
    steps_records = []
    for s in steps_db.values():
        if s.get("user_id") == user_id:
            try:
                steps_date = date.fromisoformat(s.get("date"))
                if steps_date >= monday:
                    steps_records.append(s)
            except:
                pass
    
    total_steps = sum(s.get("step_count", 0) for s in steps_records)
    
    return {
        "week_start": monday.isoformat(),
        "total_days": len(steps_records),
        "total_steps": total_steps,
        "average_steps": total_steps / len(steps_records) if steps_records else 0
    }

# ==================== 啟動 ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
