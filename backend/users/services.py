from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional, Dict

from users.models import User, DietaryPreference, WeightGoal


class UserService:
    """用戶服務"""

    def create_user(self, db: Session, user_data) -> User:
        user = User(**user_data.model_dump(), is_active=True)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def get_all_users(self, db: Session, skip: int = 0, limit: int = 10) -> List[User]:
        return db.query(User).offset(skip).limit(limit).all()

    def get_user(self, db: Session, user_id: int) -> Optional[User]:
        return db.get(User, user_id)

    def update_user(self, db: Session, user_id: int, user_data) -> Optional[User]:
        user = db.get(User, user_id)
        if not user:
            return None
        for k, v in user_data.model_dump(exclude_unset=True).items():
            setattr(user, k, v)
        user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
        return user

    def delete_user(self, db: Session, user_id: int) -> bool:
        user = db.get(User, user_id)
        if not user:
            return False
        db.delete(user)
        db.commit()
        return True


user_service = UserService()


class DietaryPreferenceService:
    def get(self, db: Session, user_id: int) -> Dict:
        row = db.query(DietaryPreference).filter(DietaryPreference.user_id == user_id).first()
        if not row:
            return {"user_id": user_id, "allergies": None, "restrictions": None, "preferences": None}
        return {"user_id": row.user_id, "allergies": row.allergies, "restrictions": row.restrictions, "preferences": row.preferences}

    def set(self, db: Session, user_id: int, data) -> Dict:
        row = db.query(DietaryPreference).filter(DietaryPreference.user_id == user_id).first()
        update_data = data.model_dump(exclude_unset=True)
        if row:
            for k, v in update_data.items():
                setattr(row, k, v)
        else:
            row = DietaryPreference(user_id=user_id, **update_data)
            db.add(row)
        db.commit()
        return self.get(db, user_id)


dietary_preference_service = DietaryPreferenceService()


class WeightGoalService:
    """減脂的目標體重＋目標日期。get_row 給 nutrition_calc 內部用（要原始 ORM 物件方便寫回快取值），
    get/set 給 API 層用（回傳 dict）。"""

    def get_row(self, db: Session, user_id: int) -> Optional[WeightGoal]:
        return db.query(WeightGoal).filter(WeightGoal.user_id == user_id).first()

    def _to_dict(self, row: Optional[WeightGoal], user_id: int) -> Dict:
        if not row:
            return {
                "user_id": user_id, "target_weight_kg": None, "target_date": None,
                "active_daily_deficit_kcal": None, "deficit_calculated_at": None, "deficit_calculated_weight_kg": None,
            }
        return {
            "user_id": row.user_id, "target_weight_kg": row.target_weight_kg, "target_date": row.target_date,
            "active_daily_deficit_kcal": row.active_daily_deficit_kcal,
            "deficit_calculated_at": row.deficit_calculated_at, "deficit_calculated_weight_kg": row.deficit_calculated_weight_kg,
        }

    def get(self, db: Session, user_id: int) -> Dict:
        return self._to_dict(self.get_row(db, user_id), user_id)

    def set(self, db: Session, user_id: int, data) -> Dict:
        row = self.get_row(db, user_id)
        update_data = data.model_dump(exclude_unset=True)
        if row:
            for k, v in update_data.items():
                setattr(row, k, v)
        else:
            row = WeightGoal(user_id=user_id, **update_data)
            db.add(row)
        # 目標改變了，舊的赤字快取失去意義，強制下次重新計算
        row.active_daily_deficit_kcal = None
        row.deficit_calculated_at = None
        row.deficit_calculated_weight_kg = None
        db.commit()
        return self.get(db, user_id)

    def record_deficit(self, db: Session, row: WeightGoal, deficit_kcal: float, calculated_at, weight_kg: float) -> None:
        row.active_daily_deficit_kcal = deficit_kcal
        row.deficit_calculated_at = calculated_at
        row.deficit_calculated_weight_kg = weight_kg
        db.commit()


weight_goal_service = WeightGoalService()
