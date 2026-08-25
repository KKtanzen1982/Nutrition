"""
BLOCK_6: 購物清單相關 API Endpoints

- POST   /meal-plans/{plan_id}/confirm                          確認推薦並生成購物清單
- GET    /shopping-lists/history                                採購歷史
- GET    /shopping-lists/{list_id}                               取得購物清單（按地點分組）
- POST   /shopping-lists/{list_id}/items                         新增購物項目
- PUT    /shopping-lists/{list_id}/items/{item_id}                編輯購物項目
- DELETE /shopping-lists/{list_id}/items/{item_id}                刪除購物項目
- PUT    /shopping-lists/{list_id}/items/{item_id}/purchased      標記已購
- PUT    /shopping-lists/{list_id}/status                         改變清單狀態
- GET    /purchase-locations                                     購買地點列表
- POST   /purchase-locations                                     新增購買地點
- PUT    /purchase-locations/{location_id}                        編輯購買地點
- DELETE /purchase-locations/{location_id}                        刪除購買地點
- GET    /ingredients/{ingredient_id}/location-preference          取得食材地點偏好
- PUT    /ingredients/{ingredient_id}/location-preference          設定食材地點偏好
"""

import logging
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session

from BLOCK_6_schemas import (
    ConfirmMealPlanResponse,
    ShoppingListResponse,
    ShoppingListItemCreate,
    ShoppingListItemUpdate,
    ShoppingListItemMarkPurchased,
    ShoppingListItemResponse,
    ShoppingListStatusUpdate,
    ShoppingListHistoryEntry,
    ShoppingListHistoryPage,
    PurchaseLocationCreate,
    PurchaseLocationUpdate,
    PurchaseLocationResponse,
    IngredientLocationPreferenceSet,
    IngredientLocationPreferenceResponse,
    GenericSuccessResponse,
)
import BLOCK_6_db_service as db_service

logger = logging.getLogger(__name__)


def get_db() -> Session:
    """
    取得數據庫連接（placeholder）。

    實際執行時由掛載的 app（見 BLOCK_6_test_app.py / main.py）用
    app.dependency_overrides[get_db] 換成真正連到資料庫的 session。
    """
    raise NotImplementedError("需要連接真實數據庫")


# ==================== 確認推薦 → 生成購物清單 ====================

router_meal_plans = APIRouter(prefix="/meal-plans", tags=["meal-plans-confirm"])


@router_meal_plans.post("/{plan_id}/confirm", response_model=ConfirmMealPlanResponse)
async def confirm_meal_plan(plan_id: int, db: Session = Depends(get_db)):
    """確認週推薦：狀態改為「已確認」，並自動生成購物清單（表 6c/6d）。"""
    try:
        confirmed_plan_id, shopping_list_id = db_service.confirm_plan_and_generate_list(db, plan_id)
        return ConfirmMealPlanResponse(success=True, plan_id=confirmed_plan_id, shopping_list_id=shopping_list_id)
    except db_service.NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except db_service.ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"確認推薦失敗：{str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 購物清單 ====================

router_shopping_lists = APIRouter(prefix="/shopping-lists", tags=["shopping-lists"])


