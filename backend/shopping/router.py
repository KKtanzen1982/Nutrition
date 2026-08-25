from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from shopping.schemas import (
    PurchaseLocationCreate, PurchaseLocationUpdate, PurchaseLocationResponse,
    IngredientLocationPreferenceSet, IngredientLocationPreferenceResponse,
    ConfirmMealPlanResponse, ShoppingListItemCreate, ShoppingListItemUpdate,
    ShoppingListItemMarkPurchased, ShoppingListItemResponse, ShoppingListResponse,
    ShoppingListStatusUpdate, ShoppingListHistoryEntry, ShoppingListHistoryPage,
    GenericSuccessResponse,
)
from shopping.services import purchase_location_service, shopping_list_service

router = APIRouter(tags=["shopping"])


@router.post("/meal-plans/{plan_id}/confirm", response_model=ConfirmMealPlanResponse)
def confirm_meal_plan(plan_id: int, db: Session = Depends(get_db)):
    try:
        confirmed_plan_id, shopping_list_id = shopping_list_service.confirm_plan(db, plan_id)
        return ConfirmMealPlanResponse(success=True, plan_id=confirmed_plan_id, shopping_list_id=shopping_list_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/shopping-lists/history", response_model=ShoppingListHistoryPage)
def get_shopping_list_history(page: int = 1, limit: int = 10, db: Session = Depends(get_db)):
    rows, total = shopping_list_service.get_history(db, page, limit)
    return ShoppingListHistoryPage(history=[ShoppingListHistoryEntry.model_validate(r) for r in rows], total=total)


@router.get("/shopping-lists/{list_id}", response_model=ShoppingListResponse)
def get_shopping_list(list_id: int, db: Session = Depends(get_db)):
    detail = shopping_list_service.get_detail(db, list_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"購物清單 {list_id} 不存在")
    return ShoppingListResponse(**detail)


@router.post("/shopping-lists/{list_id}/items", response_model=ShoppingListItemResponse)
def add_shopping_list_item(list_id: int, item: ShoppingListItemCreate, db: Session = Depends(get_db)):
    row = shopping_list_service.add_item(db, list_id, item.model_dump())
    if not row:
        raise HTTPException(status_code=404, detail=f"購物清單 {list_id} 不存在")
    name = shopping_list_service.get_ingredient_name(db, row.ingredient_id)
    return ShoppingListItemResponse(
        id=row.id, ingredient_id=row.ingredient_id, ingredient_name=name,
        quantity_needed_g=row.quantity_needed_g, unit=row.unit,
        purchase_location_id=row.purchase_location_id, cost_level=row.cost_level,
        needs_restocking=row.needs_restocking, assigned_user_id=row.assigned_user_id,
        notes=row.notes, is_purchased=row.is_purchased, purchased_at=row.purchased_at,
    )


@router.put("/shopping-lists/{list_id}/items/{item_id}", response_model=GenericSuccessResponse)
def update_shopping_list_item(list_id: int, item_id: int, updates: ShoppingListItemUpdate, db: Session = Depends(get_db)):
    row = shopping_list_service.update_item(db, list_id, item_id, updates.model_dump())
    if not row:
        raise HTTPException(status_code=404, detail=f"購物項目 {item_id}（清單 {list_id}）不存在")
    return GenericSuccessResponse(message="購物項目已更新")


@router.delete("/shopping-lists/{list_id}/items/{item_id}", response_model=GenericSuccessResponse)
def delete_shopping_list_item(list_id: int, item_id: int, db: Session = Depends(get_db)):
    if not shopping_list_service.delete_item(db, list_id, item_id):
        raise HTTPException(status_code=404, detail=f"購物項目 {item_id}（清單 {list_id}）不存在")
    return GenericSuccessResponse(message="購物項目已刪除")


@router.put("/shopping-lists/{list_id}/items/{item_id}/purchased", response_model=GenericSuccessResponse)
def mark_item_purchased(list_id: int, item_id: int, payload: ShoppingListItemMarkPurchased, db: Session = Depends(get_db)):
    row = shopping_list_service.mark_purchased(db, list_id, item_id, payload.is_purchased)
    if not row:
        raise HTTPException(status_code=404, detail=f"購物項目 {item_id}（清單 {list_id}）不存在")
    return GenericSuccessResponse(message="已更新採購狀態")


@router.put("/shopping-lists/{list_id}/status", response_model=GenericSuccessResponse)
def update_shopping_list_status(list_id: int, payload: ShoppingListStatusUpdate, db: Session = Depends(get_db)):
    try:
        row = shopping_list_service.update_status(db, list_id, payload.status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not row:
        raise HTTPException(status_code=404, detail=f"購物清單 {list_id} 不存在")
    return GenericSuccessResponse(message=f"狀態已更新為「{payload.status}」")


@router.get("/purchase-locations", response_model=List[PurchaseLocationResponse])
def list_purchase_locations(active_only: bool = True, db: Session = Depends(get_db)):
    return purchase_location_service.list_locations(db, active_only)


@router.post("/purchase-locations", response_model=PurchaseLocationResponse, status_code=201)
def create_purchase_location(location: PurchaseLocationCreate, db: Session = Depends(get_db)):
    return purchase_location_service.create_location(db, location)


@router.put("/purchase-locations/{location_id}", response_model=PurchaseLocationResponse)
def update_purchase_location(location_id: int, updates: PurchaseLocationUpdate, db: Session = Depends(get_db)):
    row = purchase_location_service.update_location(db, location_id, updates)
    if not row:
        raise HTTPException(status_code=404, detail=f"購買地點 {location_id} 不存在")
    return row


@router.delete("/purchase-locations/{location_id}", response_model=GenericSuccessResponse)
def delete_purchase_location(location_id: int, db: Session = Depends(get_db)):
    if not purchase_location_service.delete_location(db, location_id):
        raise HTTPException(status_code=404, detail=f"購買地點 {location_id} 不存在")
    return GenericSuccessResponse(message="購買地點已刪除")


@router.get("/ingredients/{ingredient_id}/location-preference", response_model=List[IngredientLocationPreferenceResponse])
def get_ingredient_location_preference(ingredient_id: int, db: Session = Depends(get_db)):
    return purchase_location_service.get_ingredient_preferences(db, ingredient_id)


@router.put("/ingredients/{ingredient_id}/location-preference", response_model=List[IngredientLocationPreferenceResponse])
def set_ingredient_location_preference(ingredient_id: int, payload: IngredientLocationPreferenceSet, db: Session = Depends(get_db)):
    rows = purchase_location_service.set_ingredient_preferences(
        db, ingredient_id, [p.model_dump() for p in payload.preferences]
    )
    if rows is None:
        raise HTTPException(status_code=404, detail=f"食材 {ingredient_id} 不存在")
    return rows
