"""
BLOCK_6: 真正的資料庫存取層

只做「查詢／持久化」，跨食譜/食材的合併計算邏輯重用 BLOCK_6_shopping_service.py
裡的純函式（不碰 DB，方便單元測試）。

架構對照（見 nutrition_system_architecture_1.md「區塊 6：購物清單管理」）：
- generate_shopping_list_for_plan() ↔「購物清單自動生成」「2 人食材合併計算」
- confirm_plan_and_generate_list() ↔ 週推薦 API 的 POST /meal-plans/:id/confirm
  （BLOCK_5_meal_plan_api.py 目前掛的是 PUT 版本的 stub，回傳 shopping_list_id=None，
   並在註解寫明「購物清單生成屬於區塊 6」；整合時請改接這裡的版本，見
   BLOCK_6_INTEGRATION_GUIDE.md）
"""

import json
import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

import BLOCK_6_shopping_service as shopping_service
from BLOCK_6_models import (
    IngredientLibrary,
    IngredientLocationPreference,
    IngredientStock,
    PurchaseLocation,
    Recipe,
    RecipeIngredient,
    ShoppingList,
    ShoppingListHistory,
    ShoppingListItem,
    WeeklyMealPlan,
    DailyMealDetail,
)

logger = logging.getLogger(__name__)


class NotFoundError(Exception):
    """查無資料（呼叫端轉成 HTTP 404）"""
    pass


class ConflictError(Exception):
    """狀態衝突，例如週計畫尚未確認就想生成購物清單（呼叫端轉成 HTTP 409）"""
    pass


# ==================== 週計畫資料查詢（給生成邏輯打包用） ====================

def _get_meal_rows_for_plan(db: Session, plan_id: int) -> List[Dict[str, Any]]:
    rows = db.query(DailyMealDetail).filter(DailyMealDetail.meal_plan_id == plan_id).all()
    return [
        {
            "recipe_id": r.recipe_id,
            "serving_weight_g": r.serving_weight_g,
            "assigned_user_id": r.assigned_user_id,
        }
        for r in rows
    ]


def _get_recipe_lookup_tables(
    db: Session, recipe_ids: List[int]
) -> Tuple[Dict[int, List[Dict[str, Any]]], Dict[int, float], Dict[int, str]]:
    """回傳 (recipe_ingredients_by_recipe, base_weight_by_id, cost_level_by_id)"""
    if not recipe_ids:
        return {}, {}, {}

    recipes = db.query(Recipe).filter(Recipe.id.in_(set(recipe_ids))).all()
    base_weight_by_id = {r.id: r.base_weight_g for r in recipes}
    cost_level_by_id = {r.id: r.cost_level for r in recipes}

    ri_rows = db.query(RecipeIngredient).filter(RecipeIngredient.recipe_id.in_(set(recipe_ids))).all()
    recipe_ingredients_by_recipe: Dict[int, List[Dict[str, Any]]] = {}
    for ri in ri_rows:
        recipe_ingredients_by_recipe.setdefault(ri.recipe_id, []).append(
            {"ingredient_id": ri.ingredient_id, "quantity_g": ri.quantity_g}
        )

    return recipe_ingredients_by_recipe, base_weight_by_id, cost_level_by_id


def _get_ingredient_lookup_tables(
    db: Session, ingredient_ids: List[int]
) -> Tuple[Dict[int, Dict[str, Any]], Dict[int, Dict[str, Any]]]:
    """回傳 (ingredient_info_by_id, stock_by_ingredient_id)"""
    if not ingredient_ids:
        return {}, {}

    ids = set(ingredient_ids)
    ingredients = db.query(IngredientLibrary).filter(IngredientLibrary.id.in_(ids)).all()
    ingredient_info_by_id = {
        i.id: {
            "ingredient_name": i.ingredient_name,
            "category": i.category,
            "unit": i.unit or "g",
            "needs_stock_tracking": bool(i.needs_stock_tracking),
            "preferred_purchase_location": i.preferred_purchase_location,
        }
        for i in ingredients
    }

    stocks = db.query(IngredientStock).filter(IngredientStock.ingredient_id.in_(ids)).all()
    stock_by_ingredient_id = {
        s.ingredient_id: {"current_quantity_g": s.current_quantity_g, "min_threshold_g": s.min_threshold_g}
        for s in stocks
    }

    return ingredient_info_by_id, stock_by_ingredient_id