@router_shopping_lists.get("/history", response_model=ShoppingListHistoryPage)
async def get_shopping_list_history(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """取得採購歷史（歸檔快照）。"""
    try:
        rows, total = db_service.get_shopping_list_history(db, page, limit)
        return ShoppingListHistoryPage(
            history=[ShoppingListHistoryEntry.model_validate(r) for r in rows],
            total=total,
        )
    except Exception as e:
        logger.error(f"取得採購歷史失敗：{str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router_shopping_lists.get("/{list_id}", response_model=ShoppingListResponse)
async def get_shopping_list(list_id: int, db: Session = Depends(get_db)):
    """取得購物清單（按購買地點 -> 食材分類分組）。"""
    try:
        detail = db_service.get_shopping_list_detail(db, list_id)
        if detail is None:
            raise HTTPException(status_code=404, detail=f"購物清單 {list_id} 不存在")
        return ShoppingListResponse(**detail)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取得購物清單失敗：{str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router_shopping_lists.post("/{list_id}/items", response_model=ShoppingListItemResponse)
async def add_shopping_list_item(list_id: int, item: ShoppingListItemCreate, db: Session = Depends(get_db)):
    """新增購物項目（例如臨時食材）。"""
    try:
        row = db_service.add_shopping_list_item(db, list_id, item.model_dump())
        name = db_service.get_ingredient_name(db, row.ingredient_id)
        return ShoppingListItemResponse(
            id=row.id, ingredient_id=row.ingredient_id, ingredient_name=name,
            quantity_needed_g=row.quantity_needed_g, unit=row.unit,
            purchase_location_id=row.purchase_location_id, cost_level=row.cost_level,
            needs_restocking=row.needs_restocking, assigned_user_id=row.assigned_user_id,
            notes=row.notes, is_purchased=row.is_purchased, purchased_at=row.purchased_at,
        )
    except db_service.NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"新增購物項目失敗：{str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router_shopping_lists.put("/{list_id}/items/{item_id}", response_model=GenericSuccessResponse)
async def update_shopping_list_item(
    list_id: int, item_id: int, updates: ShoppingListItemUpdate, db: Session = Depends(get_db)
):
    """編輯購物項目（用量、地點、備註）。"""
    try:
        db_service.update_shopping_list_item(db, list_id, item_id, updates.model_dump())
        return GenericSuccessResponse(message="購物項目已更新")
    except db_service.NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"編輯購物項目失敗：{str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router_shopping_lists.delete("/{list_id}/items/{item_id}", response_model=GenericSuccessResponse)
async def delete_shopping_list_item(list_id: int, item_id: int, db: Session = Depends(get_db)):
    """刪除購物項目。"""
    try:
        db_service.delete_shopping_list_item(db, list_id, item_id)
        return GenericSuccessResponse(message="購物項目已刪除")
    except db_service.NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"刪除購物項目失敗：{str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router_shopping_lists.put("/{list_id}/items/{item_id}/purchased", response_model=GenericSuccessResponse)
async def mark_item_purchased(
    list_id: int, item_id: int, payload: ShoppingListItemMarkPurchased, db: Session = Depends(get_db)
):
    """標記購物項目為已購（或取消已購）。"""
    try:
        db_service.mark_item_purchased(db, list_id, item_id, payload.is_purchased)
        return GenericSuccessResponse(message="已更新採購狀態")
    except db_service.NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"標記已購失敗：{str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router_shopping_lists.put("/{list_id}/status", response_model=GenericSuccessResponse)
async def update_shopping_list_status(list_id: int, payload: ShoppingListStatusUpdate, db: Session = Depends(get_db)):
    """
    改變清單狀態（草稿/已確認/採購中/已採購/歸檔）。
    改成「歸檔」時會自動把目前所有項目的快照寫入採購歷史（表 6e）。
    """
    try:
        db_service.update_shopping_list_status(db, list_id, payload.status.value)
        return GenericSuccessResponse(message=f"狀態已更新為「{payload.status.value}」")
    except db_service.NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"更新清單狀態失敗：{str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 購買地點（表 6a） ====================

router_purchase_locations = APIRouter(prefix="/purchase-locations", tags=["purchase-locations"])


@router_purchase_locations.get("", response_model=list[PurchaseLocationResponse])
async def list_purchase_locations(active_only: bool = True, db: Session = Depends(get_db)):
    """取得購買地點列表。"""
    try:
        rows = db_service.list_purchase_locations(db, active_only)
        return [PurchaseLocationResponse.model_validate(r) for r in rows]
    except Exception as e:
        logger.error(f"取得購買地點失敗：{str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router_purchase_locations.post("", response_model=PurchaseLocationResponse)
async def create_purchase_location(location: PurchaseLocationCreate, db: Session = Depends(get_db)):
    """新增購買地點。"""
    try:
        row = db_service.create_purchase_location(db, location.model_dump())
        return PurchaseLocationResponse.model_validate(row)
    except Exception as e:
        logger.error(f"新增購買地點失敗：{str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router_purchase_locations.put("/{location_id}", response_model=PurchaseLocationResponse)
async def update_purchase_location(location_id: int, updates: PurchaseLocationUpdate, db: Session = Depends(get_db)):
    """編輯購買地點。"""
    try:
        row = db_service.update_purchase_location(db, location_id, updates.model_dump())
        return PurchaseLocationResponse.model_validate(row)
    except db_service.NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"編輯購買地點失敗：{str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router_purchase_locations.delete("/{location_id}", response_model=GenericSuccessResponse)
async def delete_purchase_location(location_id: int, db: Session = Depends(get_db)):
    """刪除購買地點。"""
    try:
        db_service.delete_purchase_location(db, location_id)
        return GenericSuccessResponse(message="購買地點已刪除")
    except db_service.NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"刪除購買地點失敗：{str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 食材地點偏好（表 6b） ====================

router_ingredient_preferences = APIRouter(prefix="/ingredients", tags=["ingredient-location-preference"])


@router_ingredient_preferences.get(
    "/{ingredient_id}/location-preference", response_model=list[IngredientLocationPreferenceResponse]
)
async def get_ingredient_location_preference(ingredient_id: int, db: Session = Depends(get_db)):
    """取得某食材的地點偏好設定（依優先度排序）。"""
    try:
        rows = db_service.get_ingredient_location_preferences(db, ingredient_id)
        return [IngredientLocationPreferenceResponse(**r) for r in rows]
    except Exception as e:
        logger.error(f"取得食材地點偏好失敗：{str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router_ingredient_preferences.put(
    "/{ingredient_id}/location-preference", response_model=list[IngredientLocationPreferenceResponse]
)
async def set_ingredient_location_preference(
    ingredient_id: int, payload: IngredientLocationPreferenceSet, db: Session = Depends(get_db)
):
    """設定（整批覆蓋）某食材的地點偏好。"""
    try:
        rows = db_service.set_ingredient_location_preferences(
            db, ingredient_id, [p.model_dump() for p in payload.preferences]
        )
        return [IngredientLocationPreferenceResponse(**r) for r in rows]
    except db_service.NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"設定食材地點偏好失敗：{str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
