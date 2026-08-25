"""
BLOCK_5 測試用資料庫連線
========================

僅供本地測試 BLOCK_5 使用，獨立於 BLOCK_1/2/3/4 的資料庫檔案
（比照 BLOCK_4/extracted/test_db.py 的做法）。
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "block5_test.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def new_session() -> Session:
    """給背景任務用：不透過 FastAPI Depends，直接開一個新 session。"""
    return SessionLocal()