def _get_location_preferences(db: Session, ingredient_ids: List[int]) -> Dict[int, List[Dict[str, Any]]]:
    if not ingredient_ids:
        return {}
    rows = (
        db.query(IngredientLocationPreference)
        .filter(IngredientLocationPreference.ingredient_id.in_(set(ingredient_ids)))
        .all()
    )
    result: Dict[int, List[Dict[str, Any]]] = {}
    for row in rows:
        result.setdefault(row.ingredient_id, []).append(
            {"priority": row.priority, "preferred_location_id": row.preferred_location_id}
        )
    return result


def _get_location_id_by_name(db: Session) -> Dict[str, int]:
    rows = db.query(PurchaseLocation.id, PurchaseLocation.location_name).all()
    return {name: loc_id for loc_id, name in rows}


# ==================== 購物清單：生成 ====================

def generate_shopping_list_for_plan(
    db: Session, plan_id: int, list_date: Optional[date] = None
) -> int:
    """
    從一個週計畫（weekly_meal_plan + daily_meal_detail）生成購物清單，回傳 shopping_list_id。

    合併/成本/地點/補貨判斷全部交給 BLOCK_6_shopping_service 的純函式；
    這裡只負責把 ORM 查詢結果整理成純函式要的格式，再把結果寫回資料庫。
    """
    plan = db.query(WeeklyMealPlan).filter(WeeklyMealPlan.id == plan_id).first()
    if plan is None:
        raise NotFoundError(f"週計畫 {plan_id} 不存在")

    meal_rows = _get_meal_rows_for_plan(db, plan_id)
    if not meal_rows:
        raise ConflictError(f"週計畫 {plan_id} 沒有任何餐次，無法生成購物清單")

    recipe_ids = [m["recipe_id"] for m in meal_rows]
    recipe_ingredients_by_recipe, base_weight_by_id, cost_level_by_id = _get_recipe_lookup_tables(db, recipe_ids)

    aggregated = shopping_service.aggregate_ingredient_quantities(
        meal_rows, recipe_ingredients_by_recipe, base_weight_by_id
    )

    ingredient_ids = list(aggregated.keys())
    ingredient_info_by_id, stock_by_ingredient_id = _get_ingredient_lookup_tables(db, ingredient_ids)
    location_preferences_by_ingredient = _get_location_preferences(db, ingredient_ids)
    location_id_by_name = _get_location_id_by_name(db)

    items_data = shopping_service.build_shopping_list_items(
        aggregated=aggregated,
        recipe_cost_level_by_id=cost_level_by_id,
        ingredient_info_by_id=ingredient_info_by_id,
        location_preferences_by_ingredient=location_preferences_by_ingredient,
        location_id_by_name=location_id_by_name,
        stock_by_ingredient_id=stock_by_ingredient_id,
    )

    shopping_list = ShoppingList(
        list_date=list_date or date.today(),
        week_start_date=plan.plan_date,
        created_from_plan_id=plan_id,
        status="草稿",
        total_items=len(items_data),
    )
    db.add(shopping_list)
    db.flush()  # 取得 shopping_list.id

    for item in items_data:
        db.add(ShoppingListItem(shopping_list_id=shopping_list.id, **item))

    db.commit()
    db.refresh(shopping_list)
    logger.info(
        "購物清單已生成：shopping_list_id=%s，來自 plan_id=%s，共 %d 項食材",
        shopping_list.id, plan_id, len(items_data),
    )
    return shopping_list.id


