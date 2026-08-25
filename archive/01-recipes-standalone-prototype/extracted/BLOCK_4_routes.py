"""
BLOCK_4: 食譜和食材管理 - FastAPI Routes
==========================================

API Endpoints:
- 食材管理：CRUD、搜尋、庫存、低庫存警告
- 食譜管理：CRUD、搜尋、步驟版本控制、營養素查詢
- 購買地點管理
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional

from BLOCK_4_models import (
    IngredientLibrary, IngredientStock, Recipe, RecipeStep,
    PurchaseLocation, IngredientLocationPreference
)
from BLOCK_4_schemas import (
    # Ingredient Schemas
    IngredientLibraryCreate, IngredientLibraryUpdate, IngredientLibraryResponse,
    IngredientStockCreate, IngredientStockUpdate, IngredientStockResponse,
    IngredientSearchResult, LowStockIngredient,
    # Recipe Schemas
    RecipeCreate, RecipeUpdate, RecipeDetailResponse, RecipeListResponse,
    RecipeSearchResponse, RecipeStepCreate, RecipeStepResponse, RecipeNutritionResponse,
    RecipeListPaginatedResponse, IngredientListPaginatedResponse,
    NutritionCalculationResult, RecipeStepsVersionResponse,
    # PurchaseLocation Schemas
    PurchaseLocationCreate, PurchaseLocationUpdate, PurchaseLocationResponse,
    IngredientLocationPreferenceCreate, IngredientLocationPreferenceResponse
)
from BLOCK_4_services import IngredientService, RecipeService

from test_db import get_db

router = APIRouter(prefix="/api", tags=["recipes-ingredients"])


# ============================================================
# 食材管理 API
# ============================================================

@router.post("/ingredients", response_model=IngredientLibraryResponse, status_code=status.HTTP_201_CREATED)
def create_ingredient(
    ingredient_data: IngredientLibraryCreate,
    db: Session = Depends(get_db)
):
    """
    建立新食材
    - 自動建立庫存記錄（如果需要追蹤庫存）
    """
    # 檢查食材名稱是否已存在
    existing = db.query(IngredientLibrary).filter(
        IngredientLibrary.ingredient_name == ingredient_data.ingredient_name
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"食材 '{ingredient_data.ingredient_name}' 已存在"
        )

    db_ingredient = IngredientService.create_ingredient(db, ingredient_data)
    return db_ingredient


@router.get("/ingredients", response_model=IngredientListPaginatedResponse)
def list_ingredients(
    category: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    列表查詢食材
    - 可按分類篩選
    - 支援分頁
    """
    ingredients, total = IngredientService.list_ingredients(db, category, page, limit)
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "items": ingredients
    }


