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
    season: Optional[str] = None  # 盛產季節（春/夏/秋/冬，逗號分隔），只有蔬果類需要填；不分季節的留空


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
    season: Optional[str] = None


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
    carb_source: Optional[str] = None  # 只有「主食」類會填（飯/麵/其他），供選餐演算法主食輪替/白飯規則判斷
    pairing_style: Optional[str] = None  # 主食/肉/菜/湯適用（家常/西式），供選餐演算法判斷跟主食搭不搭
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
    carb_source: Optional[str] = None
    pairing_style: Optional[str] = None


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
    season: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class RecipeIngredientResponse(BaseModel):
    id: int
    ingredient_id: int
    quantity_g: float
    unit: str
    notes: Optional[str] = None
    ingredient: Optional[IngredientResponse] = None  # 帶出食材名稱，避免前端只能顯示 ingredient_id

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


class RecipeSummaryResponse(BaseModel):
    """瀏覽清單／搜尋結果用的輕量版本，不含食材與步驟——這兩個清單常常一次列幾十筆，
    帶上食材/步驟會讓每一筆都多觸發好幾次查詢，是清單載入慢、換頁還要重新等待的主因。"""
    id: int
    recipe_name: str
    category: str
    base_weight_g: int
    cost_level: str
    is_active: bool
    is_vegetarian: bool
    carb_source: Optional[str] = None
    pairing_style: Optional[str] = None
    total_calories_kcal: Optional[float] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None


class RecipeResponse(BaseModel):
    id: int
    recipe_name: str
    category: str
    base_weight_g: int
    cost_level: str
    is_active: bool
    is_vegetarian: bool
    allergen_tags: Optional[str] = None
    carb_source: Optional[str] = None
    pairing_style: Optional[str] = None
    created_at: datetime
    last_updated_at: datetime
    ingredients: List[RecipeIngredientResponse] = []
    steps: List[RecipeStepResponse] = []
    nutrition: Optional[RecipeNutritionResponse] = None

    class Config:
        from_attributes = True