def confirm_plan_and_generate_list(
    db: Session, plan_id: int, list_date: Optional[date] = None
) -> Tuple[int, int]:
    """
    確認週推薦：狀態改為「已確認」並生成購物清單。
    若該 plan 先前已生成過購物清單（重複確認），直接回傳既有的 shopping_list_id，不重複產生。

    回傳 (plan_id, shopping_list_id)
    """
    plan = db.query(WeeklyMealPlan).filter(WeeklyMealPlan.id == plan_id).first()
    if plan is None:
        raise NotFoundError(f"週計畫 {plan_id} 不存在")

    existing = (
        db.query(ShoppingList)
        .filter(ShoppingList.created_from_plan_id == plan_id)
        .order_by(ShoppingList.id.desc())
        .first()
    )
    if existing is not None:
        plan.plan_status = "已確認"
        db.commit()
        logger.info("週計畫 %s 已確認過，沿用既有購物清單 shopping_list_id=%s", plan_id, existing.id)
        return plan_id, existing.id

    plan.plan_status = "已確認"
    db.commit()

    shopping_list_id = generate_shopping_list_for_plan(db, plan_id, list_date)
    return plan_id, shopping_list_id


# ==================== 購物清單：讀取 ====================

def get_shopping_list_detail(db: Session, shopping_list_id: int) -> Optional[Dict[str, Any]]:
    """組出可以直接餵給 ShoppingListResponse(**result) 的字典；查無資料回傳 None。"""
    shopping_list = db.query(ShoppingList).filter(ShoppingList.id == shopping_list_id).first()
    if shopping_list is None:
        return None

    items = (
        db.query(ShoppingListItem)
        .filter(ShoppingListItem.shopping_list_id == shopping_list_id)
        .all()
    )

    ingredient_ids = [i.ingredient_id for i in items]
    ingredient_info_by_id, _ = _get_ingredient_lookup_tables(db, ingredient_ids)

    location_ids = [i.purchase_location_id for i in items if i.purchase_location_id is not None]
    locations = db.query(PurchaseLocation).filter(PurchaseLocation.id.in_(set(location_ids))).all() if location_ids else []
    location_name_by_id = {loc.id: loc.location_name for loc in locations}

    # 按「購買地點 -> 食材分類」分組
    grouped: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    for item in items:
        info = ingredient_info_by_id.get(item.ingredient_id, {})
        location_name = location_name_by_id.get(item.purchase_location_id, "未指定地點")
        category = info.get("category") or "其他"

        item_dict = {
            "id": item.id,
            "ingredient_id": item.ingredient_id,
            "ingredient_name": info.get("ingredient_name", f"食材 {item.ingredient_id}"),
            "quantity_needed_g": item.quantity_needed_g,
            "unit": item.unit or "g",
            "purchase_location_id": item.purchase_location_id,
            "cost_level": item.cost_level,
            "needs_restocking": bool(item.needs_restocking),
            "assigned_user_id": item.assigned_user_id,
            "notes": item.notes,
            "is_purchased": bool(item.is_purchased),
            "purchased_at": item.purchased_at,
        }

        grouped.setdefault(location_name, {}).setdefault(category, []).append(item_dict)

    items_by_location = {
        location_name: [
            {"category": category, "items": category_items}
            for category, category_items in categories.items()
        ]
        for location_name, categories in grouped.items()
    }

    return {
        "list_id": shopping_list.id,
        "status": shopping_list.status,
        "list_date": shopping_list.list_date,
        "week_start_date": shopping_list.week_start_date,
        "created_from_plan_id": shopping_list.created_from_plan_id,
        "total_items": shopping_list.total_items,
        "items_by_location": items_by_location,
        "notes": shopping_list.notes,
        "created_at": shopping_list.created_at,
        "updated_at": shopping_list.updated_at,
    }


