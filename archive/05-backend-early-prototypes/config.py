"""
應用配置文件
================================================

包含所有應用級別的配置參數
"""

from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """應用設置"""
    
    # 應用信息
    APP_NAME: str = "飲食管理系統"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # 數據庫
    DATABASE_URL: str = "sqlite:///nutrition.db"
    
    # 服務器
    SERVER_HOST: str = "127.0.0.1"
    SERVER_PORT: int = 8000
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
