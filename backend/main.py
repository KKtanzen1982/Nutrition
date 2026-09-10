"""
飲食管理系統 - FastAPI 應用進入點
================================================

只負責：建立 app、掛 CORS、掛各功能領域的 router、啟動時建表 + 灌示範資料。
各功能領域（users/fitness/training/recipes/meal_plans/shopping）的路由、
商業邏輯、資料表定義都在各自的資料夾底下，不在這個檔案。

API 文檔: http://localhost:8000/docs
"""

from datetime import date, timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_mcp import FastApiMCP
from sqlalchemy import text

from database import Base, engine, get_db
from auth import ApiKeyMiddleware

# 確保所有 ORM class 在 create_all() 前都已註冊到 Base.metadata（跟原本 `import models` 的作用一樣，只是拆成 6 份）
import users.models  # noqa: F401
import fitness.models  # noqa: F401
import training.models  # noqa: F401
import recipes.models  # noqa: F401
import meal_plans.models  # noqa: F401
import shopping.models  # noqa: F401

from users.router import router as users_router
from users.services import user_service
from users.schemas import UserCreate
from fitness.router import router as fitness_router
from fitness.services import WeightService, ExerciseService, StepsService
from fitness.schemas import WeightRecordCreate, ExerciseSessionCreate, DailyStepsCreate
from training.router import router as training_router
from training.seed_data import seed_exercise_item_library
from recipes.router import router as recipes_router
from recipes.seed_data import seed_recipes
from meal_plans.router import router as meal_plans_router
from shopping.router import router as shopping_router
from shopping.services import purchase_location_service
from shopping.schemas import PurchaseLocationCreate
from backup_router import router as backup_router

# ==================== FastAPI 應用初始化 ====================

app = FastAPI(
    title="飲食管理系統",
    description="完整的營養、健身、飲食管理系統（依功能領域拆分：users/fitness/training/recipes/meal_plans/shopping）",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(ApiKeyMiddleware)

for r in (users_router, fitness_router, training_router, recipes_router, meal_plans_router, shopping_router, backup_router):
    app.include_router(r, prefix="/api")

# ==================== MCP（給 Claude.ai 用的工具介面） ====================
# 開放所有功能領域（users/fitness/training/recipes/meal-plans/shopping），
# 唯獨排除 backup：/backup/import 會整個清空、覆蓋資料庫，屬於危險操作，不透過 MCP 開放。
mcp = FastApiMCP(
    app,
    name="飲食管理系統",
    description="讀寫使用者資料、體重/運動記錄、訓練排程、食譜庫、週菜單、購物地點",
    exclude_tags=["backup"],
)
mcp.mount_http()

weight_service = WeightService()
exercise_service = ExerciseService()
steps_service = StepsService()

# ==================== 根路由 ====================


@app.get("/")
def read_root():
    """根路由 - API 信息"""
    return {
        "message": "飲食管理系統後端 v2.0",
        "api_docs": "http://localhost:8000/docs",
        "domains": ["users", "fitness", "training", "recipes", "meal_plans", "shopping"],
    }


@app.get("/health")
def health_check():
    """健康檢查端點"""
    return {"status": "healthy", "message": "應用正在運行"}

# ==================== 示範資料（僅供程式試用，重啟後若已有資料則跳過） ====================


def _add_missing_columns():
    """create_all() 只會建立全新的資料表，不會幫既有資料表補欄位；這裡用最小化手動遷移補上
    後來新增的 nullable 欄位。只在 Postgres 上執行——本機開發用的 sqlite mock db 都是全新建表，
    create_all() 當下就已經含所有欄位，不需要這段。"""
    if engine.dialect.name != "postgresql":
        return
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE recipes ADD COLUMN IF NOT EXISTS carb_source VARCHAR(20)"))
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS manual_calories_target FLOAT"))
        conn.execute(text("ALTER TABLE ingredient_library ADD COLUMN IF NOT EXISTS season VARCHAR(20)"))
        conn.execute(text("ALTER TABLE fixed_meal_preferences ADD COLUMN IF NOT EXISTS start_date DATE NOT NULL DEFAULT CURRENT_DATE"))
        conn.execute(text("ALTER TABLE fixed_meal_preferences ADD COLUMN IF NOT EXISTS duration_days INTEGER"))
        conn.execute(text("ALTER TABLE fixed_meal_preferences ADD COLUMN IF NOT EXISTS category VARCHAR(20)"))
        # 午餐/晚餐固定餐點是兩人共用（不分誰），user_id 存 NULL；舊表原本是 NOT NULL，這裡放寬限制
        conn.execute(text("ALTER TABLE fixed_meal_preferences ALTER COLUMN user_id DROP NOT NULL"))
        conn.commit()


@app.on_event("startup")
def seed_demo_data():
    Base.metadata.create_all(bind=engine)
    _add_missing_columns()

    db = next(get_db())
    try:
        seed_exercise_item_library(db)
        seed_recipes(db)

        if not purchase_location_service.list_locations(db, active_only=False):
            for name, desc, order in [
                ("全聯福利中心", "日常生鮮/乾貨", 1),
                ("傳統市場", "新鮮蔬菜/肉類", 2),
                ("家樂福", "大宗採購/特價品", 3),
                ("網路商店", "不易取得的特殊食材", 4),
            ]:
                purchase_location_service.create_location(db, PurchaseLocationCreate(location_name=name, description=desc, priority_order=order))

        if user_service.get_all_users(db, limit=1):
            return

        demo_users = [
            UserCreate(name="小美", gender="女", age=29, height_cm=162, primary_goal="減脂", activity_level="中"),
            UserCreate(name="阿凱", gender="男", age=31, height_cm=175, primary_goal="增肌", activity_level="高"),
        ]
        created_users = [user_service.create_user(db, u) for u in demo_users]

        today = date.today()
        base_weights = {created_users[0].id: 58.5, created_users[1].id: 74.0}
        for user_id, base_weight in base_weights.items():
            for i in range(14, -1, -1):
                d = today - timedelta(days=i)
                drift = (7 - i) * -0.05 if user_id == created_users[0].id else (7 - i) * 0.03
                weight_service.create_weight_record(db, WeightRecordCreate(
                    user_id=user_id,
                    date=d,
                    weight_kg=round(base_weight + drift, 1),
                    body_fat_percent=None,
                    notes=None,
                ))

        exercise_plan = {
            created_users[0].id: ("瑜珈", 30, "低"),
            created_users[1].id: ("健身房", 60, "高"),
        }
        for user_id, (ex_type, duration, intensity) in exercise_plan.items():
            for i in range(6, -1, -2):
                d = today - timedelta(days=i)
                exercise_service.create_exercise_session(db, ExerciseSessionCreate(
                    user_id=user_id,
                    date=d,
                    exercise_type=ex_type,
                    duration_min=duration,
                    intensity=intensity,
                    calories_burned=duration * 5,
                    notes=None,
                    details=[],
                ))
            for i in range(6, -1, -1):
                d = today - timedelta(days=i)
                steps_service.create_steps(db, DailyStepsCreate(
                    user_id=user_id,
                    date=d,
                    step_count=6000 + user_id * 1500 + i * 200,
                    calories_burned=None,
                    notes=None,
                ))
    finally:
        db.close()

# ==================== 啟動 ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
