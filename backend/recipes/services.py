from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional, Dict

from recipes.models import IngredientLibrary, IngredientStock, Recipe, RecipeIngredient, RecipeStep, RecipeNutrition


class IngredientService:
    """食材庫服務"""

    def create_ingredient(self, db: Session, data) -> IngredientLibrary:
        payload = data.model_dump()
        needs_tracking = payload.get("needs_stock_tracking")
        ingredient = IngredientLibrary(**payload)
        db.add(ingredient)
        db.flush()
        if needs_tracking:
            db.add(IngredientStock(ingredient_id=ingredient.id, current_quantity_g=0, min_threshold_g=0))
        db.commit()
        db.refresh(ingredient)
        return ingredient

    def get_ingredient(self, db: Session, ingredient_id: int) -> Optional[IngredientLibrary]:
        return db.get(IngredientLibrary, ingredient_id)

    def update_ingredient(self, db: Session, ingredient_id: int, data) -> Optional[IngredientLibrary]:
        ingredient = db.get(IngredientLibrary, ingredient_id)
        if not ingredient:
            return None
        update_data = data.model_dump(exclude_unset=True)
        nutrition_fields = {"calories_per_100g", "protein_per_100g", "carbs_per_100g", "fat_per_100g", "fiber_per_100g"}
        nutrition_changed = bool(nutrition_fields & set(update_data.keys()))
        needs_tracking = update_data.pop("needs_stock_tracking", None)
        for k, v in update_data.items():
            setattr(ingredient, k, v)
        if needs_tracking is not None:
            ingredient.needs_stock_tracking = needs_tracking
            existing_stock = db.query(IngredientStock).filter(IngredientStock.ingredient_id == ingredient_id).first()
            if needs_tracking and not existing_stock:
                db.add(IngredientStock(ingredient_id=ingredient_id, current_quantity_g=0, min_threshold_g=0))
            elif not needs_tracking and existing_stock:
                db.delete(existing_stock)
        db.commit()
        db.refresh(ingredient)
        if nutrition_changed:
            recipe_service.recalculate_recipes_using_ingredient(db, ingredient_id)
        return ingredient

    def list_ingredients(self, db: Session, category: Optional[str] = None, skip: int = 0, limit: int = 20):
        q = db.query(IngredientLibrary)
        if category:
            q = q.filter(IngredientLibrary.category == category)
        total = q.count()
        items = q.offset(skip).limit(limit).all()
        return items, total

    def search_ingredients(self, db: Session, query: str, category: Optional[str] = None):
        q = db.query(IngredientLibrary).filter(IngredientLibrary.ingredient_name.ilike(f"%{query}%"))
        if category:
            q = q.filter(IngredientLibrary.category == category)
        return q.all()

    def get_low_stock_ingredients(self, db: Session):
        rows = (
            db.query(IngredientLibrary, IngredientStock)
            .join(IngredientStock, IngredientStock.ingredient_id == IngredientLibrary.id)
            .filter(IngredientStock.current_quantity_g <= IngredientStock.min_threshold_g)
            .all()
        )
        return [
            {
                "ingredient_id": ing.id, "ingredient_name": ing.ingredient_name,
                "current_quantity_g": stock.current_quantity_g, "min_threshold_g": stock.min_threshold_g,
                "deficit_g": (stock.min_threshold_g or 0) - (stock.current_quantity_g or 0),
            }
            for ing, stock in rows
        ]

    def get_stock(self, db: Session, ingredient_id: int) -> Optional[IngredientStock]:
        return db.query(IngredientStock).filter(IngredientStock.ingredient_id == ingredient_id).first()

    def update_stock(self, db: Session, ingredient_id: int, data) -> Optional[IngredientStock]:
        stock = self.get_stock(db, ingredient_id)
        if not stock:
            return None
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(stock, k, v)
        db.commit()
        db.refresh(stock)
        return stock


ingredient_service = IngredientService()


