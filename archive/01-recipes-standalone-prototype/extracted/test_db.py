"""
BLOCK_4 測試用資料庫連線
========================

僅供本地測試 BLOCK_4 使用，獨立於 BLOCK_1/BLOCK_2 的資料庫檔案。
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typing import Generator
from sqlalchemy.orm import Session
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "block4_test.db")
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
