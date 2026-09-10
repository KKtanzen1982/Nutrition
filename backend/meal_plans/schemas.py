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


FIXED_MEAL_TYPES = ("breakfast", "afternoon_snack")  # 個人餐點，一人一份（add_dish/remove_dish 也用這個判斷要不要指定 user_id）
SHARED_FIXED_MEAL_TYPES = ("lunch", "dinner")  # 兩人共用餐點：固定其中一個類別（主食/肉/菜/湯），不分誰吃
ALL_FIXED_MEAL_TYPES = FIXED_MEAL_TYPES + SHARED_FIXED_MEAL_TYPES


class SetFixedMealPreferenceRequest(BaseModel):
    recipe_id: int
    meal_type: str
    user_id: Optional[int] = None  # breakfast/afternoon_snack 必填；lunch/dinner 不需要（兩人共用，忽略）
    duration_days: Optional[int] = Field(None, ge=1, description="要連續套用幾天，從設定當天算起；不填則永久套用直到手動取消")


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
