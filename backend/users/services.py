from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional, Dict

from users.models import User, DietaryPreference


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
