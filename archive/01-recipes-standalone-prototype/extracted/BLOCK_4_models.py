"""
BLOCK_4: 食譜和食材管理 - SQLAlchemy ORM 模型
================================================

包含：
- 食譜管理（表 5a、5b、5c、5d）
- 食材管理（表 5i、5e）
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey, Date, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

# 假設已有 Base（來自區塊 1）
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


# ============================================================
# 食譜相關模型
# ============================================================

class Recipe(Base):
    """表 5a: 食譜庫"""
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True)
    recipe_name = Column(String(255), nullable=False, unique=True)
    category = Column(String(50), nullable=False)  # '早餐' / '主食' / '肉' / '菜' / '飲料' / '點心'
    base_weight_g = Column(Integer, nullable=False)  # 基準重量（克）
    cost_level = Column(String(20), nullable=False)  # '低' / '中' / '高'
    is_active = Column(Boolean, default=True)  # 軟刪除標記
    created_at = Column(DateTime, default=func.now())
    last_updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # 關聯
    ingredients = relationship("RecipeIngredient", back_populates="recipe", cascade="all, delete-orphan")
    steps = relationship("RecipeStep", back_populates="recipe", cascade="all, delete-orphan")
    nutrition = relationship("RecipeNutrition", back_populates="recipe", cascade="all, delete-orphan", uselist=False)

    def __repr__(self):
        return f"<Recipe {self.recipe_name}>"


class RecipeIngredient(Base):
    """表 5b: 食譜食材明細"""
    __tablename__ = "recipe_ingredients"

    id = Column(Integer, primary_key=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    ingredient_id = Column(Integer, ForeignKey("ingredient_library.id"), nullable=False)
    quantity_g = Column(Float, nullable=False)  # 數量（克）
    unit = Column(String(20), default="g")  # 'g' / 'ml' / '顆' / '把'
    notes = Column(Text)

    # 關聯
    recipe = relationship("Recipe", back_populates="ingredients")
    ingredient = relationship("IngredientLibrary", back_populates="recipe_usages")

    def __repr__(self):
        return f"<RecipeIngredient recipe_id={self.recipe_id} ingredient_id={self.ingredient_id}>"


class RecipeStep(Base):
    """表 5c: 製作步驟 - 版本控制"""
    __tablename__ = "recipe_steps"

    id = Column(Integer, primary_key=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    version = Column(Integer, nullable=False)  # 版本號（1, 2, 3...）
    step_number = Column(Integer, nullable=False)  # 步驟序號（1, 2, 3...）
    step_description = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now())
    is_current = Column(Boolean, default=False)  # 標記為最新版本

    # 關聯
    recipe = relationship("Recipe", back_populates="steps")

    # 複合唯一約束：同一食譜同一版本同一步驟號
    __table_args__ = (UniqueConstraint("recipe_id", "version", "step_number", name="uq_recipe_version_step"),)

    def __repr__(self):
        return f"<RecipeStep recipe_id={self.recipe_id} v{self.version} step{self.step_number}>"


class RecipeNutrition(Base):
    """表 5d: 營養素資訊 - 自動計算"""
    __tablename__ = "recipe_nutrition"

    id = Column(Integer, primary_key=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False, unique=True)
    total_calories_kcal = Column(Float)  # 總熱量（kcal）
    protein_g = Column(Float)  # 蛋白質（g）
    carbs_g = Column(Float)  # 碳水化合物（g）
    fat_g = Column(Float)  # 脂肪（g）
    fiber_g = Column(Float)  # 膳食纖維（g）
    calculated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # 關聯
    recipe = relationship("Recipe", back_populates="nutrition")

    def __repr__(self):
        return f"<RecipeNutrition recipe_id={self.recipe_id} calories={self.total_calories_kcal}>"


# ============================================================
# 食材相關模型
# ============================================================

class IngredientLibrary(Base):
    """表 5i: 食材庫"""
    __tablename__ = "ingredient_library"

    id = Column(Integer, primary_key=True)
    ingredient_name = Column(String(255), nullable=False, unique=True)
    category = Column(String(50), nullable=False)  # '蔬菜' / '肉類' / '穀物' / '乳製品' / '調味料' / '其他'
    unit = Column(String(20), default="g")  # '克' / 'ml' / '顆'
    calories_per_100g = Column(Float)  # 每 100g 熱量
    protein_per_100g = Column(Float)  # 每 100g 蛋白質
    carbs_per_100g = Column(Float)  # 每 100g 碳水化合物
    fat_per_100g = Column(Float)  # 每 100g 脂肪
    fiber_per_100g = Column(Float)  # 每 100g 膳食纖維
    preferred_purchase_location = Column(String(255))  # 偏好購買地點
    needs_stock_tracking = Column(Boolean, default=False)  # 是否需要追蹤庫存
    created_at = Column(DateTime, default=func.now())

    # 關聯
    stock = relationship("IngredientStock", back_populates="ingredient", cascade="all, delete-orphan", uselist=False)
    recipe_usages = relationship("RecipeIngredient", back_populates="ingredient")

    def __repr__(self):
        return f"<IngredientLibrary {self.ingredient_name}>"


class IngredientStock(Base):
    """表 5e: 食材庫存"""
    __tablename__ = "ingredient_stock"

    id = Column(Integer, primary_key=True)
    ingredient_id = Column(Integer, ForeignKey("ingredient_library.id"), nullable=False, unique=True)
    current_quantity_g = Column(Float, default=0)  # 目前數量（克）
    min_threshold_g = Column(Float)  # 警告閾值（克）
    unit = Column(String(20), default="g")
    last_purchased_at = Column(Date)  # 最後購買日期
    notes = Column(Text)

    # 關聯
    ingredient = relationship("IngredientLibrary", back_populates="stock")

    def __repr__(self):
        return f"<IngredientStock ingredient_id={self.ingredient_id} qty={self.current_quantity_g}g>"


# ============================================================
# 購買地點相關模型（用於購物清單）
# ============================================================

class PurchaseLocation(Base):
    """表 6a: 購買地點庫"""
    __tablename__ = "purchase_locations"

    id = Column(Integer, primary_key=True)
    location_name = Column(String(255), nullable=False, unique=True)
    description = Column(Text)
    priority_order = Column(Integer, default=0)  # 優先順序
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())

    # 關聯
    ingredient_preferences = relationship("IngredientLocationPreference", back_populates="location")

    def __repr__(self):
        return f"<PurchaseLocation {self.location_name}>"


class IngredientLocationPreference(Base):
    """表 6b: 食材地點偏好"""
    __tablename__ = "ingredient_location_preference"

    id = Column(Integer, primary_key=True)
    ingredient_id = Column(Integer, ForeignKey("ingredient_library.id"), nullable=False)
    preferred_location_id = Column(Integer, ForeignKey("purchase_locations.id"), nullable=False)
    priority = Column(Integer, default=1)  # 1=最優先, 2=次優先, 3=備選
    notes = Column(Text)

    # 關聯
    ingredient = relationship("IngredientLibrary")
    location = relationship("PurchaseLocation", back_populates="ingredient_preferences")

    def __repr__(self):
        return f"<IngredientLocationPreference ingredient_id={self.ingredient_id} location_id={self.preferred_location_id}>"
