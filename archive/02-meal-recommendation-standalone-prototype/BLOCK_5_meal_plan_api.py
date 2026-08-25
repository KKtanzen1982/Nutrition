"""
BLOCK_5: 推薦相關 API Endpoints
- POST /meal-plans/generate (非同步)
- GET /meal-plans/jobs/{job_id}/status
- GET /meal-plans/{plan_id}
- PUT /meal-plans/{plan_id}/confirm
"""

import logging
import uuid
from datetime import date, datetime
from typing import Callable
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from sqlalchemy.orm import Session

# 導入 Schemas
try:
    from BLOCK_5_schemas import (
        GenerateMealPlanRequest,
        GenerateMealPlanImmediateResponse,
        JobStatus,
        MealPlanResponse,
    )
except ImportError:
    from block_5.schemas import (
        GenerateMealPlanRequest,
        GenerateMealPlanImmediateResponse,
        JobStatus,
        MealPlanResponse,
    )

# 導入服務
try:
    from BLOCK_5_recommendation_service import RecipeFilter, RecommendationDataPacker
    import BLOCK_5_prompts as prompts
    import BLOCK_5_db_service as db_service
    from BLOCK_5_claude_client import get_claude_service
    from BLOCK_5_jobs import jobs_cache
except ImportError:
    from block_5.recommendation_service import RecipeFilter, RecommendationDataPacker
    from block_5 import prompts
    from block_5 import db_service
    from block_5.claude_client import get_claude_service
    from block_5.jobs import jobs_cache

logger = logging.getLogger(__name__)

# 建立 Router
router = APIRouter(prefix="/meal-plans", tags=["meal-plans"])


# ==================== 輔助函數 ====================

def get_db() -> Session:
    """
    取得數據庫連接（placeholder）。

    實際執行時由掛載的 app（見 BLOCK_5_test_app.py）用
    app.dependency_overrides[get_db] 換成真正連到資料庫的 session。
    """
    raise NotImplementedError("需要連接真實數據庫")


def get_session_factory() -> Callable[[], Session]:
    """
    取得可以自己開關 session 的 factory（placeholder）。

    背景任務（BackgroundTasks）不應該持有 request-scoped 的 `Depends(get_db)` session
    跨越 async 邊界，所以改成注入一個 factory，讓背景任務自己開、自己關。
    同樣由掛載的 app 用 app.dependency_overrides 換成真正的 factory。
    """
    raise NotImplementedError("需要提供 session factory")


async def run_recommendation_background(
    job_id: str,
    request: GenerateMealPlanRequest,
    session_factory: Callable[[], Session],
):
    """後台推薦任務：查真實資料庫 → 篩選食譜 → 打包 → 呼叫 Claude（或 Mock）→ 存回資料庫。"""
    db = session_factory()
    try:
        jobs_cache[job_id]["status"] = "processing"
        jobs_cache[job_id]["started_at"] = datetime.now()

        logger.info(f"開始推薦任務：{job_id}")

        # ========== 第 1 步：取得用戶資料 ==========
        user_a = db_service.get_user_profile_for_claude(db, request.user_a_id)
        user_a["calorie_calculation_method"] = request.calorie_calculation_method.value
        user_b = db_service.get_user_profile_for_claude(db, request.user_b_id)
        user_b["calorie_calculation_method"] = request.calorie_calculation_method.value

        # ========== 第 2 步：取得本週運動數據 ==========
        exercise_data_a = db_service.get_week_exercise_summary(db, request.user_a_id, request.week_start_date)
        exercise_data_b = db_service.get_week_exercise_summary(db, request.user_b_id, request.week_start_date)

        # ========== 第 3 步：取得所有上架食譜 ==========
        all_recipes = db_service.get_active_recipes(db)

        preselected_a = [_preselected_to_dict(m) for m in (request.user_a_preselected or [])]
        preselected_b = [_preselected_to_dict(m) for m in (request.user_b_preselected or [])]

        # ========== 第 4 步：篩選食譜 ==========
        candidate_recipes = RecipeFilter.filter_candidate_recipes(user_a, user_b, all_recipes)
        logger.info(f"篩選食譜：{len(all_recipes)} → {len(candidate_recipes)}")

        # ========== 第 5 步：打包數據（含熱量/營養目標、生理期） ==========
        recommendation_data = RecommendationDataPacker.pack_for_claude(
            user_a, user_b,
            request.week_start_date,
            exercise_data_a, exercise_data_b,
            preselected_a, preselected_b,
            candidate_recipes,
        )

        # ========== 第 6 步：構建 Prompt 並調用 Claude（或 Mock） ==========
        prompt = prompts.build_claude_prompt(recommendation_data)
        claude_service = get_claude_service()
        claude_response = await claude_service.call_claude(prompt, context={
            "candidate_recipes": candidate_recipes,
            "week_start_date": recommendation_data["week_start_date"],
            "user_a_id": request.user_a_id,
            "user_b_id": request.user_b_id,
        })

        if not claude_response.get("success"):
            raise Exception(f"Claude 推薦失敗：{claude_response.get('error')}")

        # ========== 第 7 步：存入資料庫 ==========
        plan_id = db_service.save_meal_plan(
            db,
            claude_response,
            request.week_start_date,
            request.user_a_id,
            request.user_b_id,
            request.calorie_calculation_method.value,
            recommendation_data["user_a"]["daily_calories_target"],
            recommendation_data["user_b"]["daily_calories_target"],
            recommendation_data["user_a"]["menstrual_phase"],
            recommendation_data["user_b"]["menstrual_phase"],
        )

        # ========== 第 8 步：更新任務狀態 ==========
        jobs_cache[job_id]["status"] = "completed"
        jobs_cache[job_id]["plan_id"] = plan_id
        jobs_cache[job_id]["completed_at"] = datetime.now()

        logger.info(f"推薦任務成功：{job_id} → plan_id={plan_id}")

    except Exception as e:
        logger.error(f"推薦任務失敗 {job_id}：{str(e)}")
        jobs_cache[job_id]["status"] = "failed"
        jobs_cache[job_id]["error_message"] = str(e)
        jobs_cache[job_id]["completed_at"] = datetime.now()
    finally:
        db.close()


