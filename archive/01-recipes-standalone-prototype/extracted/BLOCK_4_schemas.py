"""
BLOCK_4: 食譜和食材管理 - Pydantic Schemas
==============================================

用於請求驗證和回應序列化
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime, date


# ============================================================
# 食材相關 Schemas
# ============================================================

class IngredientStockBase(BaseModel):
    """食材庫存基礎資訊"""
    current_quantity_g: float = 0.0
    min_threshold_g: Optional[float] = None
    unit: str = "g"
    last_purchased_at: Optional[date] = None
    notes: Optional[str] = None


class IngredientStockCreate(IngredientStockBase):
    """建立食材庫存"""
    ingredient_id: int


class IngredientStockUpdate(BaseModel):
    """更新食材庫存"""
    current_quantity_g: Optional[float] = None
    min_threshold_g: Optional[float] = None
    unit: Optional[str] = None
    notes: Optional[str] = None


class IngredientStockResponse(IngredientStockBase):
    """食材庫存回應"""
    id: int
    ingredient_id: int

    class Config:
        from_attributes = True


class IngredientLibraryBase(BaseModel):
    """食材庫基礎資訊"""
    ingredient_name: str
    category: str  # '蔬菜' / '肉類' / '穀物' / '乳製品' / '調味料' / '其他'
    unit: str = "g"
    calories_per_100g: Optional[float] = None
    protein_per_100g: Optional[float] = None
    carbs_per_100g: Optional[float] = None
    fat_per_100g: Optional[float] = None
    fiber_per_100g: Optional[float] = None
    preferred_purchase_location: Optional[str] = None
    needs_stock_tracking: bool = False

    @validator("ingredient_name")
    def ingredient_name_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("食材名稱不能為空")
        return v.strip()


class IngredientLibraryCreate(IngredientLibraryBase):
    """建立食材"""
    pass


class IngredientLibraryUpdate(BaseModel):
    """更新食材"""
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


class IngredientLibraryResponse(IngredientLibraryBase):
    """食材回應（含庫存）"""
    id: int
    created_at: datetime
    stock: Optional[IngredientStockResponse] = None

    class Config:
        from_attributes = True


class IngredientSearchResult(BaseModel):
    """食材搜尋結果"""
    id: int
    ingredient_name: str
    category: str
    unit: str
    calories_per_100g: Optional[float] = None
    protein_per_100g: Optional[float] = None
    carbs_per_100g: Optional[float] = None
    fat_per_100g: Optional[float] = None
    fiber_per_100g: Optional[float] = None
    needs_stock_tracking: bool


class LowStockIngredient(BaseModel):
    """低庫存食材警告"""
    ingredient_id: int
    ingredient_name: str
    category: str
    current_quantity_g: float
    min_threshold_g: float
    unit: str
    last_purchased_at: Optional[date] = None
    deficit_g: float  # 差多少才達到最小閾值


# ============================================================
# 食譜相關 Schemas
# ============================================================

class RecipeIngredientBase(BaseModel):
    """食譜食材明細基礎資訊"""
    ingredient_id: int
    quantity_g: float = Field(..., gt=0)
    unit: str = "g"
    notes: Optional[str] = None


class RecipeIngredientCreate(RecipeIngredientBase):
    """建立食譜食材明細"""
    pass


class RecipeIngredientResponse(RecipeIngredientBase):
    """食譜食材明細回應"""
    id: int
    recipe_id: int
    ingredient: Optional[IngredientSearchResult] = None

    class Config:
        from_attributes = True


class RecipeStepBase(BaseModel):
    """製作步驟基礎資訊"""
    step_number: int = Field(..., ge=1)
    step_description: str

    @validator("step_description")
    def step_description_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("步驟描述不能為空")
        return v.strip()


class RecipeStepCreate(RecipeStepBase):
    """建立製作步驟"""
    pass


class RecipeStepResponse(RecipeStepBase):
    """製作步驟回應"""
    id: int
    recipe_id: int
    version: int
    is_current: bool
    created_at: datetime

    class Config:
        from_attributes = True


class RecipeNutritionBase(BaseModel):
    """營養素資訊基礎"""
    total_calories_kcal: Optional[float] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    fiber_g: Optional[float] = None


class RecipeNutritionResponse(RecipeNutritionBase):
    """營養素資訊回應"""
    id: int
    recipe_id: int
    calculated_at: datetime

    class Config:
        from_attributes = True


class RecipeBase(BaseModel):
    """食譜基礎資訊"""
    recipe_name: str
    category: str  # '早餐' / '主食' / '肉' / '菜' / '飲料' / '點心'
    base_weight_g: int = Field(..., gt=0)
    cost_level: str  # '低' / '中' / '高'

    @validator("recipe_name")
    def recipe_name_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("食譜名稱不能為空")
        return v.strip()


class RecipeCreate(RecipeBase):
    """建立食譜（含食材和步驟）"""
    ingredients: List[RecipeIngredientCreate] = []
    steps: List[RecipeStepCreate] = []


class RecipeUpdate(BaseModel):
    """更新食譜基本資訊"""
    recipe_name: Optional[str] = None
    category: Optional[str] = None
    base_weight_g: Optional[int] = None
    cost_level: Optional[str] = None
    is_active: Optional[bool] = None


class RecipeDetailResponse(RecipeBase):
    """食譜詳細回應（含所有關聯資訊）"""
    id: int
    is_active: bool
    created_at: datetime
    last_updated_at: datetime
    ingredients: List[RecipeIngredientResponse] = []
    steps: List[RecipeStepResponse] = []
    nutrition: Optional[RecipeNutritionResponse] = None

    class Config:
        from_attributes = True


class RecipeListResponse(RecipeBase):
    """食譜列表回應（簡化版本）"""
    id: int
    is_active: bool
    created_at: datetime
    nutrition: Optional[RecipeNutritionResponse] = None

    class Config:
        from_attributes = True


class RecipeSearchResponse(BaseModel):
    """食譜搜尋結果"""
    id: int
    recipe_name: str
    category: str
    base_weight_g: int
    cost_level: str
    total_calories_kcal: Optional[float] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None


# ============================================================
# 購買地點相關 Schemas
# ============================================================

class PurchaseLocationBase(BaseModel):
    """購買地點基礎資訊"""
    location_name: str
    description: Optional[str] = None
    priority_order: int = 0

    @validator("location_name")
    def location_name_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("地點名稱不能為空")
        return v.strip()


class PurchaseLocationCreate(PurchaseLocationBase):
    """建立購買地點"""
    pass


class PurchaseLocationUpdate(BaseModel):
    """更新購買地點"""
    location_name: Optional[str] = None
    description: Optional[str] = None
    priority_order: Optional[int] = None
    is_active: Optional[bool] = None


class PurchaseLocationResponse(PurchaseLocationBase):
    """購買地點回應"""
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class IngredientLocationPreferenceBase(BaseModel):
    """食材地點偏好基礎"""
    ingredient_id: int
    preferred_location_id: int
    priority: int = 1
    notes: Optional[str] = None


class IngredientLocationPreferenceCreate(IngredientLocationPreferenceBase):
    """建立食材地點偏好"""
    pass


class IngredientLocationPreferenceResponse(IngredientLocationPreferenceBase):
    """食材地點偏好回應"""
    id: int

    class Config:
        from_attributes = True


# ============================================================
# 分頁和列表回應
# ============================================================

class PaginatedResponse(BaseModel):
    """分頁回應基礎"""
    total: int
    page: int
    limit: int
    items: List[Any]


class RecipeListPaginatedResponse(PaginatedResponse):
    """食譜列表分頁回應"""
    items: List[RecipeListResponse]


class IngredientListPaginatedResponse(PaginatedResponse):
    """食材列表分頁回應"""
    items: List[IngredientLibraryResponse]


# ============================================================
# 營養素計算結果
# ============================================================

class NutritionCalculationResult(BaseModel):
    """營養素計算結果"""
    recipe_id: int
    recipe_name: str
    base_weight_g: int
    total_calories_kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float
    calculated_at: datetime


class RecipeStepsVersionResponse(BaseModel):
    """食譜步驟版本詳情"""
    recipe_id: int
    recipe_name: str
    version: int
    steps: List[RecipeStepResponse]
    is_current: bool
    created_at: datetime