class RecipeService:
    """食譜庫服務：含營養素自動計算、步驟版本控制"""

    def calculate_nutrition(self, db: Session, recipe_id: int):
        recipe = db.get(Recipe, recipe_id)
        if not recipe:
            return None
        totals = {"total_calories_kcal": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0, "fiber_g": 0.0}
        for ri in recipe.ingredients:
            ing = db.get(IngredientLibrary, ri.ingredient_id)
            if not ing:
                continue
            ratio = ri.quantity_g / 100.0
            totals["total_calories_kcal"] += (ing.calories_per_100g or 0) * ratio
            totals["protein_g"] += (ing.protein_per_100g or 0) * ratio
            totals["carbs_g"] += (ing.carbs_per_100g or 0) * ratio
            totals["fat_g"] += (ing.fat_per_100g or 0) * ratio
            totals["fiber_g"] += (ing.fiber_per_100g or 0) * ratio
        totals = {k: round(v, 2) for k, v in totals.items()}

        nutrition = db.query(RecipeNutrition).filter(RecipeNutrition.recipe_id == recipe_id).first()
        if nutrition:
            for k, v in totals.items():
                setattr(nutrition, k, v)
        else:
            nutrition = RecipeNutrition(recipe_id=recipe_id, **totals)
            db.add(nutrition)
        db.commit()
        return totals

    def recalculate_recipes_using_ingredient(self, db: Session, ingredient_id: int):
        recipe_ids = {
            ri.recipe_id for ri in
            db.query(RecipeIngredient).filter(RecipeIngredient.ingredient_id == ingredient_id).all()
        }
        for rid in recipe_ids:
            self.calculate_nutrition(db, rid)

    def create_recipe(self, db: Session, data) -> Recipe:
        payload = data.model_dump()
        ingredients = payload.pop("ingredients")
        steps = payload.pop("steps")
        recipe = Recipe(**payload)
        db.add(recipe)
        db.flush()
        for ing in ingredients:
            db.add(RecipeIngredient(recipe_id=recipe.id, **ing))
        for step in steps:
            db.add(RecipeStep(recipe_id=recipe.id, version=1, is_current=True, **step))
        db.commit()
        self.calculate_nutrition(db, recipe.id)
        db.refresh(recipe)
        return recipe

    def get_recipe(self, db: Session, recipe_id: int) -> Optional[Recipe]:
        return db.get(Recipe, recipe_id)

    def update_recipe(self, db: Session, recipe_id: int, data) -> Optional[Recipe]:
        recipe = db.get(Recipe, recipe_id)
        if not recipe:
            return None
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(recipe, k, v)
        recipe.last_updated_at = datetime.utcnow()
        db.commit()
        db.refresh(recipe)
        return recipe

    def replace_ingredients(self, db: Session, recipe_id: int, ingredients: List[Dict]) -> Optional[Recipe]:
        """整組取代食材清單（跟 add_recipe_steps 版本邏輯一致的做法，但食材沒有版本歷史，直接覆蓋）"""
        recipe = db.get(Recipe, recipe_id)
        if not recipe:
            return None
        db.query(RecipeIngredient).filter(RecipeIngredient.recipe_id == recipe_id).delete()
        for ing in ingredients:
            db.add(RecipeIngredient(recipe_id=recipe_id, **ing))
        recipe.last_updated_at = datetime.utcnow()
        db.commit()
        self.calculate_nutrition(db, recipe_id)
        db.refresh(recipe)
        return recipe

    def soft_delete_recipe(self, db: Session, recipe_id: int) -> bool:
        recipe = db.get(Recipe, recipe_id)
        if not recipe:
            return False
        recipe.is_active = False
        db.commit()
        return True

    def list_recipes(self, db: Session, category: Optional[str] = None, cost_level: Optional[str] = None,
                      skip: int = 0, limit: int = 20):
        q = db.query(Recipe).filter(Recipe.is_active == True)
        if category:
            q = q.filter(Recipe.category == category)
        if cost_level:
            q = q.filter(Recipe.cost_level == cost_level)
        total = q.count()
        items = q.offset(skip).limit(limit).all()
        return items, total

    def search_recipes(self, db: Session, query: str = "", search_by: str = "name",
                        category: Optional[str] = None, exclude_allergen_ids: Optional[List[int]] = None):
        q = db.query(Recipe).filter(Recipe.is_active == True)
        if search_by == "name" and query:
            q = q.filter(Recipe.recipe_name.ilike(f"%{query}%"))
        elif search_by == "ingredient" and query:
            q = q.join(RecipeIngredient).join(IngredientLibrary).filter(IngredientLibrary.ingredient_name.ilike(f"%{query}%"))
        elif search_by == "category" and query:
            q = q.filter(Recipe.category == query)
        if category:
            q = q.filter(Recipe.category == category)
        results = q.all()
        if exclude_allergen_ids:
            excluded = set(exclude_allergen_ids)
            results = [
                r for r in results
                if not excluded & {ri.ingredient_id for ri in r.ingredients}
            ]
        return results

    def add_recipe_steps_version(self, db: Session, recipe_id: int, steps: List[Dict]) -> int:
        new_version = (
            db.query(RecipeStep.version).filter(RecipeStep.recipe_id == recipe_id)
            .order_by(RecipeStep.version.desc()).first()
        )
        new_version = (new_version[0] + 1) if new_version else 1
        db.query(RecipeStep).filter(RecipeStep.recipe_id == recipe_id).update({"is_current": False})
        for step in steps:
            db.add(RecipeStep(recipe_id=recipe_id, version=new_version, is_current=True, **step))
        db.commit()
        return new_version

    def get_recipe_steps(self, db: Session, recipe_id: int, version: Optional[int] = None) -> List[RecipeStep]:
        q = db.query(RecipeStep).filter(RecipeStep.recipe_id == recipe_id)
        if version is not None:
            q = q.filter(RecipeStep.version == version)
        else:
            q = q.filter(RecipeStep.is_current == True)
        return q.order_by(RecipeStep.step_number).all()

    def set_recipe_steps_as_current(self, db: Session, recipe_id: int, version: int) -> bool:
        rows = db.query(RecipeStep).filter(RecipeStep.recipe_id == recipe_id, RecipeStep.version == version).all()
        if not rows:
            return False
        db.query(RecipeStep).filter(RecipeStep.recipe_id == recipe_id).update({"is_current": False})
        for r in rows:
            r.is_current = True
        db.commit()
        return True


recipe_service = RecipeService()
