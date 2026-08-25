"""
Block 2: 用戶管理 - 業務邏輯服務
"""

from datetime import datetime
from typing import List, Optional

# 模擬數據存儲
users_db = {}
next_user_id = 1

class UserService:
    """用戶服務"""
    
    def __init__(self, db = None):
        self.db = db
    
    def create_user(self, user_data):
        """創建新用戶"""
        global next_user_id
        user_id = next_user_id
        user = {
            "id": user_id,
            **user_data.model_dump(),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "is_active": True
        }
        users_db[user_id] = user
        next_user_id += 1
        return user
    
    def get_all_users(self, skip: int = 0, limit: int = 10):
        """獲取所有用戶"""
        users_list = list(users_db.values())
        return sorted(users_list, key=lambda x: x['id'], reverse=True)[skip:skip + limit]
    
    def get_user(self, user_id: int) -> Optional[dict]:
        """獲取特定用戶"""
        return users_db.get(user_id)
    
    def update_user(self, user_id: int, user_data):
        """更新用戶"""
        if user_id not in users_db:
            return None
        
        update_data = user_data.model_dump(exclude_unset=True)
        users_db[user_id].update(update_data)
        users_db[user_id]["updated_at"] = datetime.utcnow().isoformat()
        return users_db[user_id]
    
    def delete_user(self, user_id: int):
        """刪除用戶"""
        if user_id not in users_db:
            return False
        del users_db[user_id]
        return True
    
    def get_user_by_email(self, email: str) -> Optional[dict]:
        """通過電郵獲取用戶"""
        for user in users_db.values():
            if user.get("email") == email:
                return user
        return None
