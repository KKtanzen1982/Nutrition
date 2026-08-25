from datetime import date
from typing import Optional
from pydantic import BaseModel, Field


class GenerateMealPlanRequest(BaseModel):
    user_id_a: int
    user_id_b: int
    week_start_date: date


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
