from sqlalchemy.orm import Session
from datetime import date, datetime
from typing import List, Optional, Dict
import json

from recipes.models import Recipe, RecipeIngredient, IngredientLibrary, IngredientStock
from meal_plans.models import WeeklyMealPlan, DailyMealDetail
from shopping.models import PurchaseLocation, IngredientLocationPreference, ShoppingList, ShoppingListItem, ShoppingListHistory
from shopping.aggregation import aggregate_ingredient_quantities, build_shopping_list_items


class PurchaseLocationService:
    """購買地點 + 食材地點偏好服務"""

    def list_locations(self, db: Session, active_only: bool = True) -> List[PurchaseLocation]:
        q = db.query(PurchaseLocation)
        if active_only:
            q = q.filter(PurchaseLocation.is_active.is_(True))
        return q.order_by(PurchaseLocation.priority_order).all()

    def create_location(self, db: Session, data) -> PurchaseLocation:
        location = PurchaseLocation(**data.model_dump())
        db.add(location)
        db.commit()
        db.refresh(location)
        return location

    def update_location(self, db: Session, location_id: int, data) -> Optional[PurchaseLocation]:
        location = db.get(PurchaseLocation, location_id)
        if not location:
            return None
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(location, k, v)
        db.commit()
        db.refresh(location)
        return location

    def delete_location(self, db: Session, location_id: int) -> bool:
        location = db.get(PurchaseLocation, location_id)
        if not location:
            return False
        db.delete(location)
        db.commit()
        return True

    def _location_id_by_name(self, db: Session) -> Dict[str, int]:
        rows = db.query(PurchaseLocation.id, PurchaseLocation.location_name).all()
        return {name: loc_id for loc_id, name in rows}

    def get_ingredient_preferences(self, db: Session, ingredient_id: int) -> List[Dict]:
        rows = (
            db.query(IngredientLocationPreference)
            .filter(IngredientLocationPreference.ingredient_id == ingredient_id)
            .order_by(IngredientLocationPreference.priority)
            .all()
        )
        name_by_id = {v: k for k, v in self._location_id_by_name(db).items()}
        return [
            {
                "id": r.id, "ingredient_id": r.ingredient_id,
                "preferred_location_id": r.preferred_location_id,
                "location_name": name_by_id.get(r.preferred_location_id, ""),
                "priority": r.priority, "notes": r.notes,
            }
            for r in rows
        ]

    def set_ingredient_preferences(self, db: Session, ingredient_id: int, preferences: List[Dict]) -> Optional[List[Dict]]:
        ingredient = db.get(IngredientLibrary, ingredient_id)
        if not ingredient:
            return None
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
        return self.get_ingredient_preferences(db, ingredient_id)


purchase_location_service = PurchaseLocationService()