# 注意：靜態路徑（search、low-stock）必須定義在 /ingredients/{ingredient_id} 之前，
# 否則 FastAPI 會依註冊順序優先比對到 {ingredient_id}，把 "search"／"low-stock"
# 當成 ingredient_id 解析成整數而回傳 422。
@router.get("/ingredients/search", response_model=List[IngredientSearchResult])
def search_ingredients(
    query: str = Query(..., min_length=1),
    category: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    搜尋食材
    - 按名稱模糊搜尋
    - 可結合分類篩選
    """
    ingredients, total = IngredientService.search_ingredients(db, query, category, page, limit)
    return ingredients


@router.get("/ingredients/low-stock", response_model=List[LowStockIngredient])
def get_low_stock_ingredients(
    db: Session = Depends(get_db)
):
    """
    取得所有低庫存食材
    - 返回庫存 <= 最小閾值的食材
    - 只限啟用庫存追蹤的食材
    """
    return IngredientService.get_low_stock_ingredients(db)


@router.get("/ingredients/{ingredient_id}", response_model=IngredientLibraryResponse)
def get_ingredient(
    ingredient_id: int,
    db: Session = Depends(get_db)
):
    """取得單一食材詳情"""
    db_ingredient = IngredientService.get_ingredient(db, ingredient_id)
    if not db_ingredient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="食材不存在"
        )
    return db_ingredient


@router.put("/ingredients/{ingredient_id}", response_model=IngredientLibraryResponse)
def update_ingredient(
    ingredient_id: int,
    ingredient_data: IngredientLibraryUpdate,
    db: Session = Depends(get_db)
):
    """
    更新食材
    - 如果更新營養素，會自動重新計算所有相關食譜的營養素
    """
    db_ingredient = IngredientService.update_ingredient(db, ingredient_id, ingredient_data)
    if not db_ingredient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="食材不存在"
        )
    return db_ingredient


@router.get("/ingredients/{ingredient_id}/stock", response_model=IngredientStockResponse)
def get_ingredient_stock(
    ingredient_id: int,
    db: Session = Depends(get_db)
):
    """取得食材庫存"""
    db_ingredient = IngredientService.get_ingredient(db, ingredient_id)
    if not db_ingredient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="食材不存在"
        )

    if not db_ingredient.stock:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="該食材未啟用庫存追蹤"
        )

    return db_ingredient.stock


@router.put("/ingredients/{ingredient_id}/stock", response_model=IngredientStockResponse)
def update_ingredient_stock(
    ingredient_id: int,
    stock_data: IngredientStockUpdate,
    db: Session = Depends(get_db)
):
    """更新食材庫存"""
    db_stock = IngredientService.update_stock(db, ingredient_id, stock_data)
    if not db_stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="食材庫存記錄不存在"
        )
    return db_stock


# ============================================================
# 食譜管理 API
# ============================================================

@router.post("/recipes", response_model=RecipeDetailResponse, status_code=status.HTTP_201_CREATED)
def create_recipe(
    recipe_data: RecipeCreate,
    db: Session = Depends(get_db)
):
    """
    建立新食譜
    1. 建立食譜記錄
    2. 新增食材清單
    3. 新增製作步驟（版本 1）
    4. 自動計算營養素
    """
    # 檢查食譜名稱是否已存在
    existing = db.query(Recipe).filter(
        Recipe.recipe_name == recipe_data.recipe_name
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"食譜 '{recipe_data.recipe_name}' 已存在"
        )

    if not recipe_data.ingredients:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="食譜必須至少包含一種食材"
        )

    if not recipe_data.steps:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="食譜必須至少包含一個製作步驟"
        )

    db_recipe = RecipeService.create_recipe(db, recipe_data)
    return db_recipe


@router.get("/recipes", response_model=RecipeListPaginatedResponse)
def list_recipes(
    category: Optional[str] = Query(None),
    cost_level: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    列表查詢食譜
    - 可按分類和成本篩選
    - 預設隱藏停用食譜
    - 支援分頁
    """
    recipes, total = RecipeService.list_recipes(db, category, cost_level, page, limit)
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "items": recipes
    }


# 注意：靜態路徑 /recipes/search 必須定義在 /recipes/{recipe_id} 之前，
# 否則會被 {recipe_id} 攔截，把 "search" 當成 recipe_id 解析成整數而回傳 422。
@router.get("/recipes/search", response_model=List[RecipeSearchResponse])
def search_recipes(
    query: str = Query(..., min_length=1),
    search_by: str = Query("name", regex="^(name|ingredient|category)$"),
    category: Optional[str] = Query(None),
    cost_level: Optional[str] = Query(None),
    exclude_allergen_ids: Optional[str] = Query(None),  # 逗號分隔的 ID
    db: Session = Depends(get_db)
):
    """
    搜尋食譜
    - search_by: 'name' (食譜名)、'ingredient' (食材)、'category' (分類)
    - 可篩選分類、成本
    - 可排除含有特定食材（過敏原篩選）
      - 例：exclude_allergen_ids=1,2,3
    """
    # 解析過敏原 ID
    allergen_ids = None
    if exclude_allergen_ids:
        try:
            allergen_ids = [int(x.strip()) for x in exclude_allergen_ids.split(",")]
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="過敏原 ID 必須為整數，以逗號分隔"
            )

    recipes = RecipeService.search_recipes(
        db, query, search_by, category, cost_level, allergen_ids
    )
    return recipes


