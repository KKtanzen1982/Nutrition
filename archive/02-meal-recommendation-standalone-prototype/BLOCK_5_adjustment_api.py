"""
BLOCK_5: 微調相關 API Endpoints
- POST /meal-plans/{plan_id}/adjust/replace-meal (方案 A)
- POST /meal-plans/{plan_id}/adjust/regenerate-day (方案 B)
- POST /meal-plans/{plan_id}/adjust/search-replace (方案 C)
- PUT /meal-plans/{plan_id}/adjust/serving-weight (方案 D)
"""

import logging
import uuid
from datetime import date, datetime
from typing import Callable, List
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from sqlalchemy.orm import Session

# 導入 Schemas
try:
    from BLOCK_5_schemas import (
        ReplaceMealRequest,
        RegenerateDayRequest,
        SearchAndReplaceRequest,
        AdjustServingWeightRequest,
        AdjustmentResponse,
        UpdatedMeal,
    )
except ImportError:
    from block_5.schemas import (
        ReplaceMealRequest,
        RegenerateDayRequest,
        SearchAndReplaceRequest,
        AdjustServingWeightRequest,
        AdjustmentResponse,
        UpdatedMeal,
    )

# 導入服務
try:
    from BLOCK_5_adjustment_service import MealAdjustmentService, NutrientCalculator
    from BLOCK_5_recommendation_service import RecipeFilter, RecommendationDataPacker
    import BLOCK_5_prompts as prompts
    import BLOCK_5_db_service as db_service
    from BLOCK_5_claude_client import get_claude_service
    from BLOCK_5_jobs import jobs_cache
except ImportError:
    from block_5.adjustment_service import MealAdjustmentService, NutrientCalculator
    from block_5.recommendation_service import RecipeFilter, RecommendationDataPacker
    from block_5 import prompts
    from block_5 import db_service
    from block_5.claude_client import get_claude_service
    from block_5.jobs import jobs_cache

logger = logging.getLogger(__name__)

# 建立 Router
router = APIRouter(prefix="/meal-plans", tags=["adjustments"])


# ==================== 輔助函數 ====================

def get_db() -> Session:
    """取得數據庫連接（placeholder，由掛載的 app 覆蓋，見 BLOCK_5_meal_plan_api.get_db）。"""
    raise NotImplementedError("需要連接真實數據庫")


def get_session_factory() -> Callable[[], Session]:
    """取得 session factory（placeholder，同 BLOCK_5_meal_plan_api.get_session_factory）。"""
    raise NotImplementedError("需要提供 session factory")


def _updated_meal_response(updated_meal: dict) -> UpdatedMeal:
    return UpdatedMeal(
        meal_date=updated_meal["meal_date"],
        meal_type=updated_meal["meal_type"],
        user_id=updated_meal["user_id"],
        recipe_id=updated_meal["recipe_id"],
        recipe_name=updated_meal.get("recipe_name", ""),
        serving_weight_g=int(updated_meal.get("serving_weight_g") or 0),
        calories=updated_meal.get("calories") or 0,
        protein_g=updated_meal.get("protein_g") or 0,
        carbs_g=updated_meal.get("carbs_g") or 0,
        fat_g=updated_meal.get("fat_g") or 0,
    )


