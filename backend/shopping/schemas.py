from datetime import datetime, date
from typing import Optional, List, Dict
from pydantic import BaseModel, Field


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

    class Config:
        from_attributes = True


class IngredientLocationPreferenceItem(BaseModel):
    preferred_location_id: int
    priority: int = Field(ge=1, le=3)
    notes: Optional[str] = None


class IngredientLocationPreferenceSet(BaseModel):
    preferences: List[IngredientLocationPreferenceItem]


class IngredientLocationPreferenceResponse(BaseModel):
    id: int
    ingredient_id: int
    preferred_location_id: int
    location_name: str
    priority: int
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class ConfirmMealPlanResponse(BaseModel):
    success: bool
    plan_id: int
    shopping_list_id: int
    message: str = "推薦已確認，購物清單已生成"


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

    class Config:
        from_attributes = True


class ShoppingListItemGroup(BaseModel):
    category: str
    items: List[ShoppingListItemResponse]


class ShoppingListResponse(BaseModel):
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
    status: str


class GenericSuccessResponse(BaseModel):
    success: bool = True
    message: Optional[str] = None


class ShoppingListHistoryEntry(BaseModel):
    id: int
    shopping_list_id: int
    item_changes: Optional[str] = None
    status_log: Optional[str] = None
    archived_at: datetime
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class ShoppingListHistoryPage(BaseModel):
    history: List[ShoppingListHistoryEntry]
    total: int
