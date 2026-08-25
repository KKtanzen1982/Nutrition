"""
BLOCK_6: Pydantic 數據模型 - 購物清單管理
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import date, datetime
from enum import Enum


# ==================== 列舉型別 ====================

class ShoppingListStatus(str, Enum):
    """購物清單狀態"""
    DRAFT = "草稿"
    CONFIRMED = "已確認"
    PURCHASING = "採購中"
    PURCHASED = "已採購"
    ARCHIVED = "歸檔"


class CostLevel(str, Enum):
    """成本等級"""
    LOW = "低"
    MEDIUM = "中"
    HIGH = "高"


class MealPlanStatus(str, Enum):
    """週計畫狀態（僅本區塊需要用到的部分）"""
    DRAFT = "草稿"
    PENDING_ADJUSTMENT = "待微調"
    CONFIRMED = "已確認"


# ==================== 購買地點（表 6a） ====================

class PurchaseLocationCreate(BaseModel):
    location_name: str
    description: Optional[str] = None
    priority_order: Optional[int] = 99


class PurchaseLocationUpdate(BaseModel):
    location_name: Optional[str] = None
    description: Optional[str] = None
    priority_order: Optional[int] = None
    is_active: Optional[bool] = None


class PurchaseLocationResponse(BaseModel):
    id: int
    location_name: str
    description: Optional[str] = None
    priority_order: int
    is_active: bool

    model_config = {"from_attributes": True}


# ==================== 食材地點偏好（表 6b） ====================

class IngredientLocationPreferenceSet(BaseModel):
    """設定某個食材的地點偏好（priority=1 為最優先，可一次帶多筆）"""
    preferences: List["IngredientLocationPreferenceItem"]


class IngredientLocationPreferenceItem(BaseModel):
    preferred_location_id: int
    priority: int = Field(ge=1, le=3)
    notes: Optional[str] = None


class IngredientLocationPreferenceResponse(BaseModel):
    id: int
    ingredient_id: int
    preferred_location_id: int
    location_name: str
    priority: int
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


IngredientLocationPreferenceSet.model_rebuild()


# ==================== 購物清單生成 / 確認推薦 ====================

class GenerateShoppingListRequest(BaseModel):
    """從一個已確認的週計畫生成購物清單"""
    plan_id: int
    list_date: Optional[date] = None  # 預設今天


class ConfirmMealPlanResponse(BaseModel):
    """POST /meal-plans/:id/confirm 的回應"""
    success: bool
    plan_id: int
    shopping_list_id: int
    message: str = "推薦已確認，購物清單已生成"


# ==================== 購物項目（表 6d） ====================

class ShoppingListItemCreate(BaseModel):
    ingredient_id: int
    quantity_needed_g: float
    unit: Optional[str] = "g"
    purchase_location_id: Optional[int] = None
    assigned_user_id: Optional[int] = None
    notes: Optional[str] = None


class ShoppingListItemUpdate(BaseModel):
    quantity_needed_g: Optional[float] = None
    purchase_location_id: Optional[int] = None
    assigned_user_id: Optional[int] = None
    notes: Optional[str] = None


class ShoppingListItemMarkPurchased(BaseModel):
    is_purchased: bool = True


class ShoppingListItemResponse(BaseModel):
    id: int
    ingredient_id: int
    ingredient_name: str
    quantity_needed_g: float
    unit: str
    purchase_location_id: Optional[int] = None
    cost_level: Optional[str] = None
    needs_restocking: bool
    assigned_user_id: Optional[int] = None
    notes: Optional[str] = None
    is_purchased: bool
    purchased_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ==================== 購物清單（表 6c） ====================

class ShoppingListItemGroup(BaseModel):
    """依「食材分類」分組的項目（同一個購買地點內再分類）"""
    category: str
    items: List[ShoppingListItemResponse]


class ShoppingListResponse(BaseModel):
    """GET /shopping-lists/:id 的回應：按購買地點 -> 分類分組"""
    list_id: int
    status: str
    list_date: date
    week_start_date: date
    created_from_plan_id: Optional[int] = None
    total_items: int
    items_by_location: Dict[str, List[ShoppingListItemGroup]]
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ShoppingListStatusUpdate(BaseModel):
    status: ShoppingListStatus


class GenericSuccessResponse(BaseModel):
    success: bool = True
    message: Optional[str] = None


# ==================== 採購歷史（表 6e） ====================

class ShoppingListHistoryEntry(BaseModel):
    id: int
    shopping_list_id: int
    item_changes: Optional[str] = None
    status_log: Optional[str] = None
    archived_at: datetime
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


class ShoppingListHistoryPage(BaseModel):
    history: List[ShoppingListHistoryEntry]
    total: int