def get_ingredient_name(db: Session, ingredient_id: int) -> str:
    ingredient = db.query(IngredientLibrary).filter(IngredientLibrary.id == ingredient_id).first()
    return ingredient.ingredient_name if ingredient else f"食材 {ingredient_id}"


# ==================== 購物清單：項目管理（表 6d） ====================

def _touch_shopping_list(db: Session, shopping_list_id: int) -> None:
    shopping_list = db.query(ShoppingList).filter(ShoppingList.id == shopping_list_id).first()
    if shopping_list is not None:
        shopping_list.total_items = (
            db.query(ShoppingListItem).filter(ShoppingListItem.shopping_list_id == shopping_list_id).count()
        )
        shopping_list.updated_at = datetime.utcnow()
        db.commit()


def add_shopping_list_item(db: Session, shopping_list_id: int, item_data: Dict[str, Any]) -> ShoppingListItem:
    shopping_list = db.query(ShoppingList).filter(ShoppingList.id == shopping_list_id).first()
    if shopping_list is None:
        raise NotFoundError(f"購物清單 {shopping_list_id} 不存在")

    item = ShoppingListItem(shopping_list_id=shopping_list_id, **item_data)
    db.add(item)
    db.commit()
    db.refresh(item)
    _touch_shopping_list(db, shopping_list_id)
    return item


def update_shopping_list_item(
    db: Session, shopping_list_id: int, item_id: int, updates: Dict[str, Any]
) -> ShoppingListItem:
    item = (
        db.query(ShoppingListItem)
        .filter(ShoppingListItem.shopping_list_id == shopping_list_id, ShoppingListItem.id == item_id)
        .first()
    )
    if item is None:
        raise NotFoundError(f"購物項目 {item_id}（清單 {shopping_list_id}）不存在")

    for field, value in updates.items():
        if value is not None:
            setattr(item, field, value)

    db.commit()
    db.refresh(item)
    _touch_shopping_list(db, shopping_list_id)
    return item


def delete_shopping_list_item(db: Session, shopping_list_id: int, item_id: int) -> None:
    item = (
        db.query(ShoppingListItem)
        .filter(ShoppingListItem.shopping_list_id == shopping_list_id, ShoppingListItem.id == item_id)
        .first()
    )
    if item is None:
        raise NotFoundError(f"購物項目 {item_id}（清單 {shopping_list_id}）不存在")

    db.delete(item)
    db.commit()
    _touch_shopping_list(db, shopping_list_id)


def mark_item_purchased(
    db: Session, shopping_list_id: int, item_id: int, is_purchased: bool
) -> ShoppingListItem:
    item = (
        db.query(ShoppingListItem)
        .filter(ShoppingListItem.shopping_list_id == shopping_list_id, ShoppingListItem.id == item_id)
        .first()
    )
    if item is None:
        raise NotFoundError(f"購物項目 {item_id}（清單 {shopping_list_id}）不存在")

    item.is_purchased = is_purchased
    item.purchased_at = datetime.utcnow() if is_purchased else None
    db.commit()
    db.refresh(item)
    return item


# ==================== 購物清單：狀態變更與歸檔（表 6e） ====================

VALID_STATUS_VALUES = {"草稿", "已確認", "採購中", "已採購", "歸檔"}


def update_shopping_list_status(db: Session, shopping_list_id: int, new_status: str) -> ShoppingList:
    if new_status not in VALID_STATUS_VALUES:
        raise ValueError(f"不合法的狀態：{new_status}")

    shopping_list = db.query(ShoppingList).filter(ShoppingList.id == shopping_list_id).first()
    if shopping_list is None:
        raise NotFoundError(f"購物清單 {shopping_list_id} 不存在")

    old_status = shopping_list.status
    shopping_list.status = new_status
    shopping_list.updated_at = datetime.utcnow()

    if new_status == "歸檔":
        items = (
            db.query(ShoppingListItem)
            .filter(ShoppingListItem.shopping_list_id == shopping_list_id)
            .all()
        )
        snapshot = [
            {
                "ingredient_id": i.ingredient_id,
                "quantity_needed_g": i.quantity_needed_g,
                "is_purchased": i.is_purchased,
                "purchased_at": i.purchased_at.isoformat() if i.purchased_at else None,
            }
            for i in items
        ]
        db.add(ShoppingListHistory(
            shopping_list_id=shopping_list_id,
            original_item_id=None,
            item_changes=json.dumps(snapshot, ensure_ascii=False),
            status_log=json.dumps({"from": old_status, "to": new_status, "at": datetime.utcnow().isoformat()}, ensure_ascii=False),
            archived_at=datetime.utcnow(),
        ))

    db.commit()
    db.refresh(shopping_list)
    return shopping_list