def _preselected_to_dict(preselected) -> dict:
    """PreselectedMeal (pydantic) -> plain dict，meal_type Enum 轉成字串。"""
    data = preselected.model_dump() if hasattr(preselected, "model_dump") else preselected.dict()
    if hasattr(data.get("meal_type"), "value"):
        data["meal_type"] = data["meal_type"].value
    return data


# ==================== API Endpoints ====================

@router.post("/generate", response_model=GenerateMealPlanImmediateResponse)
async def generate_meal_plan(
    request: GenerateMealPlanRequest,
    background_tasks: BackgroundTasks,
    session_factory: Callable[[], Session] = Depends(get_session_factory),
):
    """生成週推薦（非同步）：立即返回 job_id，後台非同步處理。"""
    try:
        if request.week_start_date < date.today():
            raise ValueError("週開始日期不能早於今天")

        job_id = str(uuid.uuid4())

        jobs_cache[job_id] = {
            "status": "pending",
            "user_a_id": request.user_a_id,
            "user_b_id": request.user_b_id,
            "week_start_date": request.week_start_date,
            "plan_id": None,
            "error_message": None,
            "created_at": datetime.now(),
            "started_at": None,
            "completed_at": None,
        }

        background_tasks.add_task(
            run_recommendation_background,
            job_id,
            request,
            session_factory,
        )

        logger.info(f"推薦任務已啟動：{job_id}")

        return GenerateMealPlanImmediateResponse(
            success=True,
            job_id=job_id,
            message="推薦任務已啟動，請輪詢查詢狀態",
        )

    except ValueError as e:
        logger.error(f"建立推薦任務失敗：{str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"建立推薦任務失敗：{str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/jobs/{job_id}/status", response_model=JobStatus)
async def get_job_status(job_id: str):
    """查詢推薦任務的進度。"""
    try:
        if job_id not in jobs_cache:
            raise HTTPException(status_code=404, detail=f"任務 {job_id} 不存在")

        job = jobs_cache[job_id]

        return JobStatus(
            job_id=job_id,
            status=job.get("status", "unknown"),
            plan_id=job.get("plan_id"),
            error_message=job.get("error_message"),
            created_at=job.get("created_at"),
            started_at=job.get("started_at"),
            completed_at=job.get("completed_at"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查詢任務狀態失敗：{str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{plan_id}", response_model=MealPlanResponse)
async def get_meal_plan(plan_id: int, db: Session = Depends(get_db)):
    """取得週推薦詳情（真實查詢，查無資料回 404）。"""
    try:
        plan_dict = db_service.get_meal_plan_full(db, plan_id)
        if plan_dict is None:
            raise HTTPException(status_code=404, detail=f"週計畫 {plan_id} 不存在")
        return MealPlanResponse(**plan_dict)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取得週計畫失敗：{str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{plan_id}/confirm")
async def confirm_meal_plan(plan_id: int, db: Session = Depends(get_db)):
    """
    確認週推薦（狀態改為「已確認」）。

    購物清單生成屬於區塊 6（尚未開發），這裡不捏造 shopping_list_id。
    """
    try:
        confirmed = db_service.confirm_plan(db, plan_id)
        if not confirmed:
            raise HTTPException(status_code=404, detail=f"週計畫 {plan_id} 不存在")

        return {
            "success": True,
            "plan_id": plan_id,
            "status": "confirmed",
            "shopping_list_id": None,
            "message": "推薦已確認；購物清單將於區塊 6（購物清單管理）完成後生成",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"確認推薦失敗：{str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
