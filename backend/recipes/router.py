from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
from recipes.models import IngredientLibrary, Recipe
from recipes.schemas import (
    IngredientCreate, IngredientUpdate, IngredientStockUpdate, IngredientResponse, IngredientStockResponse,
    RecipeCreate, RecipeUpdate, RecipeStepCreate, RecipeResponse,
)
from recipes.services import ingredient_service, recipe_service

router = APIRouter(tags=["recipes"])


@router.post("/ingredients", response_model=IngredientResponse, status_code=201)
def create_ingredient(payload: IngredientCreate, db: Session = Depends(get_db)):
    existing = db.query(IngredientLibrary).filter(IngredientLibrary.ingredient_name == payload.ingredient_name).first()
    if existing:
        raise HTTPException(status_code=400, detail="食材名稱已存在")
    return ingredient_service.create_ingredient(db, payload)


@router.get("/ingredients/search")
def search_ingredients(query: str = "", category: Optional[str] = None, db: Session = Depends(get_db)):
    return ingredient_service.search_ingredients(db, query, category=category)


@router.get("/ingredients/low-stock")
def low_stock_ingredients(db: Session = Depends(get_db)):
    return ingredient_service.get_low_stock_ingredients(db)


@router.get("/ingredients")
def list_ingredients(category: Optional[str] = None, page: int = 1, limit: int = 20, db: Session = Depends(get_db)):
    items, total = ingredient_service.list_ingredients(db, category=category, skip=(page - 1) * limit, limit=limit)
    return {"items": [IngredientResponse.model_validate(i) for i in items], "total": total, "page": page}


@router.get("/ingredients/{ingredient_id}", response_model=IngredientResponse)
def get_ingredient(ingredient_id: int, db: Session = Depends(get_db)):
    item = ingredient_service.get_ingredient(db, ingredient_id)
    if not item:
        raise HTTPException(status_code=404, detail="食材不存在")
    return item


@router.put("/ingredients/{ingredient_id}", response_model=IngredientResponse)
def update_ingredient(ingredient_id: int, payload: IngredientUpdate, db: Session = Depends(get_db)):
    item = ingredient_service.update_ingredient(db, ingredient_id, payload)
    if not item:
        raise HTTPException(status_code=404, detail="食材不存在")
    return item


@router.get("/ingredients/{ingredient_id}/stock", response_model=IngredientStockResponse)
def get_ingredient_stock(ingredient_id: int, db: Session = Depends(get_db)):
    stock = ingredient_service.get_stock(db, ingredient_id)
    if not stock:
        raise HTTPException(status_code=400, detail="這個食材沒有啟用庫存追蹤")
    return stock


@router.put("/ingredients/{ingredient_id}/stock", response_model=IngredientStockResponse)
def update_ingredient_stock(ingredient_id: int, payload: IngredientStockUpdate, db: Session = Depends(get_db)):
    stock = ingredient_service.update_stock(db, ingredient_id, payload)
    if not stock:
        raise HTTPException(status_code=404, detail="這個食材沒有啟用庫存追蹤")
    return stock


@router.post("/recipes", response_model=RecipeResponse, status_code=201)
def create_recipe(payload: RecipeCreate, db: Session = Depends(get_db)):
    existing = db.query(Recipe).filter(Recipe.recipe_name == payload.recipe_name).first()
    if existing:
        raise HTTPException(status_code=400, detail="食譜名稱已存在")
    return recipe_service.create_recipe(db, payload)


@router.get("/recipes/search")
def search_recipes(query: str = "", search_by: str = "name", category: Optional[str] = None,
                    exclude_allergen_ids: Optional[str] = None, db: Session = Depends(get_db)):
    ids = [int(i) for i in exclude_allergen_ids.split(",")] if exclude_allergen_ids else None
    results = recipe_service.search_recipes(db, query, search_by=search_by, category=category, exclude_allergen_ids=ids)
    return [RecipeResponse.model_validate(r) for r in results]


@router.get("/recipes")
def list_recipes(category: Optional[str] = None, cost_level: Optional[str] = None, page: int = 1, limit: int = 20,
                  db: Session = Depends(get_db)):
    items, total = recipe_service.list_recipes(db, category=category, cost_level=cost_level, skip=(page - 1) * limit, limit=limit)
    return {"items": [RecipeResponse.model_validate(i) for i in items], "total": total, "page": page}


@router.get("/recipes/{recipe_id}", response_model=RecipeResponse)
def get_recipe(recipe_id: int, db: Session = Depends(get_db)):
    recipe = recipe_service.get_recipe(db, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="食譜不存在")
    return recipe


@router.put("/recipes/{recipe_id}", response_model=RecipeResponse)
def update_recipe(recipe_id: int, payload: RecipeUpdate, db: Session = Depends(get_db)):
    recipe = recipe_service.update_recipe(db, recipe_id, payload)
    if not recipe:
        raise HTTPException(status_code=404, detail="食譜不存在")
    return recipe


@router.delete("/recipes/{recipe_id}", status_code=204)
def delete_recipe(recipe_id: int, db: Session = Depends(get_db)):
    success = recipe_service.soft_delete_recipe(db, recipe_id)
    if not success:
        raise HTTPException(status_code=404, detail="食譜不存在")
    return None


@router.get("/recipes/{recipe_id}/steps")
def get_recipe_steps(recipe_id: int, version: Optional[int] = None, db: Session = Depends(get_db)):
    if not recipe_service.get_recipe(db, recipe_id):
        raise HTTPException(status_code=404, detail="食譜不存在")
    steps = recipe_service.get_recipe_steps(db, recipe_id, version=version)
    return {"recipe_id": recipe_id, "steps": [{"step_number": s.step_number, "description": s.step_description} for s in steps],
            "version": steps[0].version if steps else None}


@router.post("/recipes/{recipe_id}/steps", status_code=201)
def add_recipe_steps(recipe_id: int, steps: List[RecipeStepCreate], db: Session = Depends(get_db)):
    if not recipe_service.get_recipe(db, recipe_id):
        raise HTTPException(status_code=404, detail="食譜不存在")
    new_version = recipe_service.add_recipe_steps_version(db, recipe_id, [s.model_dump() for s in steps])
    return {"success": True, "recipe_id": recipe_id, "new_version": new_version}


@router.put("/recipes/{recipe_id}/steps/{version}/set-current")
def set_recipe_steps_current(recipe_id: int, version: int, db: Session = Depends(get_db)):
    success = recipe_service.set_recipe_steps_as_current(db, recipe_id, version)
    if not success:
        raise HTTPException(status_code=404, detail="找不到這個版本")
    return {"success": True, "recipe_id": recipe_id, "current_version": version}


@router.get("/recipes/{recipe_id}/nutrition")
def get_recipe_nutrition(recipe_id: int, db: Session = Depends(get_db)):
    recipe = recipe_service.get_recipe(db, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="食譜不存在")
    return recipe.nutrition


@router.post("/recipes/{recipe_id}/calculate-nutrition")
def recalc_recipe_nutrition(recipe_id: int, db: Session = Depends(get_db)):
    result = recipe_service.calculate_nutrition(db, recipe_id)
    if result is None:
        raise HTTPException(status_code=404, detail="食譜不存在")
    return result
