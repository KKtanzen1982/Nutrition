"""
數據庫配置 - Postgres 和 SQLAlchemy
================================================

包含：
- Postgres 連接配置（連線字串來自環境變數 DATABASE_URL，見 .env）
- Session 工廠
- 依賴注入
"""

import os
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session

load_dotenv()

# 數據庫 URL
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")
if not SQLALCHEMY_DATABASE_URL:
    raise RuntimeError(
        "沒有設定 DATABASE_URL 環境變數。請在 backend/.env 裡設定，"
        "格式參考 backend/.env.example（Supabase 的 Postgres 連線字串）。"
    )

# 創建引擎
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=False  # 設置為 True 以查看 SQL 日誌
)

# 創建 SessionLocal
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 創建 Base 類
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    """
    依賴注入函數，用於獲取數據庫 Session

    使用方法:
        def my_endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