@router.get("/recipes/{recipe_id}", response_model=RecipeDetailResponse)
def get_recipe(
    recipe_id: int,
    db: Session = Depends(get_db)
):
    """取得食譜詳情（含食材、步驟、營養素）"""
    db_recipe = RecipeService.get_recipe(db, recipe_id)
    if not db_recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="食譜不存在"
        )
    return db_recipe


@router.put("/recipes/{recipe_id}", response_model=RecipeDetailResponse)
def update_recipe(
    recipe_id: int,
    recipe_data: RecipeUpdate,
    db: Session = Depends(get_db)
):
    """
    更新食譜基本資訊
    - 不包含食材和步驟的修改（需分別調用步驟 API）
    """
    db_recipe = RecipeService.update_recipe(db, recipe_id, recipe_data)
    if not db_recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="食譜不存在"
        )
    return db_recipe


@router.delete("/recipes/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recipe(
    recipe_id: int,
    db: Session = Depends(get_db)
):
    """
    軟刪除食譜
    - 標記為 is_active=false，保留歷史記錄
    """
    db_recipe = RecipeService.soft_delete_recipe(db, recipe_id)
    if not db_recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="食譜不存在"
        )


# ============================================================
# 食譜步驟 API
# ============================================================

@router.get("/recipes/{recipe_id}/steps", response_model=RecipeStepsVersionResponse)
def get_recipe_steps(
    recipe_id: int,
    version: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """
    取得食譜步驟
    - version=None：取得最新版本
    - version=N：取得特定版本
    """
    db_recipe = RecipeService.get_recipe(db, recipe_id, include_inactive=True)
    if not db_recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="食譜不存在"
        )

    steps = RecipeService.get_recipe_steps(db, recipe_id, version)
    if not steps:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"步驟版本不存在"
        )

    # 取得目前版本號
    current_version = steps[0].version if steps else None

    return {
        "recipe_id": recipe_id,
        "recipe_name": db_recipe.recipe_name,
        "version": current_version,
        "steps": steps,
        "is_current": version is None or version == current_version,
        "created_at": steps[0].created_at if steps else None
    }


@router.post("/recipes/{recipe_id}/steps", status_code=status.HTTP_201_CREATED)
def add_recipe_steps_version(
    recipe_id: int,
    steps_data: List[RecipeStepCreate],
    db: Session = Depends(get_db)
):
    """
    新增食譜步驟新版本
    - 自動將新版本標記為當前版本
    - 舊版本保留在歷史中
    """
    if not steps_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="必須至少提供一個步驟"
        )

    new_version = RecipeService.add_recipe_steps_version(db, recipe_id, steps_data)
    if new_version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="食譜不存在"
        )

    return {
        "success": True,
        "recipe_id": recipe_id,
        "new_version": new_version
    }


@router.put("/recipes/{recipe_id}/steps/{version}/set-current", status_code=status.HTTP_200_OK)
def set_recipe_steps_as_current(
    recipe_id: int,
    version: int,
    db: Session = Depends(get_db)
):
    """
    設定食譜步驟某個版本為當前版本
    """
    success = RecipeService.set_recipe_steps_as_current(db, recipe_id, version)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"步驟版本 {version} 不存在"
        )

    return {
        "success": True,
        "recipe_id": recipe_id,
        "current_version": version
    }


# ============================================================
# 食譜營養素 API
# ============================================================

@router.get("/recipes/{recipe_id}/nutrition", response_model=RecipeNutritionResponse)
def get_recipe_nutrition(
    recipe_id: int,
    db: Session = Depends(get_db)
):
    """取得食譜營養素資訊"""
    db_recipe = RecipeService.get_recipe(db, recipe_id, include_inactive=True)
    if not db_recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="食譜不存在"
        )

    if not db_recipe.nutrition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="營養素資訊不存在（可能是新建食譜）"
        )

    return db_recipe.nutrition


