from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date

from database import get_db
from meal_plans.schemas import (
    GenerateMealPlanRequest, ReplaceMealRequest, SearchReplaceMealRequest,
    AdjustServingWeightRequest, RegenerateDayRequest, SetFixedMealPreferenceRequest,
    SetExcludedRecipeRequest, SetFavoriteRecipeRequest, SetSoupDaysRequest,
    AddDishRequest, RebalanceDayRequest, SetManualCaloriesTargetRequest,
)
from meal_plans.services import (
    nutrition_target_service, meal_plan_service, fixed_meal_preference_service,
    excluded_recipe_service, favorite_recipe_service, soup_day_preference_service,
)

router = APIRouter(tags=["meal-plans"])


@router.get("/users/{user_id}/nutrition-targets")
def get_nutrition_targets(user_id: int, target_date: Optional[date] = None, db: Session = Depends(get_db)):
    try:
        return nutrition_target_service.get_user_context(db, user_id, target_date or date.today())
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/users/{user_id}/nutrition-targets")
def set_manual_calories_target(user_id: int, payload: SetManualCaloriesTargetRequest, db: Session = Depends(get_db)):
    """手動覆蓋使用者每日熱量目標；傳 manual_calories_target=null 清除覆蓋，改回依 BMR/TDEE 自動計算"""
    try:
        return nutrition_target_service.set_manual_override(db, user_id, payload.manual_calories_target)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/fixed-meal-preferences")
def list_fixed_meal_preferences(user_id: int, db: Session = Depends(get_db)):
    """列出某使用者固定吃的餐點設定（目前只支援 breakfast / afternoon_snack）"""
    return fixed_meal_preference_service.list_for_user(db, user_id)


