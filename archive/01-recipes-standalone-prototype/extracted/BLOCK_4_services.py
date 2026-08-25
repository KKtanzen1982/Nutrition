"""
BLOCK_4: 食譜和食材管理 - 業務邏輯層
=====================================

包含：
- 營養素自動計算邏輯
- 食譜和食材搜尋、篩選
- 低庫存警告
- 版本控制邏輯
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import List, Optional, Tuple, Dict
from datetime import datetime

from BLOCK_4_models import (
    Recipe, RecipeIngredient, RecipeStep, RecipeNutrition,
    IngredientLibrary, IngredientStock, PurchaseLocation,
    IngredientLocationPreference
)
from BLOCK_4_schemas import (
    RecipeCreate, RecipeUpdate, RecipeIngredientCreate, RecipeStepCreate,
    IngredientLibraryCreate, IngredientLibraryUpdate, IngredientStockCreate, IngredientStockUpdate,
    LowStockIngredient, NutritionCalculationResult
)


# ============================================================
# 食材服務
# ============================================================

class IngredientService:
    """食材管理業務邏輯"""

    @staticmethod
    def create_ingredient(db: Session, ingredient_data: IngredientLibraryCreate) -> IngredientLibrary:
        """
        建立食材
        - 同時建立庫存記錄（如果需要追蹤）
        """
        db_ingredient = IngredientLibrary(**ingredient_data.dict())
        db.add(db_ingredient)
        db.flush()  # 獲取 ID

        # 如果需要追蹤庫存，自動建立庫存記錄
        if ingredient_data.needs_stock_tracking:
            db_stock = IngredientStock(ingredient_id=db_ingredient.id)
            db.add(db_stock)

        db.commit()
        db.refresh(db_ingredient)
        return db_ingredient

    @staticmethod
    def get_ingredient(db: Session, ingredient_id: int) -> Optional[IngredientLibrary]:
        """取得單一食材"""
        return db.query(IngredientLibrary).filter(
            IngredientLibrary.id == ingredient_id
        ).first()

    @staticmethod
    def update_ingredient(
        db: Session,
        ingredient_id: int,
        ingredient_data: IngredientLibraryUpdate
    ) -> Optional[IngredientLibrary]:
        """
        更新食材
        - 如果更新營養素資訊，觸發所有相關食譜的營養素重新計算
        """
        db_ingredient = IngredientService.get_ingredient(db, ingredient_id)
        if not db_ingredient:
            return None

        update_data = ingredient_data.dict(exclude_unset=True)

        # 標記是否有營養素更新
        nutrition_updated = any(
            key in update_data
            for key in ["calories_per_100g", "protein_per_100g", "carbs_per_100g", "fat_per_100g", "fiber_per_100g"]
        )

        # 更新食材基本資訊
        for key, value in update_data.items():
            if key != "needs_stock_tracking":
                setattr(db_ingredient, key, value)

        # 處理庫存追蹤的啟用/停用
        if "needs_stock_tracking" in update_data:
            if update_data["needs_stock_tracking"] and not db_ingredient.stock:
                # 啟用庫存追蹤
                db_stock = IngredientStock(ingredient_id=ingredient_id)
                db.add(db_stock)
            elif not update_data["needs_stock_tracking"] and db_ingredient.stock:
                # 停用庫存追蹤
                db.delete(db_ingredient.stock)

        db.commit()
        db.refresh(db_ingredient)

        # 如果營養素更新，重新計算所有相關食譜的營養素
        if nutrition_updated:
            RecipeService.recalculate_recipes_using_ingredient(db, ingredient_id)

        return db_ingredient

    @staticmethod
    def list_ingredients(
        db: Session,
        category: Optional[str] = None,
        page: int = 1,
        limit: int = 20
    ) -> Tuple[List[IngredientLibrary], int]:
        """
        列表查詢食材
        - 可按分類篩選
        - 支援分頁
        """
        query = db.query(IngredientLibrary)

        if category:
            query = query.filter(IngredientLibrary.category == category)

        total = query.count()
        offset = (page - 1) * limit

        ingredients = query.offset(offset).limit(limit).all()
        return ingredients, total

    @staticmethod
    def search_ingredients(
        db: Session,
        query_text: str,
        category: Optional[str] = None,
        page: int = 1,
        limit: int = 20
    ) -> Tuple[List[IngredientLibrary], int]:
        """
        搜尋食材（按名稱模糊搜尋）
        - 可結合分類篩選
        """
        query = db.query(IngredientLibrary).filter(
            IngredientLibrary.ingredient_name.ilike(f"%{query_text}%")
        )

        if category:
            query = query.filter(IngredientLibrary.category == category)

        total = query.count()
        offset = (page - 1) * limit

        ingredients = query.offset(offset).limit(limit).all()
        return ingredients, total

    @staticmethod
    def get_low_stock_ingredients(db: Session) -> List[LowStockIngredient]:
        """
        取得所有低庫存食材
        - 當前庫存 <= 最小閾值
        - 只返回啟用庫存追蹤的食材
        """
        low_stock_query = db.query(
            IngredientLibrary.id,
            IngredientLibrary.ingredient_name,
            IngredientLibrary.category,
            IngredientLibrary.unit,
            IngredientStock.current_quantity_g,
            IngredientStock.min_threshold_g,
            IngredientStock.last_purchased_at,
            (IngredientStock.min_threshold_g - IngredientStock.current_quantity_g).label("deficit_g")
        ).join(
            IngredientStock, IngredientLibrary.id == IngredientStock.ingredient_id
        ).filter(
            IngredientStock.current_quantity_g <= IngredientStock.min_threshold_g
        ).all()

        return [
            LowStockIngredient(
                ingredient_id=item[0],
                ingredient_name=item[1],
                category=item[2],
                current_quantity_g=item[4],
                min_threshold_g=item[5],
                unit=item[3],
                last_purchased_at=item[6],
                deficit_g=item[7] if item[7] else 0
            )
            for item in low_stock_query
        ]

    @staticmethod
    def update_stock(
        db: Session,
        ingredient_id: int,
        stock_data: IngredientStockUpdate
    ) -> Optional[IngredientStock]:
        """更新食材庫存"""
        db_stock = db.query(IngredientStock).filter(
            IngredientStock.ingredient_id == ingredient_id
        ).first()

        if not db_stock:
            return None

        update_data = stock_data.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_stock, key, value)

        db.commit()
        db.refresh(db_stock)
        return db_stock


# ============================================================
# 食譜服務
# ============================================================

class RecipeService:
    """食譜管理業務邏輯"""

    @staticmethod
    def create_recipe(db: Session, recipe_data: RecipeCreate) -> Recipe:
        """
        建立食譜
        1. 建立食譜記錄
        2. 新增食材清單
        3. 新增製作步驟（版本 1）
        4. 計算營養素
        """
        # 建立食譜
        db_recipe = Recipe(
            recipe_name=recipe_data.recipe_name,
            category=recipe_data.category,
            base_weight_g=recipe_data.base_weight_g,
            cost_level=recipe_data.cost_level
        )
        db.add(db_recipe)
        db.flush()

        # 新增食材
        for ingredient_data in recipe_data.ingredients:
            db_recipe_ingredient = RecipeIngredient(
                recipe_id=db_recipe.id,
                **ingredient_data.dict()
            )
            db.add(db_recipe_ingredient)

        # 新增步驟（版本 1）
        for step_data in recipe_data.steps:
            db_step = RecipeStep(
                recipe_id=db_recipe.id,
                version=1,
                step_number=step_data.step_number,
                step_description=step_data.step_description,
                is_current=True  # 版本 1 的所有步驟都屬於當前版本
            )
            db.add(db_step)

        db.commit()
        db.refresh(db_recipe)

        # 計算營養素
        RecipeService.calculate_nutrition(db, db_recipe.id)

        return db_recipe

    @staticmethod
    def get_recipe(db: Session, recipe_id: int, include_inactive: bool = False) -> Optional[Recipe]:
        """取得單一食譜"""
        query = db.query(Recipe).filter(Recipe.id == recipe_id)
        if not include_inactive:
            query = query.filter(Recipe.is_active == True)
        return query.first()

    @staticmethod
    def update_recipe(
        db: Session,
        recipe_id: int,
        recipe_data: RecipeUpdate
    ) -> Optional[Recipe]:
        """更新食譜基本資訊（不包含食材和步驟）"""
        db_recipe = RecipeService.get_recipe(db, recipe_id, include_inactive=True)
        if not db_recipe:
            return None

        update_data = recipe_data.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_recipe, key, value)

        db.commit()
        db.refresh(db_recipe)
        return db_recipe

    @staticmethod
    def soft_delete_recipe(db: Session, recipe_id: int) -> Optional[Recipe]:
        """軟刪除食譜"""
        db_recipe = RecipeService.get_recipe(db, recipe_id, include_inactive=True)
        if not db_recipe:
            return None

        db_recipe.is_active = False
        db.commit()
        db.refresh(db_recipe)
        return db_recipe

    @staticmethod
    def list_recipes(
        db: Session,
        category: Optional[str] = None,
        cost_level: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
        include_inactive: bool = False
    ) -> Tuple[List[Recipe], int]:
        """
        列表查詢食譜
        - 可按分類和成本篩選
        - 預設隱藏停用食譜
        """
        query = db.query(Recipe)

        if not include_inactive:
            query = query.filter(Recipe.is_active == True)

        if category:
            query = query.filter(Recipe.category == category)

        if cost_level:
            query = query.filter(Recipe.cost_level == cost_level)

        total = query.count()
        offset = (page - 1) * limit

        recipes = query.offset(offset).limit(limit).all()
        return recipes, total

    @staticmethod
    def search_recipes(
        db: Session,
        query_text: str,
        search_by: str = "name",  # 'name', 'ingredient', 'category'
        category: Optional[str] = None,
        cost_level: Optional[str] = None,
        exclude_allergen_ids: Optional[List[int]] = None
    ) -> List[Recipe]:
        """
        搜尋食譜
        - search_by: 'name' (按食譜名)、'ingredient' (按食材)、'category' (按分類)
        - 支援過敏原篩選
        """
        if search_by == "name":
            query = db.query(Recipe).filter(
                Recipe.recipe_name.ilike(f"%{query_text}%"),
                Recipe.is_active == True
            )
        elif search_by == "ingredient":
            # 按食材搜尋
            query = db.query(Recipe).join(
                RecipeIngredient, Recipe.id == RecipeIngredient.recipe_id
            ).join(
                IngredientLibrary, RecipeIngredient.ingredient_id == IngredientLibrary.id
            ).filter(
                IngredientLibrary.ingredient_name.ilike(f"%{query_text}%"),
                Recipe.is_active == True
            ).distinct()
        elif search_by == "category":
            query = db.query(Recipe).filter(
                Recipe.category.ilike(f"%{query_text}%"),
                Recipe.is_active == True
            )
        else:
            return []

        # 進一步篩選
        if category:
            query = query.filter(Recipe.category == category)

        if cost_level:
            query = query.filter(Recipe.cost_level == cost_level)

        # 過敏原篩選：排除包含特定食材的食譜
        if exclude_allergen_ids:
            query = query.filter(
                ~Recipe.id.in_(
                    db.query(Recipe.id).join(
                        RecipeIngredient, Recipe.id == RecipeIngredient.recipe_id
                    ).filter(
                        RecipeIngredient.ingredient_id.in_(exclude_allergen_ids)
                    )
                )
            )

        return query.all()

    @staticmethod
    def calculate_nutrition(db: Session, recipe_id: int) -> Optional[RecipeNutrition]:
        """
        計算食譜營養素（自動計算）
        邏輯：
        1. 查詢食譜的所有食材
        2. 根據每種食材的 quantity_g 和營養素/100g 計算
        3. 加總得出食譜總營養素
        4. 存入或更新 recipe_nutrition 表
        """
        db_recipe = RecipeService.get_recipe(db, recipe_id, include_inactive=True)
        if not db_recipe:
            return None

        # 查詢所有食材及其營養素
        recipe_ingredients = db.query(RecipeIngredient).filter(
            RecipeIngredient.recipe_id == recipe_id
        ).all()

        total_calories = 0.0
        total_protein = 0.0
        total_carbs = 0.0
        total_fat = 0.0
        total_fiber = 0.0

        for ri in recipe_ingredients:
            ingredient = ri.ingredient
            if not ingredient:
                continue

            # 計算該食材的營養素貢獻
            quantity_kg = ri.quantity_g / 100.0  # 轉換為 100g 的倍數

            if ingredient.calories_per_100g:
                total_calories += ingredient.calories_per_100g * quantity_kg
            if ingredient.protein_per_100g:
                total_protein += ingredient.protein_per_100g * quantity_kg
            if ingredient.carbs_per_100g:
                total_carbs += ingredient.carbs_per_100g * quantity_kg
            if ingredient.fat_per_100g:
                total_fat += ingredient.fat_per_100g * quantity_kg
            if ingredient.fiber_per_100g:
                total_fiber += ingredient.fiber_per_100g * quantity_kg

        # 查詢或建立 recipe_nutrition 記錄
        db_nutrition = db.query(RecipeNutrition).filter(
            RecipeNutrition.recipe_id == recipe_id
        ).first()

        if db_nutrition:
            db_nutrition.total_calories_kcal = round(total_calories, 2)
            db_nutrition.protein_g = round(total_protein, 2)
            db_nutrition.carbs_g = round(total_carbs, 2)
            db_nutrition.fat_g = round(total_fat, 2)
            db_nutrition.fiber_g = round(total_fiber, 2)
            db_nutrition.calculated_at = datetime.now()
        else:
            db_nutrition = RecipeNutrition(
                recipe_id=recipe_id,
                total_calories_kcal=round(total_calories, 2),
                protein_g=round(total_protein, 2),
                carbs_g=round(total_carbs, 2),
                fat_g=round(total_fat, 2),
                fiber_g=round(total_fiber, 2)
            )
            db.add(db_nutrition)

        db.commit()
        db.refresh(db_nutrition)
        return db_nutrition

    @staticmethod
    def recalculate_recipes_using_ingredient(db: Session, ingredient_id: int):
        """
        當食材營養素更新時，重新計算所有使用該食材的食譜
        """
        recipes_using_ingredient = db.query(Recipe).join(
            RecipeIngredient, Recipe.id == RecipeIngredient.recipe_id
        ).filter(
            RecipeIngredient.ingredient_id == ingredient_id
        ).distinct().all()

        for recipe in recipes_using_ingredient:
            RecipeService.calculate_nutrition(db, recipe.id)

    @staticmethod
    def add_recipe_steps_version(
        db: Session,
        recipe_id: int,
        steps_data: List[RecipeStepCreate]
    ) -> Optional[int]:
        """
        新增食譜步驟新版本
        邏輯：
        1. 取得現有最高版本號
        2. 新增新版本（版本號 + 1）
        3. 標記新版本為 is_current=true
        4. 舊版本標記為 is_current=false
        """
        db_recipe = RecipeService.get_recipe(db, recipe_id, include_inactive=True)
        if not db_recipe:
            return None

        # 獲取現有最高版本
        max_version = db.query(func.max(RecipeStep.version)).filter(
            RecipeStep.recipe_id == recipe_id
        ).scalar() or 0

        new_version = max_version + 1

        # 標記舊版本為 is_current=false
        db.query(RecipeStep).filter(
            RecipeStep.recipe_id == recipe_id
        ).update({"is_current": False}, synchronize_session=False)

        # 新增新版本步驟
        for step_data in steps_data:
            db_step = RecipeStep(
                recipe_id=recipe_id,
                version=new_version,
                step_number=step_data.step_number,
                step_description=step_data.step_description,
                is_current=True
            )
            db.add(db_step)

        db.commit()
        return new_version

    @staticmethod
    def get_recipe_steps(
        db: Session,
        recipe_id: int,
        version: Optional[int] = None
    ) -> List[RecipeStep]:
        """
        取得食譜步驟
        - version=None：取得最新版本（is_current=true）
        - version=N：取得特定版本
        """
        query = db.query(RecipeStep).filter(RecipeStep.recipe_id == recipe_id)

        if version is None:
            query = query.filter(RecipeStep.is_current == True)
        else:
            query = query.filter(RecipeStep.version == version)

        return query.order_by(RecipeStep.step_number).all()

    @staticmethod
    def set_recipe_steps_as_current(
        db: Session,
        recipe_id: int,
        version: int
    ) -> bool:
        """
        設定食譜步驟某個版本為當前版本
        """
        # 查詢該版本是否存在
        version_exists = db.query(RecipeStep).filter(
            RecipeStep.recipe_id == recipe_id,
            RecipeStep.version == version
        ).first()

        if not version_exists:
            return False

        # 標記所有版本為 is_current=false
        db.query(RecipeStep).filter(
            RecipeStep.recipe_id == recipe_id
        ).update({"is_current": False}, synchronize_session=False)

        # 標記目標版本為 is_current=true
        db.query(RecipeStep).filter(
            RecipeStep.recipe_id == recipe_id,
            RecipeStep.version == version
        ).update({"is_current": True}, synchronize_session=False)

        db.commit()
        return True