def get_shopping_list_history(db: Session, page: int = 1, limit: int = 10) -> Tuple[List[ShoppingListHistory], int]:
    total = db.query(ShoppingListHistory).count()
    rows = (
        db.query(ShoppingListHistory)
        .order_by(ShoppingListHistory.archived_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return rows, total


# ==================== 購買地點（表 6a） ====================

def list_purchase_locations(db: Session, active_only: bool = True) -> List[PurchaseLocation]:
    query = db.query(PurchaseLocation)
    if active_only:
        query = query.filter(PurchaseLocation.is_active.is_(True))
    return query.order_by(PurchaseLocation.priority_order).all()


def create_purchase_location(db: Session, data: Dict[str, Any]) -> PurchaseLocation:
    location = PurchaseLocation(**data)
    db.add(location)
    db.commit()
    db.refresh(location)
    return location


def update_purchase_location(db: Session, location_id: int, updates: Dict[str, Any]) -> PurchaseLocation:
    location = db.query(PurchaseLocation).filter(PurchaseLocation.id == location_id).first()
    if location is None:
        raise NotFoundError(f"購買地點 {location_id} 不存在")

    for field, value in updates.items():
        if value is not None:
            setattr(location, field, value)

    db.commit()
    db.refresh(location)
    return location


def delete_purchase_location(db: Session, location_id: int) -> None:
    location = db.query(PurchaseLocation).filter(PurchaseLocation.id == location_id).first()
    if location is None:
        raise NotFoundError(f"購買地點 {location_id} 不存在")
    db.delete(location)
    db.commit()


# ==================== 食材地點偏好（表 6b） ====================

def get_ingredient_location_preferences(db: Session, ingredient_id: int) -> List[Dict[str, Any]]:
    rows = (
        db.query(IngredientLocationPreference)
        .filter(IngredientLocationPreference.ingredient_id == ingredient_id)
        .order_by(IngredientLocationPreference.priority)
        .all()
    )
    location_names = _get_location_id_by_name(db)
    name_by_id = {v: k for k, v in location_names.items()}
    return [
        {
            "id": r.id,
            "ingredient_id": r.ingredient_id,
            "preferred_location_id": r.preferred_location_id,
            "location_name": name_by_id.get(r.preferred_location_id, ""),
            "priority": r.priority,
            "notes": r.notes,
        }
        for r in rows
    ]


def set_ingredient_location_preferences(
    db: Session, ingredient_id: int, preferences: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """整批覆蓋某食材的地點偏好（先刪舊的再新增，避免 priority 衝突)。"""
    ingredient = db.query(IngredientLibrary).filter(IngredientLibrary.id == ingredient_id).first()
    if ingredient is None:
        raise NotFoundError(f"食材 {ingredient_id} 不存在")

    db.query(IngredientLocationPreference).filter(
        IngredientLocationPreference.ingredient_id == ingredient_id
    ).delete()

    for pref in preferences:
        db.add(IngredientLocationPreference(
            ingredient_id=ingredient_id,
            preferred_location_id=pref["preferred_location_id"],
            priority=pref["priority"],
            notes=pref.get("notes"),
        ))

    db.commit()
    return get_ingredient_location_preferences(db, ingredient_id)