async def run_day_regeneration_background(
    job_id: str,
    plan_id: int,
    meal_date: date,
    fixed_meal_types: List[str],
    session_factory: Callable[[], Session],
):
    """後台重推整天任務：固定某些餐次類型（對 A、B 皆固定），其餘由 Claude（或 Mock）重新推薦。"""
    db = session_factory()
    try:
        jobs_cache[job_id]["status"] = "processing"
        jobs_cache[job_id]["started_at"] = datetime.now()

        logger.info(f"開始重推整天任務：{job_id}，日期 {meal_date}")

        plan_header = db_service.get_plan_header(db, plan_id)
        if plan_header is None:
            raise Exception(f"週計畫 {plan_id} 不存在")

        user_a_id = plan_header["user_id_a"]
        user_b_id = plan_header["user_id_b"]

        user_a = db_service.get_user_profile_for_claude(db, user_a_id)
        user_b = db_service.get_user_profile_for_claude(db, user_b_id)

        nutrients_a = RecommendationDataPacker.calculate_nutrient_targets(
            user_a, plan_header["user_a_daily_calories_target"] or 0
        )
        nutrients_b = RecommendationDataPacker.calculate_nutrient_targets(
            user_b, plan_header["user_b_daily_calories_target"] or 0
        )

        current_meals = db_service.get_meal_plan_meals(db, plan_id)

        # RegenerateDayRequest.fixed_meals 目前的 schema 沒有帶 user_id，
        # 所以「固定某個 meal_type」視為對 A、B 兩人在當天都固定，不個別區分。
        fixed_meals_for_logic = [
            {"meal_type": mt, "user_id": uid}
            for mt in fixed_meal_types
            for uid in (user_a_id, user_b_id)
        ]

        _job_id_unused, day_context, _fixed_info = MealAdjustmentService.prepare_for_day_regeneration(
            current_meals, meal_date, fixed_meals_for_logic
        )

        all_recipes = db_service.get_active_recipes(db)
        candidate_recipes = RecipeFilter.filter_candidate_recipes(user_a, user_b, all_recipes)

        day_name = meal_date.strftime("%A")
        recommendation_data = {
            "user_a": {
                **user_a,
                "menstrual_phase": plan_header["user_a_menstrual_phase"] or "無",
                "daily_calories_target": plan_header["user_a_daily_calories_target"] or 0,
                "daily_protein_g": nutrients_a["protein_g"],
                "daily_carbs_g": nutrients_a["carbs_g"],
                "daily_fat_g": nutrients_a["fat_g"],
            },
            "user_b": {
                **user_b,
                "menstrual_phase": plan_header["user_b_menstrual_phase"] or "無",
                "daily_calories_target": plan_header["user_b_daily_calories_target"] or 0,
                "daily_protein_g": nutrients_b["protein_g"],
                "daily_carbs_g": nutrients_b["carbs_g"],
                "daily_fat_g": nutrients_b["fat_g"],
            },
            "week_start_date": plan_header["plan_date"].isoformat(),
            "user_a_preselected_meals": [],
            "user_b_preselected_meals": [],
            "recipe_database": candidate_recipes,
        }

        prompt = prompts.build_claude_prompt(
            recommendation_data,
            target_date=meal_date.isoformat(),
            single_day_context={
                "day_name": day_name,
                "fixed_meals_summary": day_context["fixed_summary"],
                "other_days_summary": day_context["other_days_summary"],
            },
        )

        meals_to_regenerate = [
            {"meal_type": m.get("meal_type"), "user_id": m.get("user_id")}
            for m in day_context["meals_to_regenerate"]
        ]

        claude_service = get_claude_service()
        claude_response = await claude_service.call_claude(prompt, context={
            "candidate_recipes": candidate_recipes,
            "target_date": meal_date.isoformat(),
            "day_name": day_name,
            "meals_to_regenerate": meals_to_regenerate,
            "user_a_id": user_a_id,
            "user_b_id": user_b_id,
        })

        if not claude_response.get("success"):
            raise Exception(f"Claude 重推失敗：{claude_response.get('error')}")

        user_label_to_id = {"A": user_a_id, "B": user_b_id}
        regenerated_meals = []
        for meal in claude_response.get("recommendation", {}).get("meals", []):
            uid = user_label_to_id.get(meal.get("user"))
            if uid is None:
                continue
            regenerated_meals.append({
                "meal_type": meal.get("meal_type"),
                "user_id": uid,
                "recipe_id": meal.get("recipe_id"),
                "serving_weight_g": meal.get("serving_weight_g"),
                "calories": meal.get("calories"),
                "protein_g": meal.get("protein_g"),
                "carbs_g": meal.get("carbs_g"),
                "fat_g": meal.get("fat_g"),
                "fiber_g": meal.get("fiber_g"),
            })

        db_service.apply_day_regeneration(
            db, plan_id, meal_date, regenerated_meals, day_context["fixed_meal_ids"]
        )

        jobs_cache[job_id]["status"] = "completed"
        jobs_cache[job_id]["completed_at"] = datetime.now()

        logger.info(f"重推整天任務成功：{job_id}")

    except Exception as e:
        logger.error(f"重推整天任務失敗 {job_id}：{str(e)}")
        jobs_cache[job_id]["status"] = "failed"
        jobs_cache[job_id]["error_message"] = str(e)
        jobs_cache[job_id]["completed_at"] = datetime.now()
    finally:
        db.close()