class ShoppingListService:
    """購物清單服務：合併計算重用 shopping.aggregation 的純函式"""

    def _meal_rows_for_plan(self, db: Session, plan_id: int) -> List[Dict]:
        rows = db.query(DailyMealDetail).filter(DailyMealDetail.meal_plan_id == plan_id).all()
        return [{"recipe_id": r.recipe_id, "serving_weight_g": r.serving_weight_g, "assigned_user_id": r.assigned_user_id} for r in rows]

    def _recipe_lookup_tables(self, db: Session, recipe_ids: List[int]):
        if not recipe_ids:
            return {}, {}, {}
        ids = set(recipe_ids)
        recipes = db.query(Recipe).filter(Recipe.id.in_(ids)).all()
        base_weight_by_id = {r.id: r.base_weight_g for r in recipes}
        cost_level_by_id = {r.id: r.cost_level for r in recipes}
        ri_rows = db.query(RecipeIngredient).filter(RecipeIngredient.recipe_id.in_(ids)).all()
        recipe_ingredients_by_recipe: Dict[int, List[Dict]] = {}
        for ri in ri_rows:
            recipe_ingredients_by_recipe.setdefault(ri.recipe_id, []).append(
                {"ingredient_id": ri.ingredient_id, "quantity_g": ri.quantity_g}
            )
        return recipe_ingredients_by_recipe, base_weight_by_id, cost_level_by_id

    def _ingredient_lookup_tables(self, db: Session, ingredient_ids: List[int]):
        if not ingredient_ids:
            return {}, {}
        ids = set(ingredient_ids)
        ingredients = db.query(IngredientLibrary).filter(IngredientLibrary.id.in_(ids)).all()
        ingredient_info_by_id = {
            i.id: {
                "ingredient_name": i.ingredient_name, "category": i.category, "unit": i.unit or "g",
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

    def _location_preferences(self, db: Session, ingredient_ids: List[int]) -> Dict[int, List[Dict]]:
        if not ingredient_ids:
            return {}
        rows = (
            db.query(IngredientLocationPreference)
            .filter(IngredientLocationPreference.ingredient_id.in_(set(ingredient_ids)))
            .all()
        )
        result: Dict[int, List[Dict]] = {}
        for row in rows:
            result.setdefault(row.ingredient_id, []).append(
                {"priority": row.priority, "preferred_location_id": row.preferred_location_id}
            )
        return result

    def generate_for_plan(self, db: Session, plan_id: int, list_date=None) -> int:
        plan = db.get(WeeklyMealPlan, plan_id)
        if not plan:
            raise ValueError(f"週計畫 {plan_id} 不存在")

        meal_rows = self._meal_rows_for_plan(db, plan_id)
        if not meal_rows:
            raise ValueError(f"週計畫 {plan_id} 沒有任何餐次，無法生成購物清單")

        recipe_ids = [m["recipe_id"] for m in meal_rows]
        recipe_ingredients_by_recipe, base_weight_by_id, cost_level_by_id = self._recipe_lookup_tables(db, recipe_ids)

        aggregated = aggregate_ingredient_quantities(meal_rows, recipe_ingredients_by_recipe, base_weight_by_id)

        ingredient_ids = list(aggregated.keys())
        ingredient_info_by_id, stock_by_ingredient_id = self._ingredient_lookup_tables(db, ingredient_ids)
        location_preferences_by_ingredient = self._location_preferences(db, ingredient_ids)
        location_id_by_name = purchase_location_service._location_id_by_name(db)

        items_data = build_shopping_list_items(
            aggregated=aggregated, recipe_cost_level_by_id=cost_level_by_id,
            ingredient_info_by_id=ingredient_info_by_id,
            location_preferences_by_ingredient=location_preferences_by_ingredient,
            location_id_by_name=location_id_by_name, stock_by_ingredient_id=stock_by_ingredient_id,
        )

        shopping_list = ShoppingList(
            list_date=list_date or date.today(), week_start_date=plan.plan_date,
            created_from_plan_id=plan_id, status="草稿", total_items=len(items_data),
        )
        db.add(shopping_list)
        db.flush()
        for item in items_data:
            db.add(ShoppingListItem(shopping_list_id=shopping_list.id, **item))
        db.commit()
        db.refresh(shopping_list)
        return shopping_list.id

    def confirm_plan(self, db: Session, plan_id: int, list_date=None):
        plan = db.get(WeeklyMealPlan, plan_id)
        if not plan:
            raise ValueError(f"週計畫 {plan_id} 不存在")

        existing = (
            db.query(ShoppingList)
            .filter(ShoppingList.created_from_plan_id == plan_id)
            .order_by(ShoppingList.id.desc())
            .first()
        )
        if existing is not None:
            plan.plan_status = "已確認"
            db.commit()
            return plan_id, existing.id

        plan.plan_status = "已確認"
        db.commit()
        shopping_list_id = self.generate_for_plan(db, plan_id, list_date)
        return plan_id, shopping_list_id

    def get_detail(self, db: Session, shopping_list_id: int) -> Optional[Dict]:
        shopping_list = db.get(ShoppingList, shopping_list_id)
        if not shopping_list:
            return None

        items = db.query(ShoppingListItem).filter(ShoppingListItem.shopping_list_id == shopping_list_id).all()
        ingredient_ids = [i.ingredient_id for i in items]
        ingredient_info_by_id, _ = self._ingredient_lookup_tables(db, ingredient_ids)

        location_ids = [i.purchase_location_id for i in items if i.purchase_location_id is not None]
        locations = db.query(PurchaseLocation).filter(PurchaseLocation.id.in_(set(location_ids))).all() if location_ids else []
        location_name_by_id = {loc.id: loc.location_name for loc in locations}

        grouped: Dict[str, Dict[str, List[Dict]]] = {}
        for item in items:
            info = ingredient_info_by_id.get(item.ingredient_id, {})
            location_name = location_name_by_id.get(item.purchase_location_id, "未指定地點")
            category = info.get("category") or "其他"
            item_dict = {
                "id": item.id, "ingredient_id": item.ingredient_id,
                "ingredient_name": info.get("ingredient_name", f"食材 {item.ingredient_id}"),
                "quantity_needed_g": item.quantity_needed_g, "unit": item.unit or "g",
                "purchase_location_id": item.purchase_location_id, "cost_level": item.cost_level,
                "needs_restocking": bool(item.needs_restocking), "assigned_user_id": item.assigned_user_id,
                "notes": item.notes, "is_purchased": bool(item.is_purchased), "purchased_at": item.purchased_at,
            }
            grouped.setdefault(location_name, {}).setdefault(category, []).append(item_dict)

        items_by_location = {
            location_name: [{"category": category, "items": category_items} for category, category_items in categories.items()]
            for location_name, categories in grouped.items()
        }

        return {
            "list_id": shopping_list.id, "status": shopping_list.status, "list_date": shopping_list.list_date,
            "week_start_date": shopping_list.week_start_date, "created_from_plan_id": shopping_list.created_from_plan_id,
            "total_items": shopping_list.total_items, "items_by_location": items_by_location,
            "notes": shopping_list.notes, "created_at": shopping_list.created_at, "updated_at": shopping_list.updated_at,
        }

    def get_ingredient_name(self, db: Session, ingredient_id: int) -> str:
        ingredient = db.get(IngredientLibrary, ingredient_id)
        return ingredient.ingredient_name if ingredient else f"食材 {ingredient_id}"

    def _touch(self, db: Session, shopping_list_id: int) -> None:
        shopping_list = db.get(ShoppingList, shopping_list_id)
        if shopping_list is not None:
            shopping_list.total_items = db.query(ShoppingListItem).filter(ShoppingListItem.shopping_list_id == shopping_list_id).count()
            shopping_list.updated_at = datetime.utcnow()
            db.commit()

    def add_item(self, db: Session, shopping_list_id: int, item_data: Dict) -> Optional[ShoppingListItem]:
        if not db.get(ShoppingList, shopping_list_id):
            return None
        item = ShoppingListItem(shopping_list_id=shopping_list_id, **item_data)
        db.add(item)
        db.commit()
        db.refresh(item)
        self._touch(db, shopping_list_id)
        return item

    def update_item(self, db: Session, shopping_list_id: int, item_id: int, updates: Dict) -> Optional[ShoppingListItem]:
        item = db.query(ShoppingListItem).filter(
            ShoppingListItem.shopping_list_id == shopping_list_id, ShoppingListItem.id == item_id
        ).first()
        if not item:
            return None
        for field, value in updates.items():
            if value is not None:
                setattr(item, field, value)
        db.commit()
        db.refresh(item)
        self._touch(db, shopping_list_id)
        return item

    def delete_item(self, db: Session, shopping_list_id: int, item_id: int) -> bool:
        item = db.query(ShoppingListItem).filter(
            ShoppingListItem.shopping_list_id == shopping_list_id, ShoppingListItem.id == item_id
        ).first()
        if not item:
            return False
        db.delete(item)
        db.commit()
        self._touch(db, shopping_list_id)
        return True

    def mark_purchased(self, db: Session, shopping_list_id: int, item_id: int, is_purchased: bool) -> Optional[ShoppingListItem]:
        item = db.query(ShoppingListItem).filter(
            ShoppingListItem.shopping_list_id == shopping_list_id, ShoppingListItem.id == item_id
        ).first()
        if not item:
            return None
        item.is_purchased = is_purchased
        item.purchased_at = datetime.utcnow() if is_purchased else None
        db.commit()
        db.refresh(item)
        return item

    VALID_STATUS_VALUES = {"草稿", "已確認", "採購中", "已採購", "歸檔"}

    def update_status(self, db: Session, shopping_list_id: int, new_status: str) -> Optional[ShoppingList]:
        if new_status not in self.VALID_STATUS_VALUES:
            raise ValueError(f"不合法的狀態：{new_status}")

        shopping_list = db.get(ShoppingList, shopping_list_id)
        if not shopping_list:
            return None

        old_status = shopping_list.status
        shopping_list.status = new_status
        shopping_list.updated_at = datetime.utcnow()

        if new_status == "歸檔":
            items = db.query(ShoppingListItem).filter(ShoppingListItem.shopping_list_id == shopping_list_id).all()
            snapshot = [
                {
                    "ingredient_id": i.ingredient_id, "quantity_needed_g": i.quantity_needed_g,
                    "is_purchased": i.is_purchased,
                    "purchased_at": i.purchased_at.isoformat() if i.purchased_at else None,
                }
                for i in items
            ]
            db.add(ShoppingListHistory(
                shopping_list_id=shopping_list_id, original_item_id=None,
                item_changes=json.dumps(snapshot, ensure_ascii=False),
                status_log=json.dumps({"from": old_status, "to": new_status, "at": datetime.utcnow().isoformat()}, ensure_ascii=False),
                archived_at=datetime.utcnow(),
            ))

        db.commit()
        db.refresh(shopping_list)
        return shopping_list

    def get_history(self, db: Session, page: int = 1, limit: int = 10):
        total = db.query(ShoppingListHistory).count()
        rows = (
            db.query(ShoppingListHistory)
            .order_by(ShoppingListHistory.archived_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
            .all()
        )
        return rows, total


shopping_list_service = ShoppingListService()
