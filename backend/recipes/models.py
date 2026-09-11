"""食材庫、食材庫存、食譜（含步驟版本控制、營養素）"""

from sqlalchemy import Column, Integer, String, Float, Boolean, Date, DateTime, ForeignKey, UniqueConstraint, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from database import Base


class IngredientLibrary(Base):
    __tablename__ = "ingredient_library"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ingredient_name = Column(String(255), nullable=False, unique=True)
    category = Column(String(50), nullable=False)
    unit = Column(String(20), default="g")
    calories_per_100g = Column(Float, nullable=True)
    protein_per_100g = Column(Float, nullable=True)
    carbs_per_100g = Column(Float, nullable=True)
    fat_per_100g = Column(Float, nullable=True)
    fiber_per_100g = Column(Float, nullable=True)
    preferred_purchase_location = Column(String(255), nullable=True)
    needs_stock_tracking = Column(Boolean, default=False)
    # 盛產季節（春/夏/秋/冬，逗號分隔可跨季），只有蔬菜水果這類有明顯產季的才會填；
    # null/空字串＝不分季節（穀物、肉類、調味料、乳製品等常年都能買），選餐時不受季節限制
    season = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    stock = relationship("IngredientStock", uselist=False, cascade="all, delete-orphan")


class IngredientStock(Base):
    __tablename__ = "ingredient_stock"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ingredient_id = Column(Integer, ForeignKey("ingredient_library.id"), nullable=False, unique=True)
    current_quantity_g = Column(Float, default=0)
    min_threshold_g = Column(Float, nullable=True)
    unit = Column(String(20), default="g")
    last_purchased_at = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)


class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    recipe_name = Column(String(255), nullable=False, unique=True)
    category = Column(String(50), nullable=False)
    base_weight_g = Column(Integer, nullable=False)
    cost_level = Column(String(20), nullable=False)
    is_active = Column(Boolean, default=True)
    is_vegetarian = Column(Boolean, default=False)
    allergen_tags = Column(String(255), default="")
    carb_source = Column(String(20), nullable=True)  # 主食類的碳水來源（飯/麵/其他），供候選1主食輪替規則使用
    # 主食/肉/菜/湯的搭配風格（家常/西式），供選餐演算法判斷這道菜跟當餐主食搭不搭（見 selection_algorithm.py）；
    # 早餐/下午茶不涉及跨類別搭配，留 null
    pairing_style = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    ingredients = relationship("RecipeIngredient", cascade="all, delete-orphan")
    steps = relationship("RecipeStep", cascade="all, delete-orphan")
    nutrition = relationship("RecipeNutrition", uselist=False, cascade="all, delete-orphan")


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    ingredient_id = Column(Integer, ForeignKey("ingredient_library.id"), nullable=False)
    quantity_g = Column(Float, nullable=False)
    unit = Column(String(20), default="g")
    notes = Column(Text, nullable=True)

    ingredient = relationship("IngredientLibrary")


class RecipeStep(Base):
    __tablename__ = "recipe_steps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    version = Column(Integer, nullable=False)
    step_number = Column(Integer, nullable=False)
    step_description = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_current = Column(Boolean, default=False)

    __table_args__ = (UniqueConstraint("recipe_id", "version", "step_number", name="uq_recipe_version_step"),)


class RecipeNutrition(Base):
    __tablename__ = "recipe_nutrition"

    id = Column(Integer, primary_key=True, autoincrement=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False, unique=True)
    total_calories_kcal = Column(Float, nullable=True)
    protein_g = Column(Float, nullable=True)
    carbs_g = Column(Float, nullable=True)
    fat_g = Column(Float, nullable=True)
    fiber_g = Column(Float, nullable=True)
    calculated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
