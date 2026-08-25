"""
BLOCK_6: SQLAlchemy ORM 模型 - 獨立測試資料庫

這個模組跟 BLOCK_2/BLOCK_3/BLOCK_4/BLOCK_5 一樣，使用自己的 Base，
讓 BLOCK_6 的購物清單邏輯有一個真實、可持久化的資料庫可以測試，
不需要等待跨區塊的資料庫整合。

模型分成兩類：

1. 本區塊真正擁有（表 6a ~ 6e，架構文件「區塊 6：購物清單管理」的交付內容）：
   PurchaseLocation, IngredientLocationPreference,
   ShoppingList, ShoppingListItem, ShoppingListHistory

2. 唯讀參照（借用區塊 1/4/5 的表結構簡化版，僅供本區塊獨立測試查詢用，
   本區塊不宣稱擁有這些表的 DDL 所有權，正式整合時應改用區塊 1/4/5
   實際建立的資料表 —— 詳見 BLOCK_6_INTEGRATION_GUIDE.md）：
   User, Recipe, RecipeIngredient(表 5b), IngredientLibrary(表 5i),
   IngredientStock(表 5e), WeeklyMealPlan(表 5f), DailyMealDetail(表 5g)
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Text, Date, DateTime, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


# ==================== 唯讀參照：用戶（借用區塊 2 表 1 簡化版） ====================

class User(Base):
    """表 1 精簡版：僅供標示 assigned_user_id / 週計畫的 A、B 使用者"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)


# ==================== 唯讀參照：食譜 / 食材（借用區塊 4 表 5a/5b/5i/5e 簡化版） ====================

class Recipe(Base):
    """表 5a 精簡版：只保留計算購物清單所需的欄位"""
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True)
    recipe_name = Column(String(255), nullable=False, unique=True)
    base_weight_g = Column(Integer, nullable=False)
    cost_level = Column(String(10), nullable=False)  # '低' / '中' / '高'
    is_active = Column(Boolean, default=True)

    ingredients = relationship("RecipeIngredient", back_populates="recipe")


class IngredientLibrary(Base):
    """表 5i 精簡版：食材庫"""
    __tablename__ = "ingredient_library"

    id = Column(Integer, primary_key=True)
    ingredient_name = Column(String(255), nullable=False, unique=True)
    category = Column(String(50), nullable=False)  # '蔬菜' / '肉類' / '穀物' / '乳製品' / '調味料' / '其他'
    unit = Column(String(20), default="g")
    preferred_purchase_location = Column(String(100), nullable=True)  # 文字備援欄位，優先度低於表 6b
    needs_stock_tracking = Column(Boolean, default=False)


class RecipeIngredient(Base):
    """表 5b 精簡版：食譜食材明細（quantity_g 對應 Recipe.base_weight_g 這個基準份量）"""
    __tablename__ = "recipe_ingredients"

    id = Column(Integer, primary_key=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False, index=True)
    ingredient_id = Column(Integer, ForeignKey("ingredient_library.id"), nullable=False, index=True)
    quantity_g = Column(Float, nullable=False)
    unit = Column(String(20), default="g")

    recipe = relationship("Recipe", back_populates="ingredients")
    ingredient = relationship("IngredientLibrary")


class IngredientStock(Base):
    """表 5e 精簡版：食材庫存，用來判斷需補購標記"""
    __tablename__ = "ingredient_stock"

    id = Column(Integer, primary_key=True)
    ingredient_id = Column(Integer, ForeignKey("ingredient_library.id"), nullable=False, unique=True)
    current_quantity_g = Column(Float, default=0)
    min_threshold_g = Column(Float, default=0)


# ==================== 唯讀參照：週計畫（借用區塊 5 表 5f/5g 簡化版） ====================

class WeeklyMealPlan(Base):
    """表 5f 精簡版：週菜單安排，購物清單從這裡的 plan_id 觸發生成"""
    __tablename__ = "weekly_meal_plan"

    id = Column(Integer, primary_key=True)
    plan_date = Column(Date, nullable=False)  # 週一的日期
    user_id_a = Column(Integer, ForeignKey("users.id"), nullable=False)
    user_id_b = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan_status = Column(String(20), default="草稿")  # '草稿' / '待微調' / '已確認'