@router.post("/recipes/{recipe_id}/calculate-nutrition", response_model=NutritionCalculationResult)
def recalculate_recipe_nutrition(
    recipe_id: int,
    db: Session = Depends(get_db)
):
    """
    手動觸發營養素計算
    - 通常在編輯食材後調用
    """
    db_recipe = RecipeService.get_recipe(db, recipe_id, include_inactive=True)
    if not db_recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="食譜不存在"
        )

    nutrition = RecipeService.calculate_nutrition(db, recipe_id)
    if not nutrition:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="營養素計算失敗"
        )

    return {
        "recipe_id": recipe_id,
        "recipe_name": db_recipe.recipe_name,
        "base_weight_g": db_recipe.base_weight_g,
        "total_calories_kcal": nutrition.total_calories_kcal,
        "protein_g": nutrition.protein_g,
        "carbs_g": nutrition.carbs_g,
        "fat_g": nutrition.fat_g,
        "fiber_g": nutrition.fiber_g,
        "calculated_at": nutrition.calculated_at
    }


# ============================================================
# 購買地點管理 API
# ============================================================

@router.post("/purchase-locations", response_model=PurchaseLocationResponse, status_code=status.HTTP_201_CREATED)
def create_purchase_location(
    location_data: PurchaseLocationCreate,
    db: Session = Depends(get_db)
):
    """建立購買地點"""
    existing = db.query(PurchaseLocation).filter(
        PurchaseLocation.location_name == location_data.location_name
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"購買地點 '{location_data.location_name}' 已存在"
        )

    db_location = PurchaseLocation(**location_data.dict())
    db.add(db_location)
    db.commit()
    db.refresh(db_location)
    return db_location


@router.get("/purchase-locations/{location_id}", response_model=PurchaseLocationResponse)
def get_purchase_location(
    location_id: int,
    db: Session = Depends(get_db)
):
    """取得單一購買地點"""
    db_location = db.query(PurchaseLocation).filter(
        PurchaseLocation.id == location_id
    ).first()
    if not db_location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="購買地點不存在"
        )
    return db_location


@router.get("/purchase-locations", response_model=List[PurchaseLocationResponse])
def list_purchase_locations(
    db: Session = Depends(get_db)
):
    """列表所有購買地點"""
    return db.query(PurchaseLocation).filter(
        PurchaseLocation.is_active == True
    ).order_by(PurchaseLocation.priority_order).all()


@router.put("/purchase-locations/{location_id}", response_model=PurchaseLocationResponse)
def update_purchase_location(
    location_id: int,
    location_data: PurchaseLocationUpdate,
    db: Session = Depends(get_db)
):
    """更新購買地點"""
    db_location = db.query(PurchaseLocation).filter(
        PurchaseLocation.id == location_id
    ).first()
    if not db_location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="購買地點不存在"
        )

    update_data = location_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_location, key, value)

    db.commit()
    db.refresh(db_location)
    return db_location


@router.delete("/purchase-locations/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_purchase_location(
    location_id: int,
    db: Session = Depends(get_db)
):
    """軟刪除購買地點"""
    db_location = db.query(PurchaseLocation).filter(
        PurchaseLocation.id == location_id
    ).first()
    if not db_location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="購買地點不存在"
        )

    db_location.is_active = False
    db.commit()


# ============================================================
# API 統計和健康檢查
# ============================================================

@router.get("/health/block4")
def health_check():
    """區塊 4 健康檢查"""
    return {
        "status": "ok",
        "block": "BLOCK_4_食譜和食材管理",
        "endpoints": {
            "ingredients": 8,
            "recipes": 8,
            "purchase_locations": 5
        },
        "total_endpoints": 21
    }
