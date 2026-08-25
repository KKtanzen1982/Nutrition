from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field


class IngredientCreate(BaseModel):
    ingredient_name: str = Field(..., min_length=1)
    category: str
    unit: str = "g"
    calories_per_100g: Optional[float] = None
    protein_per_100g: Optional[float] = None
    carbs_per_100g: Optional[float] = None
    fat_per_100g: Optional[float] = None
    fiber_per_100g: Optional[float] = None
    preferred_purchase_location: Optional[str] = None
    needs_stock_tracking: bool = False


class IngredientUpdate(BaseModel):
    ingredient_name: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    calories_per_100g: Optional[float] = None
    protein_per_100g: Optional[float] = None
    carbs_per_100g: Optional[float] = None
    fat_per_100g: Optional[float] = None
    fiber_per_100g: Optional[float] = None
    preferred_purchase_location: Optional[str] = None
    needs_stock_tracking: Optional[bool] = None


class IngredientStockUpdate(BaseModel):
    current_quantity_g: Optional[float] = None
    min_threshold_g: Optional[float] = None


class RecipeIngredientCreate(BaseModel):
    ingredient_id: int
    quantity_g: float
    unit: str = "g"
    notes: Optional[str] = None


class RecipeStepCreate(BaseModel):
    step_number: int
    step_description: str


class RecipeCreate(BaseModel):
    recipe_name: str = Field(..., min_length=1)
    category: str
    base_weight_g: int
    cost_level: str
    is_vegetarian: bool = False
    allergen_tags: Optional[str] = ""
    ingredients: List[RecipeIngredientCreate] = Field(..., min_length=1)
    steps: List[RecipeStepCreate] = Field(..., min_length=1)


class RecipeUpdate(BaseModel):
    recipe_name: Optional[str] = None
    category: Optional[str] = None
    base_weight_g: Optional[int] = None
    cost_level: Optional[str] = None
    is_vegetarian: Optional[bool] = None
    allergen_tags: Optional[str] = None
    is_active: Optional[bool] = None


class IngredientStockResponse(BaseModel):
    id: int
    ingredient_id: int
    current_quantity_g: float
    min_threshold_g: Optional[float] = None
    unit: str
    last_purchased_at: Optional[date] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class IngredientResponse(BaseModel):
    id: int
    ingredient_name: str
    category: str
    unit: str
    calories_per_100g: Optional[float] = None
    protein_per_100g: Optional[float] = None
    carbs_per_100g: Optional[float] = None
    fat_per_100g: Optional[float] = None
    fiber_per_100g: Optional[float] = None
    preferred_purchase_location: Optional[str] = None
    needs_stock_tracking: bool
    created_at: datetime

    class Config:
        from_attributes = True


class RecipeIngredientResponse(BaseModel):
    id: int
    ingredient_id: int
    quantity_g: float
    unit: str
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class RecipeStepResponse(BaseModel):
    id: int
    version: int
    step_number: int
    step_description: str
    is_current: bool

    class Config:
        from_attributes = True


class RecipeNutritionResponse(BaseModel):
    total_calories_kcal: Optional[float] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    fiber_g: Optional[float] = None

    class Config:
        from_attributes = True


class RecipeResponse(BaseModel):
    id: int
    recipe_name: str
    category: str
    base_weight_g: int
    cost_level: str
    is_active: bool
    is_vegetarian: bool
    allergen_tags: Optional[str] = None
    created_at: datetime
    last_updated_at: datetime
    ingredients: List[RecipeIngredientResponse] = []
    steps: List[RecipeStepResponse] = []
    nutrition: Optional[RecipeNutritionResponse] = None

    class Config:
        from_attributes = True
