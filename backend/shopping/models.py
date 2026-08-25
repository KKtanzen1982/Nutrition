"""購買地點、食材地點偏好、購物清單"""

from sqlalchemy import Column, Integer, String, Float, Boolean, Date, DateTime, ForeignKey, UniqueConstraint, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from database import Base


class PurchaseLocation(Base):
    __tablename__ = "purchase_locations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    location_name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    priority_order = Column(Integer, default=99)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class IngredientLocationPreference(Base):
    __tablename__ = "ingredient_location_preference"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ingredient_id = Column(Integer, ForeignKey("ingredient_library.id"), nullable=False, index=True)
    preferred_location_id = Column(Integer, ForeignKey("purchase_locations.id"), nullable=False)
    priority = Column(Integer, default=1)
    notes = Column(Text, nullable=True)

    location = relationship("PurchaseLocation")

    __table_args__ = (
        UniqueConstraint("ingredient_id", "priority", name="uq_ingredient_priority"),
    )


class ShoppingList(Base):
    __tablename__ = "shopping_list"

    id = Column(Integer, primary_key=True, autoincrement=True)
    list_date = Column(Date, nullable=False)
    week_start_date = Column(Date, nullable=False, index=True)
    created_from_plan_id = Column(Integer, ForeignKey("weekly_meal_plan.id"), nullable=True)
    status = Column(String(20), default="草稿")
    total_items = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = Column(Text, nullable=True)

    items = relationship("ShoppingListItem", cascade="all, delete-orphan")


class ShoppingListItem(Base):
    __tablename__ = "shopping_list_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    shopping_list_id = Column(Integer, ForeignKey("shopping_list.id"), nullable=False, index=True)
    ingredient_id = Column(Integer, ForeignKey("ingredient_library.id"), nullable=False, index=True)
    quantity_needed_g = Column(Float, nullable=False)
    unit = Column(String(20), default="g")
    purchase_location_id = Column(Integer, ForeignKey("purchase_locations.id"), nullable=True)
    cost_level = Column(String(10), nullable=True)
    needs_restocking = Column(Boolean, default=False)
    assigned_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)
    is_purchased = Column(Boolean, default=False)
    purchased_at = Column(DateTime, nullable=True)


class ShoppingListHistory(Base):
    __tablename__ = "shopping_list_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    shopping_list_id = Column(Integer, ForeignKey("shopping_list.id"), nullable=False, index=True)
    original_item_id = Column(Integer, nullable=True)
    item_changes = Column(Text, nullable=True)
    status_log = Column(Text, nullable=True)
    archived_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, nullable=True)
