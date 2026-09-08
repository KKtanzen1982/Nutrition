from datetime import date
from typing import List, Optional
from pydantic import BaseModel, Field


class GenerateMealPlanRequest(BaseModel):
    user_id_a: int
    user_id_b: int
    week_start_date: date


class SetManualCaloriesTargetRequest(BaseModel):
    manual_calories_target: Optional[float] = Field(None, ge=800, le=6000, description="手動覆蓋每日熱量目標；傳 null 清除覆蓋，改回依 BMR/TDEE 自動計算")


class ReplaceMealRequest(BaseModel):
    meal_id: int
    new_recipe_id: int


class SearchReplaceMealRequest(BaseModel):
    meal_id: int
    new_recipe_id: int
    search_query: Optional[str] = None


class AdjustServingWeightRequest(BaseModel):
    meal_id: int
    new_serving_weight_g: float = Field(..., gt=0)


class RegenerateDayRequest(BaseModel):
    meal_date: date


FIXED_MEAL_TYPES = ("breakfast", "afternoon_snack")


class SetFixedMealPreferenceRequest(BaseModel):
    user_id: int
    meal_type: str
    recipe_id: int


class SetExcludedRecipeRequest(BaseModel):
    recipe_id: int


class SetFavoriteRecipeRequest(BaseModel):
    user_id: int
    recipe_id: int


class SetSoupDaysRequest(BaseModel):
    days: List[int] = Field(default_factory=list)  # 0=週一...6=週日


class AddDishRequest(BaseModel):
    meal_date: date
    meal_type: str
    recipe_id: int
    user_id: Optional[int] = None  # 早餐/下午茶必填（各自一份），午餐/晚餐忽略（兩人共用）


class RebalanceDayRequest(BaseModel):
    meal_date: date