@router.put("/fixed-meal-preferences")
def set_fixed_meal_preference(payload: SetFixedMealPreferenceRequest, db: Session = Depends(get_db)):
    """設定（或更新）某使用者某一餐固定吃的食譜；下次產生週菜單這一餐就直接套用，只調整份量"""
    try:
        return fixed_meal_preference_service.set_preference(db, payload.user_id, payload.meal_type, payload.recipe_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/fixed-meal-preferences/{preference_id}", status_code=204)
def delete_fixed_meal_preference(preference_id: int, db: Session = Depends(get_db)):
    """取消固定，之後這一餐改回規則式演算法選餐"""
    success = fixed_meal_preference_service.delete_preference(db, preference_id)
    if not success:
        raise HTTPException(status_code=404, detail="設定不存在")
    return None


@router.get("/excluded-recipes")
def list_excluded_recipes(db: Session = Depends(get_db)):
    """列出黑名單（不要再推薦的食譜），兩人共用一份"""
    return excluded_recipe_service.list_all(db)


@router.put("/excluded-recipes")
def add_excluded_recipe(payload: SetExcludedRecipeRequest, db: Session = Depends(get_db)):
    try:
        return excluded_recipe_service.add(db, payload.recipe_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/excluded-recipes/{exclusion_id}", status_code=204)
def remove_excluded_recipe(exclusion_id: int, db: Session = Depends(get_db)):
    success = excluded_recipe_service.remove(db, exclusion_id)
    if not success:
        raise HTTPException(status_code=404, detail="設定不存在")
    return None


@router.get("/favorite-recipes")
def list_favorite_recipes(user_id: int, db: Session = Depends(get_db)):
    """列出某使用者的最愛清單（軟性加權，比較容易被選到但不保證）"""
    return favorite_recipe_service.list_for_user(db, user_id)


@router.put("/favorite-recipes")
def add_favorite_recipe(payload: SetFavoriteRecipeRequest, db: Session = Depends(get_db)):
    try:
        return favorite_recipe_service.add(db, payload.user_id, payload.recipe_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/favorite-recipes/{favorite_id}", status_code=204)
def remove_favorite_recipe(favorite_id: int, db: Session = Depends(get_db)):
    success = favorite_recipe_service.remove(db, favorite_id)
    if not success:
        raise HTTPException(status_code=404, detail="設定不存在")
    return None


@router.get("/soup-day-preferences")
def list_soup_days(db: Session = Depends(get_db)):
    """列出勾選「想喝湯」的星期（0=週一...6=週日），兩人共用一份"""
    return {"days": soup_day_preference_service.list_days(db)}


@router.put("/soup-day-preferences")
def set_soup_days(payload: SetSoupDaysRequest, db: Session = Depends(get_db)):
    try:
        days = soup_day_preference_service.set_days(db, payload.days)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"days": days}


@router.post("/meal-plans/generate")
def generate_meal_plan(payload: GenerateMealPlanRequest, db: Session = Depends(get_db)):
    try:
        return meal_plan_service.generate_plan(db, payload.user_id_a, payload.user_id_b, payload.week_start_date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/meal-plans")
def list_meal_plans(user_id: Optional[int] = None, start_date: Optional[date] = None,
                     end_date: Optional[date] = None, db: Session = Depends(get_db)):
    """查詢已產生的週菜單清單（依使用者/日期區間篩選），用來找出某一週對應的 plan_id 以便查看/修改"""
    return meal_plan_service.list_plans(db, user_id, start_date, end_date)


@router.get("/meal-plans/{plan_id}")
def get_meal_plan(plan_id: int, db: Session = Depends(get_db)):
    plan = meal_plan_service.get_plan(db, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="計畫不存在")
    return plan


@router.get("/meal-plans/{plan_id}/prep-plan")
def get_prep_plan(plan_id: int, db: Session = Depends(get_db)):
    """備料規劃：週日整週肉類批次、週二/週四備便當、每日晚餐提示，含建議的備料步驟"""
    try:
        return meal_plan_service.get_prep_plan(db, plan_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/meal-plans/{plan_id}/adjust/replace-meal")
def replace_meal(plan_id: int, payload: ReplaceMealRequest, db: Session = Depends(get_db)):
    try:
        return meal_plan_service.replace_meal(db, plan_id, payload.meal_id, payload.new_recipe_id, "替換")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/meal-plans/{plan_id}/adjust/search-replace")
def search_replace_meal(plan_id: int, payload: SearchReplaceMealRequest, db: Session = Depends(get_db)):
    try:
        return meal_plan_service.replace_meal(db, plan_id, payload.meal_id, payload.new_recipe_id, "搜尋替換", payload.search_query)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/meal-plans/{plan_id}/adjust/serving-weight")
def adjust_serving_weight(plan_id: int, payload: AdjustServingWeightRequest, db: Session = Depends(get_db)):
    try:
        return meal_plan_service.adjust_serving_weight(db, plan_id, payload.meal_id, payload.new_serving_weight_g)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/meal-plans/{plan_id}/adjust/regenerate-day")
def regenerate_day(plan_id: int, payload: RegenerateDayRequest, db: Session = Depends(get_db)):
    try:
        return meal_plan_service.regenerate_day(db, plan_id, payload.meal_date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/meal-plans/{plan_id}/adjust/add-dish")
def add_dish(plan_id: int, payload: AddDishRequest, db: Session = Depends(get_db)):
    """單一餐別內自由新增一道菜（早餐/下午茶需指定 user_id，午餐/晚餐兩人共用）"""
    try:
        return meal_plan_service.add_dish(db, plan_id, payload.meal_date, payload.meal_type, payload.recipe_id, payload.user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/meal-plans/{plan_id}/adjust/dish/{meal_id}")
def remove_dish(plan_id: int, meal_id: int, db: Session = Depends(get_db)):
    """移除單一道菜（午餐/晚餐會連同對方那份一起移除）"""
    try:
        return meal_plan_service.remove_dish(db, plan_id, meal_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/meal-plans/{plan_id}/adjust/rebalance-day")
def rebalance_day(plan_id: int, payload: RebalanceDayRequest, db: Session = Depends(get_db)):
    """重跑該天的熱量規劃：菜色不變，依當天熱量目標重新分配所有餐點的份量"""
    try:
        return meal_plan_service.rebalance_day(db, plan_id, payload.meal_date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