class DailyMealDetail(Base):
    """表 5g 精簡版：日菜單詳情，購物清單的用量來源"""
    __tablename__ = "daily_meal_detail"

    id = Column(Integer, primary_key=True)
    meal_plan_id = Column(Integer, ForeignKey("weekly_meal_plan.id"), nullable=False, index=True)
    meal_date = Column(Date, nullable=False, index=True)
    meal_type = Column(String(20), nullable=False)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    assigned_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    serving_weight_g = Column(Float, nullable=True)


# ==================== 本區塊擁有：購買地點與偏好（表 6a、6b） ====================

class PurchaseLocation(Base):
    """表 6a：購買地點庫"""
    __tablename__ = "purchase_locations"

    id = Column(Integer, primary_key=True)
    location_name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    priority_order = Column(Integer, default=99)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<PurchaseLocation {self.location_name}>"


class IngredientLocationPreference(Base):
    """表 6b：食材地點偏好"""
    __tablename__ = "ingredient_location_preference"

    id = Column(Integer, primary_key=True)
    ingredient_id = Column(Integer, ForeignKey("ingredient_library.id"), nullable=False, index=True)
    preferred_location_id = Column(Integer, ForeignKey("purchase_locations.id"), nullable=False)
    priority = Column(Integer, default=1)  # 1=最優先, 2=次優先, 3=備選
    notes = Column(Text, nullable=True)

    location = relationship("PurchaseLocation")

    __table_args__ = (
        UniqueConstraint("ingredient_id", "priority", name="uq_ingredient_priority"),
    )


# ==================== 本區塊擁有：購物清單（表 6c、6d、6e） ====================

class ShoppingList(Base):
    """表 6c：購物清單主表"""
    __tablename__ = "shopping_list"

    id = Column(Integer, primary_key=True)
    list_date = Column(Date, nullable=False)
    week_start_date = Column(Date, nullable=False, index=True)
    created_from_plan_id = Column(Integer, ForeignKey("weekly_meal_plan.id"), nullable=True)
    status = Column(String(20), default="草稿")  # '草稿' / '已確認' / '採購中' / '已採購' / '歸檔'
    total_items = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = Column(Text, nullable=True)

    items = relationship("ShoppingListItem", back_populates="shopping_list", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ShoppingList(id={self.id}, status={self.status})>"


class ShoppingListItem(Base):
    """表 6d：購物項目明細"""
    __tablename__ = "shopping_list_items"

    id = Column(Integer, primary_key=True)
    shopping_list_id = Column(Integer, ForeignKey("shopping_list.id"), nullable=False, index=True)
    ingredient_id = Column(Integer, ForeignKey("ingredient_library.id"), nullable=False, index=True)
    quantity_needed_g = Column(Float, nullable=False)
    unit = Column(String(20), default="g")
    purchase_location_id = Column(Integer, ForeignKey("purchase_locations.id"), nullable=True)
    cost_level = Column(String(10), nullable=True)  # '低' / '中' / '高'
    needs_restocking = Column(Boolean, default=False)
    assigned_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # NULL = 兩人共用
    notes = Column(Text, nullable=True)
    is_purchased = Column(Boolean, default=False)
    purchased_at = Column(DateTime, nullable=True)

    shopping_list = relationship("ShoppingList", back_populates="items")
    ingredient = relationship("IngredientLibrary")
    purchase_location = relationship("PurchaseLocation")


class ShoppingListHistory(Base):
    """表 6e：採購歷史（歸檔快照）"""
    __tablename__ = "shopping_list_history"

    id = Column(Integer, primary_key=True)
    shopping_list_id = Column(Integer, ForeignKey("shopping_list.id"), nullable=False, index=True)
    original_item_id = Column(Integer, nullable=True)
    item_changes = Column(Text, nullable=True)  # JSON 格式字串
    status_log = Column(Text, nullable=True)  # JSON 格式字串
    archived_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, nullable=True)
