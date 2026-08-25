"""
Block 2: 用戶管理 - 業務邏輯服務
================================================

包含用戶相關的所有業務邏輯
"""

from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime

from app.models.users import User
from app.schemas.users import UserCreate, UserUpdate


class UserService:
    """用戶服務"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_user(self, user_data: UserCreate) -> User:
        """
        創建新用戶
        
        參數:
        - user_data: 用戶數據
        
        返回:
        - User: 創建的用戶對象
        """
        db_user = User(**user_data.model_dump())
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user
    
    def get_all_users(self, skip: int = 0, limit: int = 10) -> List[User]:
        """
        獲取所有用戶
        
        參數:
        - skip: 跳過的記錄數
        - limit: 返回的最大記錄數
        
        返回:
        - List[User]: 用戶列表
        """
        return self.db.query(User).order_by(desc(User.created_at)).offset(skip).limit(limit).all()
    
    def get_user(self, user_id: int) -> Optional[User]:
        """
        獲取特定用戶
        
        參數:
        - user_id: 用戶 ID
        
        返回:
        - User: 用戶對象或 None
        """
        return self.db.query(User).filter(User.id == user_id).first()
    
    def update_user(self, user_id: int, user_data: UserUpdate) -> Optional[User]:
        """
        更新用戶信息
        
        參數:
        - user_id: 用戶 ID
        - user_data: 更新的用戶數據
        
        返回:
        - User: 更新後的用戶對象或 None
        """
        db_user = self.get_user(user_id)
        if not db_user:
            return None
        
        # 更新只有非空的字段
        update_data = user_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_user, field, value)
        
        db_user.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(db_user)
        return db_user
    
    def delete_user(self, user_id: int) -> bool:
        """
        刪除用戶
        
        參數:
        - user_id: 用戶 ID
        
        返回:
        - bool: 是否刪除成功
        """
        db_user = self.get_user(user_id)
        if not db_user:
            return False
        
        self.db.delete(db_user)
        self.db.commit()
        return True
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """
        通過電郵獲取用戶
        
        參數:
        - email: 電郵地址
        
        返回:
        - User: 用戶對象或 None
        """
        return self.db.query(User).filter(User.email == email).first()