# ==================== API Endpoints ====================

# ========== 方案 A：替換單菜色 ==========

@router.post("/{plan_id}/adjust/replace-meal", response_model=AdjustmentResponse)
async def replace_meal(
    plan_id: int,
    request: ReplaceMealRequest,
    db: Session = Depends(get_db),
):
    """方案 A：替換單個菜色。"""
    try:
        logger.info(f"替換菜色請求：plan_id={plan_id}, date={request.meal_date}, "
                    f"meal_type={request.meal_type}, user={request.user_id}")

        if request.meal_date < date.today():
            raise ValueError("無法修改過去的日期")

        current_meals = db_service.get_meal_plan_meals(db, plan_id)
        original = db_service.get_single_meal(db, plan_id, request.meal_date, request.meal_type.value, request.user_id)
        if original is None:
            raise HTTPException(status_code=404, detail="找不到要替換的餐次")

        new_recipe = db_service.get_recipe_for_claude(db, request.new_recipe_id)

        updated_meals, updated_meal, adjustment = MealAdjustmentService.replace_meal(
            current_meals,
            request.meal_date,
            request.meal_type.value,
            request.user_id,
            new_recipe,
            original.recipe_id,
        )
        if updated_meal is None:
            raise HTTPException(status_code=404, detail="找不到要替換的餐次")

        adjustment["reason"] = request.reason
        db_service.apply_single_meal_update(db, plan_id, updated_meal, adjustment)

        return AdjustmentResponse(
            success=True,
            updated_meal=_updated_meal_response(updated_meal),
            adjustment_recorded=True,
            message="菜色替換成功",
        )

    except db_service.NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        logger.error(f"替換菜色驗證失敗：{str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"替換菜色失敗：{str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 方案 B：重推整天 ==========

@router.post("/{plan_id}/adjust/regenerate-day", response_model=AdjustmentResponse)
async def regenerate_day(
    plan_id: int,
    request: RegenerateDayRequest,
    background_tasks: BackgroundTasks,
    session_factory: Callable[[], Session] = Depends(get_session_factory),
):
    """方案 B：重新推薦某一天（非同步）。"""
    try:
        logger.info(f"重推整天請求：plan_id={plan_id}, date={request.meal_date}, "
                    f"fixed_meals={len(request.fixed_meals or [])}")

        if request.meal_date < date.today():
            raise ValueError("無法重推過去的日期")

        job_id = str(uuid.uuid4())

        jobs_cache[job_id] = {
            "status": "pending",
            "plan_id": plan_id,
            "meal_date": request.meal_date,
            "error_message": None,
            "created_at": datetime.now(),
            "started_at": None,
            "completed_at": None,
        }

        fixed_meal_types = [fm.meal_type.value for fm in (request.fixed_meals or [])]

        background_tasks.add_task(
            run_day_regeneration_background,
            job_id,
            plan_id,
            request.meal_date,
            fixed_meal_types,
            session_factory,
        )

        logger.info(f"重推整天任務已啟動：{job_id}")

        return AdjustmentResponse(
            success=True,
            job_id=job_id,
            message=f"整天重推任務已啟動，請使用 job_id {job_id} 輪詢狀態",
        )

    except ValueError as e:
        logger.error(f"重推整天驗證失敗：{str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"重推整天失敗：{str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 方案 C：搜尋替換 ==========

@router.post("/{plan_id}/adjust/search-replace", response_model=AdjustmentResponse)
async def search_and_replace(
    plan_id: int,
    request: SearchAndReplaceRequest,
    db: Session = Depends(get_db),
):
    """方案 C：搜尋並替換。"""
    try:
        logger.info(f"搜尋替換請求：plan_id={plan_id}, query='{request.search_query}', "
                    f"new_recipe_id={request.new_recipe_id}")

        if request.meal_date < date.today():
            raise ValueError("無法修改過去的日期")

        current_meals = db_service.get_meal_plan_meals(db, plan_id)
        original = db_service.get_single_meal(db, plan_id, request.meal_date, request.meal_type.value, request.user_id)
        if original is None:
            raise HTTPException(status_code=404, detail="找不到要替換的餐次")

        new_recipe = db_service.get_recipe_for_claude(db, request.new_recipe_id)

        updated_meals, updated_meal, adjustment = MealAdjustmentService.search_and_replace(
            current_meals,
            request.meal_date,
            request.meal_type.value,
            request.user_id,
            new_recipe,
            original.recipe_id,
            request.search_query,
        )
        if updated_meal is None:
            raise HTTPException(status_code=404, detail="找不到要替換的餐次")

        adjustment["reason"] = f"用戶搜尋替換（查詢：'{request.search_query}'）"
        db_service.apply_single_meal_update(db, plan_id, updated_meal, adjustment)

        return AdjustmentResponse(
            success=True,
            updated_meal=_updated_meal_response(updated_meal),
            adjustment_recorded=True,
            message=f"搜尋替換成功（查詢：'{request.search_query}'）",
        )

    except db_service.NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        logger.error(f"搜尋替換驗證失敗：{str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"搜尋替換失敗：{str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 方案 D：調整分量 ==========

@router.put("/{plan_id}/adjust/serving-weight", response_model=AdjustmentResponse)
async def adjust_serving_weight(
    plan_id: int,
    request: AdjustServingWeightRequest,
    db: Session = Depends(get_db),
):
    """方案 D：調整菜色分量，自動重新計算營養素。"""
    try:
        logger.info(f"調整分量請求：plan_id={plan_id}, date={request.meal_date}, "
                    f"meal_type={request.meal_type}, new_weight={request.new_serving_weight_g}g")

        if request.meal_date < date.today():
            raise ValueError("無法修改過去的日期")
        if request.new_serving_weight_g <= 0:
            raise ValueError("分量必須大於 0")

        current_meals = db_service.get_meal_plan_meals(db, plan_id)
        original = db_service.get_single_meal(db, plan_id, request.meal_date, request.meal_type.value, request.user_id)
        if original is None:
            raise HTTPException(status_code=404, detail="找不到要調整的餐次")

        recipe = db_service.get_recipe_for_claude(db, original.recipe_id)

        updated_meals, updated_meal, adjustment = MealAdjustmentService.adjust_serving_weight(
            current_meals,
            request.meal_date,
            request.meal_type.value,
            request.user_id,
            request.new_serving_weight_g,
            recipe,
        )
        if updated_meal is None:
            raise HTTPException(status_code=404, detail="找不到要調整的餐次")

        db_service.apply_single_meal_update(db, plan_id, updated_meal, adjustment)

        nutrition = NutrientCalculator.calculate_meal_nutrition(recipe, request.new_serving_weight_g)

        return AdjustmentResponse(
            success=True,
            updated_meal=UpdatedMeal(
                meal_date=request.meal_date,
                meal_type=request.meal_type,
                user_id=request.user_id,
                recipe_id=recipe["id"],
                recipe_name=recipe["name"],
                serving_weight_g=request.new_serving_weight_g,
                calories=nutrition["calories"],
                protein_g=nutrition["protein_g"],
                carbs_g=nutrition["carbs_g"],
                fat_g=nutrition["fat_g"],
            ),
            adjustment_recorded=True,
            message=f"分量調整成功（{request.new_serving_weight_g}g，自動重新計算營養素）",
        )

    except db_service.NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        logger.error(f"分量調整驗證失敗：{str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"分量調整失敗：{str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
